"""Guards for the check that the renderer USED the transmitted shoulders.

The ball is placed from the shoulder midpoint. Before 2026-09-04 the job did
not carry one, so this rig supplied its own: one girdle pose for all 18 graded
phases of four drills, against an engine girdle that travelled 7.40 cm inside
the overhead pass alone. Three figures of 18 passed a 1 cm rule.

Every guard here was seen to FAIL with its rule reverted, in the same session
it was written.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from girdle_agreement import (  # noqa: E402
    AGREES,
    DISAGREES,
    ROUNDING_M,
    TOLERANCE_M,
    UNAVAILABLE,
    agreement,
    midpoint,
    refuse_unless_agreed,
)

REST = (0.0, 0.0, 1.427681)


class MidpointTest(unittest.TestCase):
    def test_the_midpoint_is_the_point_the_ball_is_placed_from(self):
        self.assertEqual(
            (0.0, 0.0, 1.4), midpoint((0.15, 0.0, 1.4), (-0.15, 0.0, 1.4)))

    def test_a_symmetric_narrowing_does_NOT_move_the_midpoint(self):
        """This is why a WIDTH could never have caught the fault.

        The engine's shoulder width moves 5.63 cm inside the overhead pass and
        its midpoint moves 7.40 cm vertically. A width instrument reads the
        first and is blind to the second, and only the second moves the ball.
        """
        wide = midpoint((0.20, 0.0, 1.4), (-0.20, 0.0, 1.4))
        narrow = midpoint((0.12, 0.0, 1.4), (-0.12, 0.0, 1.4))

        self.assertEqual(wide, narrow)


class AgreementTest(unittest.TestCase):
    def test_an_exact_match_agrees(self):
        self.assertEqual(AGREES, agreement(REST, REST)["verdict"])

    def test_the_real_defect_is_caught(self):
        """7.40 cm, the overhead pass's own girdle travel."""
        moved = (REST[0], REST[1], REST[2] + 0.0740)

        report = agreement(REST, moved)

        self.assertEqual(DISAGREES, report["verdict"])
        self.assertAlmostEqual(74.0, report["offsetMm"], places=3)

    def test_the_SMALLEST_error_anyone_cares_about_is_caught(self):
        """1 cm is the pack's rule. It must not sit inside the tolerance."""
        report = agreement(REST, (REST[0], REST[1], REST[2] + 0.01))

        self.assertEqual(DISAGREES, report["verdict"])

    def test_the_job_s_own_rounding_does_NOT_trip_it(self):
        """A guard that fails on six-decimal rounding gets switched off.

        Half a micron on each axis is what the job's own precision can produce
        with nothing wrong at all.
        """
        rounded = tuple(value + ROUNDING_M / 2.0 for value in REST)

        self.assertEqual(AGREES, agreement(REST, rounded)["verdict"])

    def test_a_missing_field_is_UNAVAILABLE_and_never_agreement(self):
        """The whole finding was a missing field behaving like a satisfied one.

        A frame nobody could check must not read the same as one that passed.
        """
        report = agreement(REST, None)

        self.assertEqual(UNAVAILABLE, report["verdict"])
        self.assertNotEqual(AGREES, report["verdict"])
        self.assertIsNone(report["offsetMm"])

    def test_a_fore_and_aft_error_is_visible_and_not_hidden_in_a_magnitude(self):
        """The engine's first column was VERTICAL ONLY.

        An error of the same size front-to-back would have been invisible in a
        single distance, so the axes are reported separately.
        """
        report = agreement(REST, (REST[0], REST[1] + 0.02, REST[2]))

        self.assertEqual(DISAGREES, report["verdict"])
        self.assertAlmostEqual(0.0, report["perAxisMm"][0], places=6)
        self.assertAlmostEqual(-20.0, report["perAxisMm"][1], places=3)
        self.assertAlmostEqual(0.0, report["perAxisMm"][2], places=6)


class RefusalTest(unittest.TestCase):
    def test_agreement_lets_the_frame_through(self):
        refuse_unless_agreed(agreement(REST, REST), "overhead_pass/lift")

    def test_a_disagreement_stops_the_frame_and_names_the_axes(self):
        report = agreement(REST, (REST[0], REST[1], REST[2] + 0.074))

        with self.assertRaises(ValueError) as caught:
            refuse_unless_agreed(report, "overhead_pass/lift")

        self.assertIn("overhead_pass/lift", str(caught.exception))
        self.assertIn("74.0", str(caught.exception))

    def test_a_MISSING_field_stops_the_frame_too(self):
        """Rendering an unverifiable frame is the fault, not a lesser one."""
        with self.assertRaises(ValueError) as caught:
            refuse_unless_agreed(agreement(REST, None), "chest_pass/drive")

        self.assertIn("no shoulder positions", str(caught.exception))


class ToleranceTest(unittest.TestCase):
    def test_the_tolerance_sits_between_the_rounding_and_the_real_error(self):
        """Stated as a relationship, so a later edit to either end is caught."""
        self.assertGreater(TOLERANCE_M, ROUNDING_M)
        self.assertLess(TOLERANCE_M, 0.01 / 100.0)


if __name__ == "__main__":
    unittest.main()


