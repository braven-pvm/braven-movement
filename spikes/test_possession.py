"""Tests for who has the ball, and where it is while they have it."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ball_track import BallOffset, load_ball, stance_frame
from possession import (
    PossessionError,
    carry_path,
    resolve,
    to_offset,
)
from technique import AfterContactKey

ARM_CM = 50.0
FRAMES = 21


def ball_file(release=0.2, arrival=0.6, start_ahead=4.0, end_ahead=0.8):
    data = {
        "movementId": "test",
        "radiusCm": 11.0,
        "release": {"atPhase": release},
        "arrival": {"atPhase": arrival},
        "keys": [
            {"atPhase": release, "across": 0.0, "up": 0.3, "ahead": start_ahead},
            {
                "atPhase": (release + arrival) / 2,
                "across": 0.0,
                "up": 0.4,
                "ahead": (start_ahead + end_ahead) / 2,
            },
            {"atPhase": arrival, "across": 0.0, "up": 0.4, "ahead": end_ahead},
        ],
    }
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".ball.json", delete=False, encoding="utf-8"
    )
    json.dump(data, handle)
    handle.close()
    return load_ball(Path(handle.name))


def scene(turn_degrees=0.0, frames=FRAMES):
    """A planted athlete, or one that turns steadily, and the ball's frame."""
    phases = [number / (frames - 1) for number in range(frames)]
    chest = np.array([0.0, 130.0, 0.0])
    stance = stance_frame(chest, ARM_CM, 0.0)
    athlete = [
        stance_frame(chest, ARM_CM, turn_degrees * phase) for phase in phases
    ]
    shoulders = [np.array([0.0, 137.0, 0.0]) for _ in phases]
    return phases, stance, athlete, shoulders


CARRY = (
    AfterContactKey(0.8, "absorb", BallOffset(0.0, 0.3, 0.6)),
    AfterContactKey(1.0, "pull_in", BallOffset(0.0, 0.1, 0.4)),
)


def run(turn_degrees=0.0, after=CARRY, reach_limit=62.0, **ball):
    phases, stance, athlete, shoulders = scene(turn_degrees)
    return resolve(
        phases=phases,
        ball=ball_file(**ball),
        stance=stance,
        athlete_frames=athlete,
        shoulder_mids=shoulders,
        after_contact=after,
        reach_limit_cm=reach_limit,
        arm_length_cm=ARM_CM,
    )


class CarryPathTest(unittest.TestCase):
    def test_the_carry_always_starts_where_the_flight_ended(self):
        """Authoring both ends is how a ball comes to jump at the handover."""
        contact = BallOffset(0.1, 0.42, 0.9)
        phases, offsets = carry_path(0.55, contact, CARRY)
        self.assertAlmostEqual(phases[0], 0.55)
        self.assertEqual(offsets[0], contact)

    def test_a_key_already_in_the_past_is_dropped(self):
        phases, offsets = carry_path(0.9, BallOffset(0.0, 0.4, 0.9), CARRY)
        self.assertEqual(phases, [0.9, 1.0])
        self.assertEqual(len(offsets), 2)

    def test_a_technique_that_drives_nothing_still_gives_a_path(self):
        phases, offsets = carry_path(0.5, BallOffset(0.0, 0.4, 0.9), ())
        self.assertEqual(len(phases), 1)


class FrameTest(unittest.TestCase):
    def test_a_position_survives_a_round_trip_through_a_frame(self):
        frame = stance_frame(np.array([1.0, 130.0, -4.0]), ARM_CM, 35.0)
        offset = BallOffset(0.2, 0.4, 0.9)
        found = to_offset(frame, frame.place(offset), ARM_CM)
        self.assertAlmostEqual(found.across, offset.across, places=9)
        self.assertAlmostEqual(found.up, offset.up, places=9)
        self.assertAlmostEqual(found.ahead, offset.ahead, places=9)


