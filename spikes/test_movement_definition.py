"""Contract tests for the sport layer."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from movement_definition import (  # noqa: E402
    MINIMUM_MEANINGFUL_BAND_DEGREES,
    Checkpoint,
    MovementDefinition,
    MovementDefinitionError,
    Phase,
    definition_files,
    load,
)


def checkpoint(measure="leftElbowFlexionDegrees", minimum=20.0, maximum=60.0):
    return Checkpoint(
        measure=measure,
        minimum_degrees=minimum,
        maximum_degrees=maximum,
        cue="Soft elbows.",
        why="A locked arm cannot absorb the ball.",
    )


class CheckpointTest(unittest.TestCase):
    def test_a_band_narrower_than_the_measurement_threshold_is_rejected(self):
        """The rule that stops the tool reporting noise as coaching."""
        with self.assertRaises(MovementDefinitionError) as caught:
            checkpoint(minimum=40.0, maximum=43.0)

        self.assertIn("noise as coaching", str(caught.exception))

    def test_an_inverted_band_is_rejected(self):
        with self.assertRaises(MovementDefinitionError):
            checkpoint(minimum=60.0, maximum=20.0)

    def test_a_missing_cue_is_rejected(self):
        with self.assertRaises(MovementDefinitionError):
            Checkpoint(
                measure="leftElbowFlexionDegrees",
                minimum_degrees=20.0,
                maximum_degrees=60.0,
                cue="   ",
                why="reason",
            )

    def test_a_value_inside_the_band_is_correct(self):
        result = checkpoint().assess(35.0)

        self.assertTrue(result.correct)
        self.assertEqual(result.verdict, "within")
        self.assertTrue(result.feedback().endswith("Good."))

    def test_a_value_below_the_band_asks_for_more(self):
        result = checkpoint().assess(10.0)

        self.assertFalse(result.correct)
        self.assertEqual(result.verdict, "below")
        self.assertIn("Needs more", result.feedback())
        self.assertIn("off by 10", result.feedback())

    def test_a_value_above_the_band_asks_for_less(self):
        result = checkpoint().assess(75.0)

        self.assertEqual(result.verdict, "above")
        self.assertIn("Needs less", result.feedback())


class MovementTest(unittest.TestCase):
    def definition(self):
        return MovementDefinition(
            movement_id="test_catch",
            sport="netball",
            skill="Two-hand catch",
            source="test",
            phases=(
                Phase(name="ready", at_phase=0.0, checkpoints=(checkpoint(),)),
                Phase(name="contact", at_phase=1.0, checkpoints=(checkpoint(),)),
            ),
        )

    def test_phases_must_be_ordered(self):
        with self.assertRaises(MovementDefinitionError):
            MovementDefinition(
                movement_id="x",
                sport="netball",
                skill="y",
                source="test",
                phases=(
                    Phase(name="late", at_phase=0.9, checkpoints=(checkpoint(),)),
                    Phase(name="early", at_phase=0.1, checkpoints=(checkpoint(),)),
                ),
            )

    def test_each_phase_reads_the_frame_closest_to_its_anchor(self):
        frames = [
            {"leftElbowFlexionDegrees": 35.0},
            {"leftElbowFlexionDegrees": 999.0},
            {"leftElbowFlexionDegrees": 45.0},
        ]

        assessment = self.definition().assess(frames)

        self.assertEqual(assessment.results["ready"][0].measured, 35.0)
        self.assertEqual(assessment.results["contact"][0].measured, 45.0)
        self.assertTrue(assessment.correct)

    def test_a_missing_measurement_is_reported_clearly(self):
        with self.assertRaises(MovementDefinitionError) as caught:
            self.definition().assess([{"somethingElse": 1.0}])

        self.assertIn("leftElbowFlexionDegrees", str(caught.exception))

    def test_coaching_notes_name_the_phase(self):
        frames = [{"leftElbowFlexionDegrees": 5.0}, {"leftElbowFlexionDegrees": 35.0}]

        notes = self.definition().assess(frames).coaching_notes()

        self.assertTrue(any(note.startswith("[ready]") for note in notes))
        self.assertTrue(any("Needs more" in note for note in notes))


# The manual's OWN COVER, which is what every definition cites, followed by its
# section and page. It is deliberately not the converted markdown's file name,
# "202526 updated coaches manual": a library that cites one source under two
# titles cannot be checked, and the second title arrives silently because the
# file name is what an author has in front of them.
MANUAL_TITLE = (
    "Netball Skills and Conditioning Manual, Level 1, 3rd version, "
    "Niel du Plessis and Erin Burger"
)


def cites_the_manual(source: str) -> bool:
    """Whether a definition's source names the manual by its cover."""
    return MANUAL_TITLE in source


