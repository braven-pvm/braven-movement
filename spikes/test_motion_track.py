"""Contract tests for the movement keys and the left-right convention."""

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motion_track import (  # noqa: E402
    MotionTrackError,
    hand_targets_from_track,
    load_motion,
    turn_matrix,
)


def in_trunk_frame(track, phase, chest, point):
    """Undo the trunk turn, so left and right mean left and right of the athlete.

    Once a movement turns, world X stops meaning the athlete's left. The
    handedness invariant lives in the trunk frame, not the world frame.
    """
    rotation = turn_matrix(-track.turn_at(phase))
    return rotation @ (np.asarray(point, dtype=np.float64) - chest)

MOVEMENTS = Path(__file__).resolve().parent / "movements"
MOTION_PATHS = sorted(MOVEMENTS.glob("*.motion.json"))
PULL_IN = MOVEMENTS / "netball_two_hand_snatch_pull_in.motion.json"


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

    def test_the_left_hand_is_on_the_left_of_the_trunk(self):
        chest = np.array([0.0, 140.0, 0.0], dtype=np.float32)

        for path in MOTION_PATHS:
            track = load_motion(path)
            left, right = hand_targets_from_track(track, 0.0, chest, 53.0)
            left_local = in_trunk_frame(track, 0.0, chest, left)
            right_local = in_trunk_frame(track, 0.0, chest, right)
            self.assertGreater(left_local[0], right_local[0], path.name)
            self.assertGreater(left_local[0], 0.0, path.name)
            self.assertLess(right_local[0], 0.0, path.name)

    def test_the_hands_never_cross_at_any_phase(self):
        """Measured in the trunk frame, so a turned drill is judged fairly."""
        chest = np.array([0.0, 140.0, 0.0], dtype=np.float32)

        for path in MOTION_PATHS:
            track = load_motion(path)
            for step in range(41):
                phase = step / 40.0
                left, right = hand_targets_from_track(track, phase, chest, 53.0)
                left_local = in_trunk_frame(track, phase, chest, left)
                right_local = in_trunk_frame(track, phase, chest, right)
                self.assertGreater(
                    left_local[0], right_local[0],
                    f"{path.name}: the hands crossed at phase {phase:.3f}",
                )

    def test_both_hands_stay_in_front_of_the_trunk(self):
        chest = np.array([0.0, 140.0, 0.0], dtype=np.float32)

        for path in MOTION_PATHS:
            track = load_motion(path)
            for step in range(21):
                phase = step / 20.0
                left, right = hand_targets_from_track(track, phase, chest, 53.0)
                self.assertGreater(
                    in_trunk_frame(track, phase, chest, left)[2], 0.0, path.name
                )
                self.assertGreater(
                    in_trunk_frame(track, phase, chest, right)[2], 0.0, path.name
                )


class InterpolationTest(unittest.TestCase):
    def test_a_key_is_reached_exactly_at_its_phase(self):
        path = write_track([key(0.0, "a", ahead=0.2), key(1.0, "b", ahead=0.9)])
        track = load_motion(path)

        self.assertAlmostEqual(track.offsets_at(0.0)[0].ahead, 0.2, places=6)
        self.assertAlmostEqual(track.offsets_at(1.0)[0].ahead, 0.9, places=6)

    def test_the_midpoint_sits_between_the_keys(self):
        path = write_track([key(0.0, "a", ahead=0.2), key(1.0, "b", ahead=0.8)])
        track = load_motion(path)

        middle = track.offsets_at(0.5)[0].ahead

        self.assertAlmostEqual(middle, 0.5, places=6)

    def test_the_movement_eases_rather_than_moving_at_a_constant_rate(self):
        """A coached movement starts and ends softly at each key."""
        path = write_track([key(0.0, "a", ahead=0.0), key(1.0, "b", ahead=1.0)])
        track = load_motion(path)

        early = track.offsets_at(0.05)[0].ahead
        middle_step = track.offsets_at(0.55)[0].ahead - track.offsets_at(0.45)[0].ahead

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


