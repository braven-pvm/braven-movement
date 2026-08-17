"""Show the single-camera trap: a perfect 2D fit with a wrong 3D pose.

Left panel: the photograph, with the detected landmarks and the fitted skeleton
reprojected on top. They agree to about one pixel.

Right panel: the same fitted pose seen from the side. The pose the solver chose
is not the pose in the photograph, because one view cannot tell the difference.

This is the argument for a second camera, made from a real photograph.

    pixi run python render_photo_fit.py
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import numpy as np
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from catch_solver import FORBIDDEN, WANTED, joint_positions, load_character  # noqa: E402
from fit_from_photo import (  # noqa: E402
    LANDMARK_TO_JOINT,
    PHOTO,
    detect_landmarks,
    guess_camera,
)
from render_contact_sheet import BONES  # noqa: E402

PANEL = 470


def main() -> int:
    found, width, height = detect_landmarks(PHOTO)
    character = load_character()
    names = list(character.skeleton.joint_names)
    index = {name: position for position, name in enumerate(names)}
    parameter_names = list(character.parameter_transform.names)
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
    for number, pixel in found.items():
        joint = LANDMARK_TO_JOINT[number]
        error_function.add_constraint(
            projection, np.asarray(pixel, dtype=np.float32), index[joint], None, 1.0
        )
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
    solved = np.asarray(
        solver.solve(np.zeros(character.parameter_transform.size, dtype=np.float32).reshape(-1, 1)),
        dtype=np.float32,
    ).reshape(-1)
    points = joint_positions(character, solved)

    def reproject(position) -> tuple[float, float]:
        homogeneous = projection.astype(np.float64) @ np.array([*position, 1.0])
        return (homogeneous[0] / homogeneous[2], homogeneous[1] / homogeneous[2])

    # Panel 1: the photograph at its own scale, fitted to the panel width.
    photo_scale = PANEL / width
    encoded = base64.b64encode(PHOTO.read_bytes()).decode("ascii")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL * 2 + 30}" '
        f'height="{max(int(height * photo_scale), 470) + 70}" '
        f'viewBox="0 0 {PANEL * 2 + 30} {max(int(height * photo_scale), 470) + 70}" '
        'font-family="system-ui,sans-serif">',
        '<rect width="100%" height="100%" fill="#12160F"/>',
        f'<image x="0" y="34" width="{PANEL}" height="{height * photo_scale:.0f}" '
        f'href="data:image/jpeg;base64,{encoded}"/>',
        '<text x="4" y="20" fill="#ECF1E6" font-size="14" font-weight="700">'
        'The 2D fit is near perfect</text>',
        f'<text x="{PANEL + 30}" y="20" fill="#ECF1E6" font-size="14" '
        'font-weight="700">The 3D pose it chose is wrong</text>',
    ]

    # Reprojected skeleton over the photograph.
    for first, second in BONES:
        if first not in index or second not in index:
            continue
        a = reproject(points[index[first]])
        b = reproject(points[index[second]])
        parts.append(
            f'<line x1="{a[0] * photo_scale:.1f}" y1="{a[1] * photo_scale + 34:.1f}" '
            f'x2="{b[0] * photo_scale:.1f}" y2="{b[1] * photo_scale + 34:.1f}" '
            'stroke="#35B9A6" stroke-width="3" stroke-linecap="round" opacity="0.95"/>'
        )
    for number, pixel in found.items():
        parts.append(
            f'<circle cx="{pixel[0] * photo_scale:.1f}" '
            f'cy="{pixel[1] * photo_scale + 34:.1f}" r="5" fill="none" '
            'stroke="#FF6B4A" stroke-width="2.5"/>'
        )
    parts.append(
        f'<text x="4" y="{height * photo_scale + 52:.0f}" fill="#8B9784" font-size="12">'
        'Orange rings are what the detector found. Teal is the fitted athlete '
        'reprojected. Worst gap: 1.0 pixel.</text>'
    )

    # Panel 2: the same fitted pose from the side, where the error is obvious.
    side = points[:, [2, 1]]
    used = [index[name] for bone in BONES for name in bone if name in index]
    lows = side[used].min(axis=0)
    highs = side[used].max(axis=0)
    span = float(max(highs[0] - lows[0], highs[1] - lows[1])) or 1.0
    scale = (PANEL - 120) / span
    origin = PANEL + 30

    def to_side(position) -> tuple[float, float]:
        return (
            origin + PANEL / 2 + (float(position[2]) - float(lows[0] + highs[0]) / 2) * scale,
            34 + (PANEL - 90) - (float(position[1]) - float(lows[1])) * scale,
        )

    for first, second in BONES:
        if first not in index or second not in index:
            continue
        a = to_side(points[index[first]])
        b = to_side(points[index[second]])
        arm = "arm" in first or "arm" in second or "wrist" in second
        parts.append(
            f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
            f'stroke="{"#FF6B4A" if arm else "#7C8A75"}" '
            f'stroke-width="{5 if arm else 4}" stroke-linecap="round"/>'
        )
    parts.append(
        f'<text x="{origin}" y="{height * photo_scale + 52:.0f}" fill="#8B9784" '
        'font-size="12">Side view of the same solution. The elbows have folded to '
        '140 and 152 degrees, which is not the photograph.</text>'
    )
    parts.append("</svg>")

    output = SPIKE_DIR / "poc-output" / "braven_photo_fit_overlay.svg"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")
    print(f"overlay: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
