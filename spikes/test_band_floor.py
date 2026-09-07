"""The band floor is per unit, and the length floor is derived, not scaled.

Three defects sat under one sentence in `movement_definition`: a coach was told
"degrees" about a distance in centimetres, a 5-degree threshold was spent on a
centimetre band, and the widest-moving checkpoint of a phase was chosen by
comparing centimetres with degrees.

Every guard here is written to FAIL under the code that shipped before it, and
each was run against that code to check that it does.
"""

from __future__ import annotations

import random
import unittest

from movement_definition import (
    CENTIMETRES,
    DEGREES,
    MINIMUM_MEANINGFUL_BAND,
    MINIMUM_MEANINGFUL_BAND_CENTIMETRES,
    MINIMUM_MEANINGFUL_BAND_DEGREES,
    Checkpoint,
    MovementDefinition,
    MovementDefinitionError,
    Phase,
    minimum_meaningful_band,
)

# The noise study's own parameters, restated so this file can re-run its
# propagation without OpenSim. `opensim_crosscheck.run_noise_study` needs a
# model to turn landmark noise into ANGLE error; turning the same noise into
# LENGTH error needs no model at all, because a length IS a landmark
# coordinate. Restated rather than imported for that reason: importing would
# pull in OpenSim to reach three numbers.
LANDMARK_NOISE_MM = 5.0
SAMPLES = 400
SEED = 20260817

# Every length this engine writes is a difference of TWO landmark coordinates.
# A height is `joint - ground`; the foot gap is `|(L - g) - (R - g)| = |L - R|`,
# where the ground cancels and two joints remain. So two independent
# perturbations enter every one of them.
LANDMARKS_IN_A_LENGTH = 2


def length_error_mm() -> tuple[float, float]:
    """The mean and the 95th percentile of a length's error, in millimetres.

    Same sigma, same sample count, same seed and the same two statistics as
    the angle rows in README.md, so the two sides are read the same way.

    BOTH ARE RETURNED BECAUSE BOTH ARE SPENT. An earlier version computed the
    percentile only, while the comment beside the constant and the ledger both
    quoted a mean of 6.00 mm and used it in the second reading of the imported
    margin. That reading was therefore not re-measurable from this repository,
    which is the "commit the instrument with its numbers" rule broken in the
    one place the pack was about.
    """
    generator = random.Random(SEED)
    errors = [
        abs(
            sum(
                generator.gauss(0.0, LANDMARK_NOISE_MM)
                for _ in range(LANDMARKS_IN_A_LENGTH)
            )
        )
        for _ in range(SAMPLES)
    ]
    mean = sum(errors) / len(errors)
    return mean, sorted(errors)[int(0.95 * len(errors))]


def length_error_95th_mm() -> float:
    """The percentile alone, for the guards that only want it."""
    return length_error_mm()[1]