class LibraryTest(unittest.TestCase):
    """Every movement in the library must satisfy these, including new ones."""

    def test_the_library_is_not_empty(self):
        self.assertGreaterEqual(len(MOTION_PATHS), 1)

    def test_every_movement_loads(self):
        for path in MOTION_PATHS:
            track = load_motion(path)
            self.assertGreaterEqual(len(track.keys), 2, path.name)

    def test_every_movement_id_matches_its_file_name(self):
        """The library pairs a motion with a definition by file name."""
        for path in MOTION_PATHS:
            track = load_motion(path)
            expected = path.name[: -len(".motion.json")]
            self.assertEqual(track.movement_id, expected, path.name)

    def test_every_movement_has_a_matching_definition(self):
        for path in MOTION_PATHS:
            definition = path.parent / (path.name[: -len(".motion.json")] + ".json")
            self.assertTrue(definition.is_file(), f"no definition for {path.name}")

    def test_the_pull_in_drill_pulls_in(self):
        """The ball must finish closer to the chest than it was at contact."""
        track = load_motion(PULL_IN)
        keys = {item.name: item for item in track.keys}

        self.assertLess(keys["pull_in"].left.ahead, keys["contact"].left.ahead)

    def test_the_straight_back_drill_does_not_pull_in(self):
        """The manual's whole distinction: the ball never comes to the body."""
        path = MOVEMENTS / "netball_two_hand_snatch_straight_back.motion.json"
        track = load_motion(path)

        self.assertNotIn("pull_in", [item.name for item in track.keys])

    def test_the_drills_where_one_hand_leads_are_asymmetric(self):
        """A drill the manual describes as one-handed must not be mirrored."""
        for name in (
            "netball_one_hand_snatch_to_other_hand",
            "netball_hooks_outside_hand",
        ):
            track = load_motion(MOVEMENTS / f"{name}.motion.json")
            self.assertFalse(track.is_symmetric(), name)

    def test_a_split_stance_drill_is_not_symmetric(self):
        """The fault that made this flag read the feet.

        `double_foot_landing` lands off one foot. Its hands match, so while
        the flag read hands alone it published `symmetric: true` about a
        drill whose feet are 0.31 apart in the ahead axis.
        """
        track = load_motion(MOVEMENTS / "netball_double_foot_landing.motion.json")

        self.assertTrue(
            all(key.left == key.right for key in track.keys),
            "the hands must match, or this drill proves nothing about the feet",
        )
        gaps = [
            abs(key.foot_left.ahead - key.foot_right.ahead)
            for key in track.keys
            if key.foot_left is not None and key.foot_right is not None
        ]
        self.assertGreater(max(gaps), 0.3, "the split stance is the input")
        self.assertFalse(track.is_symmetric())

    def test_a_planted_turn_or_step_makes_a_square_drill_asymmetric(self):
        """Guards the two clauses no drill in the library exercises.

        `turn_degrees` and `root_across` both carry a side, and today every
        drill that uses them is already asymmetric in its hands. Without
        this, either clause could be deleted and the suite would stay green.
        """
        source = MOVEMENTS / "netball_two_hand_catch_chest.motion.json"

        for field, value in (("turn_degrees", 12.0), ("root_across", 0.25)):
            track = load_motion(source)
            self.assertTrue(track.is_symmetric(), "the drill must start square")

            keys = list(track.keys)
            keys[1] = replace(keys[1], **{field: value})
            track = replace(track, keys=tuple(keys))

            self.assertFalse(track.is_symmetric(), field)

    def test_a_turned_drill_declares_its_turn(self):
        track = load_motion(MOVEMENTS / "netball_hooks_outside_hand.motion.json")

        self.assertTrue(track.turns())
        self.assertGreater(abs(track.keys[0].turn_degrees), 20.0)

    def test_a_square_drill_does_not_turn(self):
        for name in (
            "netball_two_hand_snatch_pull_in",
            "netball_two_hand_catch_chest",
        ):
            self.assertFalse(load_motion(MOVEMENTS / f"{name}.motion.json").turns(), name)

    def test_a_turn_beyond_what_planted_feet_allow_is_rejected(self):
        keys = [key(0.0, "a"), key(1.0, "b")]
        keys[0]["turnDegrees"] = 95.0
        path = write_track(keys)

        with self.assertRaises(MotionTrackError) as caught:
            load_motion(path)

        self.assertIn("planted feet", str(caught.exception))


class FootworkTest(unittest.TestCase):
    """Feet that move, hips that travel, and a flight phase."""

    LANDING = MOVEMENTS / "netball_double_foot_landing.motion.json"

    def test_a_planted_drill_does_not_key_its_feet(self):
        for name in (
            "netball_two_hand_snatch_pull_in",
            "netball_hooks_outside_hand",
        ):
            track = load_motion(MOVEMENTS / f"{name}.motion.json")
            self.assertFalse(track.moves_feet(), name)

    def test_the_landing_drill_keys_its_feet(self):
        self.assertTrue(load_motion(self.LANDING).moves_feet())

    def test_the_landing_drill_leaves_the_ground(self):
        track = load_motion(self.LANDING)

        self.assertTrue(track.airborne_phases())

    def test_both_feet_leave_together_and_land_together(self):
        """A double foot landing is the whole point of the drill."""
        track = load_motion(self.LANDING)

        for phase in (0.0, 0.5, 0.82, 1.0):
            left, right = track.feet_at(phase)
            self.assertLess(
                abs(left.up - right.up), 0.12, f"feet split at phase {phase}"
            )

    def test_the_hips_travel_forward_over_the_movement(self):
        track = load_motion(self.LANDING)

        start = track.root_offset_at(0.0)[1]
        finish = track.root_offset_at(1.0)[1]

        self.assertLess(start, finish)

    def test_a_planted_drill_does_not_travel(self):
        track = load_motion(MOVEMENTS / "netball_two_hand_snatch_pull_in.motion.json")

        for step in range(11):
            across, ahead = track.root_offset_at(step / 10.0)
            self.assertAlmostEqual(across, 0.0, places=9)
            self.assertAlmostEqual(ahead, 0.0, places=9)

    def test_keying_only_one_foot_is_rejected(self):
        """Half a set of feet would jump between placed and planted."""
        keys = [key(0.0, "a"), key(1.0, "b")]
        keys[0]["footLeft"] = {"across": 0.16, "ahead": 0.0, "up": 0.0}
        keys[0]["footRight"] = {"across": 0.16, "ahead": 0.0, "up": 0.0}
        path = write_track(keys)

        with self.assertRaises(MotionTrackError) as caught:
            load_motion(path)

        self.assertIn("every key or on none", str(caught.exception))

    def test_a_foot_on_the_ground_reads_as_planted(self):
        track = load_motion(self.LANDING)
        left, right = track.feet_at(1.0)

        self.assertFalse(left.airborne)
        self.assertFalse(right.airborne)


if __name__ == "__main__":
    unittest.main()
