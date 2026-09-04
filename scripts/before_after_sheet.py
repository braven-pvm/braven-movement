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
    # `generatedFrom` FIRST, because that is the repository's one stamp and
    # what every receipt written after 2026-09-02 carries.
    #
    # THE WRITER WAS CONVERGED AND THIS READER WAS NOT, for one commit, and the
    # result was precisely backwards: a fresh receipt read "UNSTAMPED" while an
    # archived pre-convergence one read its commit correctly. The single
    # consumer of the stamp could not read the stamp. Converging a contract
    # means both ends of it.
    stamp = document.get("generatedFrom")
    retired = False
    if not stamp:
        # `build` is the retired name this lane briefly wrote. It is read only
        # so the ARCHIVED interim set stays legible, and it is labelled, so no
        # reader mistakes a receipt from that window for a current one.
        stamp = document.get("build")
        retired = bool(stamp)
    if not stamp:
        # Every receipt written before 2026-09-02 is in this state, which is
        # the whole reason the stamp exists. Say it rather than leave a blank.
        return "UNSTAMPED, predates the build stamp"
    commit = str(stamp.get("commit", "unknown"))[:7]
    if not stamp.get("treeWasClean"):
        commit = f"{commit} DIRTY TREE"
    return f"{commit} (retired `build` field)" if retired else commit


def labelled(read: str, caption: str | None) -> str:
    """The column's header: what the receipts say, or an honest caption.

    SOME BUILDS CANNOT NAME THEMSELVES. Erin's page cites `02b25cd` for its
    animations, and every receipt from that build predates the stamp tool, so
    `build_of` reads UNSTAMPED and is right to. The build is known from the
    page's own build line, which is a CAPTION and not a reading.

    A caption is allowed and is marked as one, so a reader can tell a column
    whose provenance was read from a column whose provenance was asserted by a
    person. The alternative — re-solving that build to manufacture a stamp —
    would produce a receipt that names a build these pictures did not come
    from, which is the fault the stamp exists to prevent.
    """
    if not caption:
        return read
    return f"{caption} (captioned, receipts read: {read})"


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


def build_sheet(columns: list[Path], drill: str, view: str, out: Path,
                height: int = 420, caption: str = "",
                captions: list[str] | None = None) -> dict:
    """Any number of builds of one drill, measured against the FIRST.

    Two columns was not enough. A three-state record — what a coach graded,
    what an intermediate build drew, and what the corrected build draws — needs
    the middle column to be unmistakably the middle. So every column is
    labelled by the BUILD read from its own receipt, never by its position, and
    "middle" can never be read as "after".
    """
    require_imaging()
    captions = captions or []
    label, head = load_font(14), load_font(19)
    if len(columns) < 2:
        raise SystemExit("give at least two builds to compare")

    shared = [p for p in phases_in(columns[0], drill, view)
              if all(p in phases_in(c, drill, view) for c in columns[1:])]
    if not shared:
        raise SystemExit(
            f"no phase of {drill} view {view} exists in EVERY build given: "
            + "; ".join(f"{c.name} has {phases_in(c, drill, view)}"
                        for c in columns)
        )

    builds = [labelled(build_of(c, drill), captions[index] if index < len(captions) else None)
              for index, c in enumerate(columns)]
    rows, report = [], []
    for phase in shared:
        pictures = [Image.open(c / f"{drill}.{phase}.{view}.png") for c in columns]
        # Against the FIRST build, so the number answers "has this figure
        # changed since THAT BUILD drew it".
        #
        # DO NOT CALL THE FIRST COLUMN "what a coach graded" unless it is. This
        # tool cannot know which build a coach saw. On the pack that produced
        # it the first column was the last batch before the fix, 31 Aug, while
        # Erin graded the 27 Aug set. Both predate the fix, so the sheet was
        # not wrong and the sentence would have been. Name the build; let the
        # caller say what it was.
        readings = [difference(pictures[0], later) for later in pictures[1:]]
        width = max(1, round(pictures[0].width * height / pictures[0].height))
        rows.append((phase,
                     [i.resize((width, height), Image.LANCZOS) for i in pictures],
                     readings))
        report.append({
            "phase": phase,
            "againstBuild": builds[0],
            "columns": [{"build": builds[index + 1], **reading,
                         "verdict": verdict(reading)}
                        for index, reading in enumerate(readings)],
        })

    gap, strip, pad, header = 8, 56, 14, 100
    cell = rows[0][1][0].width
    group = cell * len(columns) + gap * (len(columns) - 1)
    sheet = Image.new(
        "RGB",
        (pad * 2 + len(rows) * group + (len(rows) - 1) * pad,
         header + pad + height + strip),
        (24, 24, 27),
    )
    canvas = ImageDraw.Draw(sheet)
    canvas.text((pad, 10), f"{drill.replace('netball_', '')}, {view} view",
                font=head, fill=(240, 240, 245))
    canvas.text((pad, 36), "columns, left to right:  "
                + "   |   ".join(builds), font=label, fill=(170, 200, 240))
    canvas.text((pad, 56), "the share of pixels that moved is measured against "
                f"the FIRST column ({builds[0]}), not judged by eye.",
                font=label, fill=(170, 170, 180))
    if caption:
        canvas.text((pad, 76), caption, font=label, fill=(255, 170, 120))

    x = pad
    for phase, pictures, readings in rows:
        for index, picture in enumerate(pictures):
            sheet.paste(picture, (x + index * (cell + gap), header + pad))
        canvas.text((x, header + pad + height + 6), phase, font=label,
                    fill=(235, 235, 240))
        line = header + pad + height + 22
        for index, reading in enumerate(readings):
            changed = reading["comparable"] and reading["changedShare"] >= BAND
            canvas.text((x, line), f"{builds[index + 1]}: {verdict(reading)}",
                        font=label,
                        fill=(240, 170, 120) if changed else (150, 190, 150))
            line += 16
        x += group + pad

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return {"sheet": str(out), "drill": drill, "view": view,
            "builds": builds, "measuredAgainst": builds[0],
            "caption": caption, "phases": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="append", required=True, type=Path,
                        metavar="DIR",
                        help="a directory of renders, repeatable. The FIRST is "
                             "the reference every later one is measured against")
    parser.add_argument("--drill", required=True)
    parser.add_argument("--view", default="front")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--height", type=int, default=420)
    parser.add_argument("--column-caption", action="append", default=[],
                        metavar="TEXT",
                        help="per column, in the same order as --build. Names "
                             "a build the receipts cannot name, marked on the "
                             "sheet as a caption rather than a reading. Pass "
                             "an empty string to leave a column read-only.")
    parser.add_argument("--caption", default="",
                        help="a line printed on the sheet, for saying what a "
                             "column IS when its build alone does not say")
    arguments = parser.parse_args(argv)

    receipt = build_sheet(arguments.build, arguments.drill, arguments.view,
                          arguments.out, arguments.height, arguments.caption,
                          arguments.column_caption)
    arguments.out.with_suffix(".json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(f"{arguments.out}  {len(receipt['phases'])} phases, "
          f"{len(receipt['builds'])} builds, measured against "
          f"{receipt['measuredAgainst']}")
    for phase in receipt["phases"]:
        for column in phase["columns"]:
            print(f"   {phase['phase']:<12} {column['build']:<32} "
                  f"{column['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