class LibraryDefinitionTest(unittest.TestCase):
    """Every definition in the library must satisfy these, including new ones."""

    def definitions(self):
        folder = Path(__file__).resolve().parent / "movements"
        return definition_files(folder)

    def test_the_library_is_not_empty(self):
        self.assertGreaterEqual(len(self.definitions()), 1)

    def test_every_definition_loads(self):
        for path in self.definitions():
            definition = load(path)
            self.assertTrue(definition.skill, path.name)
            self.assertGreaterEqual(len(definition.phases), 2, path.name)

    def test_every_band_survives_the_noise_rule(self):
        """A band narrower than the measurement threshold reports noise."""
        for path in self.definitions():
            for phase in load(path).phases:
                for check in phase.checkpoints:
                    self.assertGreaterEqual(
                        check.maximum_degrees - check.minimum_degrees, 5.0,
                        f"{path.name} {phase.name} {check.measure}",
                    )

    def test_every_definition_declares_itself_provisional(self):
        """Nobody should mistake placeholder bands for coaching truth."""
        for path in self.definitions():
            self.assertIn("PROVISIONAL", load(path).source, path.name)

    def test_every_definition_cites_the_manual(self):
        for path in self.definitions():
            with self.subTest(definition=path.name):
                self.assertTrue(
                    cites_the_manual(load(path).source),
                    f"{path.name} does not cite the manual by its own cover. "
                    f"Every definition must contain {MANUAL_TITLE!r}, then its "
                    "section and page.",
                )

    def test_the_markdown_file_name_is_not_an_acceptable_title(self):
        """The mutation, and the reason this checks a title and not a word.

        It asserted only that the word "Manual" appeared, which the converted
        markdown's file name also contains, so a definition citing
        "202526 Netball Coaches Manual" passed while introducing a SECOND
        title into a library where the other eight all cite the cover. The
        first pass drill did exactly that and the guard was silent.

        The string below is the one that slipped through, kept verbatim.
        """
        slipped_through = (
            "202526 Netball Coaches Manual, Passing, pages 79 to 83, "
            "Niel du Plessis and Erin Burger."
        )
        self.assertIn("Manual", slipped_through, "the old check would pass this")
        self.assertFalse(
            cites_the_manual(slipped_through),
            "the file name is being accepted as the manual's title again",
        )
        self.assertTrue(
            cites_the_manual(
                "Netball Skills and Conditioning Manual, Level 1, 3rd version, "
                "Niel du Plessis and Erin Burger, Catching section, page 71."
            ),
            "the real citation form is being refused",
        )

    def test_every_checkpoint_has_a_cue_and_a_reason(self):
        for path in self.definitions():
            for phase in load(path).phases:
                for check in phase.checkpoints:
                    self.assertTrue(check.cue.strip(), f"{path.name} {check.measure}")
                    self.assertTrue(check.why.strip(), f"{path.name} {check.measure}")

    def test_the_netball_skills_are_all_netball(self):
        for path in self.definitions():
            self.assertEqual(load(path).sport, "netball", path.name)


class PhaseSeparationTest(unittest.TestCase):
    """A checkpoint that cannot fail is not a check.

    The same threshold that refuses a band narrower than the measurement
    resolution refuses a phase closer to its predecessor than that resolution.
    """

    @staticmethod
    def definition():
        return MovementDefinition(
            movement_id="drill",
            skill="Drill",
            sport="netball",
            source="test",
            phases=(
                Phase(name="ready", at_phase=0.0, checkpoints=(checkpoint(),)),
                Phase(name="react", at_phase=0.5, checkpoints=(checkpoint(),)),
                Phase(name="contact", at_phase=1.0, checkpoints=(checkpoint(),)),
            ),
        )

    @staticmethod
    def frames(values):
        return [{"leftElbowFlexionDegrees": value} for value in values]

    def test_a_phase_that_moved_is_distinguishable(self):
        report = self.definition().separation(
            self.frames([10.0, 40.0, 70.0])
        )
        self.assertTrue(all(item.distinguishable for item in report))
        self.assertAlmostEqual(report[1].moved, 30.0)

    def test_a_phase_identical_to_the_one_before_cannot_fail(self):
        report = self.definition().separation(
            self.frames([10.0, 10.0, 70.0])
        )
        self.assertTrue(report[0].distinguishable, "a first phase always counts")
        self.assertFalse(report[1].distinguishable)
        self.assertIn("CANNOT FAIL", report[1].why())

    def test_the_threshold_is_the_measurement_resolution(self):
        """Just under fails, just over passes. No separate constant."""
        under = MINIMUM_MEANINGFUL_BAND_DEGREES - 0.1
        over = MINIMUM_MEANINGFUL_BAND_DEGREES + 0.1
        self.assertFalse(
            self.definition()
            .separation(self.frames([10.0, 10.0 + under, 70.0]))[1]
            .distinguishable
        )
        self.assertTrue(
            self.definition()
            .separation(self.frames([10.0, 10.0 + over, 70.0]))[1]
            .distinguishable
        )

    def test_a_phase_whose_measure_is_missing_grades_nothing(self):
        """`Phase` already refuses zero checkpoints, so this is the real case.

        A checkpoint naming a measure the solver did not produce grades
        nothing, and must not be reported as distinguishable.
        """
        definition = MovementDefinition(
            movement_id="drill",
            skill="Drill",
            sport="netball",
            source="test",
            phases=(
                Phase(name="ready", at_phase=0.0, checkpoints=(checkpoint(),)),
                Phase(
                    name="absent",
                    at_phase=1.0,
                    checkpoints=(checkpoint(measure="neverMeasuredDegrees"),),
                ),
            ),
        )
        report = definition.separation(self.frames([10.0, 70.0]))
        self.assertFalse(report[1].distinguishable)
        self.assertIn("nothing is graded", report[1].why())

    def test_it_refuses_an_empty_measurement_list(self):
        with self.assertRaises(MovementDefinitionError):
            self.definition().separation([])


if __name__ == "__main__":
    unittest.main()
