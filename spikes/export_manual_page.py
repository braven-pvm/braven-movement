"""Produce a manual page for every drill: the manual's words, and a figure.

This is the first thing the engine is actually for. The coaches manual gives a
drill a title, an objective, a numbered list of instructions, and a photograph.
Everything except the photograph already exists in the repository. This makes
the photograph, at the phases the coaching definition already names.

A rendered figure has one advantage a photograph does not: the manual shows one
moment, and this shows the moments a coach is actually watching for. The phases
are not chosen here, they come from the coaching definition, which is where a
coach would set them.

The figures are Blender stills of the MPFB athlete, made by
`blender_movement_render.py` from the job that `export_blender_job.py` writes.
They arrive with kit, materials and studio lighting. This page assembles them
and does not solve, pose or render anything itself.

It drew an SMPL-X body through a numpy rasteriser before. SMPL-X is under a
research licence and may not be sold without a licence from the Max Planck
Institute, so it does not belong on the path that makes the product. Refer to
LICENCE-RISK.md. MPFB output is CC0. Refer to docs/LICENSING.md.

Render the drills first, from the repository root:

    blender -b -P blender_movement_render.py -- --job <each> --output out/manual

Then build the page:

    pixi run python export_manual_page.py --renders ../out/manual
    pixi run python export_manual_page.py --renders ../out/manual --view side
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
# `render_receipt.py` is the repository's bpy-free rule module and it lives at
# the root, beside the renderer that writes these receipts.
sys.path.insert(0, str(SPIKE_DIR.parent))

from manual_source import for_movement, load as load_manual  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from render_receipt import (  # noqa: E402
    refuse_partial_receipt,
    undrawn_phases,
)
from movement_engine import definition_path  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output"
TEMPLATE = SPIKE_DIR / "manual_page_template.html"
DEFAULT_RENDERS = SPIKE_DIR.parent / "out" / "manual"

# A manual figure is printed about 150 points wide. This is that at three
# times, which stays crisp on a dense screen and keeps a page of eight drills
# inside a couple of megabytes.
FIGURE_WIDTH = 480
FIGURE_QUALITY = 82


def figure_data_uri(path: Path) -> tuple[str, int]:
    """The rendered still, narrowed and encoded for the page.

    The page carries its pictures rather than pointing at them, because it is
    published as a single file and a strict content policy blocks any request
    to another host. The full render is about 1.5 MB and thirty three of them
    would not fit.
    """
    with Image.open(path) as image:
        image = image.convert("RGB")
        height = round(image.height * FIGURE_WIDTH / image.width)
        image = image.resize((FIGURE_WIDTH, height), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=FIGURE_QUALITY, optimize=True)
    raw = buffer.getvalue()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"), len(raw)


def still_path(recorded: str, renders: Path) -> Path:
    """Where the still actually is now.

    The receipt records the absolute path of the machine that rendered it, so
    a render directory that has been moved or copied leaves every one of them
    pointing nowhere. The file name is the stable part.
    """
    beside = renders / Path(recorded).name
    if beside.is_file():
        return beside
    return Path(recorded)


def undrawn_figure(entry: dict) -> str:
    """A visible slot saying the phase was not drawn, and why.

    The template emits `<img src=...>` for every figure, so a placeholder has
    to BE an image or the reader gets a broken box with no words in it.
    """
    reason = str(entry.get("error", "no reason recorded"))
    words = [reason[i:i + 46] for i in range(0, min(len(reason), 184), 46)]
    lines = "".join(
        f'<text x="8" y="{70 + n * 14}" font-family="monospace" '
        f'font-size="10" fill="#b23">{word}</text>'
        for n, word in enumerate(words)
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="150">'
        '<rect width="300" height="150" fill="#fdf2f2" stroke="#b23" '
        'stroke-width="2" stroke-dasharray="6 4"/>'
        f'<text x="8" y="28" font-family="sans-serif" font-size="15" '
        f'fill="#b23">NOT DRAWN: {entry.get("name", "?")}</text>'
        '<text x="8" y="48" font-family="sans-serif" font-size="11" '
        'fill="#b23">this phase could not be posed</text>'
        f'{lines}</svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(
        svg.encode("utf-8")).decode("ascii")


def build(
    movement_id: str, receipt: dict, job: dict, drills: dict, view: str, renders: Path
) -> dict:
    definition = load_definition(definition_path(movement_id))
    manual = for_movement(movement_id, drills)
    bands = {
        phase.name: [
            {
                "measure": check.measure,
                "band": [check.minimum_degrees, check.maximum_degrees],
            }
            for check in phase.checkpoints
        ]
        for phase in definition.phases
    }
    holding = {phase["name"]: phase["ball"]["holding"] for phase in job["phases"]}

    figures, embedded = [], 0
    # A PHASE THAT COULD NOT BE DRAWN STILL TAKES ITS PLACE ON THE PAGE. The
    # caller has already been refused unless it passed --allow-partial, so
    # reaching here means the omission is deliberate and must be VISIBLE.
    for entry in undrawn_phases(receipt):
        figures.append({
            "name": entry.get("name", "?"),
            "frame": entry.get("frame", -1),
            "image": undrawn_figure(entry),
            "holding": False,
            "measured": [],
            "undrawn": entry.get("error", "no reason recorded"),
        })
    for phase in receipt["phases"]:
        rendered = phase["views"].get(view)
        if rendered is None:
            raise SystemExit(
                f"{movement_id} {phase['name']} has no {view} view. "
                f"It has {sorted(phase['views'])}."
            )
        still = still_path(rendered["path"], renders)
        if not still.is_file():
            raise SystemExit(
                f"{movement_id} {phase['name']} {view} is missing: {still}"
            )
        uri, size = figure_data_uri(still)
        embedded += size
        figures.append(
            {
                "name": phase["name"],
                "frame": phase["frame"],
                "image": uri,
                "holding": holding.get(phase["name"], False),
                "measured": bands.get(phase["name"], []),
            }
        )

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
        "ballRadiusCm": round(job["phases"][0]["ball"]["radiusM"] * 100.0, 1),
        "framesPerSecond": job["framesPerSecond"],
        "figureBytes": embedded,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("movements", nargs="*", default=None)
    parser.add_argument("--renders", type=Path, default=DEFAULT_RENDERS)
    parser.add_argument("--jobs", type=Path, default=OUTPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT / "manual.html")
    parser.add_argument("--view", default="quarter")
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="build a page for a drill the renderer could not fully draw. "
             "Each undrawn phase gets a visible slot naming its reason. "
             "Without this the run refuses, because a page with fewer figures "
             "than the drill has and no notice is worse than no page.")
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    renders = args.renders.resolve()
    if not renders.is_dir():
        raise SystemExit(
            f"no render directory at {renders}. Run blender_movement_render.py "
            f"first, with --output {renders}."
        )

    receipts = sorted(renders.glob("*.render.json"))
    wanted = args.movements or [path.name[: -len(".render.json")] for path in receipts]
    drills = load_manual()

    pages, missing = [], []
    for movement_id in wanted:
        receipt_path = renders / f"{movement_id}.render.json"
        job_path = args.jobs / f"{movement_id}.job.json"
        if not receipt_path.is_file() or not job_path.is_file():
            missing.append(movement_id)
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        # REFUSED BEFORE A PAGE IS BUILT, not after. `failedPhases` is newer
        # than this reader, and a reader that predates it sees a SHORT list of
        # phases and nothing else.
        refuse_partial_receipt(movement_id, receipt, args.allow_partial)
        pages.append(
            build(
                movement_id,
                receipt,
                json.loads(job_path.read_text(encoding="utf-8")),
                drills,
                args.view,
                renders,
            )
        )

    if not pages:
        raise SystemExit(f"no drill has both a render and a job under {renders}")

    payload = {
        "figures": f"Blender 4.5 and MPFB, {args.view} view",
        "pages": pages,
    }
    page = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(payload)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8")

    quoted = sum(1 for page_data in pages if page_data["manual"])
    drawn = sum(len(page_data["figures"]) for page_data in pages)
    print(
        f"{len(pages)} pages, {quoted} quoting the manual directly, "
        f"{drawn} figures -> {args.output} "
        f"({args.output.stat().st_size // 1024} KB)"
    )
    for name in missing:
        print(f"  no render or job for {name}, so it has no page")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
