"""Draw a netball bib into the dress's planar UV frame.

`scripts/author_netball_dress.py` lays the dress's UV map as a planar
projection: front faces on the left half of the image, back faces mirrored on
the right half, x across and z up in the frame `uvFrame` of the kit file.
This script draws the bib square with the position letters in that same frame,
twice, so the letters read the right way round from the front and from behind.
Where the image is transparent the fabric colour shows through.

    pixi run --frozen python ../scripts/make_bib_image.py GS

writes `assets/kit/bib_GS.png`. The pixel box of the square is a pure function
of the kit file, so a test can check the arithmetic without drawing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KIT = ROOT / "config" / "kit" / "netball_dress.v1.json"
DEFAULT_OUT = ROOT / "assets" / "kit"
DEFAULT_FONT = Path("C:/Windows/Fonts/arialbd.ttf")


def bib_boxes_px(kit: dict) -> list[tuple[int, int, int, int]]:
    """The two pixel boxes (left, top, right, bottom) of the bib square, front
    half then back half, in the image the kit file sizes."""
    frame, bib = kit["uvFrame"], kit["bib"]
    width, height = bib["imagePx"]
    span_x = frame["x1"] - frame["x0"]
    span_z = frame["z1"] - frame["z0"]
    v0 = (bib["z0"] - frame["z0"]) / span_z
    v1 = (bib["z1"] - frame["z0"]) / span_z
    boxes = []
    for half in (0.0, 0.5):
        u0 = half + 0.5 * (-bib["halfWidthM"] - frame["x0"]) / span_x
        u1 = half + 0.5 * (bib["halfWidthM"] - frame["x0"]) / span_x
        boxes.append(
            (int(u0 * width), int((1 - v1) * height), int(u1 * width), int((1 - v0) * height))
        )
    return boxes


def draw(kit: dict, letters: str, font_path: Path | None):
    from PIL import Image, ImageDraw, ImageFont

    width, height = kit["bib"]["imagePx"]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas = ImageDraw.Draw(image)
    if font_path is not None and font_path.is_file():
        font = ImageFont.truetype(str(font_path), kit["bib"]["fontPx"])
    else:
        font = ImageFont.load_default(size=kit["bib"]["fontPx"])
    for box in bib_boxes_px(kit):
        canvas.rounded_rectangle(box, radius=kit["bib"]["cornerRadiusPx"], fill=(245, 245, 245, 255))
        centre = ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)
        canvas.text(centre, letters, font=font, fill=(10, 10, 10, 255), anchor="mm")
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("letters", help="the position letters, for example GS")
    parser.add_argument("--kit", type=Path, default=DEFAULT_KIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    args = parser.parse_args()
    kit = json.loads(args.kit.read_text(encoding="utf-8"))
    letters = args.letters.upper()
    if not letters.isalpha() or not 1 <= len(letters) <= 3:
        parser.error("letters must be one to three letters")
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"bib_{letters}.png"
    draw(kit, letters, args.font).save(target)
    print(f"[bib] {target} {kit['bib']['imagePx']} squares at {bib_boxes_px(kit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
