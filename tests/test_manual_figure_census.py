"""The census's discriminator, pinned on images whose answer is known.

`scripts/manual_figure_census.py` splits the coaches manual into figures DRAWN
on a white page and photographs. The manual is junctioned in from outside git,
so a test that read it would skip on a machine without it, and a guard that
skips guards nothing. These build their own images instead and never skip.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR / "scripts"))

from PIL import Image  # noqa: E402

from manual_figure_census import (  # noqa: E402
    DIAGRAM_SHARE,
    WHITE,
    white_share,
)


def _write(colours, size=(80, 80)) -> Path:
    """An image whose top half is the first colour and bottom half the second."""
    directory = Path(tempfile.mkdtemp())
    path = directory / "sample.png"
    image = Image.new("RGB", size, colours[0])
    if len(colours) > 1:
        lower = Image.new("RGB", (size[0], size[1] // 2), colours[1])
        image.paste(lower, (0, size[1] - size[1] // 2))
    image.save(path)
    return path


class TheDiscriminatorReadsWhatItClaims(unittest.TestCase):
    def test_a_white_page_is_all_white(self):
        self.assertEqual(white_share(_write([(255, 255, 255)])), 1.0)

    def test_a_black_frame_is_no_white(self):
        self.assertEqual(white_share(_write([(0, 0, 0)])), 0.0)

    def test_half_a_page_reads_about_a_half(self):
        share = white_share(_write([(255, 255, 255), (0, 0, 0)]))
        self.assertAlmostEqual(share, 0.5, delta=0.02)

    def test_a_near_white_scan_still_counts_as_the_page(self):
        # The manual is exported rather than pure, so the threshold sits below
        # 255. A page one shade off white must not read as a photograph.
        share = white_share(_write([(WHITE, WHITE, WHITE)]))
        self.assertEqual(share, 1.0)

    def test_one_shade_below_the_threshold_does_not_count(self):
        # And the threshold must actually be a threshold. Without this, WHITE
        # could be lowered to 0 and every test above would still pass.
        share = white_share(_write([(WHITE - 1, WHITE - 1, WHITE - 1)]))
        self.assertEqual(share, 0.0)

    def test_a_saturated_colour_is_not_white_however_bright(self):
        # A bright yellow hurdle is not page white.
        share = white_share(_write([(255, 255, 0)]))
        self.assertEqual(share, 0.0)

    def test_all_three_channels_must_be_bright_and_not_their_average(self):
        # THIS TEST EXISTS BECAUSE A MUTATION SURVIVED. Averaging the channels
        # instead of requiring all three passed every other test in this file,
        # because yellow's average is far below the threshold anyway. This
        # colour's average is ABOVE the threshold while one channel is below
        # it, so the two rules disagree here and nowhere else.
        average = (255 + 255 + 230) / 3
        self.assertGreater(average, WHITE, "the colour must separate the rules")
        self.assertLess(230, WHITE)
        self.assertEqual(white_share(_write([(255, 255, 230)])), 0.0)

    def test_the_boundary_sits_between_the_two_classes(self):
        drawn = white_share(_write([(255, 255, 255), (10, 10, 10)], size=(80, 20)))
        self.assertGreater(drawn, DIAGRAM_SHARE)
        photograph = white_share(_write([(30, 40, 50)]))
        self.assertLess(photograph, DIAGRAM_SHARE)


if __name__ == "__main__":
    unittest.main()
