"""Every graded measure declares a unit, and NOT every one is degrees.

`footHeightGapCm` is a length. Every other graded measure is an angle, and
until this table existed nothing recorded the difference: consumers read every
column as degrees because every column had, so far, been degrees. That is the
units-across-a-boundary fault this project has recorded six times, waiting for
its seventh.

The video lane keeps its own spelling of the same units in `video_measures`.
That duplication is deliberate and this file is where it is CHECKED rather
than merged. The video gate asks whether the engine's declared unit matches
the registry's; merging the two would make that question pass by construction,
which is the tautology this project keeps finding.

No solver. `segment_measures` imports `math`, `video_measures` imports
`segment_measures`, and the definitions are read off disk. The rule for which
measures get a curve lives in `reference_measures`, which imports nothing
heavier, so it is called here rather than read out of the exporter's source.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from movement_definition import (
    Checkpoint, MovementDefinition, Phase, load, union_of_graded,
)
from reference_measures import RECOVERABLE, wanted
from segment_measures import CENTIMETRES, DEGREES, MEASURE_UNITS, unit_of

SPIKE_DIR = Path(__file__).resolve().parent
MOVEMENTS = SPIKE_DIR / "movements"
NOT_DEFINITIONS = (".ball.json", ".motion.json", ".technique.json", ".proof.json")


def definitions():
    return [
        load(path)
        for path in sorted(MOVEMENTS.glob("*.json"))
        if not any(path.name.endswith(one) for one in NOT_DEFINITIONS)
    ]


class TheTableItself(unittest.TestCase):
    def test_every_declared_unit_is_a_non_empty_string(self) -> None:
        for measure, unit in MEASURE_UNITS.items():
            with self.subTest(measure=measure):
                self.assertIsInstance(unit, str)
                self.assertTrue(unit.strip())

    def test_unit_of_returns_what_the_table_declares(self) -> None:
        for measure, unit in MEASURE_UNITS.items():
            with self.subTest(measure=measure):
                self.assertEqual(unit_of(measure), unit)

    def test_an_undeclared_measure_RAISES_rather_than_defaulting(self) -> None:
        """The whole point. A fallback to degrees would make the next length
        silently an angle, and every other case here would still pass."""
        with self.assertRaises(KeyError) as caught:
            unit_of("someMeasureNobodyDeclared")
        self.assertIn("no declared unit", str(caught.exception))

    def test_the_suffix_is_not_what_decides(self) -> None:
        """`unit_of` must read the table, not the name. A suffix rule would
        pass every case above, because the names do currently agree with their
        units."""
        MEASURE_UNITS["probeThatLooksLikeDegrees"] = CENTIMETRES
        try:
            self.assertEqual(unit_of("probeThatLooksLikeDegrees"), CENTIMETRES)
        finally:
            del MEASURE_UNITS["probeThatLooksLikeDegrees"]

    def test_not_everything_is_degrees(self) -> None:
        """The anti-hollow clause for the whole file. If every measure were
        degrees, a `unit_of` that ignored its argument and returned "degrees"
        would satisfy every other case, and the table would be decoration."""
        self.assertEqual(unit_of("footHeightGapCm"), CENTIMETRES)
        self.assertNotEqual(CENTIMETRES, DEGREES)
        self.assertGreater(
            len({unit for unit in MEASURE_UNITS.values()}), 1,
            "every measure declares the same unit, so nothing here is testing "
            "that the unit is carried at all",
        )


class AgainstWhatTheLibraryGrades(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.found = definitions()

    def test_the_library_was_actually_read(self) -> None:
        """Guards the guard. A glob matching nothing passes the case below."""
        self.assertGreaterEqual(len(self.found), 8)

    def test_every_graded_measure_has_a_declared_unit(self) -> None:
        graded = {m for d in self.found for m in d.graded_measures()}
        self.assertTrue(graded, "no definition grades anything")
        missing = sorted(graded - set(MEASURE_UNITS))
        self.assertEqual(
            missing, [],
            f"{missing} are graded by a checkpoint and have no declared unit. "
            "A reference curve for one of these would be written with no way "
            "to say what it is in.",
        )


class AgainstTheVideoLanesOwnSpelling(unittest.TestCase):
    """The two-instrument check, kept as two instruments.

    The video gate compares the engine's declared unit against its registry's.
    That comparison is worth making only while the two are spelled
    independently, so they are compared here and never merged.
    """

    @classmethod
    def setUpClass(cls) -> None:
        from video_measures import MEASURES

        cls.registry = {name: entry.unit for name, entry in MEASURES.items()}

    def test_the_two_tables_actually_overlap(self) -> None:
        """Guards the guard. Two tables sharing no measure agree vacuously."""
        shared = set(self.registry) & set(MEASURE_UNITS)
        self.assertGreaterEqual(
            len(shared), 9,
            f"only {len(shared)} measures are in both tables, so the "
            "comparison below is checking almost nothing",
        )

    def test_the_two_spellings_agree_everywhere_they_meet(self) -> None:
        for measure in sorted(set(self.registry) & set(MEASURE_UNITS)):
            with self.subTest(measure=measure):
                self.assertEqual(
                    MEASURE_UNITS[measure], self.registry[measure],
                    f"the engine calls {measure} {MEASURE_UNITS[measure]!r} and "
                    f"the video registry calls it {self.registry[measure]!r}. "
                    "One of them is wrong and the gate cannot tell which.",
                )


class TheExporterCanDeclareEverythingItWrites(unittest.TestCase):
    """The export raises on an undeclared unit, so this is what stops that.

    It reconstructs the exporter's rule — graded OR recoverable — from the
    definitions and the literal floor, rather than importing the module.
    """

    def test_the_floor_holds_even_when_nothing_grades_it(self) -> None:
        """The floor's whole purpose, and it needs a hand-built library.

        Against the REAL library this cannot be tested: every recoverable
        measure happens to be graded by some drill today, so `graded` and
        `graded | recoverable` are the same set and dropping the floor changes
        nothing. That is a coincidence of the current definitions, not the
        rule. A drill that stopped grading a shoulder would silently take its
        reference curve away from the video lane, which is the opposite of
        what this list is for.
        """
        one = MovementDefinition(
            movement_id="probe", sport="netball", skill="a skill",
            source="a source",
            phases=(Phase("ready", 0.0, (Checkpoint(
                measure="somethingNobodyRecovers", minimum_degrees=10.0,
                maximum_degrees=100.0, cue="a cue", why="a reason"),)),),
        )
        found = set(wanted([one]))
        self.assertEqual(
            found, set(RECOVERABLE) | {"somethingNobodyRecovers"},
            "the recoverable floor is not held when nothing grades it",
        )

    def test_every_measure_the_exporter_would_write_has_a_unit(self) -> None:
        self.assertTrue(RECOVERABLE, "RECOVERABLE is empty")
        would_write = set(wanted(definitions()))
        self.assertGreaterEqual(
            len(would_write), len(RECOVERABLE) + 1,
            "the derived set is no wider than its floor, so either the "
            "definitions were not read or nothing is graded beyond it",
        )
        for measure in sorted(would_write):
            with self.subTest(measure=measure):
                self.assertIn(
                    measure, MEASURE_UNITS,
                    f"the exporter would write {measure} and no unit is "
                    "declared for it, so the export raises rather than writes",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
