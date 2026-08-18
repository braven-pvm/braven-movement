"""Render a solved phase to a PNG, without a browser.

The manual takes pre-rendered images. The browser page is for turning the
figure round and judging it; this is for producing the picture that goes on the
page, and for looking at the figure when the preview pane will not composite.

The projection, the lighting and the culling match figure_check_template.html
exactly, so what this writes is what that page draws.

    pixi run python render_figure.py
    pixi run python render_figure.py netball_two_hand_snatch_pull_in contact
    pixi run python render_figure.py netball_two_hand_snatch_pull_in contact 0.55
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

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
SHEET = (27, 26, 23)
FIGURE = np.array([207.0, 199.0, 184.0])
BALL = (217, 123, 60)


def project(points, centre, span, azimuth, elevation, zoom):
    """The same projection the browser page uses."""
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


def render(vertices, faces, ball, radius_cm, azimuth=0.0, elevation=-0.05, zoom=1.0):
    """Paint one figure. Returns a Pillow image."""
    lo, hi = vertices.min(axis=0), vertices.max(axis=0)
    centre = (lo + hi) / 2
    span = max(hi[1] - lo[1], 1.0)
    screen, k = project(vertices, centre, span, azimuth, elevation, zoom)
    ball_screen, _ = project(
        np.asarray([ball]), centre, span, azimuth, elevation, zoom
    )
    ball_screen = ball_screen[0]

    a, b, c = (screen[faces[:, i]] for i in range(3))
    face_normal = np.cross(b - a, c - a)

    # Smooth normals: every vertex takes the sum of the faces it belongs to.
    normals = np.zeros_like(screen)
    for i in range(3):
        np.add.at(normals, faces[:, i], face_normal)

    front = face_normal[:, 2] >= 0
    corner = normals[faces[:, 0]] + normals[faces[:, 1]] + normals[faces[:, 2]]
    length = np.linalg.norm(corner, axis=1)
    length[length == 0] = 1.0
    towards = np.where(corner[:, 2] > 0, 1.0, -1.0)
    lambert = np.clip(towards * (corner @ LIGHT) / length, 0.0, None)
    lit = 0.34 + 0.66 * lambert
    depth = (a[:, 2] + b[:, 2] + c[:, 2]) / 3.0

    image = Image.new("RGB", (WIDTH, HEIGHT), SHEET)
    draw = ImageDraw.Draw(image)
    order = np.argsort(depth)
    order = order[front[order]]

    drawn_ball = False
    for t in order:
        if not drawn_ball and depth[t] > ball_screen[2]:
            draw.ellipse(
                [
                    ball_screen[0] - radius_cm * k,
                    ball_screen[1] - radius_cm * k,
                    ball_screen[0] + radius_cm * k,
                    ball_screen[1] + radius_cm * k,
                ],
                fill=BALL,
            )
            drawn_ball = True
        shade = tuple(int(v) for v in FIGURE * lit[t])
        draw.polygon(
            [tuple(a[t][:2]), tuple(b[t][:2]), tuple(c[t][:2])],
            fill=shade,
            outline=shade,
        )
    if not drawn_ball:
        draw.ellipse(
            [
                ball_screen[0] - radius_cm * k,
                ball_screen[1] - radius_cm * k,
                ball_screen[0] + radius_cm * k,
                ball_screen[1] + radius_cm * k,
            ],
            fill=BALL,
        )
    return image


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
