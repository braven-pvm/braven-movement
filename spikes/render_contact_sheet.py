"""Draw the movement as an SVG contact sheet, so a person can judge it.

The repository rule is that numeric limits never replace human visual
acceptance. A receipt full of passing angles proves nothing until somebody looks
at the pose. This writes a stick figure per phase, straight to SVG, with no
renderer and no dependencies beyond the solver that produced the motion.

    pixi run python render_contact_sheet.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from catch_solver import FRAME_COUNT, load_character, solve_catch  # noqa: E402
from segment_measures import elbow_flexion_degrees  # noqa: E402


# The chain of bones to draw. Each pair is one line segment.
BONES = [
    ("root", "c_spine2"),
    ("c_spine2", "c_neck"),
    ("c_neck", "c_head"),
    ("c_spine2", "l_clavicle"),
    ("l_clavicle", "l_uparm"),
    ("l_uparm", "l_lowarm"),
    ("l_lowarm", "l_wrist"),
    ("c_spine2", "r_clavicle"),
    ("r_clavicle", "r_uparm"),
    ("r_uparm", "r_lowarm"),
    ("r_lowarm", "r_wrist"),
    ("root", "l_upleg"),
    ("l_upleg", "l_lowleg"),
    ("l_lowleg", "l_foot"),
    ("root", "r_upleg"),
    ("r_upleg", "r_lowleg"),
    ("r_lowleg", "r_foot"),
]

PANELS = 6
PANEL_WIDTH = 190
PANEL_HEIGHT = 300


def solve_movement():
    """Solve the catch with the shared solver, so every script agrees."""
    result = solve_catch(load_character())
    return result["index"], result["points"]


def main() -> int:
    index, points_per_frame = solve_movement()

    frames = [round(i * (FRAME_COUNT - 1) / (PANELS - 1)) for i in range(PANELS)]
    all_points = [points_per_frame[frame] for frame in frames]

    # One shared scale, so the panels are comparable to each other.
    stacked = np.concatenate(all_points, axis=0)
    minimum = stacked.min(axis=0)
    maximum = stacked.max(axis=0)
    span = float(max(maximum[0] - minimum[0], maximum[1] - minimum[1])) or 1.0
    scale = (PANEL_HEIGHT - 60) / span
    centre_x = (minimum[0] + maximum[0]) / 2.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_WIDTH * PANELS}" '
        f'height="{PANEL_HEIGHT}" viewBox="0 0 {PANEL_WIDTH * PANELS} {PANEL_HEIGHT}">',
        '<rect width="100%" height="100%" fill="#12161c"/>',
    ]

    for panel, (frame, points) in enumerate(zip(frames, all_points)):
        origin_x = panel * PANEL_WIDTH
        phase = frame / (FRAME_COUNT - 1)

        def screen(name: str) -> tuple[float, float]:
            point = points[index[name]]
            x = origin_x + PANEL_WIDTH / 2 + (float(point[0]) - centre_x) * scale
            y = PANEL_HEIGHT - 30 - (float(point[1]) - minimum[1]) * scale
            return (x, y)

        parts.append(
            f'<rect x="{origin_x + 2}" y="2" width="{PANEL_WIDTH - 4}" '
            f'height="{PANEL_HEIGHT - 4}" fill="none" stroke="#232a34"/>'
        )
        for first, second in BONES:
            if first not in index or second not in index:
                continue
            x1, y1 = screen(first)
            x2, y2 = screen(second)
            arm = "arm" in first or "arm" in second or "wrist" in second
            colour = "#4ea1ff" if arm else "#8b98a8"
            width = 3.2 if arm else 2.4
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{colour}" stroke-width="{width}" stroke-linecap="round"/>'
            )
        for name in ("l_wrist", "r_wrist"):
            x, y = screen(name)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#ffb454"/>')

        elbow = elbow_flexion_degrees(
            shoulder=tuple(float(v) for v in points[index["l_uparm"]]),
            elbow=tuple(float(v) for v in points[index["l_lowarm"]]),
            wrist=tuple(float(v) for v in points[index["l_wrist"]]),
        )
        label = "contact" if abs(phase - 0.55) < 0.08 else f"{phase * 100:.0f}%"
        parts.append(
            f'<text x="{origin_x + 10}" y="22" fill="#e6edf3" '
            f'font-family="system-ui,sans-serif" font-size="13">{label}</text>'
        )
        parts.append(
            f'<text x="{origin_x + 10}" y="{PANEL_HEIGHT - 10}" fill="#9aa7b4" '
            f'font-family="system-ui,sans-serif" font-size="11">'
            f'left elbow {elbow:.0f}&#176;</text>'
        )

    parts.append("</svg>")

    output = SPIKE_DIR / "poc-output" / "braven_catch_contact_sheet.svg"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(parts), encoding="utf-8")
    print(f"contact sheet: {output}")
    print(f"panels: {PANELS} of {FRAME_COUNT} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
