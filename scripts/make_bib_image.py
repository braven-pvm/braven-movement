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
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kit_font import BUNDLED, resolve as resolve_font  # noqa: E402

DEFAULT_KIT = ROOT / "config" / "kit" / "netball_dress.v1.json"
DEFAULT_OUT = ROOT / "assets" / "kit"


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


def draw(kit: dict, letters: str, font_request: str | None):
    """The image, and the label of the font that drew it.

    THE FONT IS RESOLVED BY `kit_font`, which the paint lane wrote after a
    hard-coded `C:/Windows/Fonts/arialbd.ttf` turned the runner red six times.
    This script carried the same path and the same fault: its own tests read
    the committed image and never redrew it, so the suite stayed green while
    the letters were undrawable on any machine but this one. The default is
    the face Pillow carries, which is the same face on both machines, and a
    named font that is absent is refused rather than quietly replaced.
    """
    from PIL import Image, ImageDraw

    width, height = kit["bib"]["imagePx"]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas = ImageDraw.Draw(image)
    font, font_used = resolve_font(font_request, kit["bib"]["fontPx"])
    for box in bib_boxes_px(kit):
        canvas.rounded_rectangle(box, radius=kit["bib"]["cornerRadiusPx"], fill=(245, 245, 245, 255))
        centre = ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)
        # THE WEIGHT IS A STROKE AND NOT A BOLD FACE. A bib reads heavy in the
        # photographs, Pillow's bundled Aileron is a Regular, and there is no
        # bold face both machines are known to carry. A stroke on the glyph
        # thickens whatever face resolved, so the weight is a number in the kit
        # file rather than a property of a machine's font library. 4 px was
        # chosen by a rendered sweep: it puts the same amount of ink in the
        # square as the Arial Bold original, 100.4% of it, and 2 px and 6 px
        # read visibly light and heavy beside it.
        stroke = int(kit["bib"].get("strokePx", 0))
        canvas.text(centre, letters, font=font, fill=(10, 10, 10, 255), anchor="mm",
                    stroke_width=stroke, stroke_fill=(10, 10, 10, 255))
    return image, font_used


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("letters", help="the position letters, for example GS")
    parser.add_argument("--kit", type=Path, default=DEFAULT_KIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--font", default=None,
                        help=f"a path to a .ttf or .otf, or {BUNDLED!r} for the "
                             "face Pillow carries (the default)")
    args = parser.parse_args()
    kit = json.loads(args.kit.read_text(encoding="utf-8"))
    letters = args.letters.upper()
    if not letters.isalpha() or not 1 <= len(letters) <= 3:
        parser.error("letters must be one to three letters")
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"bib_{letters}.png"
    image, font_used = draw(kit, letters, args.font)
    image.save(target)
    # A sidecar beside the image, with the provenance claim under the same
    # key the painted-kit layer uses: this script reads no texture at all.
    sidecar = {
        "instrument": Path(__file__).name,
        "output": target.name,
        "outputSha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "readsNoSkin": True,
        "derivedFrom": "drawn from the kit file and a font, and nothing else",
        "letters": letters,
        "textureSize": kit["bib"]["imagePx"],
        "boxesPx": bib_boxes_px(kit),
        "fontPx": kit["bib"]["fontPx"],
        "strokePx": int(kit["bib"].get("strokePx", 0)),
        "font": font_used,
        "kitFile": args.kit.relative_to(ROOT).as_posix() if args.kit.is_relative_to(ROOT) else str(args.kit),
        "kitSha256": hashlib.sha256(args.kit.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "hashNote": "kitSha256 is the input with CRLF folded to LF; outputSha256 is the raw bytes",
    }
    target.with_suffix(".json").write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    print(f"[bib] {target} {kit['bib']['imagePx']} squares at {bib_boxes_px(kit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
