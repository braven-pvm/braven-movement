"""Produce a manual page for every drill: the manual's words, and a figure.

This is the first thing the engine is actually for. The coaches manual gives a
drill a title, an objective, a numbered list of instructions, and a photograph.
Everything except the photograph already exists in the repository. This makes
the photograph, from the solve, at the phases the coaching definition already
names.

A rendered figure has one advantage a photograph does not: the manual shows one
moment, and this shows the moments a coach is actually watching for. The phases
are not chosen here, they come from the coaching definition, which is where a
coach would set them.

The body is SMPL-X, posed by fitting it to the solved MHR joint centres. MHR
ships one body and no way to change its build, and the figure in a manual has
to look like the athlete the manual is for. The solve is untouched: SMPL-X is
worn, not solved on. Refer to smplx_retarget.py, and to LICENCE-RISK.md for the
licence this is under.

If the SMPL-X model is not installed it falls back to MHR's own skin and says
so, so the page still builds.

    pixi run python export_manual_page.py
    pixi run python export_manual_page.py netball_two_hand_snatch_pull_in
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from ball_track import has_ball  # noqa: E402
from export_mesh_viewer import VIEWER_LOD, load_mesh_character  # noqa: E402
from manual_source import for_movement, load as load_manual  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from movement_engine import definition_path, library  # noqa: E402
import smplx_body  # noqa: E402
import smplx_retarget  # noqa: E402
from movement_engine import joint_positions, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output"
TEMPLATE = SPIKE_DIR / "manual_page_template.html"


def figure(character, result: dict, phase: float, body=None) -> dict:
    """The athlete, skinned, at one coaching phase."""
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
        # Whole centimetres. The figure is drawn at about two pixels per
        # centimetre, so a decimal place buys half a pixel and costs a third of
        # the page.
        "v": [round(float(value)) for value in skin.reshape(-1)],
        "ball": [round(float(value), 1) for value in held.centre],
        "holding": held.holding,
        "fit": fit_error,
    }


def build(character, movement_id: str, drills: dict, body=None) -> dict:
    definition = load_definition(definition_path(movement_id))
    result = solve_movement(character, movement_id)
    manual = for_movement(movement_id, drills)

    figures = []
    for phase in definition.phases:
        drawn = figure(character, result, phase.at_phase, body)
        drawn["name"] = phase.name
        # The measured cues, which the manual does not have and a lab does.
        drawn["measured"] = [
            {
                "measure": check.measure,
                "band": [check.minimum_degrees, check.maximum_degrees],
            }
            for check in phase.checkpoints
        ]
        figures.append(drawn)

    return {
        "movementId": movement_id,
        "skill": definition.skill,
        "sport": definition.sport,
        "manual": None
        if manual is None
        else {
            "title": manual.title,
            "intro": list(manual.intro),
            "steps": list(manual.steps),
        },
        "figures": figures,
        "ballRadiusCm": result["radiusCm"],
        "framesPerSecond": result["track"].frames_per_second,
    }


def main(argv: list[str]) -> int:
    wanted = argv[1:] or [
        name
        for name in library()
        if has_ball(name)
        and has_technique(name)
        and load_technique(technique_path(name)).possession_ready
    ]
    character = load_mesh_character()
    drills = load_manual()

    # The figure is SMPL-X where it is installed, and MHR's own skin where it
    # is not, so a missing model file costs the look and not the build.
    body, faces, wearing = None, None, "MHR"
    reason = smplx_body.missing()
    if reason:
        print("SMPL-X not installed, drawing MHR instead.")
        print(f"  {reason}")
    else:
        model = smplx_body.load()
        solver = load_character()
        rest = joint_positions(
            solver, np.zeros(solver.parameter_transform.size, dtype=np.float32)
        )
        index = {n: i for i, n in enumerate(solver.skeleton.joint_names)}
        shape = smplx_retarget.fit_shape(model, rest, index)
        shaped, _ = model.body(shape)
        merge, reduced = smplx_body.decimate(shaped * 100.0, model.faces)
        body = (model, shape, merge)
        faces = np.asarray(reduced, dtype=np.int32)
        print(
            f"  mesh reduced to {int(merge.max()) + 1} vertices and "
            f"{len(reduced)} faces for drawing"
        )
        wearing = "SMPL-X"
        print(f"SMPL-X fitted to the athlete: shape {np.round(shape, 2)}")
    if faces is None:
        faces = np.asarray(character.mesh.faces, dtype=np.int32)

    pages = [build(character, movement_id, drills, body) for movement_id in wanted]
    quoted = sum(1 for page in pages if page["manual"])
    payload = {
        "faces": [int(value) for value in faces.reshape(-1)],
        "levelOfDetail": VIEWER_LOD,
        "wearing": wearing,
        "pages": pages,
    }
    page = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(payload)
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "manual.html"
    path.write_text(page, encoding="utf-8")
    print(
        f"{len(pages)} pages, {quoted} quoting the manual directly, "
        f"{len(faces)} faces -> {path} ({path.stat().st_size // 1024} KB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
