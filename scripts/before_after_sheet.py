"""Two builds of the same figure, side by side, with the difference measured.

A before-and-after sheet is asked to answer one question: did this change. An
eye is bad at that question. This lane once reported two renders IDENTICAL from
looking at them, and a pixel comparison showed they were not; on the same day it
reported a change that turned out to be a frame of camera handling. Both were
read off pictures.

So every row here carries a NUMBER as well as the two pictures: what fraction of
the figure's pixels moved, and by how much. A reader who disagrees with the
number can look, and a reader who cannot see the change is told whether there is
one to see.

    changed  the share of pixels differing by more than 8 of 255, which is
             above the renderer's own sampling noise and below anything a
             person would call a change
    worst    the largest single-pixel difference anywhere in the frame

THE BUILD IS READ FROM EACH SIDE'S RECEIPT, never from the directory name. A
directory called "after" is a claim; `build.commit` in the receipt beside the
picture is a reading. Where a receipt carries no build, the sheet says so
rather than leaving the column blank, because these pictures predate the stamp
and that is exactly the gap the stamp was added to close.

    python before_after_sheet.py --before <dir> --after <dir> \
        --drill netball_hooks_outside_hand --view front --out sheet.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import numpy
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - the rules below need neither
    numpy = None
    Image = ImageDraw = ImageFont = None

MOVED = 8          # out of 255, per channel
BAND = 0.001       # below this share, call it unchanged


def require_imaging() -> None:
    if Image is None or numpy is None:
        raise RuntimeError(
            "drawing a sheet needs Pillow and numpy: "
            "python -m pip install pillow numpy"
        )


def build_of(directory: Path, drill: str) -> str:
    """What build drew these pictures, from the receipt beside them.

    Never from the directory's name. A folder called "after" asserts a build;
    the receipt records one.
    """
    receipt = directory / f"{drill}.render.json"
    if not receipt.exists():
        return "no receipt"
    try:
        document = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "receipt unreadable"
    stamp = document.get("build")
    if not stamp:
        # Every receipt written before 2026-09-02 is in this state, which is
        # the whole reason the stamp exists. Say it rather than leave a blank.
        return "UNSTAMPED, predates the build stamp"
    commit = str(stamp.get("commit", "unknown"))[:7]
    return commit if stamp.get("treeWasClean") else f"{commit} DIRTY TREE"


def difference(before, after) -> dict:
    """How much of the figure moved between two renders of it."""
    first = numpy.asarray(before.convert("RGB"), dtype=numpy.int16)
    second = numpy.asarray(after.convert("RGB"), dtype=numpy.int16)
    if first.shape != second.shape:
        return {"comparable": False, "changedShare": None, "worst": None}
    gap = numpy.abs(first - second)
    moved = (gap.max(axis=2) > MOVED)
    return {
        "comparable": True,
        "changedShare": float(moved.mean()),
        "worst": int(gap.max()),
    }


def verdict(reading: dict) -> str:
    """Say what the number means, so a reader does not have to decide."""
    if not reading["comparable"]:
        return "NOT COMPARABLE, the two renders are different sizes"
    if reading["changedShare"] < BAND:
        return "unchanged to the eye"
    return f"{reading['changedShare']:.1%} of pixels moved"


def phases_in(directory: Path, drill: str, view: str) -> list[str]:
    """The phase names present for this drill and view, in file order."""
    found = []
    for path in sorted(directory.glob(f"{drill}.*.{view}.png")):
        parts = path.name.split(".")
        if len(parts) >= 3:
            found.append(parts[-3])
    return found


def load_font(size: int):
    require_imaging()
    for name in ("consola.ttf", "arial.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_sheet(before: Path, after: Path, drill: str, view: str, out: Path,
                height: int = 420) -> dict:
    require_imaging()
    label, head = load_font(14), load_font(19)
    shared = [p for p in phases_in(before, drill, view)
              if p in phases_in(after, drill, view)]
    if not shared:
        raise SystemExit(
            f"no phase of {drill} view {view} exists in BOTH directories. "
            f"before has {phases_in(before, drill, view)}, "
            f"after has {phases_in(after, drill, view)}"
        )

    rows, report = [], []
    for phase in shared:
        first = Image.open(before / f"{drill}.{phase}.{view}.png")
        second = Image.open(after / f"{drill}.{phase}.{view}.png")
        reading = difference(first, second)
        width = max(1, round(first.width * height / first.height))
        rows.append((phase, first.resize((width, height), Image.LANCZOS),
                     second.resize((width, height), Image.LANCZOS), reading))
        report.append({"phase": phase, **reading, "verdict": verdict(reading)})

    gap, strip, pad, header = 8, 40, 14, 82
    cell = rows[0][1].width
    sheet = Image.new(
        "RGB",
        (pad * 2 + len(rows) * (cell * 2 + gap) + (len(rows) - 1) * pad,
         header + pad + height + strip),
        (24, 24, 27),
    )
    canvas = ImageDraw.Draw(sheet)
    canvas.text((pad, 10), f"{drill.replace('netball_', '')}, {view} view: "
                "before and after the hand mirror fix", font=head,
                fill=(240, 240, 245))
    canvas.text((pad, 36), f"LEFT of each pair {build_of(before, drill)}    "
                f"RIGHT of each pair {build_of(after, drill)}",
                font=label, fill=(170, 200, 240))
    canvas.text((pad, 56), "the share of pixels that moved is measured, not "
                "judged: an eye is bad at 'did this change'.",
                font=label, fill=(170, 170, 180))

    x = pad
    for phase, first, second, reading in rows:
        sheet.paste(first, (x, header + pad))
        sheet.paste(second, (x + cell + gap, header + pad))
        changed = reading["comparable"] and reading["changedShare"] >= BAND
        canvas.text((x, header + pad + height + 6), phase, font=label,
                    fill=(235, 235, 240))
        canvas.text((x, header + pad + height + 22), verdict(reading),
                    font=label,
                    fill=(240, 170, 120) if changed else (150, 190, 150))
        x += cell * 2 + gap + pad

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return {"sheet": str(out), "drill": drill, "view": view,
            "beforeBuild": build_of(before, drill),
            "afterBuild": build_of(after, drill), "phases": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--drill", required=True)
    parser.add_argument("--view", default="front")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--height", type=int, default=420)
    arguments = parser.parse_args(argv)

    receipt = build_sheet(arguments.before, arguments.after, arguments.drill,
                          arguments.view, arguments.out, arguments.height)
    arguments.out.with_suffix(".json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    moved = [p for p in receipt["phases"]
             if p["comparable"] and p["changedShare"] >= BAND]
    print(f"{arguments.out}  {len(receipt['phases'])} phases, "
          f"{len(moved)} changed")
    for phase in receipt["phases"]:
        print(f"   {phase['phase']:<12} {phase['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
