"""Fit the athlete from one or more cameras, and refuse to measure when it is unsafe.

This is entry point A, ready for the field footage. Give it a capture: one or
more images of the same instant, each with a camera, and it fits the MHR athlete
to the detected landmarks with joint limits active and body proportions locked.

The part that matters is not the fit. It is the verdict. A single camera cannot
recover a pose well enough to put a number in front of a coach. The round trip
measured 49 degrees of mean angle error from one camera with a perfect detector,
against 0.04 degrees from two. So a fit that cannot be trusted is marked as such,
and the caller is expected to withhold the figures.

    pixi run python multi_camera_fit.py <capture folder>
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

# The solver is imported where it is used. The verdict below is a safety rule and
# must be testable without a solver present.
from segment_measures import (  # noqa: E402
    elbow_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
    trunk_lean_degrees,
)

WORLD_UP = np.array([0.0, 1.0, 0.0])

# Spike I measured the usable window. Below 45 degrees of separation the two
# cameras see the same thing and the fit is no better than one camera.
MINIMUM_SEPARATION_DEGREES = 45.0
# The clinical threshold for a meaningful difference.
MEANINGFUL_DEGREES = 5.0
# The uncertainty estimate is itself uncertain. With 24 samples the standard
# error on a standard deviation is about 15 percent, so an angle is only shown
# when its estimated band leaves room for that. Erring toward hiding a good
# angle is the safe direction: a withheld angle costs a coach nothing, a wrong
# one costs them trust.
UNCERTAINTY_MARGIN = 0.75
UNCERTAINTY_SAMPLES = 24


class CaptureError(ValueError):
    pass


@dataclass(frozen=True)
class Camera:
    """One camera that saw the athlete, and where it stood."""

    name: str
    azimuth_degrees: float
    height_cm: float
    distance_cm: float
    width_px: int
    height_px: int
    lens_equivalent_mm: float = 26.0

    def projection(self, centre: np.ndarray) -> np.ndarray:
        """Return the 3 by 4 world-to-image matrix for this camera.

        X right, Y down, Z along the view direction. A sweep of all four sign
        combinations confirmed this is what pymomentum expects.
        """
        angle = math.radians(self.azimuth_degrees)
        location = centre + np.array(
            [
                self.distance_cm * math.sin(angle),
                self.height_cm,
                self.distance_cm * math.cos(angle),
            ]
        )
        forward = centre - location
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, WORLD_UP)
        right = right / np.linalg.norm(right)
        down = np.cross(forward, right)
        rotation = np.stack([right, down, forward], axis=0)
        translation = -rotation @ location
        focal = self.lens_equivalent_mm / 36.0 * self.width_px
        intrinsics = np.array(
            [
                [focal, 0.0, self.width_px / 2.0],
                [0.0, focal, self.height_px / 2.0],
                [0.0, 0.0, 1.0],
            ]
        )
        return (
            intrinsics @ np.concatenate([rotation, translation.reshape(3, 1)], axis=1)
        ).astype(np.float32)


@dataclass(frozen=True)
class View:
    """What one camera saw: its placement and the landmarks detected in it."""

    camera: Camera
    landmarks: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class Verdict:
    """Whether this capture may be presented as a measurement."""

    measurement_valid: bool
    cameras: int
    separation_degrees: float
    reason: str

    def as_dict(self) -> dict:
        return {
            "measurementValid": self.measurement_valid,
            "cameras": self.cameras,
            "separationDegrees": round(self.separation_degrees, 1),
            "reason": self.reason,
            "meaningfulThresholdDegrees": MEANINGFUL_DEGREES,
        }


def judge(views: list[View]) -> Verdict:
    """Decide whether this capture can carry a number."""
    if len(views) < 2:
        return Verdict(
            measurement_valid=False,
            cameras=len(views),
            separation_degrees=0.0,
            reason=(
                "One camera cannot resolve depth. The round trip measured 49 "
                "degrees of mean angle error from one camera with a perfect "
                "detector. Show the shape, withhold the figures."
            ),
        )

    azimuths = sorted(view.camera.azimuth_degrees for view in views)
    separations = [
        abs(second - first) for first, second in zip(azimuths, azimuths[1:])
    ]
    widest = max(separations)
    if widest < MINIMUM_SEPARATION_DEGREES:
        return Verdict(
            measurement_valid=False,
            cameras=len(views),
            separation_degrees=widest,
            reason=(
                f"The cameras are {widest:.0f} degrees apart. Below "
                f"{MINIMUM_SEPARATION_DEGREES:.0f} degrees they see the same "
                "thing, and the fit is no better than a single camera."
            ),
        )
    return Verdict(
        measurement_valid=True,
        cameras=len(views),
        separation_degrees=widest,
        reason=(
            f"{len(views)} cameras {widest:.0f} degrees apart. Two views "
            "recover the pose to well inside the clinical threshold."
        ),
    )


def fit(character, views: list[View], centre: np.ndarray) -> dict:
    """Fit the athlete to every view at once."""
    import pymomentum.solver2 as solver2  # noqa: PLC0415

    from movement_engine import FORBIDDEN, WANTED, joint_positions  # noqa: PLC0415

    if not views:
        raise CaptureError("a capture needs at least one view")

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

    error_function = solver2.ProjectionErrorFunction(character, weight=1.0)
    used = 0
    for view in views:
        projection = view.camera.projection(centre)
        for joint, pixel in view.landmarks.items():
            if joint not in index:
                continue
            error_function.add_constraint(
                projection,
                np.asarray(pixel, dtype=np.float32),
                index[joint],
                None,
                1.0,
            )
            used += 1
    if used == 0:
        raise CaptureError("no detected landmark matched a joint on the athlete")

    prior = solver2.ModelParametersErrorFunction(character)
    prior.weight = 0.002
    function = solver2.SkeletonSolverFunction(
        character,
        [error_function, solver2.LimitErrorFunction(character, weight=5.0), prior],
    )
    solver = solver2.GaussNewtonSolver(function, options)
    solver.set_enabled_parameters(enabled)

    rest = np.zeros(count, dtype=np.float32)
    solved = np.asarray(solver.solve(rest.reshape(-1, 1)), dtype=np.float32).reshape(-1)
    if not np.all(np.isfinite(solved)):
        raise CaptureError("the solver did not converge on this capture")

    points = joint_positions(character, solved)
    return {"parameters": solved, "points": points, "index": index, "constraints": used}


def measure(points: np.ndarray, index: dict[str, int]) -> dict[str, float]:
    def point(name: str):
        return tuple(float(v) for v in points[index[name]])

    result = {
        "trunkLeanDegrees": round(
            trunk_lean_degrees(
                pelvis=point("root"), neck=point("c_neck"), up=tuple(WORLD_UP)
            ),
            2,
        )
    }
    for side, prefix in (("l", "left"), ("r", "right")):
        result[f"{prefix}ElbowFlexionDegrees"] = round(
            elbow_flexion_degrees(
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
                wrist=point(f"{side}_wrist"),
            ),
            2,
        )
        result[f"{prefix}ShoulderElevationDegrees"] = round(
            shoulder_elevation_degrees(
                pelvis=point("root"),
                neck=point("c_neck"),
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
            ),
            2,
        )
        result[f"{prefix}KneeFlexionDegrees"] = round(
            knee_flexion_degrees(
                hip=point(f"{side}_upleg"),
                knee=point(f"{side}_lowleg"),
                ankle=point(f"{side}_foot"),
            ),
            2,
        )
    return result


def estimate_uncertainty(
    character,
    views: list[View],
    centre: np.ndarray,
    detector_noise_px: float = 2.0,
    samples: int = UNCERTAINTY_SAMPLES,
    seed: int = 20260818,
) -> dict[str, float]:
    """Return how far each measured angle moves when the detector wobbles.

    No truth is needed. The observed landmarks are perturbed by the detector's
    own noise and the pose is fitted again. An angle that barely moves is well
    determined by this camera setup. An angle that swings is not, whatever the
    camera geometry says.

    This is what makes the decision per angle rather than per capture. The right
    knee can be undetermined in a setup where every other joint is solid.
    """
    import random  # noqa: PLC0415

    generator = random.Random(seed)
    collected: dict[str, list[float]] = {}
    for _ in range(max(2, samples)):
        wobbled = [
            View(
                camera=view.camera,
                landmarks={
                    joint: (
                        pixel[0] + generator.gauss(0.0, detector_noise_px),
                        pixel[1] + generator.gauss(0.0, detector_noise_px),
                    )
                    for joint, pixel in view.landmarks.items()
                },
            )
            for view in views
        ]
        try:
            angles = measure(fit(character, wobbled, centre)["points"], _index(character))
        except CaptureError:
            continue
        for name, value in angles.items():
            collected.setdefault(name, []).append(value)

    spread: dict[str, float] = {}
    for name, values in collected.items():
        if len(values) < 2:
            spread[name] = float("inf")
            continue
        average = sum(values) / len(values)
        variance = sum((value - average) ** 2 for value in values) / (len(values) - 1)
        # Two standard deviations covers about 95 percent of the wobble.
        spread[name] = round(2.0 * math.sqrt(variance), 2)
    return spread


def _index(character) -> dict[str, int]:
    return {
        name: position
        for position, name in enumerate(character.skeleton.joint_names)
    }


def report(
    angles: dict[str, float], uncertainty: dict[str, float], verdict: Verdict
) -> dict:
    """Decide, angle by angle, what may be shown to a coach.

    An angle is shown only when the capture geometry allows a measurement AND
    that particular angle is determined to better than the clinical threshold.
    """
    shown: dict[str, dict] = {}
    for name, value in angles.items():
        band = uncertainty.get(name, float("inf"))
        trusted = (
            verdict.measurement_valid
            and band <= MEANINGFUL_DEGREES * UNCERTAINTY_MARGIN
        )
        shown[name] = {
            "degrees": value if trusted else None,
            "uncertaintyDegrees": None if band == float("inf") else band,
            "shown": trusted,
            "withheldBecause": (
                None
                if trusted
                else (
                    verdict.reason
                    if not verdict.measurement_valid
                    else f"this angle moves {band:.1f} degrees when the detector "
                    f"wobbles, against a limit of "
                    f"{MEANINGFUL_DEGREES * UNCERTAINTY_MARGIN:.1f} degrees"
                )
            ),
        }
    return shown


def load_capture(folder: Path) -> list[View]:
    """Read a capture folder written by the field card.

    capture.json names each camera, where it stood, and its image. Landmarks are
    detected from the images with MediaPipe.
    """
    from fit_from_photo import LANDMARK_TO_JOINT, detect_landmarks  # noqa: PLC0415

    manifest_path = folder / "capture.json"
    if not manifest_path.is_file():
        raise CaptureError(f"no capture.json in {folder}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    views: list[View] = []
    for entry in manifest["cameras"]:
        image = folder / entry["image"]
        if not image.is_file():
            raise CaptureError(f"missing image {image}")
        found, width, height = detect_landmarks(image)
        landmarks = {
            LANDMARK_TO_JOINT[number]: pixel for number, pixel in found.items()
        }
        views.append(
            View(
                camera=Camera(
                    name=str(entry.get("name", image.stem)),
                    azimuth_degrees=float(entry["azimuthDegrees"]),
                    height_cm=float(entry.get("heightCm", 0.0)),
                    distance_cm=float(entry.get("distanceCm", 300.0)),
                    width_px=width,
                    height_px=height,
                    lens_equivalent_mm=float(entry.get("lensEquivalentMm", 26.0)),
                ),
                landmarks=landmarks,
            )
        )
    return views


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        print("No capture folder given. Nothing to fit yet.")
        return 0

    from movement_engine import joint_positions, load_character  # noqa: PLC0415

    folder = Path(sys.argv[1])
    views = load_capture(folder)
    verdict = judge(views)

    character = load_character()
    rest_points = joint_positions(
        character, np.zeros(character.parameter_transform.size, dtype=np.float32)
    )
    names = list(character.skeleton.joint_names)
    centre = rest_points[names.index("c_neck")]

    result = fit(character, views, centre)
    angles = measure(result["points"], result["index"])

    print(f"capture: {folder.name}")
    for view in views:
        print(
            f"  {view.camera.name:<12} azimuth {view.camera.azimuth_degrees:>6.1f} deg   "
            f"{len(view.landmarks)} landmarks"
        )
    print(f"constraints used: {result['constraints']}")
    print(f"verdict: {'MEASUREMENT' if verdict.measurement_valid else 'SHAPE ONLY'}")
    print(f"  {verdict.reason}")
    print()
    if verdict.measurement_valid:
        for name, value in angles.items():
            print(f"  {name:<34} {value:7.2f} deg")
    else:
        print("  Figures withheld. This capture can show the shape, not the numbers.")

    receipt = {
        "capture": folder.name,
        "cameras": [
            {
                "name": view.camera.name,
                "azimuthDegrees": view.camera.azimuth_degrees,
                "landmarks": len(view.landmarks),
            }
            for view in views
        ],
        "verdict": verdict.as_dict(),
        "measurement": angles if verdict.measurement_valid else None,
        "measurementWithheld": not verdict.measurement_valid,
    }
    output = folder / "fit_receipt.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"\nreceipt: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
