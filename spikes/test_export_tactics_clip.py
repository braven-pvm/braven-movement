"""The conventions in the Tactics clip export, which can silently invert.

Every number this file checks is a sign or an axis. Get one backwards and the
clip still loads, still plays and still measures well, and the athlete catches
the ball behind her back. That is the whole reason these are tested rather than
inspected: the failure is invisible in every viewer.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from movement_definition import load as load_definition  # noqa: E402
from movement_engine import definition_path  # noqa: E402

from export_tactics_clip import (  # noqa: E402
    CLASSES,
    across,
    athlete_frame,
    out_of,
    rest_median,
    shortest,
    swing_of,
    unwrap,
)

UP = np.array([0.0, 1.0, 0.0])
FORWARD = np.array([0.0, 0.0, 1.0])
LATERAL = np.cross(UP, FORWARD)


class SwingTest(unittest.TestCase):
    def test_a_limb_hanging_straight_down_is_zero(self):
        self.assertAlmostEqual(swing_of([0, 100, 0], [0, 60, 0], FORWARD, UP), 0.0)

    def test_forward_is_positive(self):
        angle = swing_of([0, 100, 0], [0, 60, 40], FORWARD, UP)
        self.assertGreater(angle, 0.0)
        self.assertAlmostEqual(math.degrees(angle), 45.0, places=6)

    def test_backward_is_negative(self):
        self.assertLess(swing_of([0, 100, 0], [0, 60, -40], FORWARD, UP), 0.0)

    def test_straight_up_is_a_half_turn(self):
        self.assertAlmostEqual(
            abs(swing_of([0, 100, 0], [0, 140, 0], FORWARD, UP)), math.pi
        )


class OutTest(unittest.TestCase):
    """Positive is outward on both sides, which is what makes one number mean
    one thing. The side is supplied by the caller, never read off a name."""

    def test_a_limb_in_the_plane_of_the_run_is_zero(self):
        self.assertAlmostEqual(out_of([0, 100, 0], [0, 60, 20], LATERAL, 1), 0.0)

    def test_both_sides_read_positive_when_the_limb_goes_outward(self):
        # The lateral axis is up crossed with forward, which points at +X.
        left = out_of([20, 100, 0], [45, 70, 0], LATERAL, 1)
        right = out_of([-20, 100, 0], [-45, 70, 0], LATERAL, -1)
        self.assertGreater(left, 0.0)
        self.assertGreater(right, 0.0)
        self.assertAlmostEqual(left, right, places=9)

    def test_crossing_the_midline_reads_negative(self):
        self.assertLess(out_of([20, 100, 0], [5, 70, 0], LATERAL, 1), 0.0)


class TwistTest(unittest.TestCase):
    def test_square_shoulders_over_square_hips_is_no_twist(self):
        shoulders = across([20, 130, 0], [-20, 130, 0], FORWARD, LATERAL, UP)
        hips = across([10, 80, 0], [-10, 80, 0], FORWARD, LATERAL, UP)
        self.assertAlmostEqual(shortest(shoulders - hips), 0.0)

    def test_a_turned_girdle_reads_as_twist(self):
        turned = across([14, 130, 14], [-14, 130, -14], FORWARD, LATERAL, UP)
        hips = across([10, 80, 0], [-10, 80, 0], FORWARD, LATERAL, UP)
        self.assertAlmostEqual(abs(math.degrees(shortest(turned - hips))), 45.0, places=4)


class UnwrapTest(unittest.TestCase):
    """An arm swung past vertical steps by a whole turn, and the player reads
    that as a windmill in one frame."""

    def test_a_seam_crossing_keeps_counting(self):
        frames = [
            {"arm": {"left": {"upper": u}, "right": {"upper": 0.0}},
             "leg": {"left": {"upper": 0.0}, "right": {"upper": 0.0}}}
            for u in (math.radians(170), math.radians(-175))
        ]
        unwrap(frames)
        step = frames[1]["arm"]["left"]["upper"] - frames[0]["arm"]["left"]["upper"]
        self.assertAlmostEqual(math.degrees(step), 15.0, places=6)

    def test_an_ordinary_series_is_untouched(self):
        frames = [
            {"arm": {"left": {"upper": u}, "right": {"upper": 0.0}},
             "leg": {"left": {"upper": 0.0}, "right": {"upper": 0.0}}}
            for u in (0.1, 0.2, 0.3)
        ]
        unwrap(frames)
        self.assertAlmostEqual(frames[2]["arm"]["left"]["upper"], 0.3, places=9)


class RestMedianTest(unittest.TestCase):
    def test_the_middle_value_wins(self):
        self.assertEqual(rest_median([0.3, 0.1, 0.2]), 0.2)

    def test_an_empty_series_is_zero(self):
        self.assertEqual(rest_median([]), 0.0)


class AthleteFrameTest(unittest.TestCase):
    """MHR puts the athlete's left at positive X. Getting that backwards
    crosses the arms and twists the trunk, and it has happened twice."""

    def _points(self, left_x: float):
        points = np.zeros((5, 3))
        index = {"l_uparm": 0, "r_uparm": 1, "root": 2, "l_foot": 3}
        points[0] = [left_x, 132.0, 2.7]
        points[1] = [-left_x, 132.0, 2.7]
        points[2] = [0.0, 83.0, 0.0]
        points[3] = [18.0, 7.4, -6.0]
        return points, index

    def test_the_axes_are_right_handed_and_the_lateral_is_left(self):
        points, index = self._points(19.7)
        up, forward, lateral = athlete_frame(points, index)
        np.testing.assert_allclose(up, [0, 1, 0])
        np.testing.assert_allclose(forward, [0, 0, 1])
        np.testing.assert_allclose(lateral, [1, 0, 0], atol=1e-12)

    def test_a_mirrored_athlete_is_refused(self):
        points, index = self._points(-19.7)
        with self.assertRaises(ValueError) as caught:
            athlete_frame(points, index)
        self.assertIn("positive X", str(caught.exception))

    def test_an_upside_down_athlete_is_refused(self):
        points, index = self._points(19.7)
        points[2] = [0.0, 1.0, 0.0]
        with self.assertRaises(ValueError) as caught:
            athlete_frame(points, index)
        self.assertIn("Y up", str(caught.exception))


class ClassTest(unittest.TestCase):
    """Every class name must be one Tactics already has an event for, or no
    board can ever select the clip."""

    # From src/contract/vocabulary.ts in braven-tactics: ACTOR_EVENT_TYPES and
    # RELEASE_KINDS. Copied rather than imported, because the two repositories
    # do not share a build. The clip contract records this as a drift risk.
    TACTICS_VOCABULARY = {
        "catch", "shoot", "jump", "land", "pivot", "screen", "tackle", "ruck",
        "block", "feint", "signal", "note",
        "pass", "chest-pass", "bounce-pass", "lob", "shoulder-pass", "offload",
        "kick", "punt", "grubber", "chip", "drop-kick", "shot", "torpedo",
        "throw-in", "roll", "drop", "tap",
    }

    def test_every_movement_class_is_in_the_tactics_vocabulary(self):
        for movement_id, (movement_class, _, _) in CLASSES.items():
            self.assertIn(
                movement_class,
                self.TACTICS_VOCABULARY,
                f"{movement_id} is classed as {movement_class!r}, which no "
                "Tactics event names",
            )

    def test_every_technique_name_is_a_usable_key(self):
        for movement_id, (_, technique, _) in CLASSES.items():
            self.assertRegex(technique, r"^[a-z][a-z0-9-]*$", movement_id)
            # `idlesIn` in engine/clips.ts collects every clip whose key starts
            # with "idle", so a technique named that would be dealt out as a
            # standing pose to a random player.
            self.assertFalse(technique.startswith("idle"), movement_id)

    def test_every_movement_names_the_moment_it_is_about(self):
        """A clip is lined up on one instant, so that instant must be a phase
        the coaching definition actually names."""
        for movement_id, (_, _, moment) in CLASSES.items():
            definition = load_definition(definition_path(movement_id))
            self.assertIn(
                moment,
                [phase.name for phase in definition.phases],
                f"{movement_id} has no phase named {moment!r}",
            )


if __name__ == "__main__":
    unittest.main()
