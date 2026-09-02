"""Guards for the before-and-after sheet's two claims: the build and the change.

Both are claims a reader cannot check by looking. A directory named "after" is
not a build, and a picture that looks the same is not an unchanged one.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR / "scripts"))

from before_after_sheet import BAND, build_of, verdict  # noqa: E402


class BuildOfTest(unittest.TestCase):
    def test_the_build_comes_from_the_receipt_and_not_the_directory_name(self):
        """A folder called "after" asserts a build. A receipt records one."""
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder)
            (here / "d.render.json").write_text(json.dumps(
                {"generatedFrom": {"commit": "ac240b27db9c", "treeWasClean": True}}
            ), encoding="utf-8")

            self.assertEqual("ac240b2", build_of(here, "d"))

    def test_a_dirty_tree_is_carried_onto_the_sheet(self):
        """The reader must see it on the picture, not only in the receipt.

        A commit named from a dirty tree names a build that never existed, and
        a sheet that prints the sha alone hides that.
        """
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder)
            (here / "d.render.json").write_text(json.dumps(
                {"generatedFrom": {"commit": "ac240b27db9c", "treeWasClean": False}}
            ), encoding="utf-8")

            self.assertIn("DIRTY", build_of(here, "d"))

    def test_a_receipt_with_no_build_says_unstamped_rather_than_nothing(self):
        """Every receipt written before 2026-09-02 is in this state.

        Leaving the column blank would read as "no change of build", when what
        it means is "nobody recorded one". That gap is why the stamp exists.
        """
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder)
            (here / "d.render.json").write_text(json.dumps(
                {"movementId": "d", "phases": []}
            ), encoding="utf-8")

            self.assertIn("UNSTAMPED", build_of(here, "d"))

    def test_a_receipt_carrying_the_RETIRED_field_is_read_and_labelled(self):
        """The archived interim set carries `build`, and must stay legible.

        It is read so that archive remains readable, and LABELLED so nobody
        mistakes a receipt from that one-commit window for a current one.
        """
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder)
            (here / "d.render.json").write_text(json.dumps(
                {"build": {"commit": "05e58cd1234", "treeWasClean": True}}
            ), encoding="utf-8")

            said = build_of(here, "d")

            self.assertIn("05e58cd", said)
            self.assertIn("retired", said)

    def test_the_converged_stamp_beats_the_retired_one_when_both_are_present(self):
        """Data from the current contract wins. The fallback is a fallback."""
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder)
            (here / "d.render.json").write_text(json.dumps({
                "generatedFrom": {"commit": "9999999aaa", "treeWasClean": True},
                "build": {"commit": "05e58cd1234", "treeWasClean": True},
            }), encoding="utf-8")

            said = build_of(here, "d")

            self.assertEqual("9999999", said)
            self.assertNotIn("retired", said)

    def test_a_missing_receipt_is_named_and_not_guessed(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual("no receipt", build_of(Path(folder), "d"))


class VerdictTest(unittest.TestCase):
    def test_a_change_below_the_band_is_called_unchanged_to_the_eye(self):
        """Six of the eight drills moved by about a degree, which no one sees.

        Calling that "changed" would send a reader hunting for a difference
        that is real in the data and invisible in the picture.
        """
        self.assertIn("unchanged", verdict(
            {"comparable": True, "changedShare": BAND / 2, "worst": 3}))

    def test_a_real_change_reports_its_size(self):
        said = verdict({"comparable": True, "changedShare": 0.21, "worst": 200})

        self.assertIn("21", said)
        self.assertNotIn("unchanged", said)

    def test_renders_of_different_sizes_are_refused_not_compared(self):
        """Resizing one to match would invent the comparison.

        A difference measured between two shapes is a measurement of the
        resampling, and it would be reported as a change in the athlete.
        """
        said = verdict({"comparable": False, "changedShare": None, "worst": None})

        self.assertIn("NOT COMPARABLE", said)


if __name__ == "__main__":
    unittest.main()
