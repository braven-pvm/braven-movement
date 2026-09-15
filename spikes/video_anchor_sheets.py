"""One sheet per anchor: the front view above the side view at the SAME mapped
instant, seven columns across the event, so a person can read the pairing off
the pictures instead of trusting the arithmetic.

WHY A PERSON HAS TO LOOK. A frame offset is a claim about two recordings, and
the arithmetic that produces it agrees with itself whatever it is given. The
only check that does not share anything with the fit is a human eye on the
frames: if the offset is right, the gap-then-contact transition falls in the
SAME COLUMN in both rows. Both pairings in `PAIRS` were confirmed that way,
and the instrument that drew the sheets lived outside git until now.

THE MOMENTS COME FROM THE TABLE, NEVER FROM A LITERAL HERE. `PAIRS` records
three kinds of event and they are not interchangeable:

  anchors   the events the offset was FITTED to. A ball meeting hands, whose
            contact frame is not a judgement call.
  checks    events the fitted offset must also explain. Drawn, and labelled
            as checks, because an event that produced the answer and an event
            that agreed with it afterwards are different evidence.
  setAside  events deliberately NOT used, each with a recorded reason -- a
            soft clasp, a one-handed catch where contact is one frame either
            way. NEVER DRAWN. A sheet is what a person reads to confirm a
            pairing, and putting a knowingly ambiguous event on one invites
            the reader to resolve it by eye, which is exactly what the entry
            says nobody should do.

THIS SHEET IS LAID OUT DIFFERENTLY FROM `proof_sheet`, ON PURPOSE. It shares
the part that carries the correctness -- frames chosen BY INDEX with
`select='eq(n,i)'` and never by a timestamp, and the side row mapped through
the table's own frame offset. It does not share the composition: tiles are
scaled to 360 high with the label burned in by `drawtext`, stacked by ffmpeg.
That is the layout of the three sheets the orchestrator read and signed off
for pair 2, and reproducing it exactly is what lets those sheets be pinned
here as 42 committed tile digests. A prettier sheet nobody had confirmed would
be a comparison against nothing.

    pixi run --frozen python -B video_anchor_sheets.py \
        --pair "front 0.2 + side 0.2" --out <directory>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from video_keypoints import PAIRS  # noqa: E402
from video_section_cuts import resolve, sha256  # noqa: E402

# Seven columns: the centre, three before and three after, two frames apart.
# Two frames rather than one because a contact is visible for several frames
# and one-frame steps show the same picture twice; six frames either side is
# 0.2 s, wide enough that a wrong offset puts the transition in a different
# column and narrow enough that every tile is the same event.
SHEET_STEP = 2
SHEET_HALF = 3

# The tile height the confirmed sheets were built at. Both recordings scale to
# 202 wide at this height, so a sheet is 7 * 202 by 2 * 360.
TILE_HEIGHT = 360

# THE FRONT ROW'S LABEL RUNS PAST THE EDGE OF THE TILE.
# A tile is 202 px wide and `FRONT idx 268  t=8.933s` at fontsize 20 does not
# fit, so the front row's seconds read truncated on the picture: `t=8.9`. THE
# SIDE ROW FITS -- `SIDE idx 263  t=8.763s` is one character shorter and ends
# inside the tile. An earlier version of this comment said every tile was
# truncated, which is false and was disproved by a mutation that cut the front
# label alone: it failed on three of the six sheets, not all six.
#
# WHAT THAT MEANS FOR THE PINS, EXACTLY. A tile digest covers the pixels of
# the tile, so it pins the frame, the whole side label, and the part of the
# front label that lands inside 202 px -- which includes the entire index. It
# does NOT pin the front row's seconds beyond that edge: those characters are
# never drawn, so no digest can notice if they change.
#
# WHAT IS UNPINNED IS NOT THE MEASUREMENT. A pairing is made of INDICES, and
# every index on every tile is inside the edge. The seconds are derived from
# each file's own pts, drift about 11 microseconds a frame between the two
# cameras, and the manifest carries them in full and to four decimals.
#
# It is left alone because every fix costs more than it buys. A smaller font
# or a caption band changes the pixels, so all 84 committed tile digests would
# have to be re-pinned against sheets nobody has read -- cutting the tie to
# the artefacts that were actually confirmed. A second, legible sheet would be
# an artefact with no pin at all.

# THE LABEL IS PART OF THE PINNED PIXELS. `drawtext` renders it from this font
# file, so the committed tile digests depend on the font as much as on the
# frame. A missing font would make ffmpeg fall back to another face and every
# pinned tile would fail on the RIGHT frame, with a message about the picture.
LABEL_FONT = Path("C:/Windows/Fonts/arialbd.ttf")
LABEL_SIZE = 20

ANCHOR_DIGESTS = SPIKE_DIR / "video-annotations" / "anchor-sheets"

# THE ROWS THE LABEL IS BURNED INTO, excluded before a tile is compared with
# the recording it came from. The label box is about 30 px tall; 40 clears it.
#
# WITHOUT THIS THE NUMBER IS MEANINGLESS AND LOOKS LIKE A FAILURE. Compared
# whole, a correct tile scores 20.9 dB against its own source frame, because
# the tile carries a label and the source frame does not. Below this band the
# same comparison is 49.6 dB. A reader who meets 20.9 without that sentence
# concludes the tile shows the wrong picture.
TILE_LABEL_BAND = 40

# The bar a centre tile must beat its neighbouring frames by. Measured across
# every sheet of both pairs before it was chosen -- twelve centre tiles, six
# sheets, both rows -- where the right frame scores 47.9 to 50.3 dB and a
# neighbour 23.1 to 33.7. It sits far below the smallest margin found and far
# above zero, and a test pins it from both sides.
TILE_MARGIN_DB = 10.0

# The smallest margin that sweep found, kept so a test can read it back. A
# number in a comment that nothing reads is how the last threshold in this
# pack went wrong.
MEASURED_MIN_TILE_MARGIN_DB = 16.22


def pinned_tiles(pair_folder: str, name: str) -> list[str] | None:
    """The committed tile digests for one sheet, or None if none are pinned.

    One line per tile, the front row left to right and then the side row, in
    the order `anchor_sheet` draws them.
    """
    path = ANCHOR_DIGESTS / pair_folder / f"{name}.sha256"
    if not path.exists():
        return None
    return [line.strip() for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sheet_tiles(path: Path, columns: int = 2 * SHEET_HALF + 1) -> list[str]:
    """A digest per tile, cropped out of a FINISHED SHEET.

    MEASURED FROM THE ARTEFACT THAT IS DELIVERED, so one function reads this
    tool's sheet and the sheets that were confirmed before this tool existed.
    Hashing the intermediate tile files instead would pin something only this
    pipeline produces, and the comparison against those confirmed sheets --
    the whole reason the layout is theirs -- could not be made at all.

    The order is the front row left to right, then the side row.
    """
    from PIL import Image

    with Image.open(path) as sheet:
        if sheet.width % columns or sheet.height % 2:
            raise SystemExit(
                f"{path.name} is {sheet.width}x{sheet.height}, which does not "
                f"divide into {columns} columns and two rows")
        wide, high = sheet.width // columns, sheet.height // 2
        return [hashlib.sha256(
            sheet.crop((column * wide, row * high,
                        (column + 1) * wide, (row + 1) * high))
            .convert("RGB").tobytes()).hexdigest()
            for row in range(2) for column in range(columns)]


def check_font() -> Path:
    """Refuse early and by name if the label font is not on this machine."""
    if not LABEL_FONT.exists():
        raise SystemExit(
            f"the label font {LABEL_FONT} is not on this machine. The tile "
            "digests committed under video-annotations/anchor-sheets/ include "
            "the label, so ffmpeg falling back to another face would fail "
            "every pinned tile while showing the right frames. Install the "
            "font, or re-pin the digests on this machine's own face and say "
            "so in PROVENANCE.md.")
    return LABEL_FONT


def moments(pair_key: str) -> list[dict]:
    """Every event of a pair that BELONGS on a sheet, in table order.

    Anchors first, then checks. `setAside` is not here and must not be: refer
    to the module docstring.
    """
    pair = PAIRS[pair_key]
    found = []
    for kind in ("anchors", "checks"):
        for row in pair.get(kind, ()):
            found.append({
                "kind": kind[:-1],
                "event": row["event"],
                "referenceIndex": row["referenceIndex"],
                # The side index AS THE TABLE RECORDS IT, which is an
                # observation. `referenceIndex + offset` is a computation. A
                # test compares the two, and they are not the same arithmetic.
                "otherIndex": row["otherIndex"],
            })
    return found


def sheet_indices(centre: int) -> list[int]:
    """The seven FRONT indices a sheet draws, left to right."""
    return [centre + SHEET_STEP * i
            for i in range(-SHEET_HALF, SHEET_HALF + 1)]


def check_span(files: dict, centre: int) -> list[int]:
    """Refuse a sheet that would run off either recording, BEFORE it writes.

    A refusal that has already drawn six tiles is not a refusal, and a sheet
    left half written is a sheet somebody reads.
    """
    wanted = sheet_indices(centre)
    offset = files["offset"]
    for view, first, last in (("front", wanted[0], wanted[-1]),
                              ("side", wanted[0] + offset,
                               wanted[-1] + offset)):
        frames = len(files[view]["pts"])
        if first < 0 or last >= frames:
            raise SystemExit(
                f"a sheet centred on {centre} needs {view} frames {first}"
                f"..{last} and that recording holds {frames}.")
    return wanted


def tile(files: dict, view: str, index: int, destination: Path) -> int:
    """One labelled tile, and the index it was ASKED for.

    Not the index it drew: this function echoes its argument, and an echo is
    not a measurement. What proves a tile shows the frame it names is
    `centre_tile_alignment`, which compares the picture against the recording,
    and the committed tile digests.

    Two ffmpeg calls because that is what the confirmed sheets were built
    with, and the pinned digests are of their output.
    """
    raw = destination.with_name(f"_raw-{destination.name}")
    # `-fps_mode passthrough`, not the deprecated `-vsync 0` the confirmed
    # sheets were built with. MEASURED BEFORE IT WAS CHANGED, because the 84
    # pinned tiles depend on this command: four tiles, both views, both
    # spellings, byte-identical output every time. The flag is inert for a
    # single selected frame either way and is kept because the side file is
    # variable-rate and it says so.
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(files[view]["path"]),
         "-vf", rf"select='eq(n\,{index})'",
         "-fps_mode", "passthrough", "-frames:v", "1", str(raw)], check=True)
    if not raw.exists():
        raise SystemExit(f"ffmpeg wrote no {view} frame for index {index}")
    seconds = files[view]["pts"][index]
    text = f"{view.upper()} idx {index}  t={seconds:.3f}s"
    # FORWARD SLASHES AND AN ESCAPED COLON. A filter string is parsed by
    # ffmpeg, where a backslash is an escape, so a Windows path written
    # the Windows way breaks the filter rather than naming the file.
    font = check_font().as_posix().replace(":", r"\:")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(raw),
         "-vf", f"scale=-2:{TILE_HEIGHT},drawtext=fontfile='{font}':"
                f"text='{text}':x=8:y=8:fontsize={LABEL_SIZE}:"
                "fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=6",
         str(destination)], check=True)
    raw.unlink()
    return index


def sheet_name(moment: dict) -> str:
    """`anchor-324`, `check-484`. The KIND is in the name because the label on
    the tile cannot carry it: that text is part of the pinned pixels."""
    return f"{moment['kind']}-{moment['referenceIndex']}"


def anchor_sheet(files: dict, moment: dict, out_dir: Path) -> dict:
    """One sheet, and the indices each row was asked for.

    `frontIndices` and `sideIndices` are collected in the drawing loop, which
    makes them the requested indices rather than a second sum done afterwards
    -- worth having, and worth less than it sounds. They are echoes. The
    pinned tile digests and `centre_tile_alignment` are what tie a sheet to
    the pictures.
    """
    check_font()
    centre = moment["referenceIndex"]
    wanted = check_span(files, centre)
    offset = files["offset"]
    out_dir.mkdir(parents=True, exist_ok=True)
    scratch = out_dir / f"_tiles-{sheet_name(moment)}"
    if scratch.exists():
        for stale in scratch.glob("*.png"):
            stale.unlink()
    scratch.mkdir(parents=True, exist_ok=True)

    drawn: dict[str, list[int]] = {"front": [], "side": []}
    columns = []
    for n, index in enumerate(wanted):
        made = {}
        for view, mapped in (("front", index), ("side", index + offset)):
            out = scratch / f"{view}-{n:02d}.png"
            drawn[view].append(tile(files, view, mapped, out))
            made[view] = out
        column = scratch / f"column-{n:02d}.png"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(made["front"]),
             "-i", str(made["side"]), "-filter_complex",
             "[0:v][1:v]vstack=inputs=2", str(column)], check=True)
        columns.append(column)

    if len(columns) != len(wanted):
        raise SystemExit(
            f"asked for {len(wanted)} columns and built {len(columns)}")

    destination = out_dir / f"{sheet_name(moment)}.png"
    command = ["ffmpeg", "-v", "error", "-y"]
    for column in columns:
        command += ["-i", str(column)]
    command += ["-filter_complex",
                "".join(f"[{i}:v]" for i in range(len(columns)))
                + f"hstack=inputs={len(columns)}", str(destination)]
    subprocess.run(command, check=True)

    # A DIGEST PER TILE rather than one for the sheet, so a failure names the
    # column it happened in, and read back out of the finished sheet so the
    # same measurement can be taken on a sheet this tool did not draw.
    digests = sheet_tiles(destination, len(wanted))
    for stale in scratch.glob("*.png"):
        stale.unlink()
    scratch.rmdir()

    return {
        "sheet": destination.name,
        "kind": moment["kind"],
        "event": moment["event"],
        "centreFrontIndex": centre,
        "centreSideIndex": centre + offset,
        "frontIndices": drawn["front"],
        "sideIndices": drawn["side"],
        "sha256": sha256(destination),
        "tileDigests": digests,
    }


def centre_tile_alignment(files: dict, sheet: Path, entry: dict,
                          view: str) -> dict:
    """How well the centre tile matches the frame it is labelled with, and how
    well it matches that frame's two neighbours.

    THE ONLY CHECK HERE THAT LOOKS AT A PICTURE. Everything else about a sheet
    is an index checked against another index, or a digest pinned against a
    sheet somebody confirmed -- and a pin covers only the pairs that have been
    pinned. The day a third pair is added, this is what stands between it and
    a sheet drawn from the wrong frames.

    THE SOURCE FRAME IS RESIZED BY A DIFFERENT RESAMPLER. The tile is ffmpeg's
    `scale=-2:360`; the frame it is compared against is decoded and resized
    here by PIL's LANCZOS. Checking swscale with swscale would agree with
    itself, which is the fault this pack has now met three times.
    """
    import subprocess as run_module
    import tempfile

    import numpy as np
    from PIL import Image

    centre = (entry["frontIndices"] if view == "front"
              else entry["sideIndices"])[SHEET_HALF]
    scratch = Path(tempfile.mkdtemp())
    try:
        with Image.open(sheet) as drawn:
            wide, high = drawn.width // len(entry["frontIndices"]), \
                drawn.height // 2
            row = 0 if view == "front" else 1
            tile = np.asarray(
                drawn.crop((SHEET_HALF * wide, row * high,
                            (SHEET_HALF + 1) * wide, (row + 1) * high))
                .convert("RGB"), dtype=np.float64)[TILE_LABEL_BAND:]

        scores = {}
        for shift in (0, -1, 1):
            index = centre + shift
            if not 0 <= index < len(files[view]["pts"]):
                scores[shift] = None
                continue
            raw = scratch / f"source-{shift}.png"
            run_module.run(
                ["ffmpeg", "-v", "error", "-y", "-i",
                 str(files[view]["path"]),
                 "-vf", rf"select='eq(n\,{index})'",
                 "-fps_mode", "passthrough", "-frames:v", "1",
                 str(raw)], check=True)
            with Image.open(raw) as source:
                other = np.asarray(
                    source.convert("RGB").resize((wide, high), Image.LANCZOS),
                    dtype=np.float64)[TILE_LABEL_BAND:]
            error = float(np.mean((tile - other) ** 2))
            scores[shift] = (float("inf") if error == 0
                             else 10.0 * float(np.log10(255.0 ** 2 / error)))
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)

    neighbours = [scores[-1], scores[1]]
    measured = [n for n in neighbours if n is not None]
    return {"view": view, "centreIndex": centre, "at": scores[0],
            "before": scores[-1], "after": scores[1],
            "margin": (min(scores[0] - n for n in measured)
                       if measured and scores[0] is not None
                       else float("inf"))}


def manifest_for(files: dict, sheets: list[dict]) -> dict:
    return {
        "schemaVersion": "video-anchor-sheets-1",
        "pair": files["pairKey"],
        "sideIndexEqualsFrontIndexPlus": files["offset"],
        "front": {"file": files["front"]["name"],
                  "sha256": files["front"]["sha256"],
                  "frames": len(files["front"]["pts"])},
        "side": {"file": files["side"]["name"],
                 "sha256": files["side"]["sha256"],
                 "frames": len(files["side"]["pts"])},
        "claim": ("each sheet shows one event from both cameras at the SAME "
                  "mapped instant, seven columns two frames apart. If the "
                  "frame offset is right, the transition falls in the same "
                  "column in both rows."),
        "howFramesWereSelected": (
            f"select='eq(n,i)' on each file's own frame list, the side row at "
            f"i {files['offset']:+d}. Nothing seeks: the side file is "
            "variable-rate with a long GOP, so a seek lands near a timestamp "
            "rather than on a frame."),
        "whatIsNotHere": (
            "the pair's setAside events. Each is recorded in PAIRS with the "
            "reason it was not used, and drawing one would invite a reader to "
            "resolve by eye the ambiguity that entry exists to record."),
        # `check_font` rather than a conditional: it has already refused on
        # every path that reaches here, so the `else None` arm was a branch
        # nothing could execute, and a manifest that recorded a null font
        # would have been describing a sheet that could not exist.
        "labelFont": {"path": str(LABEL_FONT), "sha256": sha256(check_font())},
        "sheets": sheets,
    }


def pair_folder(pair_key: str) -> str:
    """`pair1` / `pair2`, from the table's order rather than from a name."""
    return f"pair{list(PAIRS).index(pair_key) + 1}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True,
                        help="a key from PAIRS in video_keypoints.py")
    parser.add_argument("--out", required=True, type=Path)
    arguments = parser.parse_args(argv[1:])

    # THE PAIR FIRST, THE FONT SECOND, and the order is the point. Checking
    # the font first made an unknown pair refuse with a message about
    # `C:/Windows/Fonts/arialbd.ttf` on any machine that has no such file --
    # so the same wrong argument produced a different answer on Linux from on
    # Windows. A refusal that depends on the machine comes after the refusals
    # that do not.
    files = resolve(arguments.pair)
    check_font()
    print(f"{arguments.pair}")
    for view in ("front", "side"):
        print(f"  {view:5s} {files[view]['name']:16s} "
              f"{files[view]['sha256'][:12]}  "
              f"{len(files[view]['pts'])} frames")
    print(f"  side index = front index {files['offset']:+d}\n")

    wanted = moments(arguments.pair)
    if not wanted:
        raise SystemExit(f"{arguments.pair} has no anchors or checks to draw")

    sheets = []
    for moment in wanted:
        entry = anchor_sheet(files, moment, arguments.out)
        sheets.append(entry)
        print(f"  {entry['kind']:6s} front {entry['frontIndices'][0]}.."
              f"{entry['frontIndices'][-1]}  side {entry['sideIndices'][0]}.."
              f"{entry['sideIndices'][-1]}  {len(entry['frontIndices'])} "
              f"columns  {entry['event']}")

    where = arguments.out / "manifest.json"
    where.write_text(
        json.dumps(manifest_for(files, sheets), indent=2, ensure_ascii=False)
        + "\n", encoding="utf-8")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
