"""Six evenly spaced frames of a clip, on one sheet, so it reads without playing.

A movie is the honest artefact for movement, and a movie cannot be put in a
document or read in a message. This lays out N frames of it, labelled with the
frame number each one came from, and prints the sha256 of the clip it read.

    python -B kit_clip_sheet.py --clip out/clip-gs/<name>.mp4 \
        --output out/kit/clip-sheet.png --caption "..."

It DECODES the clip rather than re-rendering it, so the sheet is a reading of
the artefact that was produced and not a second production of its own.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from kit_font import resolve as resolve_font


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--width", type=int, default=520)
    parser.add_argument("--caption", default="")
    parser.add_argument("--font", default=None,
                        help="path to a .ttf or .otf, or 'pillow'")
    parser.add_argument("--crop", default=None,
                        help="left,top,right,bottom as fractions")
    arguments = parser.parse_args()

    digest = hashlib.sha256(arguments.clip.read_bytes()).hexdigest()
    capture = cv2.VideoCapture(str(arguments.clip))
    if not capture.isOpened():
        raise SystemExit(f"[kit-clip-sheet] cannot open {arguments.clip}")
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    rate = capture.get(cv2.CAP_PROP_FPS)
    if total < arguments.count:
        raise SystemExit(
            f"[kit-clip-sheet] the clip holds {total} frames and "
            f"{arguments.count} were asked for"
        )
    print(f"[kit-clip-sheet] {arguments.clip.name} sha256 {digest[:16]}")
    print(f"[kit-clip-sheet] {total} frames at {rate:.1f} fps "
          f"({total / max(rate, 1e-9):.2f} s)")

    wanted = [
        int(round(index * (total - 1) / (arguments.count - 1)))
        for index in range(arguments.count)
    ]
    tiles = []
    for number in wanted:
        capture.set(cv2.CAP_PROP_POS_FRAMES, number)
        ok, frame = capture.read()
        if not ok:
            raise SystemExit(f"[kit-clip-sheet] frame {number} would not decode")
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if arguments.crop:
            box = [float(part) for part in arguments.crop.split(",")]
            width, height = image.size
            image = image.crop((
                int(box[0] * width), int(box[1] * height),
                int(box[2] * width), int(box[3] * height),
            ))
        scale = arguments.width / image.width
        tiles.append((
            number,
            image.resize((arguments.width, int(image.height * scale)), Image.LANCZOS),
        ))
    capture.release()

    label = 34
    full = arguments.width * arguments.columns
    lines: list[str] = []
    if arguments.caption:
        measure, _ = resolve_font(arguments.font, 24)
        words, current = arguments.caption.split(), ""
        for word in words:
            trial = f"{current} {word}".strip()
            if measure.getlength(trial) > full - 28 and current:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    caption = (12 + 30 * len(lines)) if lines else 0
    cell = max(image.height for _, image in tiles)
    rows = (len(tiles) + arguments.columns - 1) // arguments.columns
    sheet = Image.new("RGB", (full, rows * (cell + label) + caption), (16, 18, 22))
    draw = ImageDraw.Draw(sheet)
    font, font_used = resolve_font(arguments.font, 24)
    small, _ = resolve_font(arguments.font, 22)
    for number, line in enumerate(lines):
        draw.text((14, 8 + 30 * number), line, font=font, fill=(236, 238, 242))
    for index, (number, image) in enumerate(tiles):
        column = index % arguments.columns
        row = index // arguments.columns
        top = caption + row * (cell + label)
        draw.text((column * arguments.width + 14, top + 6),
                  f"frame {number + 1} of {total}", font=small,
                  fill=(236, 238, 242))
        sheet.paste(image, (column * arguments.width, top + label))

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(arguments.output)
    print(f"[kit-clip-sheet] font {font_used}")
    print(f"[kit-clip-sheet] wrote {arguments.output} {sheet.size}")
    print("KIT CLIP SHEET OK", flush=True)


if __name__ == "__main__":
    main()
