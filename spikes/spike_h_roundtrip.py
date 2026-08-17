"""Spike H: how accurate must a 2D detector be? A round trip answers it.

Entry point A takes an image. A detector finds 2D landmarks. The solver fits the
athlete to those pixels. The question nobody can answer from a real photograph is
how much of the final error came from the detector, because the true pose of a
photographed person is unknown.

A round trip removes that problem. Pose the athlete to a known truth. Project the
joints to pixels with a known camera. Add detector noise of a known size. Fit
from rest using only those pixels. Compare the recovered joint angles against the
truth angles that produced them.

The output is a detector budget in pixels, which is what you shop for.

    pixi run python spike_h_roundtrip.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from segment_measures import (  # noqa: E402
    elbow_flexion_degrees,
    shoulder_elevation_degrees,
)
from spike_f_movement import (  # noqa: E402
    ASSET_FOLDER,
    FORBIDDEN,
    LEVEL_OF_DETAIL,
    WANTED,
    hand_targets,
    joint_positions,
)

# A landmark set a 2D detector actually produces. No fingertips, because no
# detector is reliable there, and no synthesised points.
OBSERVED = (
    "c_head",
    "c_neck",
    "l_uparm",
    "l_lowarm",
    "l_wrist",
    "r_uparm",
    "r_lowarm",
    "r_wrist",
    "root",
    "l_upleg",
    "l_lowleg",
    "l_foot",
    "r_upleg",
    "r_lowleg",
    "r_foot",
)

FRAME = (1080, 1350)
NOISE_LEVELS_PX = (0.0, 1.0, 2.0, 5.0, 10.0, 20.0)
SAMPLES = 12
SEED = 20260817


def build_camera(centre: np.ndarray, offset: np.ndarray) -> np.ndarray:
    """A camera three metres away, looking at the athlete's chest."""
    up = np.array([0.0, 1.0, 0.0])
    location = centre + offset
    forward = centre - location
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    down = np.cross(forward, right)
    rotation = np.stack([right, down, forward], axis=0)
    translation = -rotation @ location
    width, height = FRAME
    focal = 50.0 / 36.0 * width
    intrinsics = np.array(
        [[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]]
    )
    return (intrinsics @ np.concatenate([rotation, translation.reshape(3, 1)], axis=1)).astype(
        np.float32
    )


def project_all(projection: np.ndarray, points: np.ndarray) -> np.ndarray:
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    image = homogeneous @ projection.astype(np.float64).T
    return image[:, :2] / image[:, 2:3]


def measure(points: np.ndarray, index: dict[str, int]) -> dict[str, float]:
    def point(name: str) -> tuple[float, float, float]:
        return tuple(float(v) for v in points[index[name]])  # type: ignore[return-value]

    result = {}
    for side, prefix in (("l", "left"), ("r", "right")):
        result[f"{prefix}Elbow"] = elbow_flexion_degrees(
            shoulder=point(f"{side}_uparm"),
            elbow=point(f"{side}_lowarm"),
            wrist=point(f"{side}_wrist"),
        )
        result[f"{prefix}Shoulder"] = shoulder_elevation_degrees(
            pelvis=point("root"),
            neck=point("c_neck"),
            shoulder=point(f"{side}_uparm"),
            elbow=point(f"{side}_lowarm"),
        )
    return result


