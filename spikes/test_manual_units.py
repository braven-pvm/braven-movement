"""The coach's page names the unit, and the third writer declares its measures.

Two faults, found by the consumer search that moved the receipt's schema, and
they are not the same fault repeated.

`manual_page_template.html` rendered a band as `${m.band[0]}-${m.band[1]}&deg;`
with a HARDCODED degree sign. Three shipped checkpoints hold a centimetre band,
so a length read as degrees on a page a COACH looks at. The page is formatted in
Python now and the template prints what it is given, because a template has no
way to look a unit up and should not be asked to.

`hand_orientation` writes six measures into receipts with a REPORTED verdict and
no band. Reported is not unitless: `unit_of` raised for all six. Nothing caught
it because `test_written_measures` stands at the two SOLVERS' measurement rows
and this is a THIRD writer.

Every guard here is stdlib-only, which is where a units check is most use.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import hand_orientation
from movement_definition import (
    BAND_SUFFIX,
    Checkpoint,
    band_label,
    definition_files,
    load,
)
from segment_measures import CENTIMETRES, DEGREES, MEASURE_UNITS, unit_of

SPIKES = Path(__file__).resolve().parent
TEMPLATE = SPIKES / "manual_page_template.html"
MOVEMENTS = SPIKES / "movements"


def check(measure: str, low: float, high: float) -> Checkpoint:
    return Checkpoint(measure, low, high, "a cue", "a reason")


class TheBandOnTheCoachsPageNamesItsUnit(unittest.TestCase):
    def test_a_length_reads_in_centimetres(self) -> None:
        """The defect, in the row a coach reads."""
        said = band_label(check("footHeightGapCm", 0.0, 14.0))
        self.assertIn("cm", said)
        self.assertNotIn("°", said)

    def test_an_angle_still_reads_in_degrees(self) -> None:
        said = band_label(check("leftElbowFlexionDegrees", 20.0, 60.0))
        self.assertIn("°", said)
        self.assertNotIn("cm", said)

    def test_an_undeclared_measure_gets_no_unit_rather_than_a_guess(self):
        said = band_label(check("somethingNobodyDeclared", 0.0, 9.0))
        self.assertNotIn("°", said)
        self.assertNotIn("cm", said)
        self.assertIn("9", said)

    def test_both_bounds_survive_the_formatting(self) -> None:
        """A label that drops a number is worse than one with no unit."""
        said = band_label(check("footHeightGapCm", 0.0, 14.0))
        self.assertIn("0", said)
        self.assertIn("14", said)

    def test_every_declared_unit_has_a_suffix(self) -> None:
        """A new unit must not fall through to the empty string in silence."""
        self.assertEqual(
            sorted(BAND_SUFFIX), sorted({DEGREES, CENTIMETRES}),
            "a unit is declared that the coach's page cannot spell",
        )

    def test_the_template_carries_no_unit_of_its_own(self) -> None:
        """The template must PRINT a label, not build one.

        A hardcoded `&deg;` is how a length came to read as an angle, and a
        template cannot look a unit up. This is a check on text, which is a
        weak guard on its own -- the guards above are the real ones, and this
        one stops the formatting migrating back into the file that cannot do
        it correctly.
        """
        page = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("m.bandLabel", page, "the template ignores the label")
        band_row = [line for line in page.splitlines() if "m.band" in line]
        self.assertTrue(band_row, "no row renders a band")
        for line in band_row:
            with self.subTest(line=line.strip()):
                self.assertNotIn("&deg;", line)


class TheThirdWriterDeclaresItsMeasures(unittest.TestCase):
    """`hand_orientation`, which the solvers' guard does not reach."""

    def names(self) -> list[str]:
        return sorted(
            f"{prefix}{suffix}"
            for prefix in ("left", "right")
            for suffix in hand_orientation.CONVENTIONS
        )

    def test_it_writes_six_and_this_guard_sees_all_of_them(self) -> None:
        """Guards the guard. Three conventions, two hands."""
        self.assertEqual(len(self.names()), 6)
        self.assertEqual(len(hand_orientation.CONVENTIONS), 3)

    def test_unit_of_answers_for_every_one(self) -> None:
        """The failure the gap produced: `unit_of` raised for all six."""
        for measure in self.names():
            with self.subTest(measure=measure):
                self.assertEqual(unit_of(measure), DEGREES)

    def test_they_are_reported_and_not_graded_and_that_is_unchanged(self):
        """Declaring a unit is not the same as setting a band.

        Bands are coaching content and no coach has seen these numbers. This
        pack gives the six a UNIT and leaves them ungraded, so a later reader
        cannot take the declaration as a licence to band them.
        """
        graded = {
            measure
            for path in definition_files(MOVEMENTS)
            for phase in load(path).phases
            for measure in phase.graded_measures()
        }
        self.assertTrue(graded, "no definition graded anything")
        for measure in self.names():
            with self.subTest(measure=measure):
                self.assertNotIn(measure, graded)
                self.assertIn(measure, MEASURE_UNITS)

    def test_their_names_would_have_been_guessed_right(self) -> None:
        """Which is the reason the gap was invisible, stated as a check.

        Every one ends in "Degrees" and every one IS degrees, so a reader
        applying the suffix rule would have been correct and the table would
        still have said nothing. `unit_of` refuses that rule on purpose.
        """
        for measure in self.names():
            with self.subTest(measure=measure):
                self.assertTrue(measure.endswith("Degrees"))
        with self.assertRaises(KeyError):
            unit_of("somethingThatEndsInDegrees")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
