"""Tests for the ball trajectory.

The point of the possession model is that the ball does not follow the athlete,
so most of these tests are about what the ball ignores.
"""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ball_track import (
    BallOffset,
    BallTrackError,
    ball_path,
    load_ball,
    stance_frame,
)

SNATCH = "netball_two_hand_snatch_pull_in"

VALID = {
    "movementId": "test_movement",
    "radiusFraction": 0.21,
    "release": {"atPhase": 0.2},
    "arrival": {"atPhase": 0.6},
    "keys": [
        {"atPhase": 0.2, "name": "release", "across": 0.0, "up": 0.2, "ahead": 4.0},
        {"atPhase": 0.4, "name": "flight", "across": 0.1, "up": 0.5, "ahead": 2.4},
        {"atPhase": 0.6, "name": "arrival", "across": 0.2, "up": 0.4, "ahead": 0.8},
    ],
}


def write(data: dict) -> Path:
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".ball.json", delete=False, encoding="utf-8"
    )
    json.dump(data, handle)
    handle.close()
    return Path(handle.name)


def variant(**changes) -> dict:
    data = json.loads(json.dumps(VALID))
    data.update(changes)
    return data


class LoadTest(unittest.TestCase):
    def test_loads_a_valid_trajectory(self):
        track = load_ball(write(VALID))
        self.assertEqual(track.movement_id, "test_movement")
        self.assertAlmostEqual(track.release_phase, 0.2)
        self.assertAlmostEqual(track.arrival_phase, 0.6)
        self.assertEqual(len(track.keys), 3)

    def test_a_ball_already_in_the_air_needs_no_release(self):
        data = variant()
        del data["release"]
        data["keys"][0]["atPhase"] = 0.0
        track = load_ball(write(data))
        self.assertAlmostEqual(track.release_phase, 0.0)

    def test_rejects_a_single_key(self):
        data = variant()
        data["keys"] = data["keys"][:1]
        with self.assertRaises(BallTrackError):
            load_ball(write(data))

    def test_rejects_unordered_keys(self):
        data = variant()
        data["keys"] = [data["keys"][0], data["keys"][2], data["keys"][1]]
        with self.assertRaises(BallTrackError):
            load_ball(write(data))

    def test_rejects_a_flight_that_does_not_start_at_release(self):
        """A stationary key beside a flying one is what this guards.

        The interpolator keeps speed continuous through a key, so it zeroes the
        speed where a held segment meets a flying one and the ball drifts out of
        the passer's hand instead of leaving it.
        """
        data = variant()
        data["keys"][0]["atPhase"] = 0.0
        with self.assertRaises(BallTrackError):
            load_ball(write(data))

    def test_rejects_a_flight_that_does_not_end_at_arrival(self):
        data = variant()
        data["arrival"] = {"atPhase": 0.9}
        with self.assertRaises(BallTrackError):
            load_ball(write(data))

    def test_rejects_a_release_after_arrival(self):
        data = variant()
        data["release"] = {"atPhase": 0.8}
        data["keys"][0]["atPhase"] = 0.8
        with self.assertRaises(BallTrackError):
            load_ball(write(data))

    def test_rejects_a_ball_with_no_size(self):
        data = variant()
        del data["radiusFraction"]
        with self.assertRaises(BallTrackError):
            load_ball(write(data))

    def test_rejects_a_key_missing_an_axis(self):
        data = variant()
        del data["keys"][1]["up"]
        with self.assertRaises(BallTrackError):
            load_ball(write(data))


class SizeTest(unittest.TestCase):
    def test_a_stated_radius_does_not_scale_with_the_athlete(self):
        """A size 5 netball is the same ball whoever catches it."""
        data = variant(radiusCm=11.0)
        track = load_ball(write(data))
        self.assertAlmostEqual(track.radius_cm_for(52.68), 11.0)
        self.assertAlmostEqual(track.radius_cm_for(40.0), 11.0)

    def test_a_fraction_scales_with_the_athlete(self):
        track = load_ball(write(VALID))
        self.assertAlmostEqual(track.radius_cm_for(52.68), 0.21 * 52.68)
        self.assertAlmostEqual(track.radius_cm_for(40.0), 0.21 * 40.0)


class SampleTest(unittest.TestCase):
    def setUp(self):
        self.track = load_ball(write(VALID))

    def test_the_passer_holds_the_ball_before_release(self):
        first = self.track.keys[0].offset
        for phase in (0.0, 0.1, 0.199):
            self.assertEqual(self.track.offset_at(phase), first)

    def test_the_athlete_holds_the_ball_after_arrival(self):
        last = self.track.keys[-1].offset
        for phase in (0.6, 0.8, 1.0):
            self.assertEqual(self.track.offset_at(phase), last)

    def test_a_key_is_reached_exactly(self):
        for key in self.track.keys:
            self.assertAlmostEqual(
                self.track.offset_at(key.at_phase).ahead, key.offset.ahead, places=6
            )

    def test_the_flight_never_leaves_the_authored_range(self):
        """The interpolator must not invent a swing the author never wrote."""
        lowest = min(key.offset.ahead for key in self.track.keys)
        highest = max(key.offset.ahead for key in self.track.keys)
        for step in range(101):
            ahead = self.track.offset_at(step / 100).ahead
            self.assertGreaterEqual(ahead, lowest - 1e-9)
            self.assertLessEqual(ahead, highest + 1e-9)

    def test_states_name_who_has_the_ball(self):
        self.assertEqual(self.track.state_at(0.1), "held")
        self.assertEqual(self.track.state_at(0.4), "flight")
        self.assertEqual(self.track.state_at(0.9), "carried")


