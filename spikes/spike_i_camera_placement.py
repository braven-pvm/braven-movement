"""Spike I: where do the two cameras go, and how much does it matter?

The recovery study proved two cameras beat one. It did not say how far apart
they must stand, how high, or what happens when the athlete turns away. A shoot
costs a trip to the field, so these answers are worth having before the trip
rather than after it.

Method is the same round trip as spike H. Pose the athlete to a known truth,
project the joints a detector reports, add detector noise, fit from rest using
only pixels, and compare the recovered angles against the truth.

    pixi run python spike_i_camera_placement.py
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from catch_solver import (  # noqa: E402
    FORBIDDEN,
    WANTED,
    joint_positions,
    load_character,
    solve_catch,
)
from segment_measures import (  # noqa: E402
    elbow_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
)

# The landmarks a 2D detector actually reports. No fingertips.
OBSERVED = (
    "c_head", "c_neck", "root",
    "l_uparm", "l_lowarm", "l_wrist",
    "r_uparm", "r_lowarm", "r_wrist",
    "l_upleg", "l_lowleg", "l_foot",
    "r_upleg", "r_lowleg", "r_foot",
)

FRAME = (1080, 1920)
DISTANCE_CM = 320.0
DETECTOR_NOISE_PX = 2.0
SAMPLES = 8
SEED = 20260817
UP = np.array([0.0, 1.0, 0.0])


def camera_at(centre: np.ndarray, azimuth_degrees: float, height_cm: float) -> np.ndarray:
    """Build a camera standing at this angle around the athlete."""
    angle = math.radians(azimuth_degrees)
    location = centre + np.array(
        [DISTANCE_CM * math.sin(angle), height_cm, DISTANCE_CM * math.cos(angle)]
    )
    forward = centre - location
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, UP)
    right = right / np.linalg.norm(right)
    down = np.cross(forward, right)
    rotation = np.stack([right, down, forward], axis=0)
    translation = -rotation @ location
    width, height = FRAME
    # A phone main camera is close to a 26 mm equivalent lens.
    focal = 26.0 / 36.0 * width
    intrinsics = np.array(
        [[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]]
    )
    return (
        intrinsics @ np.concatenate([rotation, translation.reshape(3, 1)], axis=1)
    ).astype(np.float32)


def project_all(projection: np.ndarray, points: np.ndarray) -> np.ndarray:
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    image = homogeneous @ projection.astype(np.float64).T
    return image[:, :2] / image[:, 2:3]


def measure(points: np.ndarray, index: dict[str, int]) -> dict[str, float]:
    def point(name: str):
        return tuple(float(v) for v in points[index[name]])

    result = {}
    for side, prefix in (("l", "left"), ("r", "right")):
        result[f"{prefix}Elbow"] = elbow_flexion_degrees(
            shoulder=point(f"{side}_uparm"),
            elbow=point(f"{side}_lowarm"),
            wrist=point(f"{side}_wrist"),
        )
        result[f"{prefix}Shoulder"] = shoulder_elevation_degrees(
            pelvis=point("root"), neck=point("c_neck"),
            shoulder=point(f"{side}_uparm"), elbow=point(f"{side}_lowarm"),
        )
        result[f"{prefix}Knee"] = knee_flexion_degrees(
            hip=point(f"{side}_upleg"), knee=point(f"{side}_lowleg"),
            ankle=point(f"{side}_foot"),
        )
    return result


def recover(
    character, index, enabled, options, truth_points, truth_angles,
    azimuths, heights, noise_px, samples,
):
    """Fit from the given cameras and return the mean and worst angle error."""
    centre = truth_points[index["c_neck"]]
    projections = [
        camera_at(centre, azimuth, height)
        for azimuth, height in zip(azimuths, heights)
    ]
    observed = [index[name] for name in OBSERVED]
    clean = [project_all(p, truth_points[observed]) for p in projections]

    count = character.parameter_transform.size
    rest = np.zeros(count, dtype=np.float32)
    generator = random.Random(SEED)
    means, worsts = [], []
    for _ in range(1 if noise_px == 0 else samples):
        error_function = solver2.ProjectionErrorFunction(character, weight=1.0)
        for projection, pixels_clean in zip(projections, clean):
            pixels = pixels_clean.copy()
            if noise_px > 0:
                pixels += np.array(
                    [
                        [generator.gauss(0, noise_px), generator.gauss(0, noise_px)]
                        for _ in range(len(pixels))
                    ]
                )
            for joint_index, pixel in zip(observed, pixels):
                error_function.add_constraint(
                    projection, np.asarray(pixel, dtype=np.float32),
                    joint_index, None, 1.0,
                )
        prior = solver2.ModelParametersErrorFunction(character)
        prior.weight = 0.002
        function = solver2.SkeletonSolverFunction(
            character,
            [error_function, solver2.LimitErrorFunction(character, weight=5.0), prior],
        )
        solver = solver2.GaussNewtonSolver(function, options)
        solver.set_enabled_parameters(enabled)
        recovered = np.asarray(
            solver.solve(rest.reshape(-1, 1)), dtype=np.float32
        ).reshape(-1)
        if not np.all(np.isfinite(recovered)):
            continue
        angles = measure(joint_positions(character, recovered), index)
        differences = [abs(angles[k] - truth_angles[k]) for k in truth_angles]
        means.append(sum(differences) / len(differences))
        worsts.append(max(differences))
    if not means:
        return None, None
    return sum(means) / len(means), max(worsts)


def main() -> int:
    character = load_character()
    result = solve_catch(character)
    index = result["index"]
    enabled = np.array(
        [
            any(k in n for k in WANTED) and not any(k in n for k in FORBIDDEN)
            for n in character.parameter_transform.names
        ],
        dtype=bool,
    )
    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 40
    options.min_iterations = 5

    # Use the contact frame. It is the pose the coaching actually turns on.
    contact = round(0.55 * (len(result["points"]) - 1))
    truth_points = result["points"][contact]
    truth_angles = measure(truth_points, index)

    report = {"truthAngles": {k: round(v, 2) for k, v in truth_angles.items()}}

    print("Camera separation, both cameras at chest height, 2 px detector noise")
    print(f"{'separation':>12} {'mean error':>12} {'worst error':>13} {'verdict':>10}")
    separations = []
    for separation in (0, 15, 30, 45, 60, 75, 90, 120, 150, 180):
        mean, worst = recover(
            character, index, enabled, options, truth_points, truth_angles,
            azimuths=[-separation / 2, separation / 2], heights=[0.0, 0.0],
            noise_px=DETECTOR_NOISE_PX, samples=SAMPLES,
        )
        if mean is None:
            print(f"{separation:9.0f} deg    solver failed")
            continue
        verdict = "usable" if worst <= 5.0 else "no"
        separations.append(
            {"separationDegrees": separation, "meanDegrees": round(mean, 2),
             "worstDegrees": round(worst, 2), "withinFiveDegrees": worst <= 5.0}
        )
        print(
            f"{separation:9.0f} deg {mean:9.2f} deg {worst:10.2f} deg {verdict:>10}"
        )
    report["separation"] = separations

    print("\nCamera height, 90 degree separation, 2 px detector noise")
    print(f"{'height':>12} {'mean error':>12} {'worst error':>13}")
    heights = []
    for height in (-60.0, 0.0, 40.0, 80.0, 140.0):
        mean, worst = recover(
            character, index, enabled, options, truth_points, truth_angles,
            azimuths=[-45.0, 45.0], heights=[height, height],
            noise_px=DETECTOR_NOISE_PX, samples=SAMPLES,
        )
        if mean is None:
            continue
        heights.append(
            {"heightCm": height, "meanDegrees": round(mean, 2),
             "worstDegrees": round(worst, 2)}
        )
        print(f"{height:9.0f} cm {mean:9.2f} deg {worst:10.2f} deg")
    report["height"] = heights

    print("\nThree cameras against two, 2 px detector noise")
    for label, azimuths in (
        ("two at 90", [-45.0, 45.0]),
        ("three at 60", [-60.0, 0.0, 60.0]),
    ):
        mean, worst = recover(
            character, index, enabled, options, truth_points, truth_angles,
            azimuths=azimuths, heights=[0.0] * len(azimuths),
            noise_px=DETECTOR_NOISE_PX, samples=SAMPLES,
        )
        print(f"  {label:14s} mean {mean:5.2f} deg   worst {worst:5.2f} deg")
        report[label.replace(" ", "_")] = {
            "meanDegrees": round(mean, 2), "worstDegrees": round(worst, 2)
        }

    output = SPIKE_DIR / "poc-output" / "braven_camera_placement.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nreceipt: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
