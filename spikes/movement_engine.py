"""Solve any movement in the library, not one hard-coded catch.

The solver used to load a single motion file at import time, so adding a skill
meant editing the engine. It now takes a movement and returns the solve, and the
library is just a folder of movements.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

from motion_track import (
    MotionTrack,
    arm_length,
    leg_length,
    hand_targets_from_track,
    load_motion,
    turn_matrix,
)
from segment_measures import (
    elbow_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
    trunk_lean_degrees,
)

SPIKE_DIR = Path(__file__).resolve().parent
ASSET_FOLDER = SPIKE_DIR / "mhr-assets" / "assets"
MOVEMENT_DIR = SPIKE_DIR / "movements"
LEVEL_OF_DETAIL = 3
MOTION_SUFFIX = ".motion.json"

# MHR is Y up, so vertical is the second axis.
WORLD_UP = (0.0, 1.0, 0.0)

# Pose parameters only. The legs are included because these drills are coached
# from a wide base power position, which the knees have to produce.
WANTED = (
    "root", "spine", "clavicle", "uparm", "lowarm", "elbow", "wrist",
    "neck", "head", "upleg", "lowleg", "knee", "foot", "ankle",
)
# Shape parameters must never move, or the solver stretches the athlete.
FORBIDDEN = ("scale", "flexible")

# The manual keeps the feet static. Pinning the feet and lowering the hips is
# what produces the power position.
FOOT_WEIGHT = 12.0
# How far off the ground a foot may be and still count as planted.
#
# The keys place a foot's height in leg lengths, and a planted foot is keyed at
# zero. One centimetre is slack for the interpolation between keys, and is far
# below the height of any keyed step in the library.
PLANTED_CM = 1.0
# Joint limits have to outrank every target, or the solver pays the penalty and
# bends a joint past where a person bends.
#
# 200 was chosen when the limit check reported a squared error, which made a
# hundredth of a degree look the same as six degrees. Reading the overshoot in
# degrees instead showed the collarbone sitting 4 degrees outside its range on
# every drill in the library, and 24 on the high deflect. The limit term is
# soft, so the overshoot scales with the weight: 200 gives 4.1 degrees, 4000
# gives 0.70, 20000 gives 0.157 and 30000 gives 0.09, which is a fiftieth of
# what a goniometer resolves. The library stays green at all of them and the
# palms stay on the ball to within half a millimetre.
#
# Past 30000 it starts to cost movement rather than buy anatomy. The outside
# hand hooks drill turns 45 degrees away and takes the ball one handed across
# the body, so it is already near the edge of her range, and the harder the
# limit pushes back the sharper that drill gets: its worst spike against
# neighbouring frames is 2.4 at 20000, 5.6 at 30000 and 9.0 at 60000. 30000 is
# the last weight where the limits pass and the movement is still smooth.
#
# It also fixed the footwork drill, which was pressing against its own limits
# and wandering as it came off them. Its worst spike against neighbouring
# frames fell from 9.22 to 1.08.
LIMIT_WEIGHT = 30000.0
# The wrist had a position target and nothing else, so the hand was free to spin
# about the forearm between frames. That is what threw the fingers around: the
# thumb tip moved 17.7 cm in a single frame on the jump catch while the fingers
# themselves never move, because they are frozen.
#
# Pointing the knuckles along the arm removes the spin, and it is also what the
# manual asks for: fingers up, thumbs in the middle.
HAND_WEIGHT = 2.5
HAND_LIFT = 0.25
# The trunk is held firmly, because a drifting trunk lets the athlete cheat every
# hand target by moving her chest instead of her hands.
TRUNK_WEIGHT = 10.0
# The shoulder line says which way the athlete faces, so it is held only when
# there is a turn to hold. A square drill leaves it free, because a shoulder
# naturally travels a little during a reach and pinning it folds the elbow
# instead. The weight rises with the turn and reaches full strength by 15
# degrees.
SHOULDER_LINE_WEIGHT = 6.0
SHOULDER_LINE_FULL_AT_DEGREES = 15.0
# Held at zero, deliberately, after a failed attempt at a fix.
#
# The shoulder girdle currently slides up to 28 cm forward to help a hand reach,
# which is far past the few centimetres a clavicle allows, and it is why the high
# deflect never extends its elbow. Holding the shoulder at its rest position
# instead was worse: it broke five passing drills, and pulling their reach back
# to compensate still left the hands 3 cm short at the scaling floor.
#
# The reason is that a rest target is also anatomically wrong. A shoulder blade
# rotates as the arm rises, about one degree of scapula for every two of humerus
# above thirty. The right model is travel proportional to arm elevation, not zero
# travel, and that is a real piece of engine work rather than a weight.
SHOULDER_BASE_WEIGHT = 0.0

# Scapulohumeral rhythm.
#
# Pinning the shoulder near its rest position broke every reaching drill, and
# leaving it free let it slide 28 cm forward and snap between frames. Both are
# wrong because both treat the shoulder as if it had one correct place. It does
# not. A shoulder blade rotates as the arm rises, contributing roughly one
# degree for every two of humerus above thirty, so where the shoulder belongs
# depends on how high the arm is reaching.
#
# The shoulder target is therefore computed per frame from the elevation the
# hand target asks for, and held there. Below thirty degrees it does not move at
# all, which is why the drills that already worked are unaffected.
SCAPULA_START_DEGREES = 30.0
SCAPULA_RATIO = 0.5
SCAPULA_MAX_DEGREES = 24.0
SCAPULA_WEIGHT = 4.0
# A drill that moves its feet does get a shoulder hold, for a different reason.
# Split feet twist the pelvis, and with nothing holding the shoulder line the
# trunk rotates freely and the arms swing across the body. Footwork drills do
# not reach at full stretch, so the hold costs them nothing.
FOOTWORK_SHOULDER_WEIGHT = 3.0
# The elbow pole only breaks the tie, so it never fights the wrist target.
ELBOW_POLE_WEIGHT = 0.35
ELBOW_POLE_DOWN_CM = 11.0
ELBOW_POLE_OUT_CM = 5.0


class SolveError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrunkFrame:
    """Where the trunk is at one phase, before any arm is solved.

    The hip drop, the hip travel and the trunk turn are all authored, so the
    trunk is known without solving anything. Anything measured in the athlete's
    own frame is measured from here: a hand key, a foot placement, and now a
    ball position.
    """

    root: np.ndarray
    chest: np.ndarray
    neck: np.ndarray
    shoulders: dict[str, np.ndarray]
    rotation: np.ndarray
    rest_root: np.ndarray

    def place(self, rest_point: np.ndarray) -> np.ndarray:
        """Carry a rest pose point into this frame."""
        return self.root + self.rotation @ (rest_point - self.rest_root)


def trunk_frame(
    track: MotionTrack,
    phase: float,
    rest_positions: np.ndarray,
    index: dict[str, int],
    reach_cm: float,
    turn_degrees: float | None = None,
    leg_cm: float | None = None,
) -> TrunkFrame:
    """Return the trunk placement at this phase. No solving happens here.

    The turn is read from the movement unless one is given. The possession
    model derives it from where the ball is, because turning toward a wide
    ball is something an athlete does rather than something a coach types.
    """
    rest_root = rest_positions[index["root"]]
    # Stance is measured in leg lengths. It is the legs that drop the hips and
    # carry them through space, not the arms.
    stance_cm = leg_length(rest_positions, index) if leg_cm is None else leg_cm
    drop = np.array([0.0, track.hip_drop_at(phase) * stance_cm, 0.0])
    # A footwork drill moves the hips through space. A planted drill leaves
    # these at zero and behaves exactly as before.
    across_cm, ahead_cm = track.root_offset_at(phase)
    travel = np.array([across_cm * stance_cm, 0.0, ahead_cm * stance_cm])
    # A turn rotates the trunk about the vertical axis through the hips. The
    # feet stay planted, so the turn has to come from the trunk itself.
    rotation = turn_matrix(
        track.turn_at(phase) if turn_degrees is None else turn_degrees
    )
    root = rest_root - drop + travel

    def place(rest_point: np.ndarray) -> np.ndarray:
        return root + rotation @ (rest_point - rest_root)

    return TrunkFrame(
        root=root,
        chest=place(rest_positions[index["c_spine3"]]),
        neck=place(rest_positions[index["c_neck"]]),
        shoulders={
            side: place(rest_positions[index[f"{side}_uparm"]])
            for side in ("l", "r")
        },
        rotation=rotation,
        rest_root=rest_root,
    )


def load_character() -> geometry.Character:
    return geometry.Character.load_fbx(
        str(ASSET_FOLDER / f"lod{LEVEL_OF_DETAIL}.fbx"),
        str(ASSET_FOLDER / "compact_v6_1.model"),
        load_blendshapes=False,
    )


def joint_positions(character: geometry.Character, parameters: np.ndarray) -> np.ndarray:
    state = geometry.model_parameters_to_skeleton_state(character, parameters)
    return np.asarray(state).reshape(-1, 8)[:, :3]


def enabled_parameters(character: geometry.Character) -> np.ndarray:
    names = list(character.parameter_transform.names)
    return np.array(
        [
            any(key in name for key in WANTED)
            and not any(key in name for key in FORBIDDEN)
            for name in names
        ],
        dtype=bool,
    )


def measure_frame(points: np.ndarray, index: dict[str, int], phase: float) -> dict:
    def point(name: str) -> tuple[float, float, float]:
        return tuple(float(v) for v in points[index[name]])  # type: ignore[return-value]

    entry: dict[str, float] = {"phase": round(phase, 4)}
    # A drifting trunk is how an athlete, or a solver, fakes a hand position.
    entry["trunkTurnDegrees"] = 0.0  # filled in by the caller, which knows the track
    entry["trunkLeanDegrees"] = round(
        trunk_lean_degrees(pelvis=point("root"), neck=point("c_neck"), up=WORLD_UP), 2
    )
    for side, prefix in (("l", "left"), ("r", "right")):
        entry[f"{prefix}ElbowFlexionDegrees"] = round(
            elbow_flexion_degrees(
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
                wrist=point(f"{side}_wrist"),
            ),
            2,
        )
        entry[f"{prefix}ShoulderElevationDegrees"] = round(
            shoulder_elevation_degrees(
                pelvis=point("root"),
                neck=point("c_neck"),
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
            ),
            2,
        )
        entry[f"{prefix}KneeFlexionDegrees"] = round(
            knee_flexion_degrees(
                hip=point(f"{side}_upleg"),
                knee=point(f"{side}_lowleg"),
                ankle=point(f"{side}_foot"),
            ),
            2,
        )
    return entry


def foot_targets(
    track: MotionTrack,
    phase: float,
    placed: TrunkFrame,
    rest_positions: np.ndarray,
    index: dict[str, int],
    reach_cm: float,
    leg_cm: float | None = None,
) -> dict[str, np.ndarray]:
    """Return where each foot belongs at this phase.

    A movement that keys its feet places them relative to the hips and turns
    them with the trunk. One that does not leaves them where the athlete
    started, which is what every planted drill wants.

    A planted foot also gets its ball placed, not only its ankle. An ankle on
    its own leaves the foot's pitch unobserved, and the solver held it 48 to 62
    degrees plantarflexed against a rest of 21 on every frame of every drill,
    which put the ball of the foot 3.7 to 5.2 cm through the floor. The ball is
    placed at its rest offset from the ankle, turned with the trunk, so flat
    means what the rig means by flat. A foot off the ground keeps a free pitch,
    because a foot in flight points.
    """
    placements = track.feet_at(phase)
    if placements is None:
        targets = {
            joint: rest_positions[index[joint]] for joint in ("l_foot", "r_foot")
        }
        for joint in ("l_ball", "r_ball"):
            if joint in index:
                targets[joint] = rest_positions[index[joint]]
        return targets
    # Height is measured from the ground, not from the hips, so a planted foot
    # stays on the floor however the hips move.
    ground = float(rest_positions[index["l_foot"]][1])
    stance_cm = leg_length(rest_positions, index) if leg_cm is None else leg_cm
    targets: dict[str, np.ndarray] = {}
    for joint, placement, sign in (
        ("l_foot", placements[0], 1.0),
        ("r_foot", placements[1], -1.0),
    ):
        local = np.array(
            [
                sign * placement.across * stance_cm,
                0.0,
                placement.ahead * stance_cm,
            ]
        )
        point = placed.root + placed.rotation @ local
        point[1] = ground + placement.up * stance_cm
        targets[joint] = point

        toe = joint.replace("_foot", "_ball")
        lifted = placement.up * stance_cm
        if toe in index and lifted <= PLANTED_CM:
            offset = rest_positions[index[toe]] - rest_positions[index[joint]]
            targets[toe] = point + placed.rotation @ offset
    return targets


def scapula_targets(
    placed: TrunkFrame, hand_targets: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    """Return where each shoulder belongs, given how high its arm is reaching.

    A shoulder blade rotates as the arm rises, contributing roughly one degree
    for every two of humerus above thirty. A side with no hand target, such as
    the free arm of a one hand drill, is left out and keeps its held position.
    """
    found: dict[str, np.ndarray] = {}
    trunk_down = placed.root - placed.neck
    trunk_length = float(np.linalg.norm(trunk_down))
    if trunk_length <= 1e-6:
        return found
    trunk_down = trunk_down / trunk_length
    for side, hand_target in hand_targets.items():
        base = placed.shoulders[side]
        reach = np.asarray(hand_target, dtype=np.float64) - base
        reach_length = float(np.linalg.norm(reach))
        if reach_length < 1e-6:
            continue
        cosine = float(np.dot(reach / reach_length, trunk_down))
        elevation = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
        excess = max(0.0, elevation - SCAPULA_START_DEGREES)
        contribution = min(excess * SCAPULA_RATIO, SCAPULA_MAX_DEGREES)
        if contribution <= 0.0:
            continue
        # Rotate the shoulder about the sternoclavicular joint, in the plane the
        # arm is reaching through. That is the direction a scapula travels, and
        # pivoting at the chest instead put the lever in the wrong place and
        # made the legs compensate.
        pivot = placed.neck
        arm = base - pivot
        axis = np.cross(arm, reach)
        axis_length = float(np.linalg.norm(axis))
        if axis_length < 1e-6:
            continue
        axis = axis / axis_length
        angle = math.radians(contribution)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        found[side] = pivot + (
            arm * cos_a
            + np.cross(axis, arm) * sin_a
            + axis * float(np.dot(axis, arm)) * (1.0 - cos_a)
        )
    return found


def solve(
    character: geometry.Character,
    track: MotionTrack,
    identity: np.ndarray | None = None,
) -> dict:
    """Solve every frame of this movement and measure each one.

    ``identity`` carries the athlete's size. It is a set of scale parameters,
    which are in FORBIDDEN, so the solver never moves them and the athlete
    keeps her proportions however hard a target pulls. Left out, it is the
    reference body the model ships with.
    """
    names = list(character.skeleton.joint_names)
    index = {name: position for position, name in enumerate(names)}
    count = character.parameter_transform.size
    enabled = enabled_parameters(character)

    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 30
    options.min_iterations = 4

    rest = (
        np.zeros(count, dtype=np.float32)
        if identity is None
        else np.asarray(identity, dtype=np.float32).copy()
    )
    rest_positions = joint_positions(character, rest)
    reach_cm = arm_length(rest_positions, index)

    rest_shoulders = {
        side: rest_positions[index[f"{side}_uparm"]].copy() for side in ("l", "r")
    }
    # How far the knuckles sit from the wrist on this athlete.
    palm_cm = {
        side: float(
            np.linalg.norm(
                rest_positions[index[f"{side}_middle1"]]
                - rest_positions[index[f"{side}_wrist"]]
            )
        )
        for side in ("l", "r")
    }

    frame_count = track.frames
    motion = np.zeros((frame_count, count), dtype=np.float32)
    points_per_frame: list[np.ndarray] = []
    measurements: list[dict] = []
    misses: list[float] = []

    previous = rest.copy()
    for frame in range(frame_count):
        phase = frame / (frame_count - 1)
        placed = trunk_frame(track, phase, rest_positions, index, reach_cm)
        rotation = placed.rotation
        root_target = placed.root
        turned = placed.place
        # place() is measured from the dropped root, so the drop is already in
        # it. Subtracting it again sinks the whole trunk twice.
        chest_target = placed.chest
        neck_target = placed.neck
        # Hand keys are measured from the chest, so they must be measured from
        # where the chest is held, not from where it started.
        left_target, right_target = hand_targets_from_track(
            track, phase, chest_target, reach_cm
        )

        position_error = solver2.PositionErrorFunction(character, weight=1.0)
        for joint, target in (("l_wrist", left_target), ("r_wrist", right_target)):
            position_error.add_constraint(
                index[joint],
                target=np.asarray(target, dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=1.0,
            )
        # An elbow pole. A wrist target alone leaves the elbow free to sit
        # anywhere on a circle around the shoulder-to-wrist axis, so the solver
        # picks a different answer for each arm.
        for side, target, sign in (
            ("l", left_target, 1.0),
            ("r", right_target, -1.0),
        ):
            shoulder = turned(rest_shoulders[side])
            midpoint = (shoulder + np.asarray(target)) / 2.0
            # The pole is scaled by how much slack the arm has. A hand at full
            # reach leaves the elbow nowhere to go, so a pole there only fights
            # the reach and bends an arm that should be straight. A hand held
            # close leaves the elbow free, and that is where the pole is needed.
            span = float(np.linalg.norm(np.asarray(target) - shoulder))
            slack = max(0.0, min(1.0, 1.0 - span / max(reach_cm, 1e-6)))
            pole = midpoint + slack * np.array(
                [sign * ELBOW_POLE_OUT_CM, -ELBOW_POLE_DOWN_CM, 0.0]
            )
            position_error.add_constraint(
                index[f"{side}_lowarm"],
                target=np.asarray(pole, dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=ELBOW_POLE_WEIGHT * slack,
            )
        # Point the knuckles along the arm, lifted a little, so the hand keeps a
        # stable orientation instead of spinning about the forearm between
        # frames. That spin is what threw the fingers around, and this is also
        # what the manual asks for: fingers up, thumbs in the middle.
        for side, hand_target in (("l", left_target), ("r", right_target)):
            shoulder = turned(rest_shoulders[side])
            along = np.asarray(hand_target) - shoulder
            length = float(np.linalg.norm(along))
            if length > 1e-6:
                lifted = along / length + np.array([0.0, HAND_LIFT, 0.0])
                lifted = lifted / float(np.linalg.norm(lifted))
                position_error.add_constraint(
                    index[f"{side}_middle1"],
                    target=np.asarray(
                        np.asarray(hand_target) + lifted * palm_cm[side],
                        dtype=np.float32,
                    ),
                    offset=np.zeros(3, dtype=np.float32),
                    weight=HAND_WEIGHT,
                )

        # Feet either follow the movement or stay where the athlete started.
        placed_feet = foot_targets(
            track, phase, placed, rest_positions, index, reach_cm
        )
        for joint, target in placed_feet.items():
            position_error.add_constraint(
                index[joint],
                target=np.asarray(target, dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=FOOT_WEIGHT,
            )
        # The shoulders carry the turn. Pinning the chest position alone leaves
        # the trunk free to face anywhere, so the shoulder line is what actually
        # says which way the athlete is turned.
        shoulder_targets = {
            side: turned(rest_shoulders[side]) for side in ("l", "r")
        }

        # Then let each shoulder ride up with its own arm, by the amount a
        # shoulder blade actually contributes at that elevation.
        scapula = scapula_targets(
            placed, {"l": left_target, "r": right_target}
        )
        turn_now = abs(track.turn_at(phase))
        base = FOOTWORK_SHOULDER_WEIGHT if track.moves_feet() else SHOULDER_BASE_WEIGHT
        shoulder_weight = base + SHOULDER_LINE_WEIGHT * min(
            1.0, turn_now / SHOULDER_LINE_FULL_AT_DEGREES
        )
        for joint, target, weight in (
            ("root", root_target, TRUNK_WEIGHT),
            ("c_spine3", chest_target, TRUNK_WEIGHT),
            ("c_neck", neck_target, TRUNK_WEIGHT * 0.6),
            ("l_uparm", scapula.get("l", shoulder_targets["l"]),
             max(shoulder_weight, SCAPULA_WEIGHT)),
            ("r_uparm", scapula.get("r", shoulder_targets["r"]),
             max(shoulder_weight, SCAPULA_WEIGHT)),
        ):
            if weight <= 0.0:
                continue
            position_error.add_constraint(
                index[joint],
                target=np.asarray(target, dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=weight,
            )

        continuity = solver2.ModelParametersErrorFunction(character)
        continuity.weight = 0.02

        function = solver2.SkeletonSolverFunction(
            character,
            [
                position_error,
                solver2.LimitErrorFunction(character, weight=LIMIT_WEIGHT),
                continuity,
            ],
        )
        solver = solver2.GaussNewtonSolver(function, options)
        solver.set_enabled_parameters(enabled)
        solved = np.asarray(
            solver.solve(previous.reshape(-1, 1)), dtype=np.float32
        ).reshape(-1)
        if frame == 0:
            # The first frame starts far from the answer, and a half-converged
            # first frame biases every frame after it through the continuity term.
            solved = np.asarray(
                solver.solve(solved.reshape(-1, 1)), dtype=np.float32
            ).reshape(-1)
        if not np.all(np.isfinite(solved)):
            solved = previous.copy()
        motion[frame] = solved
        previous = solved

        points = joint_positions(character, solved)
        # A left hand on the right of the right hand means a left and right
        # mix-up upstream. This repository has produced that defect twice.
        #
        # Measured along the athlete's own shoulder line, not along world X. A
        # turned drill, or a running stride that rotates the trunk, moves the
        # hands across world centre without either hand changing sides.
        shoulder_line = points[index["l_uparm"]] - points[index["r_uparm"]]
        length = float(np.linalg.norm(shoulder_line))
        if length > 1e-6:
            wrists = points[index["l_wrist"]] - points[index["r_wrist"]]
            separation = float(np.dot(wrists, shoulder_line) / length)
            if separation <= 0.0:
                raise SolveError(
                    f"{track.movement_id} frame {frame}: the hands have crossed. "
                    f"Along the shoulder line, left minus right is "
                    f"{separation:.1f} cm"
                )
        points_per_frame.append(points)
        frame_measure = measure_frame(points, index, phase)
        frame_measure["trunkTurnDegrees"] = round(track.turn_at(phase), 2)
        ground_level = float(rest_positions[index["l_foot"]][1])
        left_up = float(points[index["l_foot"]][1]) - ground_level
        right_up = float(points[index["r_foot"]][1]) - ground_level
        frame_measure["leftFootHeightCm"] = round(left_up, 2)
        frame_measure["rightFootHeightCm"] = round(right_up, 2)
        # A double foot landing means both feet arrive together. The gap between
        # their heights is what a coach is watching for.
        frame_measure["footHeightGapCm"] = round(abs(left_up - right_up), 2)
        measurements.append(frame_measure)
        misses.append(float(np.linalg.norm(points[index["l_wrist"]] - left_target)))

    return {
        "track": track,
        "index": index,
        "enabled": enabled,
        "motion": motion,
        "points": points_per_frame,
        "measurements": measurements,
        "misses": misses,
    }


def motion_path(movement_id: str) -> Path:
    return MOVEMENT_DIR / (movement_id + MOTION_SUFFIX)


def definition_path(movement_id: str) -> Path:
    return MOVEMENT_DIR / (movement_id + ".json")


def library() -> list[str]:
    """Return every movement id in the library, in a stable order."""
    return sorted(
        path.name[: -len(MOTION_SUFFIX)]
        for path in MOVEMENT_DIR.glob("*" + MOTION_SUFFIX)
    )


def solve_movement(
    character: geometry.Character,
    movement_id: str,
    identity: np.ndarray | None = None,
) -> dict:
    return solve(character, load_motion(motion_path(movement_id)), identity)
