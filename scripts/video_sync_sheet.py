"""Render front and side frame pairs at matched wall clock times.

The two cameras filmed the same drill from 90 degrees apart and started at
different moments. The movement lane measures the offset between them from two
visual events far apart in the clip, which is a point measurement at two
points. This is the other instrument: it lays the two clips beside each other
across the WHOLE duration, so a wrong offset or an unmodelled drift shows as
body motion that does not match, anywhere, to a person looking at the sheet.

The two instruments fail differently. A point measurement can be exactly right
at both its anchors and wrong between them. An eye check over the whole clip
cannot give a number, and cannot see 10 ms. Neither certifies alone.

THE OFFSET CONVENTION, stated once and printed on every sheet:

    side_time = front_time + offset

So a POSITIVE offset means the side camera was already running, and the
instant that happens at 9.0 s of the front clip happens LATER in the side
clip's own timeline. Pass the movement lane's number straight in. If the
figures on the sheet do not line up, say so and give this convention back to
them, because a sign error reads exactly like a wrong measurement.

WHY THIS DOES NOT SEEK THE OBVIOUS WAY. `ffmpeg -ss T` serves the first frame
AT OR AFTER T. On the front clip, whose frames sit exactly on 1/30 s, that is
the frame wanted. On the side clip, whose frames sit at 33.32 ms and start on
no round number, it is up to a full frame LATE, and always late. Measured at
three sample times the side ran 25 to 30 ms behind what was asked for, while
the front hit exactly. A sheet built that way carries a half frame of
systematic bias that reads as a sync error and belongs to the tool. So this
decodes a small window around the target and keeps the frame NEAREST to it,
then prints the error it could not remove.

Every cell carries the time it actually shows, never the time asked for.

    python video_sync_sheet.py --front "front 0.1.mp4" --side "side 0.1.mp4" \
        --offset -1.0 --out sheet.png
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PTS = re.compile(r"pts_time:([0-9.]+)")
WINDOW_HALF_S = 0.07
WINDOW_FRAMES = 5


def run(command: list[str]) -> str:
    """Run ffmpeg and return its stderr, where showinfo writes."""
    finished = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return finished.stderr


def probe(path: Path) -> dict:
    """Read the facts a caller must not assume: size, rate, and rotation."""
    fields = "stream=width,height,avg_frame_rate,nb_frames,duration"
    text = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", fields, "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    stream = json.loads(text)["streams"][0]
    rate = stream.get("avg_frame_rate", "0/1")
    numerator, _, denominator = rate.partition("/")
    fps = float(numerator) / float(denominator) if float(denominator) else 0.0
    return {
        "path": str(path),
        "name": path.name,
        "codedWidth": stream.get("width"),
        "codedHeight": stream.get("height"),
        "fps": round(fps, 4),
        "frames": int(stream.get("nb_frames", 0)),
        "durationS": round(float(stream.get("duration", 0.0)), 3),
    }


def pair_stamps_to_images(stamps: list[float], image_count: int) -> list[float]:
    """Keep the timestamps that belong to the frames actually written.

    showinfo reports every frame the decoder READS, and -frames:v stops the
    writer earlier, so ffmpeg reports one more timestamp than there are files.
    The extra one is at the END. Pairing from the end, or zipping the two lists
    without trimming, shifts every label by one frame and puts a wrong time
    under every picture on the sheet. That is 33 ms of silent error in an
    instrument whose whole job is to be trusted about time.
    """
    return stamps[:image_count]


def choose_nearest(stamps: list[float], target: float) -> int:
    """Index of the frame nearest the target, which may be BEFORE it.

    `ffmpeg -ss` serves the first frame at or after the request, which is up to
    a full frame late and always late. Nearest halves the error and removes the
    bias, and the bias is what would read as a sync offset.
    """
    if not stamps:
        raise ValueError("no timestamps to choose from")
    return min(range(len(stamps)), key=lambda i: abs(stamps[i] - target))


def sample_times(
    front_duration: float, side_duration: float, offset: float, samples: int,
    margin: float = 0.4,
) -> list[float]:
    """Front times whose partner frame exists in the side clip.

    A NEGATIVE offset means the side camera started later, so the early front
    times map to a side time BEFORE the side clip begins. Asking for those
    gives a frame from 0.0 s, which the sheet would then label with the time it
    was asked for and show as a mismatch belonging to the shoot.
    """
    first = max(margin, margin - offset)
    last = min(front_duration, side_duration - offset) - margin
    if last <= first:
        return []
    if samples <= 1:
        return [first]
    step = (last - first) / (samples - 1)
    return [first + step * index for index in range(samples)]


def nearest_frame(path: Path, target: float, work: Path, tag: str) -> tuple[Path, float]:
    """Decode a window around target and keep the frame NEAREST to it.

    Returns the written image and the timestamp it truly carries. The caller
    must print that timestamp rather than the target, because the two differ
    by up to half a frame and the difference is the reading.
    """
    for attempt in range(3):
        start = max(0.0, target - WINDOW_HALF_S * (attempt + 1))
        folder = work / f"{tag}_{attempt}"
        folder.mkdir(parents=True, exist_ok=True)
        stderr = run([
            "ffmpeg", "-hide_banner", "-copyts", "-accurate_seek",
            "-ss", f"{start:.6f}", "-i", str(path),
            "-frames:v", str(WINDOW_FRAMES + attempt * 3),
            "-vf", "showinfo", "-y", str(folder / "f_%03d.png"),
        ])
        images = sorted(folder.glob("f_*.png"))
        # showinfo reports every frame it DECODES, and -frames:v stops the
        # writer earlier, so there is one more timestamp than there are files.
        # Pairing from the end would mislabel every frame on the sheet.
        stamps = pair_stamps_to_images(
            [float(value) for value in PTS.findall(stderr)], len(images)
        )
        if not images or not stamps:
            continue

        best = choose_nearest(stamps, target)
        at_edge = best in (0, len(stamps) - 1)
        if at_edge and attempt < 2 and start > 0.0:
            # The true nearest frame may lie outside the window. Widen it
            # rather than report an edge frame as the nearest one.
            continue
        return images[best], stamps[best]

    raise RuntimeError(f"no frame decoded near {target:.3f}s in {path.name}")


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("consola.ttf", "arial.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_sheet(
    front: Path,
    side: Path,
    offset: float,
    times: list[float],
    out: Path,
    height: int = 300,
    per_row: int = 4,
) -> dict:
    work = Path(tempfile.mkdtemp(prefix="syncsheet_"))
    label_font = load_font(13)
    head_font = load_font(17)
    pairs = []

    try:
        for index, front_time in enumerate(times):
            front_image, front_at = nearest_frame(front, front_time, work, f"f{index}")
            # Anchor the side on the front frame that is actually shown, NOT on
            # the time asked for. Both cameras quantise to their own 33 ms
            # grid, and asking each independently lets the two snaps run in
            # OPPOSITE directions: measured at 12.381 s the front went back
            # 14.1 ms while the side went forward 14.4, for 28.4 ms between two
            # pictures that were each within half a frame of the request. The
            # cameras are not phase locked, so half a frame cannot be removed.
            # This removes the other half.
            side_time = front_at + offset
            side_image, side_at = nearest_frame(side, side_time, work, f"s{index}")
            # What the two pictures are truly apart, in the front's clock,
            # after the offset is taken out. This is the tool's own error.
            residual_ms = ((side_at - offset) - front_at) * 1000.0
            pairs.append({
                "askedFrontS": round(front_time, 4),
                "askedSideS": round(side_time, 4),
                "frontAtS": round(front_at, 4),
                "sideAtS": round(side_at, 4),
                "frontErrorMs": round((front_at - front_time) * 1000.0, 2),
                "sideErrorMs": round((side_at - side_time) * 1000.0, 2),
                "residualMs": round(residual_ms, 2),
                "_front": front_image,
                "_side": side_image,
            })

        thumbs = []
        for pair in pairs:
            cell = []
            for key in ("_front", "_side"):
                image = Image.open(pair[key]).convert("RGB")
                width = max(1, round(image.width * height / image.height))
                cell.append(image.resize((width, height), Image.LANCZOS))
            thumbs.append(cell)

        gap, label_h, pad = 6, 34, 14
        cell_w = max(a.width + gap + b.width for a, b in thumbs)
        cell_h = height + label_h
        rows = math.ceil(len(thumbs) / per_row)
        header_h = 82
        sheet = Image.new(
            "RGB",
            (pad * 2 + per_row * cell_w + (per_row - 1) * pad,
             header_h + pad + rows * (cell_h + pad)),
            (24, 24, 27),
        )
        draw = ImageDraw.Draw(sheet)
        worst = max(abs(pair["residualMs"]) for pair in pairs)
        draw.text((pad, 10), f"{front.name}   beside   {side.name}", font=head_font,
                  fill=(240, 240, 245))
        draw.text((pad, 34), f"side_time = front_time + offset,  offset = {offset:+.4f} s"
                  f"    left frame FRONT, right frame SIDE", font=label_font,
                  fill=(170, 200, 240))
        draw.text((pad, 52), f"{len(pairs)} pairs across the clip. Each label is the time the"
                  f" frame TRULY carries. Worst extraction residual {worst:+.1f} ms,"
                  f" and one frame is 33.3 ms.", font=label_font, fill=(170, 170, 180))

        for index, (pair, (front_thumb, side_thumb)) in enumerate(zip(pairs, thumbs)):
            column, row = index % per_row, index // per_row
            x = pad + column * (cell_w + pad)
            y = header_h + pad + row * (cell_h + pad)
            sheet.paste(front_thumb, (x, y + label_h))
            sheet.paste(side_thumb, (x + front_thumb.width + gap, y + label_h))
            flag = abs(pair["residualMs"]) > 16.7
            draw.text((x, y + 2), f"front {pair['frontAtS']:8.3f} s",
                      font=label_font, fill=(235, 235, 240))
            draw.text((x, y + 17), f"side  {pair['sideAtS']:8.3f} s  "
                      f"residual {pair['residualMs']:+.1f} ms", font=label_font,
                      fill=(240, 160, 120) if flag else (150, 190, 150))

        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    for pair in pairs:
        pair.pop("_front", None)
        pair.pop("_side", None)

    return {
        "sheet": str(out),
        "offsetS": offset,
        "front": probe(front),
        "side": probe(side),
        "worstResidualMs": max(abs(pair["residualMs"]) for pair in pairs),
        "frameMs": 33.333,
        "pairs": pairs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--front", required=True, type=Path)
    parser.add_argument("--side", required=True, type=Path)
    parser.add_argument("--offset", type=float, default=0.0,
                        help="seconds, where side_time = front_time + offset")
    parser.add_argument("--samples", type=int, default=8,
                        help="evenly spaced pairs across the overlapping span")
    parser.add_argument("--times", type=str, default="",
                        help="explicit front times in seconds, comma separated, "
                             "for ball contacts and other anchor moments")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--height", type=int, default=300)
    arguments = parser.parse_args(argv)

    front_facts, side_facts = probe(arguments.front), probe(arguments.side)
    if arguments.times.strip():
        times = [float(value) for value in arguments.times.split(",") if value.strip()]
    else:
        times = sample_times(
            front_facts["durationS"], side_facts["durationS"],
            arguments.offset, arguments.samples,
        )
        if not times:
            print("the clips do not overlap at this offset", file=sys.stderr)
            return 2

    receipt = build_sheet(arguments.front, arguments.side, arguments.offset,
                          times, arguments.out, height=arguments.height)
    receipt_path = arguments.out.with_suffix(".json")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    print(f"{arguments.out}  {len(times)} pairs  "
          f"worst extraction residual {receipt['worstResidualMs']:+.1f} ms "
          f"against a 33.3 ms frame")
    print(f"{receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
