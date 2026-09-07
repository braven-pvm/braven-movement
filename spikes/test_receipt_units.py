"""A receipt says what its numbers are in.

`to_receipt` wrote `band` as two bare numbers. Three of the library's shipped
checkpoints are centimetres and the rest are degrees, so a consumer reading a
receipt had exactly the problem the coach sentence had before it named the
measure's unit: a pair of numbers and no way to say what they measure.

The same fault ran through `build_library`'s receipt and its two prints, where
one scalar described a threshold that is now per unit. All four were latent —
the landing is the only drill grading a length and its phase winner is an angle
on both solve paths — and latent is not fixed.

These guards need no solver: they build a definition and hand it measurements.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from movement_definition import (
    MINIMUM_MEANINGFUL_BAND,
    Checkpoint,
    MovementDefinition,
    Phase,
    definition_files,
    load,
    minimum_meaningful_band,
)
from segment_measures import CENTIMETRES, DEGREES, unit_of

MOVEMENTS = Path(__file__).resolve().parent / "movements"

A_LENGTH = "footHeightGapCm"
AN_ANGLE = "leftElbowFlexionDegrees"


def a_movement() -> MovementDefinition:
    """One phase grading a length and an angle together."""
    return MovementDefinition(
        movement_id="probe",
        sport="netball",
        skill="a skill",
        source="a source",
        phases=(
            Phase("only", 0.0, (
                Checkpoint(A_LENGTH, 0.0, 6.0, "a cue", "a reason"),
                Checkpoint(AN_ANGLE, 20.0, 60.0, "a cue", "a reason"),
            )),
        ),
    )


class TheReceiptCarriesItsUnits(unittest.TestCase):
    def rows(self) -> list[dict]:
        frame = {A_LENGTH: 3.0, AN_ANGLE: 40.0}
        receipt = a_movement().assess([frame]).to_receipt()
        return receipt["phases"]["only"]

    def test_every_row_names_the_unit_of_its_own_measure(self) -> None:
        rows = self.rows()
        self.assertEqual(len(rows), 2, "the probe lost a checkpoint")
        for row in rows:
            with self.subTest(measure=row["measure"]):
                self.assertEqual(row["unit"], unit_of(row["measure"]))

    def test_the_two_rows_do_not_agree_or_this_guards_nothing(self) -> None:
        """Guards the guard.

        A hardcoded "degrees" passes a check that only ever sees angles, which
        is why the probe grades a length and an angle in the SAME phase.
        """
        units = {row["unit"] for row in self.rows()}
        self.assertEqual(units, {DEGREES, CENTIMETRES})

    def test_the_band_pair_is_unchanged_so_readers_still_work(self) -> None:
        """The fix is ADDITIVE. `tuple(row["band"])` is read elsewhere."""
        for row in self.rows():
            with self.subTest(measure=row["measure"]):
                self.assertEqual(len(row["band"]), 2)
                self.assertLess(row["band"][0], row["band"][1])

    def test_the_shipped_library_produces_a_unit_on_every_row(self) -> None:
        """Against the real definitions, not only the probe."""
        seen = set()
        for path in definition_files(MOVEMENTS):
            definition = load(path)
            frame = {
                measure: 0.0
                for phase in definition.phases
                for measure in phase.graded_measures()
            }
            receipt = definition.assess([frame] * len(definition.phases)).to_receipt()
            for rows in receipt["phases"].values():
                for row in rows:
                    self.assertEqual(row["unit"], unit_of(row["measure"]))
                    seen.add(row["unit"])
        self.assertIn(
            CENTIMETRES, seen,
            "no shipped checkpoint grades a length, so this saw only angles",
        )
        self.assertIn(DEGREES, seen)


class TheSeparationThresholdIsPerUnit(unittest.TestCase):
    """`build_library` wrote one `thresholdDegrees` into every receipt.

    The verdict beside it is taken against each measure's own floor, so a
    centimetre winner judged at 2.0 was described by a receipt saying the
    threshold was 5 degrees. The rows below are what `build_library` writes;
    the module itself needs a solver, so the values it derives are checked
    here and the wiring is covered by the suite's own build test.
    """

    def test_every_declared_unit_has_a_floor_to_publish(self) -> None:
        self.assertEqual(
            sorted(MINIMUM_MEANINGFUL_BAND), sorted({DEGREES, CENTIMETRES})
        )
        for unit, floor in MINIMUM_MEANINGFUL_BAND.items():
            with self.subTest(unit=unit):
                self.assertGreater(floor, 0.0)

    def test_a_length_and_an_angle_get_different_thresholds(self) -> None:
        """The whole reason one scalar could not describe it."""
        length, _ = minimum_meaningful_band(A_LENGTH)
        angle, _ = minimum_meaningful_band(AN_ANGLE)
        self.assertNotEqual(length, angle)
        self.assertEqual(length, MINIMUM_MEANINGFUL_BAND[CENTIMETRES])
        self.assertEqual(angle, MINIMUM_MEANINGFUL_BAND[DEGREES])

    def test_an_undeclared_measure_publishes_no_unit(self) -> None:
        """A phase with no checkpoints has `measure` None, and the receipt
        must carry None rather than inventing a unit for it."""
        floor, unit = minimum_meaningful_band("somethingNobodyDeclared")
        self.assertIsNone(unit)
        self.assertEqual(floor, max(MINIMUM_MEANINGFUL_BAND.values()))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
