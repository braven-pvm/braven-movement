"""One definition of the catch solve, shared by every script that needs it.

Three scripts used to rebuild this loop separately. They drifted, and a
checkpoint added in one place was missing in another. The solve lives here now.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

from motion_track import arm_length, hand_targets_from_track, load_motion
from segment_measures import (
    elbow_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
    trunk_lean_degrees,
)

# MHR is Y up, so vertical is the second axis.
WORLD_UP = (0.0, 1.0, 0.0)

SPIKE_DIR = Path(__file__).resolve().parent
ASSET_FOLDER = SPIKE_DIR / "mhr-assets" / "assets"
MOTION_PATH = SPIKE_DIR / "movements" / "netball_two_hand_catch.motion.json"
LEVEL_OF_DETAIL = 3

# The movement is data now. These read from the motion file so that editing the
# keys is the only thing needed to change the movement.
_TRACK = load_motion(MOTION_PATH)
FRAME_COUNT = _TRACK.frames
FRAMES_PER_SECOND = _TRACK.frames_per_second
CONTACT_PHASE = _TRACK.contact_phase()

# Pose parameters only. The legs are included because the manual coaches this
# drill from a wide base power position, which the knees have to produce.
WANTED = (
    "root", "spine", "clavicle", "uparm", "lowarm", "elbow", "wrist",
    "neck", "head", "upleg", "lowleg", "knee", "foot", "ankle",
)
# Shape parameters must never move, or the solver stretches the athlete.
FORBIDDEN = ("scale", "flexible")

# The manual keeps the feet static: "Worker is static with feet, in power
# position ready to move but use hands & arms to pull in ball." Pinning the feet
# and lowering the hips is what produces a power position. Locking the root
# instead leaves the athlete standing straight-legged and lets the torso lean.
FOOT_WEIGHT = 12.0
# The trunk is held firmly, because a drifting trunk lets the athlete cheat every
# hand target by moving her chest instead of her hands.
TRUNK_WEIGHT = 10.0
# The elbow pole only has to break the tie, so it is weak enough that it never
# fights the wrist target. Elbows sit below and slightly outside the line from
# the shoulder to the hand, which is where a netball catch puts them.
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


def hand_targets(
    track,
    phase: float,
    chest: np.ndarray,
    arm_length_cm: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return both hand targets at this phase, read from the motion keys."""
    return hand_targets_from_track(track, phase, chest, arm_length_cm)


def measure_frame(points: np.ndarray, index: dict[str, int], phase: float) -> dict:
    def point(name: str) -> tuple[float, float, float]:
        return tuple(float(v) for v in points[index[name]])  # type: ignore[return-value]

    entry: dict[str, float] = {"phase": round(phase, 4)}
    # How far the trunk has left upright. A drifting trunk is how an athlete, or
    # a solver, fakes a hand position without moving the hands.
    entry["trunkLeanDegrees"] = round(
        trunk_lean_degrees(pelvis=point("root"), neck=point("c_neck"), up=WORLD_UP),
        2,
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


def solve_catch(character: geometry.Character) -> dict:
    """Solve every frame of the catch and measure each one.

    Returns the motion parameters, the joint positions per frame, the
    measurements per frame, and how far each hand missed its target.
    """
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
    rest_root = rest_positions[index["root"]].copy()
    reach_cm = arm_length(rest_positions, index)
    track = _TRACK

    # The power position lowers the whole body, so the trunk landmarks drop with
    # the hips. These are where the trunk must stay for the whole movement.
    drop = np.array([0.0, track.hip_drop_fraction * reach_cm, 0.0])
    root_target = rest_root - drop
    chest_target = rest_positions[index["c_spine3"]].copy() - drop
    neck_target = rest_positions[index["c_neck"]].copy() - drop

    # The hand keys are measured from the chest, so they must be measured from
    # where the chest is held, not from where it started. Anchoring them to the
    # rest chest let the athlete satisfy a target by leaning her trunk backwards,
    # which pulled her chest away from the ball instead of the ball to her chest.
    hand_anchor = chest_target

    motion = np.zeros((FRAME_COUNT, count), dtype=np.float32)
    points_per_frame: list[np.ndarray] = []
    measurements: list[dict] = []
    misses: list[float] = []

    previous = rest.copy()
    for frame in range(FRAME_COUNT):
        phase = frame / (FRAME_COUNT - 1)
        left_target, right_target = hand_targets(
            track, phase, hand_anchor, reach_cm
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
        # picks a different answer for each arm and the two elbows disagree even
        # though the targets are mirrored. The original Blender generator carried
        # arm_poles in its configuration for exactly this reason.
        for side, target, sign in (
            ("l", left_target, 1.0),
            ("r", right_target, -1.0),
        ):
            shoulder = rest_positions[index[f"{side}_uparm"]] - drop
            midpoint = (shoulder + np.asarray(target)) / 2.0
            pole = midpoint + np.array(
                [sign * ELBOW_POLE_OUT_CM, -ELBOW_POLE_DOWN_CM, 0.0]
            )
            position_error.add_constraint(
                index[f"{side}_lowarm"],
                target=np.asarray(pole, dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=ELBOW_POLE_WEIGHT,
            )
        # Feet stay planted and the hips sit lower than standing. Together those
        # two facts are the power position.
        for foot in ("l_foot", "r_foot"):
            position_error.add_constraint(
                index[foot],
                target=np.asarray(rest_positions[index[foot]], dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=FOOT_WEIGHT,
            )
        # The trunk is held, not just the hips. The manual is explicit that the
        # hands and arms do the work: "use hands & arms to pull in ball". Holding
        # the hips alone still let the pelvis tilt back and take the chest with
        # it, so the ball never actually came to the chest.
        for joint, target, weight in (
            ("root", root_target, TRUNK_WEIGHT),
            ("c_spine3", chest_target, TRUNK_WEIGHT),
            ("c_neck", neck_target, TRUNK_WEIGHT * 0.6),
        ):
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
                solver2.LimitErrorFunction(character, weight=5.0),
                continuity,
            ],
        )
        solver = solver2.GaussNewtonSolver(function, options)
        solver.set_enabled_parameters(enabled)
        solved = np.asarray(
            solver.solve(previous.reshape(-1, 1)), dtype=np.float32
        ).reshape(-1)
        if frame == 0:
            # The first frame starts from the rest pose, which is far from the
            # answer, and a half-converged first frame biases every frame after
            # it through the continuity term. Solving it twice settles it.
            solved = np.asarray(
                solver.solve(solved.reshape(-1, 1)), dtype=np.float32
            ).reshape(-1)
        if not np.all(np.isfinite(solved)):
            solved = previous.copy()
        motion[frame] = solved
        previous = solved

        points = joint_positions(character, solved)
        # A left hand that has travelled to the right of the right hand means a
        # left and right mix-up upstream, not a pose worth measuring. This
        # repository has produced that class of defect twice, so it is checked
        # rather than trusted.
        separation = float(
            points[index["l_wrist"]][0] - points[index["r_wrist"]][0]
        )
        if separation <= 0.0:
            raise SolveError(
                f"frame {frame}: the hands have crossed, left minus right is "
                f"{separation:.1f} cm. MHR places the left side at positive X."
            )
        points_per_frame.append(points)
        measurements.append(measure_frame(points, index, phase))
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