class TheLengthFloorIsDerivedFromTheNoiseStudy(unittest.TestCase):
    def test_the_propagation_produces_a_real_number(self) -> None:
        """Guards the guard. A propagation returning zero passes anything."""
        measured = length_error_95th_mm()
        self.assertGreater(measured, LANDMARK_NOISE_MM)
        self.assertLess(measured, 10.0 * LANDMARK_NOISE_MM)

    def test_both_statistics_are_the_ones_the_derivation_quotes(self) -> None:
        """The mean is SPENT, so it must be re-measurable here.

        3.268 x 6.00 mm = 19.61 mm is one of the two readings that set the
        floor. A comment quoting a number no committed instrument produces is
        a figure nobody can check.
        """
        mean, percentile = length_error_mm()
        self.assertAlmostEqual(mean, 6.00, delta=0.1)
        self.assertAlmostEqual(percentile, 14.53, delta=0.1)

    def test_the_floor_is_at_or_above_the_measured_percentile(self) -> None:
        """The constant cannot drift from the evidence that set it."""
        measured_cm = length_error_95th_mm() / 10.0
        self.assertGreaterEqual(
            MINIMUM_MEANINGFUL_BAND_CENTIMETRES, measured_cm,
            f"the floor {MINIMUM_MEANINGFUL_BAND_CENTIMETRES} cm sits BELOW "
            f"the {measured_cm:.3f} cm the noise study propagates, so a band "
            "at the floor would report noise as coaching",
        )

    def test_the_floor_carries_the_margin_the_degrees_floor_carries(self):
        """And no more, because the extra would be an unstated judgment.

        The degrees floor sits 1.285 times its own 95th percentile. The
        length floor imports that margin deliberately, which the comment
        beside the constant says outright.

        THIS ADMITS AN INTERVAL AND NOT A VALUE, and the interval is worth
        stating rather than implying: [1.453, 2.018) cm. It does not pin the
        floor to 2.0 and it is not meant to; it bounds it below by the
        propagated percentile and above by the imported margin plus the
        rounding that reaches a round number. An earlier slack of 0.5 cm
        admitted 2.3, which no rounding explains — 1.868 rounds up to 2.0, a
        step of 0.132, so the slack is 0.15.
        """
        measured_cm = length_error_95th_mm() / 10.0
        imported = (MINIMUM_MEANINGFUL_BAND_DEGREES / 3.89) * measured_cm
        rounding = 0.15
        self.assertGreaterEqual(MINIMUM_MEANINGFUL_BAND_CENTIMETRES, measured_cm)
        self.assertLess(
            MINIMUM_MEANINGFUL_BAND_CENTIMETRES, imported + rounding,
            f"the floor sits further above the {imported:.3f} cm margin the "
            f"degrees floor carries than the {rounding} cm rounding explains, "
            "so it holds a coaching judgment nobody has stated",
        )

    def test_it_is_none_of_the_three_wrong_numbers(self) -> None:
        """All three were actually written down, so all three are ruled out.

        Each spends a ratio from an OUTPUT on an INPUT: 5 mm is the landmark
        noise that ENTERS the study; 1.53 and 3.89 are what leaves it. The
        first route was written into a draft of this branch. The second was
        ruled by the orchestrator and withdrawn by it the same hour, once this
        lane showed where the ratio came from. Asserting the shipped constant
        is neither number stops a later reader re-deriving the floor the wrong
        way and landing on something that looks right.
        """
        # THREE NUMBERS, NOT TWO, and they are 0.016 cm apart at the
        # closest. `assertNotAlmostEqual(places=1)` cannot separate them: it
        # rejects anything within 0.05, so a floor of 1.634 failed the 1.65
        # subTest as well and the per-route labels said nothing. The tolerance
        # is 0.01 cm, which is under the smallest gap between the three and so
        # names the route actually taken.
        for label, wrong in (
            ("3.268 x 5.00 mm, the ratio spent on the input noise",
             0.5 * (MINIMUM_MEANINGFUL_BAND_DEGREES / 1.53)),
            ("3.3 x 5.00 mm, the same ratio rounded first", 0.5 * 3.3),
            ("1.6 cm, that product as it was written down", 1.6),
        ):
            with self.subTest(route=label):
                self.assertGreater(
                    abs(MINIMUM_MEANINGFUL_BAND_CENTIMETRES - wrong), 0.01,
                    f"the floor is {label} = {wrong:.4f} cm",
                )


class TheFloorIsChosenByUnit(unittest.TestCase):
    def test_each_unit_gets_its_own_floor(self) -> None:
        self.assertEqual(
            minimum_meaningful_band("leftElbowFlexionDegrees"),
            (MINIMUM_MEANINGFUL_BAND_DEGREES, DEGREES),
        )
        self.assertEqual(
            minimum_meaningful_band("footHeightGapCm"),
            (MINIMUM_MEANINGFUL_BAND_CENTIMETRES, CENTIMETRES),
        )

    def test_an_undeclared_measure_gets_the_strictest_floor_and_no_unit(self):
        """It must not get degrees, and it must not get the loosest floor."""
        floor, unit = minimum_meaningful_band("somethingNobodyDeclared")
        self.assertIsNone(unit)
        self.assertEqual(floor, max(MINIMUM_MEANINGFUL_BAND.values()))

    def test_a_centimetre_band_narrower_than_the_length_floor_is_refused(self):
        with self.assertRaises(MovementDefinitionError):
            Checkpoint(
                measure="footHeightGapCm",
                minimum_degrees=0.0,
                maximum_degrees=MINIMUM_MEANINGFUL_BAND_CENTIMETRES - 0.5,
                cue="a cue",
                why="a reason",
            )

    def test_a_centimetre_band_the_old_degrees_floor_refused_is_accepted(self):
        """The fix, stated as the case that changed.

        A 3 cm band is twice the 1.45 cm the noise study propagates into a
        length, and it was rejected before because it was held to a threshold
        belonging to angles.
        """
        width = 3.0
        self.assertLess(width, MINIMUM_MEANINGFUL_BAND_DEGREES)
        self.assertGreater(width, MINIMUM_MEANINGFUL_BAND_CENTIMETRES)
        Checkpoint(
            measure="footHeightGapCm",
            minimum_degrees=0.0,
            maximum_degrees=width,
            cue="a cue",
            why="a reason",
        )

    def test_an_angle_band_is_still_held_to_five_degrees(self) -> None:
        """The fix must not loosen the rule it was not about."""
        with self.assertRaises(MovementDefinitionError):
            Checkpoint(
                measure="leftElbowFlexionDegrees",
                minimum_degrees=20.0,
                maximum_degrees=20.0 + MINIMUM_MEANINGFUL_BAND_DEGREES - 0.5,
                cue="a cue",
                why="a reason",
            )


