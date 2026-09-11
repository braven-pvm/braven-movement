"""Which font a kit's letters are drawn with, and what happens when there is none.

`kit_paint.py` hard-coded `C:/Windows/Fonts/arialbd.ttf`. The suite was green on
the machine that wrote it and the hosted runner failed six tests with
`OSError: cannot open resource`. An absolute path to another operating system is
the escape nobody greps for, and no test here could have caught it, because
every one of them ran on the machine the path was true on.

So these tests do not check that A font loads. They check the two things that
were actually wrong: that the default depends on NOTHING outside Pillow, and
that every way of having no font ends in a refusal that names what was tried.

**The face is pinned on purpose.** Pillow carries Aileron, and both machines
were measured before this was written: Pillow 10.4.0 here and 12.3.0 on the
runner, both returning a scalable Aileron Regular. Pinning the NAME is what
turns "the letters are the same on both machines" from a hope into something
that fails out loud the day a Pillow release changes it.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from kit_font import BUNDLED, resolve  # noqa: E402


class KitFont(unittest.TestCase):
    def test_the_default_needs_nothing_outside_pillow(self):
        """No path, no system font directory, no operating system."""
        from PIL import ImageFont

        font, label = resolve(None, 40)
        self.assertIsInstance(font, ImageFont.FreeTypeFont)
        self.assertEqual(label, "pillow:Aileron Regular")
        self.assertGreater(font.getlength("GS"), 0)

    def test_asking_for_the_bundled_face_by_name_is_the_same_thing(self):
        self.assertEqual(resolve(BUNDLED, 40)[1], resolve(None, 40)[1])

    def test_a_font_that_is_not_there_is_refused_and_named(self):
        missing = MODULE_DIR / "no-such-font-8f3a.ttf"
        self.assertFalse(missing.exists(), "the fixture must not exist")
        with self.assertRaises(SystemExit) as refusal:
            resolve(str(missing), 40)
        self.assertIn("does not exist", str(refusal.exception))
        self.assertIn(missing.name, str(refusal.exception))

    def test_a_file_that_is_not_a_font_is_refused_and_named(self):
        """The path existing is not the same as the file being readable.

        A silent success here would draw nothing and report nothing, which is
        the shape of fault this whole file exists for.
        """
        with tempfile.TemporaryDirectory() as name:
            impostor = Path(name) / "pretend.ttf"
            impostor.write_text("this is not a font", encoding="utf-8")
            with self.assertRaises(SystemExit) as refusal:
                resolve(str(impostor), 40)
            self.assertIn("cannot read it as a font", str(refusal.exception))
            self.assertIn("pretend.ttf", str(refusal.exception))

    def test_no_instrument_carries_a_hard_coded_font_path(self):
        """The fault was one line in one file, and it had already been copied.

        `kit_sheet.py` held the same line and no test executed it, so the runner
        could not have found that one either. This reads the SOURCE of every
        instrument, because the next copy will be made the same way.
        """
        offenders = []
        for path in sorted(MODULE_DIR.glob("kit_*.py")):
            if path.name == "kit_font.py":
                continue  # it quotes the old path in its own explanation
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), start=1):
                lowered = line.lower()
                if "windows/fonts" in lowered or "windows\\fonts" in lowered:
                    offenders.append(f"{path.name}:{number}")
                if "/usr/share/fonts" in lowered:
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual(offenders, [], "a font path is hard coded again")


if __name__ == "__main__":
    unittest.main()
