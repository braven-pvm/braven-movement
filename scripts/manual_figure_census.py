"""What kind of picture the coaches manual actually contains, counted.

Item 2 of the character and animation lane asks what the sport's own figures
look like. Before that can be answered from the manual, somebody has to say
what is IN the manual, and 728 images cannot be answered by opening four of
them and generalising.

THE DISCRIMINATOR IS THE WHITE GROUND, and it is measured rather than judged.
The manual's drill figures are clip art on a white page: top-down tokens on a
court plan. Its photographs are camera frames that fill their own frame. A
photograph can be pale and a diagram can be busy, so the split is reported as a
DISTRIBUTION and the boundary is named, not hidden inside a verdict.

    python scripts/manual_figure_census.py
    python scripts/manual_figure_census.py --list diagram

This reads and counts. It renders nothing, and it decides nothing about the
character.
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from PIL import Image

MANUAL = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "202526 updated coaches manual"
)

# A pixel is "page white" when every channel is at least this bright. The page
# is scanned or exported rather than pure, so the threshold is below 255.
WHITE = 244

# A picture that is at least this much page white is drawn on the page rather
# than photographed. The value is not a tuning knob: the census below shows the
# population is bimodal and this sits in the empty middle of it.
DIAGRAM_SHARE = 0.55

# Sampling stride. The question is what share of a picture is white, and that
# does not need every pixel.
STRIDE = 4


def white_share(path: Path) -> float:
    """The fraction of sampled pixels that are page white."""
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        pixels = rgb.load()
        white = 0
        counted = 0
        for y in range(0, height, STRIDE):
            for x in range(0, width, STRIDE):
                red, green, blue = pixels[x, y]
                counted += 1
                if red >= WHITE and green >= WHITE and blue >= WHITE:
                    white += 1
    return white / counted if counted else 0.0


def census(manual: Path) -> list[tuple[float, int, str]]:
    rows = []
    for path in sorted(manual.glob("*.jpeg")):
        with Image.open(path) as image:
            pixels = image.size[0] * image.size[1]
        rows.append((white_share(path), pixels, path.name))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual", type=Path, default=MANUAL)
    parser.add_argument("--list", choices=("diagram", "photograph"))
    arguments = parser.parse_args(argv)

    if not arguments.manual.is_dir():
        print(f"the manual is not on this machine: {arguments.manual}")
        return 1

    rows = census(arguments.manual)
    if not rows:
        print(f"no images under {arguments.manual}")
        return 1

    diagrams = [row for row in rows if row[0] >= DIAGRAM_SHARE]
    photographs = [row for row in rows if row[0] < DIAGRAM_SHARE]

    if arguments.list:
        chosen = diagrams if arguments.list == "diagram" else photographs
        for share, pixels, name in sorted(chosen, reverse=True):
            print(f"{share:6.1%} {pixels // 1000:6d} kpx  {name}")
        return 0

    print(f"{len(rows)} images in {arguments.manual.name}")
    print()
    print("Share of each picture that is page white, in tenths:")
    for low in range(0, 10):
        band = [row for row in rows if low / 10 <= row[0] < (low + 1) / 10]
        bar = "#" * (len(band) * 60 // len(rows)) if band else ""
        print(f"  {low / 10:.1f}-{(low + 1) / 10:.1f}  {len(band):4d}  {bar}")
    print()
    print(f"DRAWN ON THE PAGE (>= {DIAGRAM_SHARE:.0%} white): {len(diagrams)}")
    print(f"PHOTOGRAPHED      (<  {DIAGRAM_SHARE:.0%} white): {len(photographs)}")
    print()

    # THE SIZE OF EACH CLASS MATTERS AS MUCH AS ITS COUNT. A drill token drawn
    # 200 pixels wide cannot show a technique whatever it is a picture of.
    for label, group in (("drawn", diagrams), ("photographed", photographs)):
        if not group:
            continue
        sizes = sorted(row[1] for row in group)
        median = int(statistics.median(sizes))
        print(
            f"{label:13s} median {median // 1000:5d} kpx, "
            f"smallest {sizes[0] // 1000:5d}, largest {sizes[-1] // 1000:5d}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
