"""What the coaching layer actually grades, asked of the definition itself.

Several things downstream pick their own list of measures, and none was ever
reconciled with what the checkpoints read. `export_reference_curves.WANTED` is
five angles chosen for what a two-camera lift can plausibly recover, and
`leftKneeFlexionDegrees` — graded by every drill in the library — is not one of
them. A consumer wanting "the measures that matter" has had to hand-write a
list and let it drift.

`graded_measures()` is the definition's own answer, so a consumer can ask
rather than guess. These cases pin what it means and, at the end, what the
library currently says, because that number is the reason the video lane asked
for it.

No solver. `movement_definition` is stdlib-only and this reads definitions off
disk.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from movement_definition import Checkpoint, MovementDefinition, Phase, load

SPIKE_DIR = Path(__file__).resolve().parent
MOVEMENTS = SPIKE_DIR / "movements"
# The other JSON beside a definition: a ball, a motion track, a technique, a
# proof run. A definition is the one with no second suffix.
NOT_DEFINITIONS = (".ball.json", ".motion.json", ".technique.json", ".proof.json")


def definitions() -> list[MovementDefinition]:
    return [
        load(path)
        for path in sorted(MOVEMENTS.glob("*.json"))
        if not any(path.name.endswith(one) for one in NOT_DEFINITIONS)
    ]


def checkpoint(measure: str) -> Checkpoint:
    return Checkpoint(
        measure=measure,
        minimum_degrees=10.0,
        maximum_degrees=100.0,
        cue="a cue",
        why="a reason",
    )


def movement(*phases: Phase) -> MovementDefinition:
    return MovementDefinition(
        movement_id="probe",
        sport="netball",
        skill="a skill",
        source="a source",
        phases=tuple(phases),
    )


class WhatOnePhaseGrades(unittest.TestCase):
    def test_it_is_the_measures_its_checkpoints_read(self) -> None:
        phase = Phase("ready", 0.0, (checkpoint("a"), checkpoint("b")))
        self.assertEqual(phase.graded_measures(), {"a", "b"})

    def test_a_measure_graded_twice_in_one_phase_appears_once(self) -> None:
        phase = Phase("ready", 0.0, (checkpoint("a"), checkpoint("a")))
        self.assertEqual(phase.graded_measures(), {"a"})


class WhatAMovementGrades(unittest.TestCase):
    def test_it_is_the_union_across_the_phases(self) -> None:
        found = movement(
            Phase("ready", 0.0, (checkpoint("a"), checkpoint("b"))),
            Phase("contact", 0.5, (checkpoint("c"),)),
        ).graded_measures()
        self.assertEqual(found, {"a", "b", "c"})

    def test_a_measure_graded_in_two_phases_appears_once(self) -> None:
        """It is a SET. A measure graded at ready and again at contact is one
        measure, and a consumer building a column per measure wants one
        column."""
        found = movement(
            Phase("ready", 0.0, (checkpoint("a"),)),
            Phase("contact", 0.5, (checkpoint("a"), checkpoint("b"))),
        ).graded_measures()
        self.assertEqual(found, {"a", "b"})

    def test_it_reads_every_phase_and_not_only_the_first(self) -> None:
        """The mistake this shape invites. A union that stopped early would
        pass both cases above if the extra measure were in phase one."""
        found = movement(
            Phase("ready", 0.0, (checkpoint("a"),)),
            Phase("middle", 0.4, (checkpoint("b"),)),
            Phase("last", 0.9, (checkpoint("c"),)),
        ).graded_measures()
        self.assertEqual(found, {"a", "b", "c"})


class AgainstTheRealLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.found = definitions()

    def test_the_library_was_actually_read(self) -> None:
        """Guards the guard. A glob that matched nothing would pass every
        case below by vacuum."""
        self.assertGreaterEqual(
            len(self.found), 8, f"only {len(self.found)} definitions were read"
        )

    def test_every_drill_grades_something(self) -> None:
        for definition in self.found:
            with self.subTest(movement=definition.movement_id):
                self.assertTrue(definition.graded_measures())

    def test_every_returned_measure_is_on_a_real_checkpoint(self) -> None:
        """The round trip. A set built from anything other than the
        checkpoints could still look plausible."""
        for definition in self.found:
            written = {
                one.measure
                for phase in definition.phases
                for one in phase.checkpoints
            }
            with self.subTest(movement=definition.movement_id):
                self.assertEqual(definition.graded_measures(), written)

    def test_some_drill_grades_a_measure_at_more_than_one_phase(self) -> None:
        """The anti-hollow clause for the union. If no drill graded a measure
        twice, the set and a plain concatenation would agree everywhere and
        nothing above would be testing the union at all."""
        repeated = False
        for definition in self.found:
            counted = [
                one.measure
                for phase in definition.phases
                for one in phase.checkpoints
            ]
            if len(counted) != len(set(counted)):
                repeated = True
                break
        self.assertTrue(
            repeated,
            "no drill grades any measure at two phases, so the union is doing "
            "no work and these cases prove less than they appear to",
        )

    def test_the_knee_is_graded_everywhere_and_this_is_why_it_was_asked_for(
        self,
    ) -> None:
        """The finding that prompted this method, kept as a case.

        `leftKneeFlexionDegrees` is graded by every drill in the library and
        has no reference curve, because `export_reference_curves.WANTED` was
        chosen for what a two-camera lift can recover and never reconciled
        with what the checkpoints read.

        If this ever stops being true the widening design in
        `docs/REFERENCE_CURVE_WIDENING.md` needs re-reading, not deleting.
        """
        grading = [
            definition.movement_id
            for definition in self.found
            if "leftKneeFlexionDegrees" in definition.graded_measures()
        ]
        self.assertEqual(
            len(grading), len(self.found),
            f"the left knee is graded by {len(grading)} of {len(self.found)} "
            "drills, not all of them",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
