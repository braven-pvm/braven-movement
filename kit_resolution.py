"""Is the painted texture, or the camera, the limit on what a coach can see?

Two measurements, in the same unit.

1. The texture's own resolution on the body: for every body triangle, its area
   in the texture (square pixels) against its area on the athlete (square
   millimetres). The square root is texture pixels per millimetre of skin.
2. The camera's resolution at the athlete: the sensor width, the lens and the
   distance from the camera to the point it is aimed at give millimetres per
   image pixel on that plane.

    python -B kit_resolution.py --body out/kit/body.npz \
        --job spikes/poc-output/netball_double_foot_landing.job.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def triangles(loop_start, loop_total):
    out = []
    for start, total in zip(loop_start.tolist(), loop_total.tolist()):
        for step in range(1, total - 1):
            out.append((start, start + step, start + step + 1))
    return np.asarray(out, dtype=np.int64)


def area(points):
    """Twice-signed area of every triangle, halved. Works in 2D and in 3D."""
    first = points[:, 1] - points[:, 0]
    second = points[:, 2] - points[:, 0]
    if points.shape[2] == 2:
        return 0.5 * np.abs(first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0])
    return 0.5 * np.linalg.norm(np.cross(first, second), axis=1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--texture-size", type=int, default=2048)
    parser.add_argument("--neck-fraction", type=float, default=0.828)
    parser.add_argument("--hem-fraction", type=float, default=0.430)
    arguments = parser.parse_args()

    data = np.load(arguments.body)
    co = data["co"]
    uv = data["uv"]
    loop_vert = data["loop_vert"]
    body = data["w_body"] > 0.0
    faces = triangles(data["loop_start"], data["loop_total"])
    vertex = loop_vert[faces]
    keep = body[vertex].all(axis=1)
    faces, vertex = faces[keep], vertex[keep]

    metres = area(co[vertex])
    pixels = area(uv[faces] * (arguments.texture_size - 1))
    live = metres > 1e-12
    density = np.sqrt(pixels[live] / (metres[live] * 1e6))  # texture px per mm

    # The torso only: the band a bodice covers, so the number describes the
    # surface the kit is painted on and not her scalp.
    span = co[body].max(axis=0) - co[body].min(axis=0)
    up = int(np.argmax(span))
    low, high = float(co[body][:, up].min()), float(co[body][:, up].max())
    height = co[vertex][:, :, up].mean(axis=1)
    band = (
        (height > low + arguments.hem_fraction * (high - low))
        & (height < low + arguments.neck_fraction * (high - low))
        & live
    )
    torso = np.sqrt(pixels[band] / (metres[band] * 1e6))

    print(f"[kit-resolution] body triangles {faces.shape[0]}, "
          f"surface {metres.sum():.3f} m^2")
    for label, values in (("whole body", density), ("bodice band", torso)):
        print(
            f"[kit-resolution] {label:12s} texture pixels per mm: "
            f"median {np.median(values):.2f}  "
            f"10th {np.percentile(values, 10):.2f}  "
            f"90th {np.percentile(values, 90):.2f}"
        )

    job = json.loads(arguments.job.read_text(encoding="utf-8"))
    print(f"[kit-resolution] job {arguments.job.name}")
    for name, view in job["views"].items():
        location = np.asarray(view["locationM"], dtype=float)
        target = np.asarray(view["targetM"], dtype=float)
        distance = float(np.linalg.norm(location - target))
        width_px = int(view["resolutionPx"][0])
        across = view["sensorWidthMm"] / view["lensMm"] * distance  # metres wide
        per_pixel = across / width_px * 1000.0  # millimetres per image pixel
        print(
            f"[kit-resolution] view {name:8s} distance {distance:.2f} m  "
            f"frame {across * 1000:.0f} mm wide over {width_px} px  "
            f"= {per_pixel:.2f} mm per image pixel "
            f"({1 / per_pixel:.2f} image pixels per mm)"
        )
        print(
            f"[kit-resolution]      texture is "
            f"{np.median(torso) * per_pixel:.2f} times the camera's sampling "
            f"in the bodice band"
        )
    print("KIT RESOLUTION OK", flush=True)


if __name__ == "__main__":
    main()
