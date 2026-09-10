"""Put two kits side by side on one sheet, at the same phase and the same view.

    python -B kit_sheet.py --row "painted:out/painted-netball" \
        --row "modelled:out/modelled-dress" --phase land --output out/kit/sheet.png

Each row is `label:directory`. The sheet is built from the renders themselves,
and it prints the sha256 of every image it used, so the sheet can be tied back
to the runs that made it.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = Path("C:/Windows/Fonts/arialbd.ttf")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--row", action="append", required=True)
    parser.add_argument("--movement", default="netball_double_foot_landing")
    parser.add_argument("--phase", default="land")
    parser.add_argument("--views", default="front,quarter,side")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=560)
    parser.add_argument("--crop", default=None,
                        help="left,top,right,bottom as fractions of the image")
    arguments = parser.parse_args()

    views = arguments.views.split(",")
    rows = [item.split(":", 1) for item in arguments.row]
    box = None
    if arguments.crop:
        box = [float(part) for part in arguments.crop.split(",")]

    tiles: list[list[Image.Image]] = []
    for label, directory in rows:
        line = []
        for view in views:
            path = Path(directory) / f"{arguments.movement}.{arguments.phase}.{view}.png"
            if not path.is_file():
                raise SystemExit(f"[kit-sheet] missing render: {path}")
            print(f"[kit-sheet] {label:9s} {view:8s} {sha256(path)[:16]} {path}")
            image = Image.open(path).convert("RGB")
            if box:
                width, height = image.size
                image = image.crop((
                    int(box[0] * width), int(box[1] * height),
                    int(box[2] * width), int(box[3] * height),
                ))
            scale = arguments.width / image.width
            image = image.resize(
                (arguments.width, int(image.height * scale)), Image.LANCZOS
            )
            line.append(image)
        tiles.append(line)

    header = 46
    cell_height = max(image.height for line in tiles for image in line)
    sheet = Image.new(
        "RGB",
        (arguments.width * len(views), (cell_height + header) * len(rows)),
        (16, 18, 22),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(FONT), 26)
    for row, ((label, _), line) in enumerate(zip(rows, tiles)):
        top = row * (cell_height + header)
        draw.text((14, top + 10), f"{label}  ({arguments.phase})", font=font,
                  fill=(236, 238, 242))
        for column, image in enumerate(line):
            sheet.paste(image, (column * arguments.width, top + header))
            draw.text((column * arguments.width + 14, top + header + 8),
                      views[column], font=font, fill=(236, 238, 242))

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(arguments.output)
    print(f"[kit-sheet] wrote {arguments.output} {sheet.size}")
    print("KIT SHEET OK", flush=True)


if __name__ == "__main__":
    main()