class TheCoachIsToldTheRightUnit(unittest.TestCase):
    def failing(self, measure: str, top: float) -> str:
        return Checkpoint(
            measure=measure,
            minimum_degrees=0.0,
            maximum_degrees=top,
            cue="A cue.",
            why="A reason.",
        ).assess(top + 3.0).feedback()

    def test_a_length_is_reported_in_centimetres(self) -> None:
        """The defect, in the sentence a coach reads.

        Before this, `netball_double_foot_landing` told a coach "Needs less:
        17 degrees against a target of 0 to 14" about a distance.
        """
        said = self.failing("footHeightGapCm", 14.0)
        self.assertIn("centimetres", said)
        self.assertNotIn("degrees", said)

    def test_an_angle_is_still_reported_in_degrees(self) -> None:
        said = self.failing("leftElbowFlexionDegrees", 60.0)
        self.assertIn("degrees", said)
        self.assertNotIn("centimetres", said)

    def test_an_undeclared_measure_is_given_no_unit_at_all(self) -> None:
        """No unit beats a wrong unit."""
        said = self.failing("somethingNobodyDeclared", 60.0)
        self.assertNotIn("degrees", said)
        self.assertNotIn("centimetres", said)
        self.assertIn("against a target of", said)


class ThePhaseWinnerIsChosenWithoutMixingUnits(unittest.TestCase):
    """`separation` maximised raw values across units.

    Inert in today's library, because the only phases grading both a length and
    an angle are the landing's, where the foot gap moves 0.00 to 0.01 cm. This
    builds the case the library does not have.
    """

    def movement(self) -> MovementDefinition:
        return MovementDefinition(
            movement_id="probe",
            sport="netball",
            skill="a skill",
            source="a source",
            phases=(
                Phase("first", 0.0, (
                    Checkpoint("footHeightGapCm", 0.0, 20.0, "c", "w"),
                )),
                Phase("second", 1.0, (
                    Checkpoint("footHeightGapCm", 0.0, 20.0, "c", "w"),
                    Checkpoint("leftElbowFlexionDegrees", 0.0, 90.0, "c", "w"),
                )),
            ),
        )

    def test_the_larger_number_does_not_win_when_it_is_a_different_unit(self):
        """The length moves 4 cm, which is 2.0 floors. The angle moves 6
        degrees, which is 1.2 floors. The raw maximum picks the angle."""
        first = {"footHeightGapCm": 0.0, "leftElbowFlexionDegrees": 0.0}
        second = {"footHeightGapCm": 4.0, "leftElbowFlexionDegrees": 6.0}
        report = self.movement().separation([first, second])
        winner = report[1]
        self.assertGreater(6.0, 4.0, "the angle must be the larger raw number")
        self.assertEqual(
            winner.measure, "footHeightGapCm",
            "the winner was picked by comparing centimetres with degrees",
        )
        self.assertEqual(winner.moved, 4.0)

    def test_a_length_is_distinguishable_at_its_own_floor(self) -> None:
        """3 cm cleared nothing before, because it was held to 5 degrees.

        It is twice the 1.45 cm the noise study propagates into a length.
        """
        first = {"footHeightGapCm": 0.0}
        second = {"footHeightGapCm": 3.0}
        report = self.movement().separation([first, second])
        self.assertTrue(report[1].distinguishable)

    def test_a_length_under_its_own_floor_is_still_refused(self) -> None:
        first = {"footHeightGapCm": 0.0}
        second = {"footHeightGapCm": MINIMUM_MEANINGFUL_BAND_CENTIMETRES - 0.5}
        report = self.movement().separation([first, second])
        self.assertFalse(report[1].distinguishable)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
