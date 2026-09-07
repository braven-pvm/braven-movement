"""Guards for the check that the renderer USED the transmitted shoulders.

The ball is placed from the shoulder midpoint. Before 2026-09-04 the job did
not carry one, so this rig supplied its own: one girdle pose for every graded
phase, against an engine girdle that travelled 8.45 cm inside the overhead pass
alone.

EVERY MUTATION BELOW WAS SEEN TO FAIL, with the guard that caught it. The pack
said "nine mutations" and enumerated none, so the count could not be checked.
These are the distinct ones, run with `python -B` because a same-length
constant rewrite inside one second reuses the previous mutation's bytecode.

  the tolerance                                     caught by
   1 a missing field reads as agreement             a_missing_field_is_UNAVAILABLE
   2 the tolerance is widened to 1 cm               the_SMALLEST_error
   3 only the magnitude is reported, not the axes   a_fore_and_aft_error_is_visible
   4 an unverifiable frame is let through           a_MISSING_field_stops_the_frame
   5 the midpoint becomes the left shoulder         the_midpoint_is_the_point

  the divisor
   6 the divisor becomes the vertical component     the_divisor_is_the_MAGNITUDE
   7 the divisor becomes an arm length              an_ARM_divisor_gives_a_different_answer
   8 the offset is added without scaling            a_transmitted_displacement_lands
   9 the displacement is ignored, rest returned     a_transmitted_displacement_lands
  10 the displacement is applied unscaled           an_ARM_divisor / the_real_defect

  the reach
  11 a bad aim is excused as anatomy                a_miss_BEYOND_the_anatomy
  12 the reachable miss loses its absolute value    a_target_INSIDE_the_sphere
  13 the reach tolerance is widened to a centimetre the_reach_tolerance_sits_far_under
  14 out of reach is reported as agreement          a_miss_that_matches_the_anatomy
  15 the bone length is ignored                     a_target_beyond_the_sphere

  the refusal
  16 a missing girdle is waved through              a_MISSING_girdle_STOPS_the_frame
  17 an unknown verdict fails OPEN                  an_unknown_verdict_is_refused
  18 a reach limit is refused, so nothing renders   a_reach_limit_is_ALLOWED_through
  19 a failed aim is waved through                  an_aim_that_FAILED_stops_the_frame

THESE ARE THE PURE-PYTHON RULES ONLY. The renderer's WIRING of them is guarded
in tests/test_blender_sources.py, because five mutations of the call path left
this file's suite entirely green.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from girdle_agreement import (  # noqa: E402
    AGREES,
    OUT_OF_REACH,
    classify,
    refuse_unrenderable_girdle,
    reachable_miss_mm,
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


class ReachTest(unittest.TestCase):
    """A bone that cannot stretch is not a defect in the aim.

    The engine's clavicle is 20.4 percent longer relative to its torso than
    this rig's. Of 102 transmitted shoulder targets 97 sit outside this rig's
    sphere and 5 sit inside it, and none lies on it, so all 102 are out of
    reach. Merging that with a bad aim under one word would either hide a real
    defect or report anatomy as one.
    """

    PIVOT = (0.0, 0.0, 0.0)
    BONE = 0.126298  # this rig's clavicle, metres

    def test_a_target_on_the_sphere_costs_nothing(self):
        self.assertAlmostEqual(
            0.0, reachable_miss_mm((self.BONE, 0.0, 0.0), self.PIVOT, self.BONE),
            places=9)

    def test_a_target_beyond_the_sphere_costs_the_difference(self):
        """25.5 mm is the real figure at `chest_pass/ready`."""
        target = (self.BONE + 0.0255, 0.0, 0.0)

        self.assertAlmostEqual(
            25.5, reachable_miss_mm(target, self.PIVOT, self.BONE), places=6)

    def test_a_target_INSIDE_the_sphere_also_costs_the_difference(self):
        """5 of the 102 targets are nearer than the clavicle is long.

        An absolute value, not a signed one: a bone cannot shorten either.
        """
        target = (self.BONE - 0.0255, 0.0, 0.0)

        self.assertAlmostEqual(
            25.5, reachable_miss_mm(target, self.PIVOT, self.BONE), places=6)

    def test_a_miss_that_matches_the_anatomy_is_OUT_OF_REACH(self):
        self.assertEqual(OUT_OF_REACH, classify(25.531, 25.531))

    def test_a_miss_BEYOND_the_anatomy_is_a_DEFECT_and_not_anatomy(self):
        """The guard that stops "out of reach" retiring a real defect.

        If the aim itself failed, the miss exceeds what the bone explains, and
        calling that anatomy would be a true-sounding excuse for a bug.
        """
        self.assertEqual(DISAGREES, classify(25.531, 1.0))

    def test_a_reached_target_still_AGREES(self):
        self.assertEqual(AGREES, classify(0.0, 0.0))
        self.assertEqual(AGREES, classify(0.005, 0.0))

    def test_the_reach_tolerance_sits_far_under_the_figures_rule(self):
        """Stated as a relationship so an edit to either end is caught.

        The measured excess over the reachable minimum was 0.0001 mm across all
        102 targets. The figures are judged at 10 mm.
        """
        from girdle_agreement import REACH_TOLERANCE_MM

        self.assertGreater(REACH_TOLERANCE_MM, 0.0001)
        self.assertLess(REACH_TOLERANCE_MM, 10.0 / 100.0)


class RefuseUnrenderableTest(unittest.TestCase):
    """A frame nobody can check must not reach a coach.

    Six of the fifteen findings in the 2026-09-07 review were this one gap,
    found independently by five lenses: a job with no girdle field rendered the
    PRE-FIX figure, with the whole 5 to 6 cm error back in the ball, and the
    run printed PASS and wrote a receipt like any other.
    """

    def test_a_reach_limit_is_ALLOWED_through(self):
        """All 102 targets are out of reach. Refusing them renders nothing.

        A bone that cannot stretch is a fact about the body, not a defect in
        the render, and it must not stop a figure.
        """
        refuse_unrenderable_girdle(
            {"verdict": OUT_OF_REACH, "worstOffsetMm": 52.091}, "chest/ready")

    def test_agreement_is_allowed_through(self):
        refuse_unrenderable_girdle({"verdict": AGREES}, "chest/ready")

    def test_a_MISSING_girdle_STOPS_the_frame(self):
        with self.assertRaises(ValueError) as caught:
            refuse_unrenderable_girdle(
                {"verdict": UNAVAILABLE, "worstOffsetMm": None}, "chest/ready")

        self.assertIn("chest/ready", str(caught.exception))
        self.assertIn("girdle at rest", str(caught.exception))

    def test_an_aim_that_FAILED_stops_the_frame(self):
        """Beyond what the bone explains is a defect, not anatomy."""
        with self.assertRaises(ValueError) as caught:
            refuse_unrenderable_girdle(
                {"verdict": DISAGREES, "worstOffsetMm": 40.0,
                 "worstBeyondReachableMm": 14.5}, "overhead/lift")

        self.assertIn("BEYOND", str(caught.exception))
        self.assertIn("14.5", str(caught.exception))

    def test_an_unknown_verdict_is_refused_and_not_waved_through(self):
        """A verdict this function does not recognise must fail closed.

        Failing open would let a later rename of a verdict silently disable
        every refusal here.
        """
        with self.assertRaises(ValueError):
            refuse_unrenderable_girdle({"verdict": "probably fine"}, "x/y")
