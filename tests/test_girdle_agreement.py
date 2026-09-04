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
    """The transmitted offset is in TORSO lengths, and lands on this body."""

    PELVIS = (0.0, -0.0202, 0.914878)
    ENGINE_REST_TORSO = 0.496456

    def test_a_transmitted_offset_lands_on_this_body(self):
        """The worked example from the ruling: 48.8867 on him is 42.114 here.

        His neutral girdle sits 1.53 percent compressed from his own rest, and
        reproducing that compression on this body is the entire point.
        """
        from girdle_agreement import REST_TORSO_M, resolve

        engine_neutral = 0.488867
        offset = (0.0, 0.0, engine_neutral / self.ENGINE_REST_TORSO)

        landed = resolve(offset, (0.0, 0.0, 0.0), REST_TORSO_M)

        # 11 microns from the ruling's quoted 42.114 cm. That residue is the
        # rounding of the QUOTED inputs, which carry six significant figures,
        # and it is LARGER than this guard's 1e-5 m tolerance. So the guard
        # must run against the transmitted values themselves and never against
        # numbers re-derived from a quoted table.
        self.assertLess(abs(landed[2] - 0.42114), 2e-5)

    def test_an_ARM_divisor_gives_a_different_answer(self):
        """Arm lengths were proposed by this lane and refuted by measurement.

        The test keeps the refutation, because the wrong divisor is a silent
        error: it returns a number, and the number is wrong by centimetres.
        """
        from girdle_agreement import REST_TORSO_M, resolve

        offset = (0.0, 0.0, 0.488867 / self.ENGINE_REST_TORSO)

        by_torso = resolve(offset, (0.0, 0.0, 0.0), REST_TORSO_M)
        by_arm = resolve(offset, (0.0, 0.0, 0.0), 0.48547)

        self.assertGreater(abs(by_arm[2] - by_torso[2]), 0.02)

    def test_resolving_then_comparing_reads_agreement(self):
        """The round trip the acceptance test runs, and it must reach zero."""
        from girdle_agreement import REST_TORSO_M, agreement, resolve

        offset = (0.01, -0.02, 0.98)
        landed = resolve(offset, self.PELVIS, REST_TORSO_M)

        self.assertEqual(AGREES, agreement(landed, landed)["verdict"])

    def test_the_divisor_is_the_MAGNITUDE_and_not_the_vertical(self):
        """42.7689 is the span. 42.7681 is its vertical component.

        This lane published the component first. They agree to 8 microns on
        this rig only because its rest torso is almost purely vertical.
        """
        from girdle_agreement import REST_TORSO_M

        self.assertAlmostEqual(0.427689, REST_TORSO_M, places=6)
        self.assertNotAlmostEqual(0.427681, REST_TORSO_M, places=6)
