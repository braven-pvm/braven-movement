"""The docs number audit, which had no test until 2026-09-09.

The tool marks a row that carries a quantity below the hips, because nothing
below the hips may be presented as a graded value on this rig. The mark decides
whether a reader refreshes a number or leaves it, so a wrong mark in EITHER
direction costs something:

- A false mark tells a lane not to refresh a number it should refresh. The word
  "shipped" contains `hip` and put the mark on 44 rows about builds.
- A missed mark lets a lower body number be refreshed and published. The terms
  appear inside `leftKneeFlexionDegrees` and `double_foot_landing`, where a
  plain word boundary does not match.

Both directions are pinned here, by example, and the examples are the real
strings from the documents rather than invented ones.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIT = REPO / "scripts" / "docs_number_audit.py"


def _load():
    spec = importlib.util.spec_from_file_location("docs_number_audit", AUDIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BelowTheHipsTest(unittest.TestCase):
    """Every case is a string that appears in `docs/`, or is shaped like one."""

    BELOW = (
        "leftKneeFlexionDegrees at 12.4",
        "footHeightGapCm is 0.5",
        "double_foot_landing 19.91",
        "the hips drop 0.30 of a leg",
        "her ankle sits 2.1 cm off",
        "both feet 0.0 off the ground",
        "the stance is 0.42 legs wide",
        "the thigh at 3.0",
        "the toe at 1.0",
        "the shin at 1.0",
        "the calf at 1.0",
    )

    ABOVE = (
        "the parameter set that shipped reached 15.44",
        "the library that ships carries 11 drills",
        "a relationship of 2.0 between the two",
        "the elbows sit 38.73 cm apart, a distance",
        "two distances, 1.02 and 1.13",
    )

    def setUp(self):
        self.module = _load()

    def test_a_lower_body_row_is_marked(self):
        for text in self.BELOW:
            with self.subTest(text=text):
                self.assertTrue(self.module.below_the_hips(text), text)

    def test_a_row_that_only_spells_a_term_is_not_marked(self):
        for text in self.ABOVE:
            with self.subTest(text=text):
                self.assertFalse(self.module.below_the_hips(text), text)

    def test_the_word_boundary_alone_would_miss_a_camel_case_identifier(self):
        """The reason the text is split before the boundary is applied.

        Without this the fix for "shipped" would silently unmark every
        `leftKneeFlexionDegrees` row, which is the dangerous direction.
        """
        module = self.module
        self.assertIsNone(module.LOWER_BODY.search("leftKneeFlexionDegrees"))
        self.assertIsNotNone(
            module.LOWER_BODY.search(module.WORD_START.sub(" ", "leftKneeFlexionDegrees")))


class RowsForTest(unittest.TestCase):
    """The row reader, on a document written for the test rather than a real one."""

    def setUp(self):
        self.module = _load()

    def _rows(self, text: str):
        path = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        document = path / "SAMPLE.md"
        document.write_text(text, encoding="utf-8")
        return list(self.module.rows_for(document))

    def test_a_number_takes_the_build_named_above_it(self):
        rows = self._rows("# Head\n\nOn `2413f9d` the elbows sit 38.73 cm apart.\n")
        self.assertEqual([row["build"] for row in rows], ["2413f9d"])

    def test_a_later_build_replaces_an_earlier_one(self):
        rows = self._rows(
            "On `ac240b2` it read 45.68.\n\nOn `2413f9d` it reads 40.36.\n")
        self.assertEqual([row["build"] for row in rows], ["ac240b2", "2413f9d"])

    def test_the_build_carries_down_to_a_line_that_does_not_name_one(self):
        """The rule that decides how a paper must be laid out.

        A table under a heading carries no hash on any of its rows, so the build
        must persist from the sentence above it. This is not decoration: it is
        why a section that names an older build MIS-ATTRIBUTES every section
        after it, and why a paper puts such a section last.
        """
        rows = self._rows(
            "# Part two, on `2413f9d`\n\n"
            "    elbows    38.73\n"
            "    wrists    33.07\n")
        self.assertEqual([row["build"] for row in rows], ["2413f9d", "2413f9d"])

    def test_an_older_build_named_mid_document_carries_on_downwards(self):
        rows = self._rows(
            "On `2413f9d` it reads 40.36.\n\n"
            "The agenda read 45.68 on `ac240b2`.\n\n"
            "    a later table    1.11\n")
        self.assertEqual([row["build"] for row in rows],
                         ["2413f9d", "ac240b2", "ac240b2"])

    def test_a_line_naming_two_builds_takes_the_first(self):
        """A writer must split such a line, and this pins which way it falls.

        The tool cannot resolve a line that names two builds. It takes the
        first, so a sentence carrying an old figure and a new one is attributed
        to the old build, and the new figure is mislabelled. The fix is in the
        document and not in the tool: put each build's numbers on its own line.
        """
        rows = self._rows("On `ac240b2` 45.68, and on `2413f9d` 40.36.\n")
        self.assertEqual([row["build"] for row in rows], ["ac240b2"])
        self.assertEqual(rows[0]["numbers"], ["45.68", "40.36"])

    def test_a_number_with_no_build_above_it_is_reported_as_such(self):
        rows = self._rows("# Head\n\nThe elbows sit 38.73 cm apart.\n")
        self.assertEqual([row["build"] for row in rows], [""])

    def test_a_version_in_a_file_name_is_not_a_measurement(self):
        self.assertEqual(self._rows("Read `elbow-curve-0.1.json` for it.\n"), [])

    def test_the_marked_flag_reaches_the_row(self):
        rows = self._rows("On `2413f9d` leftKneeFlexionDegrees is 12.40.\n")
        self.assertEqual([row["lowerBody"] for row in rows], [True])
        rows = self._rows("On `2413f9d` the set that shipped read 15.44.\n")
        self.assertEqual([row["lowerBody"] for row in rows], [False])


if __name__ == "__main__":
    unittest.main()
