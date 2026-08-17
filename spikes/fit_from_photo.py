"""Entry point A, end to end, on a real photograph.

A detector finds 2D landmarks in the image. The solver fits the MHR athlete to
those pixels with joint limits active and body proportions locked. The result is
a pose taken from a real athlete rather than one I authored.

The output records the honest limit: this is one camera, so spike H measured a
worst angle error of 9.71 degrees even with a perfect detector. The pose is a
starting point for a coach to correct. It is not a measurement.

    pixi run python fit_from_photo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from catch_solver import (  # noqa: E402
    FORBIDDEN,
    WANTED,
    joint_positions,
    load_character,
)
from segment_measures import (  # noqa: E402
    elbow_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
)

PHOTO = (
    SPIKE_DIR.parent
    / "references"
    / "202526 updated coaches manual"
    / "_page_71_Picture_13.jpeg"
)

# MediaPipe pose landmark indices, mapped to MHR joints. Only the landmarks a
# detector reports reliably are used. No fingertips, no synthesised points.
LANDMARK_TO_JOINT = {
    0: "c_head",
    11: "l_uparm",
    12: "r_uparm",
    13: "l_lowarm",
    14: "r_lowarm",
    15: "l_wrist",
    16: "r_wrist",
    23: "l_upleg",
    24: "r_upleg",
    25: "l_lowleg",
    26: "r_lowleg",
    27: "l_foot",
    28: "r_foot",
}
# MediaPipe reports a visibility score. Below this the landmark is guesswork and
# would drag the fit toward a joint the camera never saw.
MINIMUM_VISIBILITY = 0.6


DETECTOR_MODEL = SPIKE_DIR / "mhr-assets" / "detector" / "pose_landmarker_heavy.task"


def detect_landmarks(image_path: Path) -> tuple[dict[int, tuple[float, float]], int, int]:
    """Return the detected pixel landmarks, plus the image size.

    MediaPipe 1.0 removed the old ``solutions`` API, so this uses the Tasks API
    with the heavy pose landmarker. Heavy is the most accurate of the three, and
    spike H showed the detector budget is tight.
    """
    import mediapipe as mp  # noqa: PLC0415
    from mediapipe.tasks import python as mp_python  # noqa: PLC0415
    from mediapipe.tasks.python import vision  # noqa: PLC0415

    if not DETECTOR_MODEL.is_file():
        raise SystemExit(f"detector model not found: {DETECTOR_MODEL}")

    image = mp.Image.create_from_file(str(image_path))
    width, height = image.width, image.height

    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(DETECTOR_MODEL)),
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
    )
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        result = landmarker.detect(image)

    if not result.pose_landmarks:
        raise SystemExit("the detector found no person in the photograph")

    found: dict[int, tuple[float, float]] = {}
    for number, landmark in enumerate(result.pose_landmarks[0]):
        if number not in LANDMARK_TO_JOINT:
            continue
        if getattr(landmark, "visibility", 1.0) < MINIMUM_VISIBILITY:
            continue
        found[number] = (landmark.x * width, landmark.y * height)
    return found, width, height


def guess_camera(width: int, height: int) -> np.ndarray:
    """Return a plausible projection for an unknown phone camera.

    A photograph carries no calibration. A 50 mm equivalent lens on a 36 mm
    sensor is a reasonable stand-in, and the solver recovers the athlete's
    position and orientation, so the guess only has to be close.
    """
    focal = 50.0 / 36.0 * width
    intrinsics = np.array(
        [[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]]
    )
    # The athlete stands in front of the camera, three metres away, upright.
    rotation = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    translation = np.array([0.0, -150.0, 300.0])
    extrinsics = np.concatenate([rotation, translation.reshape(3, 1)], axis=1)
    return (intrinsics @ extrinsics).astype(np.float32)


def main() -> int:
    if not PHOTO.is_file():
        raise SystemExit(f"photograph not found: {PHOTO}")

    found, width, height = detect_landmarks(PHOTO)
    print(f"photograph: {PHOTO.name}  {width} by {height}")
    print(f"landmarks detected above visibility {MINIMUM_VISIBILITY}: {len(found)}")
    for number in sorted(found):
        print(f"  {LANDMARK_TO_JOINT[number]:10s} at {found[number][0]:7.1f}, {found[number][1]:7.1f}")

    if len(found) < 6:
        raise SystemExit("too few visible landmarks to fit a pose")

    character = load_character()
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

    projection = guess_camera(width, height)
    error_function = solver2.ProjectionErrorFunction(character, weight=1.0)
    used = []
    for number, pixel in found.items():
        joint = LANDMARK_TO_JOINT[number]
        if joint not in index:
            continue
        error_function.add_constraint(
            projection, np.asarray(pixel, dtype=np.float32), index[joint], None, 1.0
        )
        used.append(joint)

    prior = solver2.ModelParametersErrorFunction(character)
    prior.weight = 0.004
    function = solver2.SkeletonSolverFunction(
        character,
        [error_function, solver2.LimitErrorFunction(character, weight=5.0), prior],
    )
    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 60
    options.min_iterations = 6
    solver = solver2.GaussNewtonSolver(function, options)
    solver.set_enabled_parameters(enabled)

    rest = np.zeros(count, dtype=np.float32)
    solved = np.asarray(solver.solve(rest.reshape(-1, 1)), dtype=np.float32).reshape(-1)
    if not np.all(np.isfinite(solved)):
        raise SystemExit("the solver produced non-finite parameters")

    points = joint_positions(character, solved)

    def reproject(position: np.ndarray) -> tuple[float, float]:
        homogeneous = projection.astype(np.float64) @ np.array([*position, 1.0])
        return (homogeneous[0] / homogeneous[2], homogeneous[1] / homogeneous[2])

    errors = {}
    for number, pixel in found.items():
        joint = LANDMARK_TO_JOINT[number]
        got = reproject(points[index[joint]])
        errors[joint] = round(
            float(np.hypot(got[0] - pixel[0], got[1] - pixel[1])), 1
        )

    def point(name: str) -> tuple[float, float, float]:
        return tuple(float(v) for v in points[index[name]])  # type: ignore[return-value]

    measured = {}
    for side, prefix in (("l", "left"), ("r", "right")):
        measured[f"{prefix}ElbowFlexionDegrees"] = round(
            elbow_flexion_degrees(
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
                wrist=point(f"{side}_wrist"),
            ),
            1,
        )
        measured[f"{prefix}ShoulderElevationDegrees"] = round(
            shoulder_elevation_degrees(
                pelvis=point("root"),
                neck=point("c_neck"),
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
            ),
            1,
        )
        measured[f"{prefix}KneeFlexionDegrees"] = round(
            knee_flexion_degrees(
                hip=point(f"{side}_upleg"),
                knee=point(f"{side}_lowleg"),
                ankle=point(f"{side}_foot"),
            ),
            1,
        )

    print(f"\nreprojection error per landmark, pixels: {errors}")
    print(f"worst: {max(errors.values()):.1f} px on a {width} px wide frame")
    print(f"\nangles read from the fitted pose: {measured}")
    print(
        "\nONE CAMERA. Spike H measured a 9.71 degree worst error from a single"
        "\nview with a perfect detector, which is past the 5 degree clinical"
        "\nthreshold. These angles initialise a pose for a coach to correct."
        "\nThey are not a measurement."
    )

    output = SPIKE_DIR / "poc-output" / "photo_fit.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "photograph": PHOTO.name,
                "framePx": [width, height],
                "detector": "MediaPipe Pose, model_complexity 2",
                "minimumVisibility": MINIMUM_VISIBILITY,
                "landmarksUsed": used,
                "detectedPixels": {
                    LANDMARK_TO_JOINT[n]: [round(v, 1) for v in p]
                    for n, p in found.items()
                },
                "reprojectionErrorPx": errors,
                "worstReprojectionErrorPx": max(errors.values()),
                "cameraAssumed": "50 mm equivalent, 3 m, upright, uncalibrated",
                "angles": measured,
                "measurementValid": False,
                "measurementNote": (
                    "One camera. Worst angle error measured at 9.71 degrees with a "
                    "perfect detector, past the 5 degree clinical threshold. Use as "
                    "a starting pose, never as a measurement."
                ),
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
