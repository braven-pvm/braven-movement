from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


JOB_VERSION = 1


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class GlbInspection:
    bytes: int
    sha256: str
    nodes: int
    animations: int
    channels: int


@dataclass(frozen=True)
class MovementJob:
    version: int
    movement_id: str
    asset_path: Path
    asset_format: str
    asset_sha256: str
    fps: float
    frame_start: int
    frame_end: int
    publishable: bool


@dataclass(frozen=True)
class Normalization:
    scale: float
    offset_x: float
    offset_y: float
    offset_z: float


def inspect_glb(path: Path) -> GlbInspection:
    path = Path(path)
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ContractError(f"not a GLB 2 container: {path}")

    version, declared_length = struct.unpack_from("<II", data, 4)
    if version != 2:
        raise ContractError(f"unsupported GLB version {version}")
    if declared_length != len(data):
        raise ContractError(
            f"GLB length mismatch: header={declared_length}, bytes={len(data)}"
        )

    chunk_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    if chunk_type != b"JSON" or 20 + chunk_length > len(data):
        raise ContractError("GLB first chunk is not valid JSON")
    try:
        document = json.loads(data[20 : 20 + chunk_length].rstrip(b" \x00"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"invalid GLB JSON chunk: {error}") from error

    animations = document.get("animations", [])
    channels = sum(len(animation.get("channels", [])) for animation in animations)
    if not animations or channels == 0:
        raise ContractError("GLB contains no animation channels")

    return GlbInspection(
        bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        nodes=len(document.get("nodes", [])),
        animations=len(animations),
        channels=channels,
    )


def max_rgba_alpha(values: Iterable[float]) -> float:
    maximum = 0.0
    for index, value in enumerate(values):
        if index % 4 == 3:
            maximum = max(maximum, float(value))
    return maximum


def normalization_transform(
    *,
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
    target_height: float,
) -> Normalization:
    height = float(maximum[2]) - float(minimum[2])
    if height <= 0:
        raise ContractError("figure bounds must have positive height")
    if target_height <= 0:
        raise ContractError("target height must be greater than zero")
    scale = float(target_height) / height
    centre_x = (float(minimum[0]) + float(maximum[0])) / 2.0
    centre_y = (float(minimum[1]) + float(maximum[1])) / 2.0
    return Normalization(
        scale=scale,
        offset_x=-centre_x * scale,
        offset_y=-centre_y * scale,
        offset_z=-float(minimum[2]) * scale,
    )


def write_job_manifest(
    path: Path,
    *,
    movement_id: str,
    asset_path: Path,
    fps: float,
    frame_start: int,
    frame_end: int,
    inspection: GlbInspection,
    publishable: bool,
) -> Path:
    path = Path(path)
    asset_path = Path(asset_path)
    if asset_path.parent.resolve() != path.parent.resolve():
        raise ContractError("GLB asset and job manifest must share one directory")
    if not movement_id.strip():
        raise ContractError("movement id must not be blank")
    if fps <= 0:
        raise ContractError("fps must be greater than zero")
    if frame_end < frame_start:
        raise ContractError("frame end must not precede frame start")

    payload = {
        "jobVersion": JOB_VERSION,
        "movementId": movement_id,
        "publishable": bool(publishable),
        "source": {
            "format": "glb",
            "asset": asset_path.name,
            "sha256": inspection.sha256,
            "bytes": inspection.bytes,
            "nodes": inspection.nodes,
            "animations": inspection.animations,
            "channels": inspection.channels,
        },
        "timeline": {
            "fps": float(fps),
            "frameStart": int(frame_start),
            "frameEnd": int(frame_end),
        },
        "warnings": [
            "Internal feasibility sample only; source figure publication rights are unresolved."
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def read_job_manifest(path: Path) -> MovementJob:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        source = payload["source"]
        timeline = payload["timeline"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ContractError(f"invalid movement job manifest: {error}") from error

    version = int(payload.get("jobVersion", -1))
    if version != JOB_VERSION:
        raise ContractError(f"unsupported job version {version}")
    if source.get("format") != "glb":
        raise ContractError(f"unsupported source format {source.get('format')!r}")

    asset_path = path.parent / source["asset"]
    if not asset_path.is_file():
        raise ContractError(f"movement asset does not exist: {asset_path}")
    actual_sha256 = hashlib.sha256(asset_path.read_bytes()).hexdigest()
    if actual_sha256 != source["sha256"]:
        raise ContractError("movement asset SHA-256 does not match the manifest")

    return MovementJob(
        version=version,
        movement_id=str(payload["movementId"]),
        asset_path=asset_path,
        asset_format="glb",
        asset_sha256=str(source["sha256"]),
        fps=float(timeline["fps"]),
        frame_start=int(timeline["frameStart"]),
        frame_end=int(timeline["frameEnd"]),
        publishable=bool(payload["publishable"]),
    )
