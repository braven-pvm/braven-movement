"""Contract tests for the movement keys and the left-right convention."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motion_track import (  # noqa: E402
    MotionTrackError,
    hand_targets_from_track,
    load_motion,
)

MOTION_PATH = Path(__file__).resolve().parent / "movements" / "netball_two_hand_catch.motion.json"


def write_track(keys, stance=0.18):
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(
        {
            "movementId": "test",
            "frames": 12,
            "framesPerSecond": 24,
            "stance": {"hipDropFraction": stance},
            "keys": keys,
        },
        handle,
    )
    handle.close()
    return Path(handle.name)


def key(at_phase, name, across=0.25, up=0.0, ahead=0.4):
    return {
        "atPhase": at_phase,
        "name": name,
        "across": across,
        "up": up,
        "ahead": ahead,
    }


class HandednessTest(unittest.TestCase):
    """MHR places the left side at positive X. Getting this wrong crosses the arms."""

    def test_the_left_hand_target_is_on_the_positive_x_side(self):
        track = load_motion(MOTION_PATH)
        chest = np.array([0.0, 140.0, 0.0], dtype=np.float32)

        left, right = hand_targets_from_track(track, 0.0, chest, 53.0)

        self.assertGreater(left[0], right[0])
        self.assertGreater(left[0], chest[0])
        self.assertLess(right[0], chest[0])

    def test_the_hands_never_cross_at_any_phase(self):
        track = load_motion(MOTION_PATH)
        chest = np.array([0.0, 140.0, 0.0], dtype=np.float32)

        for step in range(41):
            phase = step / 40.0
            left, right = hand_targets_from_track(track, phase, chest, 53.0)
            self.assertGreater(
                left[0], right[0], f"the hands crossed at phase {phase:.3f}"
            )

    def test_both_hands_stay_in_front_of_the_chest(self):
        track = load_motion(MOTION_PATH)
        chest = np.array([0.0, 140.0, 0.0], dtype=np.float32)

        for step in range(21):
            phase = step / 20.0
            left, right = hand_targets_from_track(track, phase, chest, 53.0)
            self.assertGreater(left[2], chest[2])
            self.assertGreater(right[2], chest[2])


class InterpolationTest(unittest.TestCase):
    def test_a_key_is_reached_exactly_at_its_phase(self):
        path = write_track([key(0.0, "a", ahead=0.2), key(1.0, "b", ahead=0.9)])
        track = load_motion(path)

        self.assertAlmostEqual(track.offsets_at(0.0)[2], 0.2, places=6)
        self.assertAlmostEqual(track.offsets_at(1.0)[2], 0.9, places=6)

    def test_the_midpoint_sits_between_the_keys(self):
        path = write_track([key(0.0, "a", ahead=0.2), key(1.0, "b", ahead=0.8)])
        track = load_motion(path)

        middle = track.offsets_at(0.5)[2]

        self.assertAlmostEqual(middle, 0.5, places=6)

    def test_the_movement_eases_rather_than_moving_at_a_constant_rate(self):
        """A coached movement starts and ends softly at each key."""
        path = write_track([key(0.0, "a", ahead=0.0), key(1.0, "b", ahead=1.0)])
        track = load_motion(path)

        early = track.offsets_at(0.05)[2]
        middle_step = track.offsets_at(0.55)[2] - track.offsets_at(0.45)[2]

        self.assertLess(early, 0.05)
        self.assertGreater(middle_step, 0.09)


class ValidationTest(unittest.TestCase):
    def test_a_reach_beyond_the_arm_is_rejected(self):
        path = write_track([key(0.0, "a"), key(1.0, "b", ahead=1.4)])

        with self.assertRaises(MotionTrackError) as caught:
            load_motion(path)

        self.assertIn("further than the arm can reach", str(caught.exception))

    def test_keys_out_of_order_are_rejected(self):
        path = write_track([key(0.0, "a"), key(0.8, "c"), key(0.4, "b"), key(1.0, "d")])

        with self.assertRaises(MotionTrackError):
            load_motion(path)

    def test_keys_that_do_not_span_the_whole_movement_are_rejected(self):
        path = write_track([key(0.0, "a"), key(0.7, "b")])

        with self.assertRaises(MotionTrackError):
            load_motion(path)

    def test_a_single_key_is_rejected(self):
        path = write_track([key(0.0, "only")])

        with self.assertRaises(MotionTrackError):
            load_motion(path)


class ShippedMotionTest(unittest.TestCase):
    def test_the_netball_motion_loads_and_names_its_phases(self):
        track = load_motion(MOTION_PATH)

        self.assertEqual(
            [item.name for item in track.keys],
            ["ready", "react", "contact", "absorb", "pull_in"],
        )
        self.assertAlmostEqual(track.contact_phase(), 0.55, places=6)

    def test_contact_is_the_furthest_reach(self):
        """The manual takes the ball out in front, then pulls it in."""
        track = load_motion(MOTION_PATH)

        furthest = max(track.keys, key=lambda item: item.ahead)

        self.assertEqual(furthest.name, "contact")

    def test_the_pull_in_is_closer_than_the_contact(self):
        track = load_motion(MOTION_PATH)
        keys = {item.name: item for item in track.keys}

        self.assertLess(keys["pull_in"].ahead, keys["contact"].ahead)


if __name__ == "__main__":
    unittest.main()
