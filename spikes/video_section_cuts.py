"""Cut one section from BOTH views of a pair, on the frame mapping, with proof.

WHAT THIS IS FOR. A coach reads a section of a page and wants to see the moment
from two angles. The two clips must show the SAME INSTANTS, or the pair of them
is worse than either alone: two clips that look synchronised and are not will be
read as one movement and they are two.

THE SIDE WINDOW IS NEVER CHOSEN BY EYE. A section is given as a window of FRONT
frame indices. The side window is that window mapped through
`frameOffsetToReference` in the pair table, so a section cannot be cut with a
side window somebody picked because it looked right. That is how -0.7295 s was
published: a catch found where an offset predicted a catch is not evidence in a
clip of catches.

FRAMES ARE SELECTED BY INDEX AND NOTHING SEEKS. `trim=start_frame:end_frame`
takes frames by their position in the container's own list. The side file is
variable-rate and its GOP is long, so `-ss` on it lands somewhere near a
timestamp rather than on a frame, and "near" is exactly the error this pack
spent a day removing. Both clips are then written with `setpts=N/30/TB`, so
each holds the same number of frames and they play in lockstep.

THE FILES ARE RESOLVED BY sha256, NOT BY NAME. On 2026-09-07 the two side files'
names were swapped at source and a suite of fifty tests did not notice, because
the only field that told them apart was written into every artefact and read by
nothing. A cut made from the wrong file would produce a clip that looks
perfectly ordinary.

    pixi run python video_section_cuts.py --pair "front 0.1 + side 0.1" \\
        --section catch-rep01=258:312 --out somewhere

Every window is a FRONT index range, inclusive at both ends.
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

from video_keypoints import PAIRS, SAMPLES  # noqa: E402

# The clips are written at this rate. Both views get the same one on purpose:
# the point of the pair is that frame k of one is frame k of the other, and a
# player that is told two different rates will drift them apart again.
OUTPUT_FPS = 30

# Six is what a person can take in at a glance across a section, and it is the
# number the orchestrator's own sheets used, so the two are comparable.
PROOF_INSTANTS = 6

# The tile width a ball in hands can be read at. The front camera of run 2
# stands far enough back that 150 px is not enough; refer to the contact sheet
# in video_event_ledger.py, which learnt this the same way.
PROOF_TILE_WIDTH = 420


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pts(path: Path) -> list[float]:
    """The container's own frame timestamps. Nothing here computes a timestamp
    from an index and a rate: the side file is variable-rate and that sum is
    wrong by a frame within seconds."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "frame=pts_time", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout
    return [float(v.strip().rstrip(",")) for v in out.split()
            if v.strip().rstrip(",")]


def resolve(pair_key: str) -> dict:
    """The pair's two files, checked by hash, with their timestamps.

    REFUSES ON A HASH MISMATCH rather than cutting from whatever carries the
    name. The names of these recordings have moved once already.
    """
    pair = PAIRS.get(pair_key)
    if pair is None:
        raise SystemExit(f"no pair named {pair_key!r}. Known: "
                         + ", ".join(repr(k) for k in PAIRS))
    found = {}
    for side, name_key, sha_key in (("front", "referenceFile", "referenceSha256"),
                                    ("side", "otherFile", "otherSha256")):
        name = pair[name_key]
        path = SAMPLES / name
        if not path.exists():
            raise SystemExit(f"{path} is not on this machine")
        stamped = pair[sha_key]
        actual = sha256(path)
        if not actual.startswith(stamped):
            raise SystemExit(
                f"{name} on disk is {actual[:12]} and the pair table says "
                f"{stamped}. THE NAME AND THE CONTENT DISAGREE. Do not cut "
                "from it: on 2026-09-07 these two recordings' names were "
                "swapped at source and nothing noticed, because the only field "
                "that told them apart was never read. Find the file whose hash "
                f"is {stamped} and cut from that.")
        found[side] = {"name": name, "path": path, "sha256": actual,
                       "pts": pts(path)}
    found["offset"] = int(pair["frameOffsetToReference"])
    found["pairKey"] = pair_key
    return found


def side_window(files: dict, start: int, end: int) -> tuple[int, int]:
    """The front window mapped through the table's own frame offset.

    NOT A PARAMETER, AND THAT IS THE POINT. A caller cannot pass a side window,
    so a section cannot be cut against a side range that somebody chose because
    it looked right.
    """
    offset = files["offset"]
    return start + offset, end + offset


