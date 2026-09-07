"""A band names the unit it is in, and the loader refuses any other spelling.

`footHeightGapCm` is a length and its three shipped checkpoints hold their
bounds in `minimumDegrees`. The ledger has carried that as "Centimetres are
stored in a field called degrees" since it was found, and a height measure
would have made it a fourth instance.

So a checkpoint's band is spelled in its measure's own unit, and `read_band`
refuses every other arrangement: no band, two bands, and a band whose unit is
not the measure's -- in BOTH directions, because a degrees measure carrying
centimetre bounds is the same fault wearing the other hat.

The three existing checkpoints are excused by name, because their file is under
`spikes/movements/` and a change there is a key retune that needs a ruling
first. That list must only shrink, and the guards below hold it to that.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from movement_definition import (
    BAND_FIELDS,
    BANDS_AWAITING_A_GATE_FOUR_RULING,
    MovementDefinitionError,
    definition_files,
    load,
    read_band,
)
from segment_measures import CENTIMETRES, DEGREES, MEASURE_UNITS

MOVEMENTS = Path(__file__).resolve().parent / "movements"

A_LENGTH = "ballHeightCm"
AN_ANGLE = "leftElbowFlexionDegrees"


def band(measure: str, **fields) -> dict:
    return {"measure": measure, "cue": "a cue", "why": "a reason", **fields}


class TheLoaderRefusesASpellingThatIsNotTheUnit(unittest.TestCase):
    def refuses(self, checkpoint: dict) -> str:
        with self.assertRaises(MovementDefinitionError) as raised:
            read_band(checkpoint, "someDrill", "somePhase")
        return str(raised.exception)

    def test_a_length_may_not_hold_its_band_in_degrees_fields(self) -> None:
        """The fault this whole field exists for."""
        said = self.refuses(band(A_LENGTH, minimumDegrees=0.0, maximumDegrees=9.0))
        self.assertIn("degrees", said)
        self.assertIn("centimetres", said)

    def test_an_angle_may_not_hold_its_band_in_centimetre_fields(self) -> None:
        """The other direction, which is the same fault reversed.

        A guard that only refused one way would let the next measure be
        mis-spelled as long as it was mis-spelled the fashionable way.
        """
        said = self.refuses(
            band(AN_ANGLE, minimumCentimetres=0.0, maximumCentimetres=9.0)
        )
        self.assertIn("centimetres", said)
        self.assertIn("degrees", said)

    def test_two_bands_are_refused_rather_than_one_of_them_chosen(self) -> None:
        said = self.refuses(band(
            A_LENGTH,
            minimumDegrees=0.0, maximumDegrees=9.0,
            minimumCentimetres=0.0, maximumCentimetres=9.0,
        ))
        self.assertIn("two bands", said)

    def test_no_band_is_refused_and_the_message_says_which_to_use(self) -> None:
        said = self.refuses(band(A_LENGTH))
        self.assertIn("minimumCentimetres", said)

    def test_an_undeclared_measure_is_refused_before_its_band_is_read(self):
        """`unit_of` raises, and it should: a band with no unit is unreadable."""
        with self.assertRaises(KeyError):
            read_band(
                band("somethingNobodyDeclared", minimumDegrees=0.0,
                     maximumDegrees=9.0),
                "someDrill", "somePhase",
            )

    def test_the_right_spelling_is_accepted_for_each_unit(self) -> None:
        """Guards the guards. A `read_band` that refused everything would
        pass every case above and ship a loader that reads nothing."""
        self.assertEqual(
            read_band(band(A_LENGTH, minimumCentimetres=150.0,
                           maximumCentimetres=230.0), "d", "p"),
            (150.0, 230.0),
        )
        self.assertEqual(
            read_band(band(AN_ANGLE, minimumDegrees=20.0, maximumDegrees=60.0),
                      "d", "p"),
            (20.0, 60.0),
        )


class TheExcusedListOnlyShrinks(unittest.TestCase):
    """Three checkpoints in a gate-4 file, excused by name until a ruling.

    Renaming their two keys changes no number any checkpoint reads, so it may
    be ruled a correction rather than a retune. Until then the loader must read
    the shipped library, and the excuse must not become a door.
    """

    def test_it_holds_exactly_the_three_that_exist(self) -> None:
        found = set()
        for path in definition_files(MOVEMENTS):
            data = json.loads(path.read_text(encoding="utf-8"))
            for phase in data["phases"]:
                for checkpoint in phase["checkpoints"]:
                    measure = checkpoint["measure"]
                    if MEASURE_UNITS.get(measure) != CENTIMETRES:
                        continue
                    if "minimumDegrees" not in checkpoint:
                        continue
                    found.add((data["movementId"], phase["name"], measure))
        self.assertEqual(
            found, set(BANDS_AWAITING_A_GATE_FOUR_RULING),
            "the excused list and the library disagree. It may only SHRINK: "
            "a new centimetre checkpoint spells its band in centimetres, and "
            "an excused one leaves this list when its file is corrected.",
        )

    def test_every_excused_entry_is_a_real_checkpoint(self) -> None:
        """An excuse for something that does not exist excuses anything."""
        for movement_id, phase_name, measure in sorted(
            BANDS_AWAITING_A_GATE_FOUR_RULING
        ):
            with self.subTest(movement=movement_id, phase=phase_name):
                data = json.loads(
                    (MOVEMENTS / f"{movement_id}.json").read_text(encoding="utf-8")
                )
                phases = {p["name"]: p for p in data["phases"]}
                self.assertIn(phase_name, phases)
                self.assertIn(
                    measure,
                    [c["measure"] for c in phases[phase_name]["checkpoints"]],
                )

    def test_an_unexcused_drill_with_the_same_fault_is_still_refused(self):
        """The excuse is per checkpoint, not per fault."""
        with self.assertRaises(MovementDefinitionError):
            read_band(
                band("footHeightGapCm", minimumDegrees=0.0, maximumDegrees=9.0),
                "netball_double_foot_landing", "aPhaseThatIsNotExcused",
            )


class TheShippedLibraryStillLoads(unittest.TestCase):
    def test_every_definition_reads_through_the_new_rule(self) -> None:
        found = definition_files(MOVEMENTS)
        self.assertGreaterEqual(len(found), 12, "the library was not read")
        for path in found:
            with self.subTest(definition=path.name):
                load(path)

    def test_both_units_have_a_field_pair(self) -> None:
        self.assertEqual(sorted(BAND_FIELDS), sorted({DEGREES, CENTIMETRES}))
        for unit in (DEGREES, CENTIMETRES):
            low, high = BAND_FIELDS[unit]
            self.assertTrue(low.startswith("minimum"))
            self.assertTrue(high.startswith("maximum"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