class ResolveTest(unittest.TestCase):
    """The transmitted field is a DISPLACEMENT from each body's rest pose."""

    # This rig's rest shoulder midpoint above the pelvis: across, up, ahead cm,
    # measured on 2026-09-04 and identical on all 43 phases of all 10 drills.
    REST = (0.0, 0.427681, -0.002648)
    ENGINE_REST_TORSO = 0.496456

    def test_a_transmitted_displacement_lands_on_this_body(self):
        """The engine's -0.76 cm compression from rest becomes -0.65 cm here.

        Scaled by this body's smaller torso, not copied across as a length.
        """
        from girdle_agreement import REST_TORSO_M, resolve

        transmitted = (0.0, -0.0076 / self.ENGINE_REST_TORSO, 0.0)

        landed = resolve(transmitted, self.REST, REST_TORSO_M)

        # Bounded, not asserted to six places: -0.76 cm is itself a rounded
        # quote of -0.7589, so the last micron here belongs to the quote and
        # not to the arithmetic.
        self.assertLess(abs((landed[1] - self.REST[1]) - -0.006548), 2e-6)
        self.assertLess(abs(landed[1] - 0.421133), 2e-6)

    def test_a_ZERO_displacement_leaves_this_body_at_its_own_rest(self):
        """THIS is what a position could not do.

        Resolving the engine's POSITIONS put `chest_pass/ready` 2.488 cm out at
        a phase where both bodies sit at their neutral girdle. A displacement
        of zero must leave this rig exactly where it is, whatever the engine's
        own posture and landmark conventions are.
        """
        from girdle_agreement import REST_TORSO_M, agreement, resolve

        landed = resolve((0.0, 0.0, 0.0), self.REST, REST_TORSO_M)

        self.assertEqual(self.REST, landed)
        self.assertEqual(AGREES, agreement(self.REST, landed)["verdict"])

    def test_an_ARM_divisor_gives_a_different_answer(self):
        """Arm lengths were proposed by this lane and refuted by measurement.

        The refutation is kept, because the wrong divisor is a silent error: it
        returns a plausible number that is wrong by centimetres.
        """
        from girdle_agreement import REST_TORSO_M, resolve

        transmitted = (0.0, -0.074 / self.ENGINE_REST_TORSO, 0.0)

        by_torso = resolve(transmitted, self.REST, REST_TORSO_M)
        by_arm = resolve(transmitted, self.REST, 0.48547)

        self.assertGreater(abs(by_arm[1] - by_torso[1]), 0.0009)

    def test_the_real_defect_is_still_caught_after_resolving(self):
        """A rig that never poses its girdle disagrees by the whole travel."""
        from girdle_agreement import REST_TORSO_M, agreement, resolve

        travel = -0.074 / self.ENGINE_REST_TORSO
        wanted = resolve((0.0, travel, 0.0), self.REST, REST_TORSO_M)

        report = agreement(self.REST, wanted)

        self.assertEqual(DISAGREES, report["verdict"])
        self.assertAlmostEqual(63.75, report["offsetMm"], places=1)

    def test_the_divisor_is_the_MAGNITUDE_and_not_the_vertical(self):
        """42.7689 is the span. 42.7681 is its vertical component.

        This lane published the component first. They agree to 8 microns on
        this rig only because its rest torso is almost purely vertical.
        """
        from girdle_agreement import REST_TORSO_M

        self.assertAlmostEqual(0.427689, REST_TORSO_M, places=6)
        self.assertNotAlmostEqual(0.427681, REST_TORSO_M, places=6)


if __name__ == "__main__":
    unittest.main()


class PelvisRelativeTest(unittest.TestCase):
    """Both sides of the subtraction are pelvis-relative, or the root leaks in."""

    REST_SPAN = (0.0, 0.427681, -0.002648)
    REST_PELVIS = (0.0, 0.914878, -0.0202)

    def test_the_posed_pelvis_is_added_and_not_the_rest_pelvis(self):
        """The solved root is 8.4 cm off its rest at every ready phase.

        Applying a displacement to an absolute rest position would carry that
        motion into the girdle, which is a pose no solve produced.
        """
        from girdle_agreement import REST_TORSO_M, shoulder_position

        posed = (0.0, 0.830878, -0.0202)  # the pelvis 8.4 cm below its rest

        placed = shoulder_position((0.0, 0.0, 0.0), self.REST_SPAN, posed,
                                   REST_TORSO_M)

        self.assertAlmostEqual(posed[1] + self.REST_SPAN[1], placed[1],
                               places=9)
        self.assertNotAlmostEqual(self.REST_PELVIS[1] + self.REST_SPAN[1],
                                  placed[1], places=3)

    def test_a_span_and_an_absolute_position_are_not_interchangeable(self):
        """Passing the absolute rest shoulder where a span belongs.

        It returns a number either way, which is what makes it dangerous.
        """
        from girdle_agreement import REST_TORSO_M, resolve

        absolute_rest = (0.0, 1.342558, -0.017551)
        step = (0.0, 0.1144, 0.0)

        as_span = resolve(step, self.REST_SPAN, REST_TORSO_M)
        as_absolute = resolve(step, absolute_rest, REST_TORSO_M)

        self.assertGreater(abs(as_absolute[1] - as_span[1]), 0.9)
