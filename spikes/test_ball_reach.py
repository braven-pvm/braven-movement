"""Tests for the reach test itself.

The reach test is the thing that can say "she could not have caught that". If it
is wrong in the generous direction, the engine will keep claiming catches that
never happened, which is the failure this whole change exists to prevent.
"""

from __future__ import annotations

import math
import unittest

import numpy as np

from ball_reach import (
    ReachEnvelope,
    hand_reach,
    reach_envelope,
    verdict,
)

# The reference athlete, measured from the rest pose.
UPPER_CM = 25.68
FORE_CM = 27.00
PALM_CM = 8.21


class EnvelopeTest(unittest.TestCase):
    def setUp(self):
        self.envelope = reach_envelope(UPPER_CM, FORE_CM, PALM_CM)

    def test_full_stretch_is_the_arm_plus_half_a_palm(self):
        self.assertAlmostEqual(
            self.envelope.far_cm, UPPER_CM + FORE_CM + PALM_CM / 2.0, places=6
        )

    def test_the_folded_arm_sets_the_near_edge(self):
        folded = math.sqrt(
            UPPER_CM**2 + FORE_CM**2 - 2 * UPPER_CM * FORE_CM * math.cos(math.radians(30))
        )
        self.assertAlmostEqual(
            self.envelope.near_cm, folded - PALM_CM / 2.0, places=6
        )

    def test_the_near_edge_is_well_inside_the_far_edge(self):
        self.assertLess(self.envelope.near_cm, self.envelope.far_cm / 2.0)

    def test_a_straighter_elbow_limit_pushes_the_near_edge_out(self):
        stiff = reach_envelope(UPPER_CM, FORE_CM, PALM_CM, elbow_flexion_limit_degrees=90.0)
        self.assertGreater(stiff.near_cm, self.envelope.near_cm)


class HoldsTest(unittest.TestCase):
    def setUp(self):
        self.envelope = ReachEnvelope(near_cm=10.0, far_cm=50.0)

    def test_a_surface_inside_the_reach_is_reachable(self):
        self.assertTrue(self.envelope.holds(30.0, diameter_cm=22.0))

    def test_a_surface_beyond_the_reach_is_not(self):
        self.assertFalse(self.envelope.holds(50.1, diameter_cm=22.0))

    def test_the_boundary_counts_as_reachable(self):
        self.assertTrue(self.envelope.holds(50.0, diameter_cm=22.0))

    def test_a_ball_against_the_chest_is_still_reachable(self):
        """The far side of a close ball is still out where a hand can get to it."""
        self.assertTrue(self.envelope.holds(0.0, diameter_cm=22.0))

    def test_a_point_target_inside_the_fold_is_not_reachable(self):
        self.assertFalse(self.envelope.holds(2.0, diameter_cm=0.0))


class HandReachTest(unittest.TestCase):
    def setUp(self):
        self.envelope = ReachEnvelope(near_cm=10.0, far_cm=50.0)
        self.shoulder = np.array([0.0, 140.0, 0.0])

    def test_the_test_is_against_the_surface_not_the_centre(self):
        """A hand meets a ball at its skin. Ignoring the radius loses 11 cm."""
        ball = np.array([0.0, 140.0, 55.0])
        result = hand_reach("l", self.shoulder, ball, 11.0, self.envelope)
        self.assertAlmostEqual(result.centre_distance_cm, 55.0)
        self.assertAlmostEqual(result.surface_distance_cm, 44.0)
        self.assertTrue(result.reachable)

    def test_the_margin_is_negative_when_the_ball_is_too_far(self):
        ball = np.array([0.0, 140.0, 90.0])
        result = hand_reach("l", self.shoulder, ball, 11.0, self.envelope)
        self.assertFalse(result.reachable)
        self.assertAlmostEqual(result.margin_cm, 50.0 - 79.0)

    def test_the_margin_is_how_much_reach_is_left(self):
        ball = np.array([0.0, 140.0, 41.0])
        result = hand_reach("l", self.shoulder, ball, 11.0, self.envelope)
        self.assertAlmostEqual(result.margin_cm, 20.0)


class VerdictTest(unittest.TestCase):
    def hand(self, side, reachable):
        return hand_reach(
            side,
            np.zeros(3),
            np.array([0.0, 0.0, 20.0 if reachable else 200.0]),
            11.0,
            ReachEnvelope(near_cm=0.0, far_cm=50.0),
        )

    def test_both(self):
        hands = {"l": self.hand("l", True), "r": self.hand("r", True)}
        self.assertEqual(verdict(hands), "both")

    def test_neither(self):
        hands = {"l": self.hand("l", False), "r": self.hand("r", False)}
        self.assertEqual(verdict(hands), "neither")

    def test_one_side_only(self):
        hands = {"l": self.hand("l", True), "r": self.hand("r", False)}
        self.assertEqual(verdict(hands), "left only")
        hands = {"l": self.hand("l", False), "r": self.hand("r", True)}
        self.assertEqual(verdict(hands), "right only")


class ArmSpanTest(unittest.TestCase):
    """The envelope has to agree with the athlete it came from."""

    def test_full_stretch_is_close_to_the_authored_arm_length(self):
        """A hand key of 1.0 ahead means a straight arm, so the two must agree."""
        envelope = reach_envelope(UPPER_CM, FORE_CM, PALM_CM)
        arm_length = UPPER_CM + FORE_CM
        self.assertLess(abs(envelope.far_cm - arm_length), 0.1 * arm_length)


if __name__ == "__main__":
    unittest.main()