def main() -> int:
    character = geometry.Character.load_fbx(
        str(ASSET_FOLDER / f"lod{LEVEL_OF_DETAIL}.fbx"),
        str(ASSET_FOLDER / "compact_v6_1.model"),
        load_blendshapes=False,
    )
    names = list(character.skeleton.joint_names)
    index = {name: position for position, name in enumerate(names)}
    parameter_names = list(character.parameter_transform.names)
    count = character.parameter_transform.size
    enabled = np.array(
        [
            any(key in name for key in WANTED)
            and not any(key in name for key in FORBIDDEN)
            for name in parameter_names
        ],
        dtype=bool,
    )

    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 40
    options.min_iterations = 5

    rest = np.zeros(count, dtype=np.float32)
    rest_positions = joint_positions(character, rest)

    # Build a truth pose: the catch at contact, solved the same way the movement
    # spike solves it.
    left_target, right_target = hand_targets(
        rest_positions[index["l_wrist"]].copy(),
        rest_positions[index["r_wrist"]].copy(),
        0.55,
    )
    truth_error = solver2.PositionErrorFunction(character, weight=1.0)
    for joint, target in (("l_wrist", left_target), ("r_wrist", right_target)):
        truth_error.add_constraint(
            index[joint],
            target=np.asarray(target, dtype=np.float32),
            offset=np.zeros(3, dtype=np.float32),
            weight=1.0,
        )
    truth_function = solver2.SkeletonSolverFunction(
        character, [truth_error, solver2.LimitErrorFunction(character, weight=5.0)]
    )
    truth_solver = solver2.GaussNewtonSolver(truth_function, options)
    truth_solver.set_enabled_parameters(enabled)
    truth_parameters = np.asarray(
        truth_solver.solve(rest.reshape(-1, 1)), dtype=np.float32
    ).reshape(-1)

    truth_positions = joint_positions(character, truth_parameters)
    truth_angles = measure(truth_positions, index)

    observed_indices = [index[name] for name in OBSERVED]
    centre = truth_positions[index["c_neck"]]
    # One camera in front, and a second turned about 70 degrees around the
    # athlete. Two viewpoints remove the depth ambiguity that one cannot.
    views = {
        "one camera": [np.array([90.0, 25.0, 300.0])],
        "two cameras": [
            np.array([90.0, 25.0, 300.0]),
            np.array([-290.0, 25.0, 105.0]),
        ],
    }

    print("Truth pose:")
    for name, value in truth_angles.items():
        print(f"  {name:15s} {value:7.2f} degrees")
    print()
    report = []
    for view_name, offsets in views.items():
        projections = [build_camera(centre, offset) for offset in offsets]
        clean = [
            project_all(projection, truth_positions[observed_indices])
            for projection in projections
        ]

        print(f"\nRecovery with {view_name}")
        print(
            f"{'detector noise':>15} {'mean angle error':>18} {'worst angle error':>19}"
        )

        for noise_px in NOISE_LEVELS_PX:
            generator = random.Random(SEED)
            means, worsts = [], []
            repeats = 1 if noise_px == 0.0 else SAMPLES
            for _ in range(repeats):
                error_function = solver2.ProjectionErrorFunction(character, weight=1.0)
                for projection, pixels_clean in zip(projections, clean):
                    pixels = pixels_clean.copy()
                    if noise_px > 0.0:
                        pixels += np.array(
                            [
                                [
                                    generator.gauss(0.0, noise_px),
                                    generator.gauss(0.0, noise_px),
                                ]
                                for _ in range(len(pixels))
                            ]
                        )
                    for joint_index, pixel in zip(observed_indices, pixels):
                        error_function.add_constraint(
                            projection,
                            np.asarray(pixel, dtype=np.float32),
                            joint_index,
                            None,
                            1.0,
                        )
                prior = solver2.ModelParametersErrorFunction(character)
                prior.weight = 0.002
                function = solver2.SkeletonSolverFunction(
                    character,
                    [
                        error_function,
                        solver2.LimitErrorFunction(character, weight=5.0),
                        prior,
                    ],
                )
                solver = solver2.GaussNewtonSolver(function, options)
                solver.set_enabled_parameters(enabled)
                recovered = np.asarray(
                    solver.solve(rest.reshape(-1, 1)), dtype=np.float32
                ).reshape(-1)
                if not np.all(np.isfinite(recovered)):
                    continue
                angles = measure(joint_positions(character, recovered), index)
                differences = [
                    abs(angles[key] - truth_angles[key]) for key in truth_angles
                ]
                means.append(sum(differences) / len(differences))
                worsts.append(max(differences))

            if not means:
                print(f"{noise_px:12.0f} px    solver failed")
                continue
            mean_error = sum(means) / len(means)
            worst_error = max(worsts)
            report.append(
                {
                    "view": view_name,
                    "noisePx": noise_px,
                    "meanAngleErrorDegrees": round(mean_error, 2),
                    "worstAngleErrorDegrees": round(worst_error, 2),
                    "withinFiveDegrees": bool(worst_error <= 5.0),
                }
            )
            print(f"{noise_px:12.0f} px {mean_error:15.2f} deg {worst_error:16.2f} deg")

    output = SPIKE_DIR / "poc-output" / "braven_roundtrip.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "truthAngles": {k: round(v, 2) for k, v in truth_angles.items()},
                "landmarks": list(OBSERVED),
                "framePx": list(FRAME),
                "recovery": report,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nreceipt: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
