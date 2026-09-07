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
    what_the_ball_changes,
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


class TheVariantFilterUsesEachMeasuresOwnFloor(unittest.TestCase):
    """`build_library`'s "what the ball changes" filter, driven directly.

    IT WAS INLINE IN `main`, which needs a solver and a built library, so
    reverting its floor lookup failed no test — and a first fix WAS inert,
    because `readings` is keyed "{phase}/{measure}" and the whole key went to
    the lookup, which cannot resolve it and answers with the strictest floor
    and no unit. Every reading stayed at 5 degrees under a heading claiming
    each was held to its own.
    """

    def rows(self, name: str, low: float, high: float) -> list[dict]:
        varied = {
            "probe": [
                {"variant": "a", "readings": {name: low}},
                {"variant": "b", "readings": {name: high}},
            ]
        }
        return what_the_ball_changes(varied).get("probe", [])

    def test_a_three_centimetre_spread_survives(self) -> None:
        """3.0 cm clears the 2.0 length floor and not the 5.0 degrees one."""
        found = self.rows(f"land/{A_LENGTH}", 0.0, 3.0)
        self.assertEqual(len(found), 1, "a 3 cm spread was filtered out")
        self.assertEqual(found[0]["unit"], CENTIMETRES)
        self.assertEqual(found[0]["spread"], 3.0)

    def test_a_three_degree_spread_does_not(self) -> None:
        """The same number, the other unit, the other side of its floor."""
        self.assertEqual(self.rows(f"ready/{AN_ANGLE}", 0.0, 3.0), [])

    def test_the_phase_prefix_is_split_off_before_the_lookup(self) -> None:
        """The blocking defect, stated as the case that failed.

        A bare measure name resolved and a phase-prefixed one did not, so the
        filter worked in a unit test of the helper and not in the program.
        """
        self.assertEqual(len(self.rows(A_LENGTH, 0.0, 3.0)), 1)
        self.assertEqual(len(self.rows(f"anyPhaseAtAll/{A_LENGTH}", 0.0, 3.0)), 1)

    def test_an_unresolvable_name_keeps_the_strictest_floor(self) -> None:
        """No unit, and the tightest rule, rather than a guess."""
        self.assertEqual(self.rows("nothing/likeAMeasure", 0.0, 3.0), [])
        found = self.rows("nothing/likeAMeasure", 0.0, 9.0)
        self.assertEqual(len(found), 1)
        self.assertIsNone(found[0]["unit"])


class TheSeparationThresholdIsPerUnit(unittest.TestCase):
    """`build_library` wrote one `thresholdDegrees` into every receipt.

    The verdict beside it is taken against each measure's own floor, so a
    centimetre winner judged at 2.0 was described by a receipt saying the
    threshold was 5 degrees.

    THE VALUES ARE CHECKED HERE AND THE WIRING IS CHECKED IN
    `test_build_library`. An earlier version of this docstring said the wiring
    was "covered by the suite's own build test", which was not true of any test
    then in the suite: nothing read `phaseSeparation` at all, and reverting the
    receipt's per-row threshold passed every one of these.
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
