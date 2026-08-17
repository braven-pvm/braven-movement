from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "reference_catch.v1.json"


class ReferencePoseConfigError(ValueError):
    pass


def _require_keys(values: Mapping[str, Any], required: set[str], name: str) -> None:
    missing = sorted(required - set(values))
    if missing:
        raise ReferencePoseConfigError(
            f"{name} is missing required keys: {', '.join(missing)}"
        )


def _float_tuple(values: Any, size: int, name: str) -> tuple[float, ...]:
    converted = tuple(float(value) for value in values)
    if len(converted) != size:
        raise ReferencePoseConfigError(f"{name} must contain exactly {size} values")
    return converted


def _int_tuple(values: Any, size: int, name: str) -> tuple[int, ...]:
    converted = tuple(int(value) for value in values)
    if len(converted) != size:
        raise ReferencePoseConfigError(f"{name} must contain exactly {size} values")
    return converted


@dataclass(frozen=True)
class HandTarget:
    finger_direction: tuple[float, float, float]
    palm_normal: tuple[float, float, float]


@dataclass(frozen=True)
class ViewConfig:
    resolution_px: tuple[int, int]
    location_m: tuple[float, float, float]
    target_m: tuple[float, float, float]
    lens_mm: float
    sensor_width_mm: float


@dataclass(frozen=True)
class ReferenceCatchConfig:
    source_path: Path
    schema_version: int
    movement_id: str
    licence: str
    publishable: bool
    reference_asset_file: str
    reference_sha256: str
    reference_frame_px: tuple[int, int]
    reference_targets_px: dict[str, tuple[float, float]]
    pixel_limits_px: dict[str, float]
    ball_radius_m: float
    ball_centre_m: tuple[float, float, float]
    wrist_targets_m: dict[str, tuple[float, float, float]]
    shoulder_targets_m: dict[str, tuple[float, float, float]]
    arm_poles: dict[str, tuple[float, float, float]]
    hand_targets: dict[str, HandTarget]
    finger_curl_degrees: dict[str, tuple[float, float]]
    anatomy_limits_degrees: dict[str, float]
    views: dict[str, ViewConfig]


def load_reference_catch_config(path: Path | None = None) -> ReferenceCatchConfig:
    config_path = (path or DEFAULT_CONFIG_PATH).resolve()
    try:
        data: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        reference = data["reference"]
        pose = data["pose"]
        views = data["views"]
        schema_version = int(data["schemaVersion"])
        if schema_version != 1:
            raise ReferencePoseConfigError(
                f"schemaVersion must be 1, got {schema_version}"
            )
        _require_keys(pose["wristTargetsM"], {"l", "r"}, "pose.wristTargetsM")
        _require_keys(
            pose["shoulderTargetsM"],
            {"l", "r"},
            "pose.shoulderTargetsM",
        )
        _require_keys(pose["armPoles"], {"l", "r"}, "pose.armPoles")
        _require_keys(pose["handTargets"], {"l", "r"}, "pose.handTargets")
        _require_keys(
            pose["fingerCurlDegrees"],
            {"thumb", "index", "middle", "ring", "pinky"},
            "pose.fingerCurlDegrees",
        )
        _require_keys(
            pose["anatomyLimitsDegrees"],
            {"forearmRoll", "wristBend", "fingerJointBend", "fingerBaseDeviation"},
            "pose.anatomyLimitsDegrees",
        )
        _require_keys(
            reference["pixelLimitsPx"],
            {"ball", "joints", "fingertips"},
            "reference.pixelLimitsPx",
        )
        _require_keys(
            views,
            {"referenceCrop", "referenceMatch", "fullBody"},
            "views",
        )
        return ReferenceCatchConfig(
            source_path=config_path,
            schema_version=schema_version,
            movement_id=str(data["movementId"]),
            licence=str(data["licence"]),
            publishable=bool(data["publishable"]),
            reference_asset_file=str(reference["assetFile"]),
            reference_sha256=str(reference["sha256"]),
            reference_frame_px=_int_tuple(reference["framePx"], 2, "reference.framePx"),
            reference_targets_px={
                name: _float_tuple(point, 2, f"reference.targetsPx.{name}")
                for name, point in reference["targetsPx"].items()
            },
            pixel_limits_px={
                name: float(value)
                for name, value in reference["pixelLimitsPx"].items()
            },
            ball_radius_m=float(pose["ballRadiusM"]),
            ball_centre_m=_float_tuple(pose["ballCentreM"], 3, "pose.ballCentreM"),
            wrist_targets_m={
                side: _float_tuple(point, 3, f"pose.wristTargetsM.{side}")
                for side, point in pose["wristTargetsM"].items()
            },
            shoulder_targets_m={
                side: _float_tuple(point, 3, f"pose.shoulderTargetsM.{side}")
                for side, point in pose["shoulderTargetsM"].items()
            },
            arm_poles={
                side: _float_tuple(point, 3, f"pose.armPoles.{side}")
                for side, point in pose["armPoles"].items()
            },
            hand_targets={
                side: HandTarget(
                    finger_direction=_float_tuple(
                        target["fingerDirection"],
                        3,
                        f"pose.handTargets.{side}.fingerDirection",
                    ),
                    palm_normal=_float_tuple(
                        target["palmNormal"],
                        3,
                        f"pose.handTargets.{side}.palmNormal",
                    ),
                )
                for side, target in pose["handTargets"].items()
            },
            finger_curl_degrees={
                digit: _float_tuple(
                    angles,
                    2,
                    f"pose.fingerCurlDegrees.{digit}",
                )
                for digit, angles in pose["fingerCurlDegrees"].items()
            },
            anatomy_limits_degrees={
                name: float(value)
                for name, value in pose["anatomyLimitsDegrees"].items()
            },
            views={
                name: ViewConfig(
                    resolution_px=_int_tuple(
                        view["resolutionPx"], 2, f"views.{name}.resolutionPx"
                    ),
                    location_m=_float_tuple(
                        view["locationM"], 3, f"views.{name}.locationM"
                    ),
                    target_m=_float_tuple(
                        view["targetM"], 3, f"views.{name}.targetM"
                    ),
                    lens_mm=float(view["lensMm"]),
                    sensor_width_mm=float(view["sensorWidthMm"]),
                )
                for name, view in views.items()
            },
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ReferencePoseConfigError(
            f"invalid reference catch config {config_path}: {error}"
        ) from error
