"""Render a solved phase to a PNG, without a browser.

The manual takes pre-rendered images. The browser page is for turning the
figure round and judging it; this is for producing the picture that goes on the
page, and for looking at the figure when the preview pane will not composite.

A depth buffer decides what is in front, one pixel at a time. Sorting whole
triangles by their centre is cheaper and it is wrong wherever two surfaces come
close in depth: the far arm painted over the near shoulder and the far thigh
over the near hip, which reads as looking through the athlete. The same buffer
carries the ball as a sphere rather than a flat disc, so the fingers in front
of it stay in front and the fingers behind it are hidden, which is the whole
point of a picture of a catch.

Shading interpolates the vertex normals across each triangle instead of
lighting the triangle flat, so the mesh reads as a body and not as facets.

    pixi run python render_figure.py
    pixi run python render_figure.py netball_two_hand_snatch_pull_in contact
    pixi run python render_figure.py netball_two_hand_snatch_pull_in contact 1.5708
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

import smplx_body  # noqa: E402
import smplx_retarget  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from movement_engine import (  # noqa: E402
    definition_path,
    joint_positions,
    load_character,
)
from possession_solve import solve_movement  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output"
WIDTH, HEIGHT, PAD = 900, 1200, 30
# Up, to the left, and toward the viewer. Screen y points down and depth grows
# toward the camera, so up is negative and near is positive.
LIGHT = np.array([-0.40, -0.55, 0.73])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
SHEET = np.array([27.0, 26.0, 23.0])
FIGURE = np.array([207.0, 199.0, 184.0])
BALL = np.array([217.0, 123.0, 60.0])
AMBIENT = 0.34


def project(points, centre, span, azimuth, elevation, zoom):
    """Orthographic, with the same axes the browser page uses."""
    ca, sa = np.cos(azimuth), np.sin(azimuth)
    ce, se = np.cos(elevation), np.sin(elevation)
    k = (HEIGHT - 2 * PAD) / (span * 1.05) * zoom
    d = np.asarray(points, dtype=np.float64) - centre
    px = d[:, 0] * ca + d[:, 2] * sa
    zr = d[:, 2] * ca - d[:, 0] * sa
    return np.stack(
        [
            WIDTH / 2 + px * k,
            HEIGHT - PAD - (d[:, 1] * ce - zr * se + span / 2) * k,
            (d[:, 1] * se + zr * ce) * k,
        ],
        axis=1,
    ), k


def _shade(normals):
    """Lambert, with the normal turned to face the camera."""
    length = np.linalg.norm(normals, axis=-1)
    length[length == 0] = 1.0
    unit = normals / length[..., None]
    towards = np.where(unit[..., 2] > 0, 1.0, -1.0)
    lambert = np.clip(towards * (unit @ LIGHT), 0.0, None)
    return AMBIENT + (1.0 - AMBIENT) * lambert


def _mesh(screen, faces, colour, depth, image):
    """Rasterise the body into the depth buffer."""
    a, b, c = (screen[faces[:, i]] for i in range(3))
    face_normal = np.cross(b - a, c - a)

    # Smooth normals: every vertex takes the sum of the faces it belongs to.
    vertex_normal = np.zeros_like(screen)
    for i in range(3):
        np.add.at(vertex_normal, faces[:, i], face_normal)

    keep = np.where(face_normal[:, 2] >= 0)[0]
    for t in keep:
        pa, pb, pc = a[t], b[t], c[t]
        x0 = max(int(np.floor(min(pa[0], pb[0], pc[0]))), 0)
        x1 = min(int(np.ceil(max(pa[0], pb[0], pc[0]))) + 1, WIDTH)
        y0 = max(int(np.floor(min(pa[1], pb[1], pc[1]))), 0)
        y1 = min(int(np.ceil(max(pa[1], pb[1], pc[1]))) + 1, HEIGHT)
        if x0 >= x1 or y0 >= y1:
            continue
        area = ((pb[0] - pa[0]) * (pc[1] - pa[1])
                - (pc[0] - pa[0]) * (pb[1] - pa[1]))
        if area == 0:
            continue
        ys, xs = np.mgrid[y0:y1, x0:x1]
        px, py = xs + 0.5, ys + 0.5
        w0 = ((pb[0] - px) * (pc[1] - py) - (pc[0] - px) * (pb[1] - py)) / area
        w1 = ((pc[0] - px) * (pa[1] - py) - (pa[0] - px) * (pc[1] - py)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        z = w0 * pa[2] + w1 * pb[2] + w2 * pc[2]
        nearer = inside & (z > depth[y0:y1, x0:x1])
        if not nearer.any():
            continue
        n = (w0[..., None] * vertex_normal[faces[t, 0]]
             + w1[..., None] * vertex_normal[faces[t, 1]]
             + w2[..., None] * vertex_normal[faces[t, 2]])
        lit = _shade(n)[nearer]
        depth[y0:y1, x0:x1][nearer] = z[nearer]
        image[y0:y1, x0:x1][nearer] = colour * lit[:, None]


def _sphere(centre, radius, colour, depth, image):
    """Rasterise the ball, so the fingers in front of it stay in front."""
    x0 = max(int(centre[0] - radius) - 1, 0)
    x1 = min(int(centre[0] + radius) + 2, WIDTH)
    y0 = max(int(centre[1] - radius) - 1, 0)
    y1 = min(int(centre[1] + radius) + 2, HEIGHT)
    if x0 >= x1 or y0 >= y1:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1]
    dx, dy = xs + 0.5 - centre[0], ys + 0.5 - centre[1]
    squared = radius * radius - dx * dx - dy * dy
    inside = squared >= 0
    dz = np.sqrt(np.where(inside, squared, 0.0))
    z = centre[2] + dz
    nearer = inside & (z > depth[y0:y1, x0:x1])
    if not nearer.any():
        return
    normals = np.stack([dx, dy, dz], axis=-1)
    lit = _shade(normals)[nearer]
    depth[y0:y1, x0:x1][nearer] = z[nearer]
    image[y0:y1, x0:x1][nearer] = colour * lit[:, None]


def render(vertices, faces, ball, radius_cm, azimuth=0.0, elevation=-0.05, zoom=1.0):
    """Paint one figure. Returns a Pillow image."""
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)
    centre = (lo + hi) / 2
    span = max(hi[1] - lo[1], 1.0)
    screen, k = project(vertices, centre, span, azimuth, elevation, zoom)
    ball_screen, _ = project(
        np.asarray([ball]), centre, span, azimuth, elevation, zoom
    )

    depth = np.full((HEIGHT, WIDTH), -np.inf)
    image = np.tile(SHEET, (HEIGHT, WIDTH, 1))
    _mesh(screen, faces, FIGURE, depth, image)
    _sphere(ball_screen[0], radius_cm * k, BALL, depth, image)
    return Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))


def main(argv: list[str]) -> int:
    movement_id = argv[1] if len(argv) > 1 else "netball_two_hand_snatch_pull_in"
    wanted = argv[2] if len(argv) > 2 else "contact"
    azimuth = float(argv[3]) if len(argv) > 3 else 0.0

    reason = smplx_body.missing()
    if reason:
        print(reason)
        return 1

    model = smplx_body.load()
    character = load_character()
    rest = joint_positions(
        character, np.zeros(character.parameter_transform.size, dtype=np.float32)
    )
    index = {n: i for i, n in enumerate(character.skeleton.joint_names)}
    shape = smplx_retarget.fit_shape(model, rest, index)

    result = solve_movement(character, movement_id)
    definition = load_definition(definition_path(movement_id))
    names = [phase.name for phase in definition.phases]
    if wanted not in names:
        print(f"{wanted} is not a phase of {movement_id}. It has: {names}")
        return 1
    phase = definition.phases[names.index(wanted)]

    frames = len(result["points"])
    number = max(0, min(frames - 1, round(phase.at_phase * (frames - 1))))
    theta, translation, worst, mean, shaped, rest_joints = smplx_retarget.fit(
        model, result["points"][number], result["index"], shape=shape
    )
    skin = smplx_retarget.skin(model, shaped, rest_joints, theta, translation)
    held = result["possession"].frames[number]

    image = render(
        np.asarray(skin, dtype=np.float64),
        np.asarray(model.faces, dtype=np.int64),
        np.asarray(held.centre, dtype=np.float64),
        result["radiusCm"],
        azimuth=azimuth,
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    view = {0.0: "front", 0.55: "quarter", 1.5708: "side"}.get(
        round(azimuth, 4), f"az{azimuth:g}"
    )
    path = OUTPUT / f"{movement_id}.{wanted}.{view}.png"
    image.save(path)
    print(
        f"{movement_id} {wanted} frame {number}, fit {mean:.2f} cm mean "
        f"{worst:.2f} cm worst -> {path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