class StanceFrameTest(unittest.TestCase):
    """The frame is fixed at the start. The trunk moves inside it."""

    def test_a_forward_offset_lands_in_front_of_the_chest(self):
        frame = stance_frame(np.array([0.0, 130.0, 0.0]), 50.0)
        placed = frame.place(BallOffset(across=0.0, up=0.0, ahead=2.0))
        np.testing.assert_allclose(placed, [0.0, 130.0, 100.0])

    def test_across_is_positive_to_the_athletes_left(self):
        """MHR places the left side at positive X, and the ball follows suit."""
        frame = stance_frame(np.zeros(3), 50.0)
        placed = frame.place(BallOffset(across=1.0, up=0.0, ahead=0.0))
        self.assertGreater(placed[0], 0.0)

    def test_the_frame_ignores_a_turn_taken_later(self):
        """A ball placed in a fixed frame cannot be carried around by a turn.

        This is the whole inversion. If the ball moved with the trunk, turning
        toward the ball would move the ball, and the athlete could never arrive
        at it.
        """
        square = stance_frame(np.zeros(3), 50.0, turn_degrees_at_start=0.0)
        offset = BallOffset(across=0.0, up=0.0, ahead=2.0)
        first = square.place(offset)
        # Building the same frame again, whatever the trunk has since done,
        # gives the same world position.
        second = stance_frame(np.zeros(3), 50.0, turn_degrees_at_start=0.0).place(
            offset
        )
        np.testing.assert_allclose(first, second)

    def test_a_drill_that_starts_turned_carries_that_turn(self):
        turned = stance_frame(np.zeros(3), 50.0, turn_degrees_at_start=90.0)
        placed = turned.place(BallOffset(across=0.0, up=0.0, ahead=1.0))
        # Ninety degrees to her left puts straight ahead onto positive X.
        self.assertAlmostEqual(float(placed[0]), 50.0, places=4)
        self.assertAlmostEqual(float(placed[2]), 0.0, places=4)


class SnatchTrajectoryTest(unittest.TestCase):
    """The shipped snatch flight must stay a real throw."""

    def setUp(self):
        self.track = load_ball(ball_path(SNATCH))
        self.arm_cm = 52.68
        self.frames = 40
        self.fps = 24.0

    def test_it_is_the_snatch(self):
        self.assertEqual(self.track.movement_id, SNATCH)

    def test_the_ball_travels_at_a_constant_speed_across_the_ground(self):
        keys = self.track.keys
        seconds = [
            key.at_phase * (self.frames - 1) / self.fps for key in keys
        ]
        speeds = [
            (keys[i].offset.ahead - keys[i + 1].offset.ahead)
            * self.arm_cm
            / (seconds[i + 1] - seconds[i])
            for i in range(len(keys) - 1)
        ]
        for speed in speeds:
            # The key phases are rounded to four places in the file, which moves
            # each segment by a fraction of a percent.
            self.assertAlmostEqual(speed, speeds[0], delta=0.01 * speeds[0])
        # A drill feed, not a game pass.
        self.assertGreater(speeds[0], 400.0)
        self.assertLess(speeds[0], 900.0)

    def test_the_ball_falls_under_gravity(self):
        """Fit the vertical acceleration from the keys. It must be gravity.

        Without this a later edit can turn the flight into any shape at all,
        and a ball that floats is not a pass.
        """
        keys = self.track.keys
        seconds = [key.at_phase * (self.frames - 1) / self.fps for key in keys]
        heights = [key.offset.up * self.arm_cm for key in keys]
        # Second difference over evenly spaced keys is acceleration times the
        # step squared.
        step = seconds[1] - seconds[0]
        accelerations = [
            (heights[i] - 2.0 * heights[i + 1] + heights[i + 2]) / (step * step)
            for i in range(len(keys) - 2)
        ]
        for value in accelerations:
            self.assertAlmostEqual(value, -981.0, delta=30.0)

    def test_the_ball_is_a_size_five_netball(self):
        self.assertAlmostEqual(self.track.radius_cm_for(self.arm_cm), 11.0, places=2)

    def test_the_flight_is_short_enough_to_be_a_pass(self):
        flight = (
            (self.track.arrival_phase - self.track.release_phase)
            * (self.frames - 1)
            / self.fps
        )
        self.assertLess(flight, 0.5)
        self.assertGreater(flight, 0.1)

    def test_the_ball_starts_well_out_of_arm_span(self):
        release = self.track.keys[0].offset
        self.assertGreater(release.ahead, 2.0)

    def test_the_ball_arrives_within_arm_span(self):
        arrival = self.track.keys[-1].offset
        reach = math.sqrt(
            arrival.across**2 + arrival.up**2 + arrival.ahead**2
        )
        self.assertLess(reach, 1.5)


if __name__ == "__main__":
    unittest.main()