def check_window(files: dict, start: int, end: int) -> tuple[int, int]:
    """Refuse a window that runs past either file, rather than clamping it.

    Clamping would return a clip SHORTER than asked for with nothing saying so,
    and the two views would then hold different numbers of frames, which is the
    one property this tool exists to guarantee.
    """
    if end < start:
        raise SystemExit(f"window {start}..{end} ends before it starts")
    front_frames = len(files["front"]["pts"])
    if start < 0 or end >= front_frames:
        raise SystemExit(
            f"front window {start}..{end} is outside {files['front']['name']}, "
            f"which has {front_frames} frames (0..{front_frames - 1})")
    first, last = side_window(files, start, end)
    side_frames = len(files["side"]["pts"])
    if first < 0 or last >= side_frames:
        raise SystemExit(
            f"front window {start}..{end} maps to side {first}..{last} at an "
            f"offset of {files['offset']}, and {files['side']['name']} has "
            f"{side_frames} frames (0..{side_frames - 1}). The section runs "
            "off the end of the other view, so the two clips cannot show the "
            "same instants.")
    return first, last


def cut(path: Path, first: int, last: int, destination: Path) -> None:
    """Frames first..last inclusive, by INDEX, written at OUTPUT_FPS.

    `end_frame` is exclusive in ffmpeg's trim filter, so it takes last + 1.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(path),
         "-vf", (f"trim=start_frame={first}:end_frame={last + 1},"
                 f"setpts=N/{OUTPUT_FPS}/TB"),
         "-an", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
         str(destination)], check=True)


def frame_count(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout
    return int(out.strip().rstrip(","))


def frame_digests(path: Path) -> list[str]:
    """A hash per DECODED frame, so two clips can be compared on what they
    show rather than on their bytes. Two encodes of the same frames differ in
    bytes for reasons that have nothing to do with the pictures."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v", "-f",
         "framehash", "-hash", "md5", "-"],
        capture_output=True, text=True, check=True).stdout
    return [line.rsplit(",", 1)[-1].strip()
            for line in out.splitlines() if not line.startswith("#")]


# THE FLOOR, AND WHERE IT COMES FROM. A clip is re-encoded, so its frames are
# not bit-identical to the source and equality is the wrong test. Measured on
# `catch-rep01` of pair 1, front view, 55 frames:
#
#     clip frame k against source frame start+k     min 39.9 dB, median 41.6
#     the same clip against start+k-1               max 33.2 dB
#     the same clip against start+k+1               max 33.1 dB
#     two frames out, either way                    max 30.1 dB
#
# Six decibels separate the worst correct pair from the best wrong one. The
# floor is 36, which sits between them with margin on both sides, and it is a
# CHOSEN threshold on a measured separation rather than a number that looked
# round.
PSNR_FLOOR_DB = 36.0


def clip_against_source(files: dict, view: str, clip: Path,
                        start: int, end: int) -> list[float]:
    """Per-frame PSNR of a clip against THE SOURCE FRAMES IT CLAIMS TO HOLD.

    WHY THIS EXISTS AND WHAT IT ANSWERS THAT NOTHING ELSE DOES. Comparing this
    tool's clips against clips made by another instrument proves only that the
    two agree: if both mapped an index wrongly, every frame would still match.
    This compares a clip against the recording itself.

    THE SOURCE FRAMES ARE SELECTED BY A DIFFERENT FILTER FROM THE ONE UNDER
    TEST. The cut uses `trim=start_frame:end_frame`, whose end is exclusive and
    whose off-by-one at either edge is the fault this tool exists to prevent.
    The comparison uses `select='between(n,start,end)'`, which is inclusive at
    both ends and shares no arithmetic with it. Checking trim with trim would
    agree with itself.
    """
    import tempfile
    import numpy as np
    from PIL import Image

    scratch = Path(tempfile.mkdtemp())
    try:
        clip_dir, source_dir = scratch / "clip", scratch / "source"
        clip_dir.mkdir()
        source_dir.mkdir()
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-vsync", "0",
             str(clip_dir / "f-%05d.png")], check=True)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(files[view]["path"]),
             "-vf", f"select='between(n\\,{start}\\,{end})'", "-vsync", "0",
             str(source_dir / "f-%05d.png")], check=True)
        made = sorted(clip_dir.glob("*.png"))
        wanted = sorted(source_dir.glob("*.png"))
        if len(made) != len(wanted):
            raise SystemExit(
                f"the clip holds {len(made)} frames and the source window "
                f"{start}..{end} holds {len(wanted)}")
        found = []
        for a, b in zip(made, wanted):
            u = np.asarray(Image.open(a).convert("RGB"), dtype=np.float64)
            v = np.asarray(Image.open(b).convert("RGB"), dtype=np.float64)
            error = float(np.mean((u - v) ** 2))
            found.append(float("inf") if error == 0
                         else 10.0 * float(np.log10(255.0 ** 2 / error)))
        return found
    finally:
        import shutil
        shutil.rmtree(scratch, ignore_errors=True)