class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.held = run()

    def test_she_catches_it(self):
        self.assertTrue(self.held.caught)

    def test_contact_is_the_first_frame_the_ball_is_within_reach(self):
        number = self.held.contact_frame
        shoulder = np.array([0.0, 137.0, 0.0])
        self.assertLessEqual(
            float(np.linalg.norm(self.held.frames[number].centre - shoulder)), 62.0
        )
        before = self.held.frames[number - 1]
        self.assertGreater(float(np.linalg.norm(before.centre - shoulder)), 62.0)

    def test_the_ball_does_not_jump_when_possession_transfers(self):
        """The whole point of the handover. Nothing else in the model checks it."""
        number = self.held.contact_frame
        steps = [
            self.held.ball_step_at(n) for n in range(1, len(self.held.frames))
        ]
        self.assertLessEqual(
            self.held.ball_step_at(number), max(steps) + 1e-9
        )

    def test_she_holds_the_ball_from_contact_onward(self):
        number = self.held.contact_frame
        for frame in self.held.frames[:number]:
            self.assertFalse(frame.holding)
        for frame in self.held.frames[number:]:
            self.assertTrue(frame.holding)
            self.assertEqual(frame.state, "carried")

    def test_the_hands_are_on_the_ball_once_she_has_it(self):
        for frame in self.held.frames:
            if frame.holding:
                np.testing.assert_allclose(frame.presented, frame.centre)

    def test_the_hands_wait_before_the_passer_lets_go(self):
        early = [f for f in self.held.frames if f.phase <= 0.2]
        for frame in early[1:]:
            np.testing.assert_allclose(
                frame.presented, early[0].presented, atol=1e-9
            )

    def test_the_hands_are_never_further_out_than_she_can_reach(self):
        shoulder = np.array([0.0, 137.0, 0.0])
        for frame in self.held.frames:
            self.assertLessEqual(
                float(np.linalg.norm(frame.presented - shoulder)), 62.0 + 1e-6
            )

    def test_the_hands_arrive_where_the_ball_arrives(self):
        """Anticipation. The ball must not have to be chased."""
        number = self.held.contact_frame
        np.testing.assert_allclose(
            self.held.frames[number].presented,
            self.held.frames[number].centre,
            atol=1e-9,
        )

    def test_the_hands_move_smoothly_into_the_catch(self):
        number = self.held.contact_frame
        steps = [
            float(
                np.linalg.norm(
                    self.held.frames[n].presented - self.held.frames[n - 1].presented
                )
            )
            for n in range(1, number + 1)
        ]
        # No single approach frame may move the hands more than twice as far as
        # the one before it. That is what catches a snap.
        for before, after in zip(steps, steps[1:]):
            if before > 0.5:
                self.assertLess(after, 2.0 * before + 1e-9)


class DroppedBallTest(unittest.TestCase):
    def test_a_ball_that_never_arrives_is_not_caught(self):
        held = run(reach_limit=20.0)
        self.assertFalse(held.caught)
        self.assertIsNone(held.contact_frame)

    def test_an_uncaught_ball_stays_in_its_own_frame(self):
        held = run(reach_limit=20.0)
        for frame in held.frames:
            self.assertFalse(frame.holding)


class TurningTest(unittest.TestCase):
    """Possession is a statement about frames of reference."""

    def test_the_flight_ignores_the_athlete_turning(self):
        square = run(turn_degrees=0.0)
        turned = run(turn_degrees=40.0)
        number = square.contact_frame
        for a, b in zip(square.frames[:number], turned.frames[:number]):
            np.testing.assert_allclose(a.centre, b.centre, atol=1e-9)

    def test_a_carried_ball_travels_with_her(self):
        square = run(turn_degrees=0.0)
        turned = run(turn_degrees=40.0)
        last_square = square.frames[-1].centre
        last_turned = turned.frames[-1].centre
        self.assertGreater(float(np.linalg.norm(last_square - last_turned)), 5.0)


class InputTest(unittest.TestCase):
    def test_every_frame_needs_a_trunk(self):
        phases, stance, athlete, shoulders = scene()
        with self.assertRaises(PossessionError):
            resolve(
                phases=phases,
                ball=ball_file(),
                stance=stance,
                athlete_frames=athlete[:-1],
                shoulder_mids=shoulders,
                after_contact=CARRY,
                reach_limit_cm=62.0,
                arm_length_cm=ARM_CM,
            )


if __name__ == "__main__":
    unittest.main()
