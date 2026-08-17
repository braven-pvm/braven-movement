from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from movement_contract import inspect_glb, write_job_manifest


MOVEMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class ExportError(RuntimeError):
    pass


def build_export_expression(path: Path, *, fps: float) -> str:
    output = Path(path).resolve().as_posix()
    return (
        "(lambda o: ("
        "setattr(o, 'include_animation', True), "
        "setattr(o, 'throw_exception', True), "
        "setattr(o, 'for_selected_objects', False), "
        f"setattr(o, 'fps', {float(fps)!r}), "
        f"csc.glb.process_export(scene, {output!r}, o), "
        "'exported'))(csc.glb.ExportOptions())"
    )


def require_ok(response: dict) -> dict:
    if not isinstance(response, dict) or not response.get("ok"):
        error = response.get("error", "Cascadeur returned an invalid response") if isinstance(response, dict) else repr(response)
        raise ExportError(str(error))
    return response


def parse_frame_range(response: dict) -> tuple[int, int]:
    value = require_ok(response).get("value", "")
    try:
        first, last = ast.literal_eval(value)
        first, last = int(first), int(last)
    except (ValueError, SyntaxError, TypeError) as error:
        raise ExportError(f"invalid frame range response: {value!r}") from error
    if last < first:
        raise ExportError(f"invalid frame range: {first}..{last}")
    return first, last


def request_json(
    *,
    host: str,
    port: int,
    path: str,
    payload: dict | None = None,
    timeout: float = 60.0,
) -> dict:
    url = f"http://{host}:{port}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="GET" if data is None else "POST",
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise ExportError(f"Cascadeur request failed at {url}: {error}") from error


def export_scene(
    *,
    movement_id: str,
    fps: float,
    output_dir: Path,
    host: str,
    port: int,
) -> Path:
    if not MOVEMENT_ID.fullmatch(movement_id):
        raise ExportError("movement id must use only letters, digits, underscores, and hyphens")
    if fps <= 0:
        raise ExportError("fps must be greater than zero")

    health = request_json(host=host, port=port, path="/health", timeout=5.0)
    if health.get("ok") is not True:
        raise ExportError(f"Cascadeur script server is unhealthy: {health!r}")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    partial = output_dir / f"{movement_id}.partial.{os.getpid()}.glb"
    asset = output_dir / f"{movement_id}.glb"
    manifest = output_dir / "job.json"
    if partial.exists():
        partial.unlink()

    expression = build_export_expression(partial, fps=fps)
    require_ok(
        request_json(
            host=host,
            port=port,
            path="/run",
            payload={"code": expression},
            timeout=90.0,
        )
    )
    if not partial.is_file():
        raise ExportError("Cascadeur returned success but did not write the GLB")
    inspection = inspect_glb(partial)

    frame_response = request_json(
        host=host,
        port=port,
        path="/run",
        payload={
            "code": "(app.current_scene().animation_boundary().first_frame, app.current_scene().animation_boundary().last_frame)"
        },
        timeout=30.0,
    )
    frame_start, frame_end = parse_frame_range(frame_response)

    partial.replace(asset)
    return write_job_manifest(
        manifest,
        movement_id=movement_id,
        asset_path=asset,
        fps=fps,
        frame_start=frame_start,
        frame_end=frame_end,
        inspection=inspection,
        publishable=False,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Export the open Cascadeur scene as animated GLB")
    result.add_argument("--movement-id", required=True)
    result.add_argument("--fps", required=True, type=float)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--host", default="127.0.0.1")
    result.add_argument("--port", default=8765, type=int)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        manifest = export_scene(
            movement_id=arguments.movement_id,
            fps=arguments.fps,
            output_dir=arguments.output,
            host=arguments.host,
            port=arguments.port,
        )
    except ExportError as error:
        print(f"[export] FAIL {error}", file=sys.stderr)
        return 2
    print(f"[export] PASS manifest={manifest}")
    print(manifest.read_text(encoding="utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
