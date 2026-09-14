"""Which frames a clip sheet says it shows, and which it actually shows.

The sheet labels every tile with the frame number it came from, and a coach
reads those numbers as a claim about the clip. So the arithmetic that picks the
frames is checked here against a clip whose every frame is a different colour:
if the picker drifts by one, the colour under the label is wrong and this fails.

The clip is synthetic and tiny. It is not a render and it is not meant to be.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

SHEET = MODULE_DIR / "kit_clip_sheet.py"
FRAMES = 12
SIDE = 96
WIDTH = 120
COUNT = 4


def build_clip(path: Path) -> None:
    """A clip whose frame N is a solid grey of value 20*N."""
    import cv2

    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (SIDE, SIDE)
    )
    if not writer.isOpened():
        raise unittest.SkipTest("no mp4v encoder on this machine")
    for number in range(FRAMES):
        frame = np.full((SIDE, SIDE, 3), 20 * number, dtype=np.uint8)
        writer.write(frame)
    writer.release()


class ClipSheet(unittest.TestCase):
    def test_the_labels_match_the_frames(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            clip = root / "clip.mp4"
            build_clip(clip)
            output = root / "sheet.png"
            finished = subprocess.run(
                [sys.executable, "-B", str(SHEET), "--clip", str(clip),
                 "--output", str(output), "--count", str(COUNT),
                 "--columns", str(COUNT), "--width", str(WIDTH)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(
                finished.returncode, 0,
                f"{finished.stdout}\n{finished.stderr}",
            )
            self.assertIn("KIT CLIP SHEET OK", finished.stdout)
            self.assertIn(f"{FRAMES} frames", finished.stdout)

            sheet = np.asarray(Image.open(output).convert("RGB"))
            wanted = [
                int(round(index * (FRAMES - 1) / (COUNT - 1)))
                for index in range(COUNT)
            ]
            self.assertEqual(wanted, [0, 4, 7, 11])
            for column, number in enumerate(wanted):
                middle = sheet[
                    sheet.shape[0] - WIDTH // 2,
                    column * WIDTH + WIDTH // 2,
                ]
                self.assertAlmostEqual(
                    float(middle.mean()), 20.0 * number, delta=12.0,
                    msg=f"tile {column} is labelled frame {number + 1} and is "
                        f"not that frame's colour",
                )

    def test_a_clip_shorter_than_the_sheet_is_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            clip = root / "clip.mp4"
            build_clip(clip)
            finished = subprocess.run(
                [sys.executable, "-B", str(SHEET), "--clip", str(clip),
                 "--output", str(root / "sheet.png"), "--count", str(FRAMES + 4),
                 "--width", str(WIDTH)],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(finished.returncode, 0)
            self.assertIn("were asked for", finished.stdout + finished.stderr)


if __name__ == "__main__":
    unittest.main()
