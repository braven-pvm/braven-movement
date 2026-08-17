from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from reference_pose_config import load_reference_catch_config


Point = tuple[float, float]
Point3 = tuple[float, float, float]
_DEFAULT_CONFIG = load_reference_catch_config()
GROUP_LIMITS_PX = dict(_DEFAULT_CONFIG.pixel_limits_px)
REFERENCE_FRAME_PX = _DEFAULT_CONFIG.reference_frame_px
REFERENCE_TARGETS_PX: dict[str, Point] = dict(_DEFAULT_CONFIG.reference_targets_px)
REQUIRED_REFERENCE_LANDMARKS = frozenset(REFERENCE_TARGETS_PX)


class PoseCalibrationError(ValueError):
    pass


def _add(left: Point3, right: Point3) -> Point3:
    return tuple(left[index] + right[index] for index in range(3))  # type: ignore[return-value]


def _subtract(left: Point3, right: Point3) -> Point3:
    return tuple(left[index] - right[index] for index in range(3))  # type: ignore[return-value]


def _scale(vector: Point3, factor: float) -> Point3:
    return tuple(value * factor for value in vector)  # type: ignore[return-value]


def _dot(left: Point3, right: Point3) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _cross(left: Point3, right: Point3) -> Point3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _normalise(vector: Point3) -> Point3:
    length = math.sqrt(_dot(vector, vector))
    if length < 1e-9:
        raise PoseCalibrationError("cannot normalise a zero-length vector")
    return _scale(vector, 1.0 / length)


def point_on_camera_ray_at_radius(
    *,
    pixel: Point,
    centre: Point3,
    radius: float,
    preferred_direction: Point3,
    camera_location: Point3,
    camera_target: Point3,
    frame: tuple[int, int],
    lens: float,
    sensor_width: float,
) -> Point3:
    """Return the reachable 3D point that projects to ``pixel`` without flipping.

    The two ray/sphere intersections represent bending the joint toward or away
    from the camera. ``preferred_direction`` selects the anatomically continuous
    solution rather than silently accepting the mirrored one.
    """
    if radius <= 0.0 or lens <= 0.0 or sensor_width <= 0.0:
        raise PoseCalibrationError("radius and camera dimensions must be positive")
    width, height = frame
    forward = _normalise(_subtract(camera_target, camera_location))
    right_seed = _cross(forward, (0.0, 0.0, 1.0))
    if _dot(right_seed, right_seed) < 1e-12:
        right_seed = _cross(forward, (0.0, 1.0, 0.0))
    right = _normalise(right_seed)
    up = _cross(right, forward)
    horizontal = (pixel[0] / width - 0.5) * sensor_width / lens
    vertical = (0.5 - pixel[1] / height) * sensor_width * height / width / lens
    ray = _add(forward, _add(_scale(right, horizontal), _scale(up, vertical)))

    offset = _subtract(camera_location, centre)
    a = _dot(ray, ray)
    b = 2.0 * _dot(offset, ray)
    c = _dot(offset, offset) - radius * radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0.0:
        raise PoseCalibrationError(
            f"reference pixel {pixel} is unreachable at radius {radius:.5f}"
        )
    root = math.sqrt(discriminant)
    depths = ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a))
    candidates = [
        _add(camera_location, _scale(ray, depth))
        for depth in depths
        if depth > 0.0
    ]
    if not candidates:
        raise PoseCalibrationError("reference pixel ray is behind the camera")
    preferred = _normalise(preferred_direction)
    return max(
        candidates,
        key=lambda point: _dot(_normalise(_subtract(point, centre)), preferred),
    )


@dataclass(frozen=True)
class PixelCalibration:
    errors_px: dict[str, float]
    group_max_px: dict[str, float]


def validate_reference_target_schema(
    frame: tuple[int, int],
    targets: Mapping[str, Point],
) -> None:
    if frame != REFERENCE_FRAME_PX:
        raise PoseCalibrationError(
            f"reference frame must be {REFERENCE_FRAME_PX[0]}x{REFERENCE_FRAME_PX[1]}"
        )
    missing = sorted(REQUIRED_REFERENCE_LANDMARKS - set(targets))
    if missing:
        raise PoseCalibrationError(f"missing reference landmarks: {', '.join(missing)}")
    width, height = frame
    for name, point in targets.items():
        if len(point) != 2 or not all(math.isfinite(value) for value in point):
            raise PoseCalibrationError(f"invalid reference landmark {name}")
        if not (0.0 <= point[0] <= width and 0.0 <= point[1] <= height):
            raise PoseCalibrationError(f"reference landmark {name} is outside the frame")


def landmark_group(name: str) -> str:
    if name.startswith("ball_"):
        return "ball"
    if name.endswith("_tip"):
        return "fingertips"
    return "joints"


def compare_projected_landmarks(
    targets: Mapping[str, Point],
    actual: Mapping[str, Point],
    group_limits: Mapping[str, float] | None = None,
) -> PixelCalibration:
    missing = sorted(set(targets) - set(actual))
    if missing:
        raise PoseCalibrationError(f"missing projected landmarks: {', '.join(missing)}")

    errors: dict[str, float] = {}
    limits = group_limits or GROUP_LIMITS_PX
    group_max = {group: 0.0 for group in limits}
    for name, target in targets.items():
        point = actual[name]
        error = math.hypot(point[0] - target[0], point[1] - target[1])
        errors[name] = round(error, 4)
        group = landmark_group(name)
        group_max[group] = max(group_max[group], error)
    return PixelCalibration(
        errors_px=errors,
        group_max_px={name: round(value, 4) for name, value in group_max.items()},
    )


def validate_pixel_calibration(
    result: PixelCalibration,
    group_limits: Mapping[str, float] | None = None,
) -> None:
    for group, limit in (group_limits or GROUP_LIMITS_PX).items():
        actual = result.group_max_px[group]
        if actual > limit:
            raise PoseCalibrationError(
                f"{group} pixel error {actual:.2f}px exceeds {limit:.1f}px"
            )
