"""Solve any movement in the library, not one hard-coded catch.

The solver used to load a single motion file at import time, so adding a skill
meant editing the engine. It now takes a movement and returns the solve, and the
library is just a folder of movements.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

from motion_track import (
    MotionTrack,
    arm_length,
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
# Joint limits have to outrank every target, or the solver pays the penalty and
# bends a joint past where a person bends. At weight 5 the whole library solved
# outside its limits, worst error 70.98 on the high deflect. At 200 the worst is
# 0.005, and the hands reach their targets slightly better rather than worse.
LIMIT_WEIGHT = 200.0
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


def solve(character: geometry.Character, track: MotionTrack) -> dict:
    """Solve every frame of this movement and measure each one."""
    names = list(character.skeleton.joint_names)
    index = {name: position for position, name in enumerate(names)}
    count = character.parameter_transform.size
    enabled = enabled_parameters(character)

    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 30
    options.min_iterations = 4

    rest = np.zeros(count, dtype=np.float32)
    rest_positions = joint_positions(character, rest)
    reach_cm = arm_length(rest_positions, index)

    # The stance can change during a movement. A steady drill holds one hip
    # drop, while a jump loads, rises and lands, so it is read per frame.
    rest_root = rest_positions[index["root"]].copy()
    rest_chest = rest_positions[index["c_spine3"]].copy()
    rest_neck = rest_positions[index["c_neck"]].copy()
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
        drop = np.array([0.0, track.hip_drop_at(phase) * reach_cm, 0.0])
        # A footwork drill moves the hips through space. A planted drill leaves
        # these at zero and behaves exactly as before.
        across_cm, ahead_cm = track.root_offset_at(phase)
        travel = np.array([across_cm * reach_cm, 0.0, ahead_cm * reach_cm])
        # A turn rotates the trunk about the vertical axis through the hips. The
        # feet stay planted, so the turn has to come from the trunk itself.
        rotation = turn_matrix(track.turn_at(phase))
        root_target = rest_root - drop + travel

        def turned(rest_point: np.ndarray) -> np.ndarray:
            return root_target + rotation @ (rest_point - rest_root)

        # turned() is measured from the dropped root, so the drop is already in
        # it. Subtracting it again sinks the whole trunk twice.
        chest_target = turned(rest_chest)
        neck_target = turned(rest_neck)
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
        placements = track.feet_at(phase)
        if placements is None:
            foot_targets = {
                "l_foot": rest_positions[index["l_foot"]],
                "r_foot": rest_positions[index["r_foot"]],
            }
        else:
            ground = float(rest_positions[index["l_foot"]][1])
            foot_targets = {}
            for joint, placement, sign in (
                ("l_foot", placements[0], 1.0),
                ("r_foot", placements[1], -1.0),
            ):
                local = np.array(
                    [
                        sign * placement.across * reach_cm,
                        0.0,
                        placement.ahead * reach_cm,
                    ]
                )
                point = root_target + rotation @ local
                # Height is measured from the ground, not from the hips, so a
                # planted foot stays on the floor however the hips move.
                point[1] = ground + placement.up * reach_cm
                foot_targets[joint] = point
        for joint, target in foot_targets.items():
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
        scapula_targets = {}
        trunk_down = root_target - neck_target
        trunk_length = float(np.linalg.norm(trunk_down))
        if trunk_length > 1e-6:
            trunk_down = trunk_down / trunk_length
            for side, hand_target in (("l", left_target), ("r", right_target)):
                base = shoulder_targets[side]
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
                # Rotate the shoulder about the chest, in the plane the arm is
                # reaching through. That is the direction a scapula travels.
                pivot = neck_target
                arm = base - pivot
                axis = np.cross(arm, reach)
                axis_length = float(np.linalg.norm(axis))
                if axis_length < 1e-6:
                    continue
                axis = axis / axis_length
                angle = math.radians(contribution)
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                rotated = (
                    arm * cos_a
                    + np.cross(axis, arm) * sin_a
                    + axis * float(np.dot(axis, arm)) * (1.0 - cos_a)
                )
                scapula_targets[side] = pivot + rotated
        turn_now = abs(track.turn_at(phase))
        base = FOOTWORK_SHOULDER_WEIGHT if track.moves_feet() else SHOULDER_BASE_WEIGHT
        shoulder_weight = base + SHOULDER_LINE_WEIGHT * min(
            1.0, turn_now / SHOULDER_LINE_FULL_AT_DEGREES
        )
        for joint, target, weight in (
            ("root", root_target, TRUNK_WEIGHT),
            ("c_spine3", chest_target, TRUNK_WEIGHT),
            ("c_neck", neck_target, TRUNK_WEIGHT * 0.6),
            ("l_uparm", scapula_targets.get("l", shoulder_targets["l"]),
             max(shoulder_weight, SCAPULA_WEIGHT)),
            ("r_uparm", scapula_targets.get("r", shoulder_targets["r"]),
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


def solve_movement(character: geometry.Character, movement_id: str) -> dict:
    return solve(character, load_motion(motion_path(movement_id)))
