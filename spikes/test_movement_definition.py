"""Contract tests for the sport layer."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from movement_definition import (  # noqa: E402
    Checkpoint,
    MovementDefinition,
    MovementDefinitionError,
    Phase,
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


class ShippedDefinitionTest(unittest.TestCase):
    def test_the_netball_catch_definition_loads_and_validates(self):
        path = Path(__file__).resolve().parent / "movements" / "netball_two_hand_catch.json"

        definition = load(path)

        self.assertEqual(definition.sport, "netball")
        self.assertEqual(
            [phase.name for phase in definition.phases],
            ["ready", "reach", "contact", "pull_in"],
        )
        # Every shipped band must survive the noise rule.
        for phase in definition.phases:
            for check in phase.checkpoints:
                self.assertGreaterEqual(
                    check.maximum_degrees - check.minimum_degrees, 5.0
                )

    def test_the_shipped_definition_declares_itself_provisional(self):
        """Nobody should mistake placeholder bands for coaching truth."""
        path = Path(__file__).resolve().parent / "movements" / "netball_two_hand_catch.json"

        definition = load(path)

        self.assertIn("PROVISIONAL", definition.source)


if __name__ == "__main__":
    unittest.main()
