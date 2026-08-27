"""One figure, full size, so the body can be judged rather than guessed at.

The manual page draws four figures 150 pixels wide. That is the right size for
a manual and the wrong size for deciding whether the shading is correct, the
build is right, or the hands are where they should be. Three rendering faults
in a row survived that page and were only obvious once the figure was large.

    pixi run python export_figure_check.py
    pixi run python export_figure_check.py netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

import pymomentum.geometry as geometry  # noqa: E402

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
TEMPLATE = SPIKE_DIR / "figure_check_template.html"
DEFAULT = "netball_two_hand_snatch_pull_in"

# A manual figure is 150 pixels wide and this one is about 900. Both dials
# below are set for that. The mesh is not merged at all, because facets that
# vanish at 150 pixels are plain at 900. Vertices are in fifths of a
# centimetre, because at five pixels per centimetre whole centimetres snap
# every vertex to a five pixel grid and the smooth normals come out looking
# like scales. The page is served over HTTP, so its size is not the
# constraint it is for the manual.
GRID_CM = None
VERTEX_SCALE = 5


def figure(
    character, result: dict, phase: float, body=None, scale: int = 1
) -> dict:
    """The athlete, skinned, at one coaching phase.

    Vertices come back as integers in units of 1/scale centimetres. The
    drawing divides by the same number.

    This lived in export_manual_page.py, which drew the same figure. The
    manual page now shows Blender stills, so this is the only caller and the
    only place SMPL-X still reaches a page. Refer to LICENCE-RISK.md.
    """
    frames = len(result["points"])
    number = max(0, min(frames - 1, round(phase * (frames - 1))))
    fit_error = None
    if body is None:
        state = geometry.model_parameters_to_skeleton_state(
            character, np.asarray(result["motion"][number], dtype=np.float32)
        )
        skin = np.asarray(character.skin_points(state), dtype=np.float64)
    else:
        model, shape, merge = body
        theta, translation, worst, mean, shaped, rest = smplx_retarget.fit(
            model, result["points"][number], result["index"], shape=shape
        )
        skin = smplx_retarget.skin(model, shaped, rest, theta, translation)
        # The same merge every frame, so the faces stay valid.
        merged = np.zeros((int(merge.max()) + 1, 3), dtype=np.float64)
        np.add.at(merged, merge, skin)
        counts = np.bincount(merge, minlength=len(merged)).reshape(-1, 1)
        skin = merged / np.maximum(counts, 1)
        fit_error = {"worstCm": round(worst, 2), "meanCm": round(mean, 2)}
    held = result["possession"].frames[number]
    return {
        "frame": number,
        # Integers, in units of 1/scale centimetres. A manual figure is drawn
        # at about two pixels per centimetre, where whole centimetres cost
        # half a pixel. A full size figure is drawn at five, where whole
        # centimetres snap every vertex to a five pixel grid and the smooth
        # normals come out faceted.
        "v": [round(float(value) * scale) for value in skin.reshape(-1)],
        "ball": [round(float(value), 1) for value in held.centre],
        "holding": held.holding,
        "fit": fit_error,
    }


def main(argv: list[str]) -> int:
    movement_id = argv[1] if len(argv) > 1 else DEFAULT
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
    shaped, _ = model.body(shape)
    if GRID_CM is None:
        merge = np.arange(len(shaped))
        faces = np.asarray(model.faces)
    else:
        merge, faces = smplx_body.decimate(shaped * 100.0, model.faces, GRID_CM)
    body = (model, shape, merge)

    result = solve_movement(character, movement_id)
    definition = load_definition(definition_path(movement_id))
    figures = []
    for phase in definition.phases:
        drawn = figure(character, result, phase.at_phase, body, VERTEX_SCALE)
        drawn["name"] = phase.name
        figures.append(drawn)

    payload = {
        "heading": f"{definition.skill}, full size",
        "faces": [int(v) for v in np.asarray(faces).reshape(-1)],
        "vertexScale": VERTEX_SCALE,
        "ballRadiusCm": result["radiusCm"],
        "figures": figures,
    }
    page = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(payload)
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"{movement_id}.figure.html"
    path.write_text(page, encoding="utf-8")
    print(
        f"{len(figures)} phases, {int(merge.max()) + 1} vertices, {len(faces)} "
        f"faces -> {path} ({path.stat().st_size // 1024} KB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
