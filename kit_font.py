"""Which font draws a kit's letters, chosen at run time and written down.

`kit_paint.py` hard-coded `C:/Windows/Fonts/arialbd.ttf`. It was green on the
machine that wrote it and red six times on the hosted runner, which has no such
path: `OSError: cannot open resource`. Nothing greps for an absolute Windows
path, and the font was the one parameter the layer's sidecar did not record, so
it was invisible in every receipt as well.

THE DEFAULT IS PILLOW'S OWN FACE, and that is a measurement rather than a
preference. Both machines were asked what they had before this was written:

    this machine   Pillow 10.4.0, win32   183 files in C:/Windows/Fonts
    the runner     Pillow 12.3.0, linux    53 files in /usr/share/fonts
    both           ImageFont.load_default(size=N) -> FreeTypeFont, Aileron Regular

So the bundled face resolves on both AND IS THE SAME FACE ON BOTH. A kit painted
here and a kit painted on the runner carry identical letters, which a system
font could not promise: this machine's best bold is Arial and the runner's is
DejaVu. Pillow ships Aileron, so this repository ships no font and needs no new
licence determination to draw a letter.

`--font <path>` overrides it for a nicer face, and then the sidecar says so.

NOTHING HERE FALLS BACK QUIETLY. A named font that is absent is refused, and a
Pillow too old to supply a scalable face is refused, because the alternative is
a bitmap font drawn at one size and silently ignored at every other.
"""
from __future__ import annotations

from pathlib import Path

import PIL
from PIL import ImageFont

BUNDLED = "pillow"


def resolve(requested: str | None, size: int) -> tuple[ImageFont.FreeTypeFont, str]:
    """The font to draw with, and the label that goes in the receipt.

    `requested` is a path, or the word "pillow", or None for the default.
    """
    if requested is not None and requested != BUNDLED:
        path = Path(requested)
        if not path.is_file():
            raise SystemExit(
                f"[kit-font] the font asked for does not exist: {path}. "
                f"Pass a path to a .ttf or .otf, or pass {BUNDLED!r} to use the "
                f"face Pillow carries with it."
            )
        try:
            return ImageFont.truetype(str(path), size), str(path)
        except OSError as error:
            raise SystemExit(
                f"[kit-font] {path} exists but Pillow cannot read it as a "
                f"font: {error}"
            ) from error

    try:
        font = ImageFont.load_default(size=size)
    except TypeError as error:
        raise SystemExit(
            f"[kit-font] Pillow {PIL.__version__} cannot supply a font at a "
            f"size: {error}. `load_default(size=...)` arrived in Pillow 10.1. "
            f"Upgrade Pillow, or pass --font with a path to a .ttf."
        ) from error
    except OSError as error:
        raise SystemExit(
            f"[kit-font] Pillow {PIL.__version__} has no usable default font: "
            f"{error}. Pass --font with a path to a .ttf."
        ) from error

    # A BITMAP FONT IS NOT A REFUSAL TO DRAW, WHICH IS WHY IT IS CHECKED. Before
    # Pillow 10.1 `load_default` returned a fixed-size bitmap face. It draws,
    # it returns no error, and it ignores the size entirely, so a bib asking
    # for 317-pixel letters gets 11-pixel ones and a green run.
    if not isinstance(font, ImageFont.FreeTypeFont):
        raise SystemExit(
            f"[kit-font] Pillow {PIL.__version__} returned a "
            f"{type(font).__name__}, which cannot be drawn at a size. Pass "
            f"--font with a path to a .ttf."
        )
    return font, f"{BUNDLED}:{' '.join(font.getname())}"
