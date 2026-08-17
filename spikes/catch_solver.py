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

from segment_measures import (
    elbow_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
)

ASSET_FOLDER = Path(__file__).resolve().parent / "mhr-assets" / "assets"
LEVEL_OF_DETAIL = 3
FRAME_COUNT = 24
FRAMES_PER_SECOND = 24.0
CONTACT_PHASE = 0.55

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
POWER_POSITION_DROP_CM = 9.0
FOOT_WEIGHT = 12.0


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
    rest_left: np.ndarray,
    rest_right: np.ndarray,
    phase: float,
    chest: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return where both hands should be at this phase of the catch.

    The shape comes from the manual: react to the front, in front of the
    shoulder, snatch with two hands, then pull the ball in to the chest. The
    arms extend to nearly full reach at contact and only then fold.
    """
    if phase <= CONTACT_PHASE:
        reach = 0.5 - 0.5 * math.cos(math.pi * phase / CONTACT_PHASE)
        pull_in = 0.0
    else:
        reach = 1.0
        pull_in = 0.5 - 0.5 * math.cos(
            math.pi * (phase - CONTACT_PHASE) / (1.0 - CONTACT_PHASE)
        )

    extension = np.array([0.0, 30.0, 52.0], dtype=np.float32)
    left = rest_left + extension * reach
    right = rest_right + extension * reach
    left[0] -= 22.0 * reach
    right[0] += 22.0 * reach

    if pull_in > 0.0:
        chest_left = chest + np.array([-11.0, -6.0, 9.0], dtype=np.float32)
        chest_right = chest + np.array([11.0, -6.0, 9.0], dtype=np.float32)
        left = left + (chest_left - left) * pull_in
        right = right + (chest_right - right) * pull_in
    return left, right


def measure_frame(points: np.ndarray, index: dict[str, int], phase: float) -> dict:
    def point(name: str) -> tuple[float, float, float]:
        return tuple(float(v) for v in points[index[name]])  # type: ignore[return-value]

    entry: dict[str, float] = {"phase": round(phase, 4)}
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
    rest_left = rest_positions[index["l_wrist"]].copy()
    rest_right = rest_positions[index["r_wrist"]].copy()
    rest_chest = rest_positions[index["c_spine3"]].copy()
    rest_root = rest_positions[index["root"]].copy()

    motion = np.zeros((FRAME_COUNT, count), dtype=np.float32)
    points_per_frame: list[np.ndarray] = []
    measurements: list[dict] = []
    misses: list[float] = []

    previous = rest.copy()
    for frame in range(FRAME_COUNT):
        phase = frame / (FRAME_COUNT - 1)
        left_target, right_target = hand_targets(
            rest_left, rest_right, phase, rest_chest
        )

        position_error = solver2.PositionErrorFunction(character, weight=1.0)
        for joint, target in (("l_wrist", left_target), ("r_wrist", right_target)):
            position_error.add_constraint(
                index[joint],
                target=np.asarray(target, dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=1.0,
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
        position_error.add_constraint(
            index["root"],
            target=np.asarray(
                rest_root - np.array([0.0, POWER_POSITION_DROP_CM, 0.0]),
                dtype=np.float32,
            ),
            offset=np.zeros(3, dtype=np.float32),
            weight=3.0,
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
        if not np.all(np.isfinite(solved)):
            solved = previous.copy()
        motion[frame] = solved
        previous = solved

        points = joint_positions(character, solved)
        points_per_frame.append(points)
        measurements.append(measure_frame(points, index, phase))
        misses.append(float(np.linalg.norm(points[index["l_wrist"]] - left_target)))

    return {
        "index": index,
        "enabled": enabled,
        "motion": motion,
        "points": points_per_frame,
        "measurements": measurements,
        "misses": misses,
    }