def frames_below_floor(scores: list[float],
                       floor: float = PSNR_FLOOR_DB) -> list[int]:
    """Which frames of a clip are not the source frames they claim to be."""
    return [n for n, value in enumerate(scores) if value < floor]


def proof_sheet(files: dict, name: str, start: int, end: int,
                destination: Path, instants: int = PROOF_INSTANTS) -> Path:
    """Front above side at the SAME mapped instant, `instants` times across the
    window, every tile labelled with its index and its own pts.

    THE TILE COUNT IS ASSERTED AGAINST THE REQUEST. A sheet that quietly holds
    a different number of tiles than were asked for is how a contact sheet in
    this repository showed frames from a different part of the clip under a
    plausible caption, and a person read a ledger off it.
    """
    from PIL import Image, ImageDraw

    scratch = destination.parent / f"_raw-{name}"
    if scratch.exists():
        for stale in scratch.glob("*.png"):
            stale.unlink()
    scratch.mkdir(parents=True, exist_ok=True)

    if instants < 2:
        raise SystemExit("a proof sheet needs at least two instants")
    span = end - start
    wanted = [start + round(i * span / (instants - 1)) for i in range(instants)]

    offset = files["offset"]
    columns = []
    for n, index in enumerate(wanted):
        pair_images = []
        for view, mapped in (("front", index), ("side", index + offset)):
            out = scratch / f"{view}-{n:02d}.png"
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(files[view]["path"]),
                 "-vf", f"select='eq(n\\,{mapped})',scale={PROOF_TILE_WIDTH}:-2",
                 "-vsync", "0", "-frames:v", "1", str(out)], check=True)
            if not out.exists():
                raise SystemExit(
                    f"ffmpeg wrote no frame for {view} index {mapped}")
            pair_images.append((Image.open(out), view.upper(), mapped,
                                files[view]["pts"][mapped]))
        columns.append(pair_images)

    if len(columns) != instants:
        raise SystemExit(
            f"asked for {instants} instants and built {len(columns)} columns")

    tile_width = columns[0][0][0].width
    tile_height = max(image.height for column in columns for image, *_ in column)
    band = 22
    sheet = Image.new("RGB", (tile_width * instants,
                              2 * (tile_height + band)), "white")
    pen = ImageDraw.Draw(sheet)
    tiles = 0
    for n, column in enumerate(columns):
        for row, (image, view, index, seconds) in enumerate(column):
            x = n * tile_width
            y = row * (tile_height + band)
            pen.text((x + 4, y + 4), f"{view} idx {index}  t={seconds:.4f}s",
                     fill="black")
            sheet.paste(image, (x, y + band))
            tiles += 1
    if tiles != 2 * instants:
        raise SystemExit(f"expected {2 * instants} tiles and drew {tiles}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination)
    for stale in scratch.glob("*.png"):
        stale.unlink()
    scratch.rmdir()
    return destination


def cut_section(files: dict, name: str, start: int, end: int,
                out_dir: Path) -> dict:
    """One section, both views, with its proof sheet and its manifest entry."""
    first, last = check_window(files, start, end)
    front_clip = out_dir / f"{name}-front.mp4"
    side_clip = out_dir / f"{name}-side.mp4"
    cut(files["front"]["path"], start, end, front_clip)
    cut(files["side"]["path"], first, last, side_clip)

    wanted = end - start + 1
    counts = {"front": frame_count(front_clip), "side": frame_count(side_clip)}
    if counts["front"] != wanted or counts["side"] != wanted:
        raise SystemExit(
            f"{name}: asked for {wanted} frames and the clips hold "
            f"{counts['front']} and {counts['side']}. Two clips of one section "
            "with different frame counts do not play in lockstep.")

    sheet = proof_sheet(files, name, start, end, out_dir / f"{name}-proof.png")
    front_pts, side_pts = files["front"]["pts"], files["side"]["pts"]
    return {
        "section": name,
        "frames": wanted,
        "front": {"indexStart": start, "indexEnd": end,
                  "ptsStart": round(front_pts[start], 4),
                  "ptsEnd": round(front_pts[end], 4),
                  "file": front_clip.name},
        "side": {"indexStart": first, "indexEnd": last,
                 "ptsStart": round(side_pts[first], 4),
                 "ptsEnd": round(side_pts[last], 4),
                 "file": side_clip.name},
        "proofSheet": sheet.name,
    }


def manifest_for(files: dict, sections: list[dict]) -> dict:
    return {
        "schemaVersion": "video-section-cuts-1",
        "pair": files["pairKey"],
        "sideIndexEqualsFrontIndexPlus": files["offset"],
        "front": {"file": files["front"]["name"],
                  "sha256": files["front"]["sha256"],
                  "frames": len(files["front"]["pts"])},
        "side": {"file": files["side"]["name"],
                 "sha256": files["side"]["sha256"],
                 "frames": len(files["side"]["pts"])},
        "claim": ("both clips of a section show the SAME INSTANTS, mapped by "
                  "frame index through the pair table's own frame offset. The "
                  "side window is derived and was never chosen by eye."),
        "howFramesWereSelected": (
            "trim=start_frame:end_frame on each file's own frame list, then "
            "setpts=N/30/TB. NOTHING SEEKS: the side file is variable-rate "
            "with a long GOP, so a seek lands near a timestamp rather than on "
            "a frame."),
        "identity": ("The two recordings are named here by sha256 as well as "
                     "by file name, because these names were swapped at source "
                     "on 2026-09-07 and the file name is not the identity."),
        "sections": sections,
    }


# THE FOUR SECTIONS OF ERIN'S PAGE FOR PAIR 1, as FRONT frame indices.
#
# They are indices and not seconds on purpose. The windows were first chosen as
# front SECONDS and turned into indices by multiplying by 30, which works only
# because the front file is constant-rate at exactly 30.000. The side file is
# not, and neither will the next camera be. An index is what `trim` takes and
# what the pair table maps; a second has to be converted by somebody, and this
# repository has already withdrawn two measurements that were converted.
PAIR1_SECTIONS = (
    ("catch-rep01", 258, 312,
     "section 1, the hand mirror: her hands meeting the ball"),
    ("release-rep09", 598, 653,
     "section 5, the release moment: the ball leaving her hands"),
    ("hold-rep09", 654, 715,
     "section 7, the elbow dial: the pull-in reaching her chest"),
    ("ready-between", 538, 584,
     "section 6, the arm-span ready: her stance between repetitions"),
)


def parse_section(text: str) -> tuple[str, int, int]:
    """`name=start:end`, both FRONT indices, inclusive."""
    try:
        name, window = text.split("=", 1)
        start, end = window.split(":", 1)
        return name, int(start), int(end)
    except ValueError:
        raise SystemExit(
            f"cannot read section {text!r}. Give it as name=start:end, with "
            "both numbers FRONT frame indices, for example "
            "catch-rep01=258:312.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True,
                        help="a key from PAIRS in video_keypoints.py")
    parser.add_argument("--section", action="append", default=[],
                        metavar="NAME=START:END",
                        help="a FRONT frame window, inclusive, repeatable")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--pair1-sections", action="store_true",
                        help="cut the four sections of Erin's page for pair 1")
    arguments = parser.parse_args(argv[1:])
    wanted = list(arguments.section)
    if arguments.pair1_sections:
        wanted += [f"{name}={start}:{end}"
                   for name, start, end, _ in PAIR1_SECTIONS]
    if not wanted:
        raise SystemExit("give at least one --section NAME=START:END, or "
                         "--pair1-sections")

    files = resolve(arguments.pair)
    print(f"{arguments.pair}")
    for view in ("front", "side"):
        print(f"  {view:5s} {files[view]['name']:16s} "
              f"{files[view]['sha256'][:12]}  "
              f"{len(files[view]['pts'])} frames")
    print(f"  side index = front index {files['offset']:+d}\n")

    arguments.out.mkdir(parents=True, exist_ok=True)
    sections = []
    for text in wanted:
        name, start, end = parse_section(text)
        entry = cut_section(files, name, start, end, arguments.out)
        sections.append(entry)
        print(f"  {name:14s} front {entry['front']['indexStart']}.."
              f"{entry['front']['indexEnd']} "
              f"({entry['front']['ptsStart']:.3f}-{entry['front']['ptsEnd']:.3f}s)"
              f"  side {entry['side']['indexStart']}..{entry['side']['indexEnd']} "
              f"({entry['side']['ptsStart']:.3f}-{entry['side']['ptsEnd']:.3f}s)"
              f"  {entry['frames']} frames")

    where = arguments.out / "manifest.json"
    where.write_text(
        json.dumps(manifest_for(files, sections), indent=2, ensure_ascii=False)
        + "\n", encoding="utf-8")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
