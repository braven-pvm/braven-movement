from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
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


def _optional_str(values: Mapping[str, Any], key: str, name: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ReferencePoseConfigError(f"{name} must be a non-empty string or absent")
    return value


def _optional_positive_float(values: Mapping[str, Any], key: str, name: str) -> float | None:
    value = values.get(key)
    if value is None:
        return None
    converted = float(value)
    if not converted > 0.0:
        raise ReferencePoseConfigError(f"{name} must be a positive number or absent")
    return converted


# Where the assets this repository authors live. The generator's `asset_path`
# refuses any file outside the MPFB data tree; this is the same refusal for the
# repository's own tree, so a config cannot make a receipt hash whatever file
# happened to be at an arbitrary path.
KIT_ASSET_DIR = ("assets", "kit")


def kit_asset_path(relative: str, repository_root: Path | None = None) -> Path:
    """The file a `presentation.kit` path names, under `assets/kit/` only.

    A POSIX path relative to the repository root, with no `..`, no drive and
    no leading slash, naming a file that exists. Everything else is refused
    with the reason, at load time and not at render time.
    """
    root = (repository_root or DEFAULT_CONFIG_PATH.parents[1]).resolve()
    if not relative or "\\" in relative or ":" in relative or relative.startswith("/"):
        raise ReferencePoseConfigError(
            "presentation.kit paths are POSIX and relative to the repository "
            f"root, got {relative!r}"
        )
    parts = PurePosixPath(relative).parts
    if ".." in parts or parts[: len(KIT_ASSET_DIR)] != KIT_ASSET_DIR:
        raise ReferencePoseConfigError(
            f"presentation.kit paths must lie under {'/'.join(KIT_ASSET_DIR)}/, "
            f"got {relative!r}"
        )
    path = root.joinpath(*parts)
    if not path.is_file():
        raise ReferencePoseConfigError(
            f"presentation.kit names a file that is not there: {path}"
        )
    return path


def mhclo_obj_path(mhclo: Path) -> Path:
    """The mesh file an `.mhclo` names, beside it.

    A garment is two files: the `.mhclo` holds the fitting and the `.obj` it
    names holds the geometry. A receipt that hashes only the first has not
    hashed the shape, so the generator lists both.
    """
    for line in mhclo.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "obj_file":
            return mhclo.parent / parts[1]
    raise ReferencePoseConfigError(f"{mhclo} names no obj_file")


def _kit_file(values: Mapping[str, Any], key: str) -> str | None:
    """An optional kit path, checked at load time so a render never starts
    for a garment that is not there or not ours."""
    relative = _optional_str(values, key, f"presentation.kit.{key}")
    if relative is not None:
        kit_asset_path(relative)
    return relative


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
class MaterialPresentation:
    base_color: tuple[float, float, float, float]
    roughness: float
    # THE KIT IS OPTIONAL. Absent, the generator wears the MPFB casual suit it
    # has always worn, and every existing config and receipt reads as before.
    # `garment` and `bib_image` are POSIX paths relative to the repository
    # root; `kit_asset_path` refuses anything outside `assets/kit/`. The sock
    # top is a height in metres above the floor at which the shoe asset's
    # tall sock is cut, because no shoe asset ships with a low one.
    garment: str | None = None
    bib_image: str | None = None
    sock_top_m: float | None = None


@dataclass(frozen=True)
class BallPresentation:
    primary_color: tuple[float, float, float, float]
    secondary_color: tuple[float, float, float, float]
    accent_color: tuple[float, float, float, float]
    seam_color: tuple[float, float, float, float]
    roughness: float
    grip_scale: float
    seam_loop_count: int


@dataclass(frozen=True)
class StudioPresentation:
    world_color: tuple[float, float, float]
    cyclorama_color: tuple[float, float, float, float]
    cyclorama_roughness: float
    light_target_m: tuple[float, float, float]


@dataclass(frozen=True)
class LightPresentation:
    name: str
    location_m: tuple[float, float, float]
    energy: float
    size_m: float
    color: tuple[float, float, float]


@dataclass(frozen=True)
class PresentationConfig:
    style: str
    kit: MaterialPresentation
    ball: BallPresentation
    studio: StudioPresentation
    lights: tuple[LightPresentation, ...]


@dataclass(frozen=True)
class AthletePhenotype:
    age: float
    cupsize: float
    firmness: float
    gender: float
    height: float
    muscle: float
    proportions: float
    race: dict[str, float]
    weight: float


@dataclass(frozen=True)
class AthleticReadiness:
    pelvis_translation_m: tuple[float, float, float]
    hip_hinge_degrees: float
    chest_lift_degrees: float


@dataclass(frozen=True)
class AthleteExpression:
    name: str
    face_units: dict[str, float]


@dataclass(frozen=True)
class AthleteConfig:
    phenotype: AthletePhenotype
    readiness: AthleticReadiness
    expression: AthleteExpression


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
    athlete: AthleteConfig
    presentation: PresentationConfig
    views: dict[str, ViewConfig]


def load_reference_catch_config(path: Path | None = None) -> ReferenceCatchConfig:
    config_path = (path or DEFAULT_CONFIG_PATH).resolve()
    try:
        data: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
        reference = data["reference"]
        pose = data["pose"]
        athlete = data["athlete"]
        presentation = data["presentation"]
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
        _require_keys(
            athlete,
            {"phenotype", "readiness", "expression"},
            "athlete",
        )
        _require_keys(
            athlete["phenotype"],
            {
                "age",
                "cupsize",
                "firmness",
                "gender",
                "height",
                "muscle",
                "proportions",
                "race",
                "weight",
            },
            "athlete.phenotype",
        )
        _require_keys(
            athlete["readiness"],
            {"pelvisTranslationM", "hipHingeDegrees", "chestLiftDegrees"},
            "athlete.readiness",
        )
        _require_keys(
            athlete["expression"],
            {"name", "faceUnits"},
            "athlete.expression",
        )
        _require_keys(
            presentation,
            {"style", "kit", "ball", "studio", "lights"},
            "presentation",
        )
        _require_keys(
            presentation["kit"],
            {"baseColor", "roughness"},
            "presentation.kit",
        )
        _require_keys(
            presentation["ball"],
            {
                "primaryColor",
                "secondaryColor",
                "accentColor",
                "seamColor",
                "roughness",
                "gripScale",
                "seamLoopCount",
            },
            "presentation.ball",
        )
        _require_keys(
            presentation["studio"],
            {
                "worldColor",
                "cycloramaColor",
                "cycloramaRoughness",
                "lightTargetM",
            },
            "presentation.studio",
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
            athlete=AthleteConfig(
                phenotype=AthletePhenotype(
                    age=float(athlete["phenotype"]["age"]),
                    cupsize=float(athlete["phenotype"]["cupsize"]),
                    firmness=float(athlete["phenotype"]["firmness"]),
                    gender=float(athlete["phenotype"]["gender"]),
                    height=float(athlete["phenotype"]["height"]),
                    muscle=float(athlete["phenotype"]["muscle"]),
                    proportions=float(athlete["phenotype"]["proportions"]),
                    race={
                        name: float(value)
                        for name, value in athlete["phenotype"]["race"].items()
                    },
                    weight=float(athlete["phenotype"]["weight"]),
                ),
                readiness=AthleticReadiness(
                    pelvis_translation_m=_float_tuple(
                        athlete["readiness"]["pelvisTranslationM"],
                        3,
                        "athlete.readiness.pelvisTranslationM",
                    ),
                    hip_hinge_degrees=float(
                        athlete["readiness"]["hipHingeDegrees"]
                    ),
                    chest_lift_degrees=float(
                        athlete["readiness"]["chestLiftDegrees"]
                    ),
                ),
                expression=AthleteExpression(
                    name=str(athlete["expression"]["name"]),
                    face_units={
                        name: float(value)
                        for name, value in athlete["expression"]["faceUnits"].items()
                    },
                ),
            ),
            presentation=PresentationConfig(
                style=str(presentation["style"]),
                kit=MaterialPresentation(
                    base_color=_float_tuple(
                        presentation["kit"]["baseColor"],
                        4,
                        "presentation.kit.baseColor",
                    ),
                    roughness=float(presentation["kit"]["roughness"]),
                    garment=_kit_file(presentation["kit"], "garment"),
                    bib_image=_kit_file(presentation["kit"], "bibImage"),
                    sock_top_m=_optional_positive_float(
                        presentation["kit"], "sockTopM", "presentation.kit.sockTopM"
                    ),
                ),
                ball=BallPresentation(
                    primary_color=_float_tuple(
                        presentation["ball"]["primaryColor"],
                        4,
                        "presentation.ball.primaryColor",
                    ),
                    secondary_color=_float_tuple(
                        presentation["ball"]["secondaryColor"],
                        4,
                        "presentation.ball.secondaryColor",
                    ),
                    accent_color=_float_tuple(
                        presentation["ball"]["accentColor"],
                        4,
                        "presentation.ball.accentColor",
                    ),
                    seam_color=_float_tuple(
                        presentation["ball"]["seamColor"],
                        4,
                        "presentation.ball.seamColor",
                    ),
                    roughness=float(presentation["ball"]["roughness"]),
                    grip_scale=float(presentation["ball"]["gripScale"]),
                    seam_loop_count=int(presentation["ball"]["seamLoopCount"]),
                ),
                studio=StudioPresentation(
                    world_color=_float_tuple(
                        presentation["studio"]["worldColor"],
                        3,
                        "presentation.studio.worldColor",
                    ),
                    cyclorama_color=_float_tuple(
                        presentation["studio"]["cycloramaColor"],
                        4,
                        "presentation.studio.cycloramaColor",
                    ),
                    cyclorama_roughness=float(
                        presentation["studio"]["cycloramaRoughness"]
                    ),
                    light_target_m=_float_tuple(
                        presentation["studio"]["lightTargetM"],
                        3,
                        "presentation.studio.lightTargetM",
                    ),
                ),
                lights=tuple(
                    LightPresentation(
                        name=str(light["name"]),
                        location_m=_float_tuple(
                            light["locationM"],
                            3,
                            f"presentation.lights.{index}.locationM",
                        ),
                        energy=float(light["energy"]),
                        size_m=float(light["sizeM"]),
                        color=_float_tuple(
                            light["color"],
                            3,
                            f"presentation.lights.{index}.color",
                        ),
                    )
                    for index, light in enumerate(presentation["lights"])
                ),
            ),
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
