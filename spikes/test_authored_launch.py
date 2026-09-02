"""A ball file may say where its own pass goes, instead of it being derived.

The outgoing pass used to take both its target and its speed from the INCOMING
flight: the ball goes back to where the passer stood, at the speed he threw.
That is right for a catch-and-return and it is what every drill in the library
does. It is wrong wherever there is no meaningful incoming flight, and it is
wrong SILENTLY, which is why the content lane's pass family found it by probing
rather than by an error.

Both probes are cases here, and both are the numbers this file exists to keep
fixed:

- A drill she holds from phase 0 releases at 0, so the derived target is the
  ball in her own hands. The pass launched backwards over her shoulder.
- The derived speed is the flight's length over its duration, so a short
  fictional flight authored only to satisfy `arrival` sets the throw. The
  earlier she holds it, the harder she throws.

No solver. `ball_track` and `possession` are both arithmetic, so this runs
wherever the tests run.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ball_track import (
    BALL_SUFFIX,
    MOVEMENT_DIR,
    BallKey,
    BallOffset,
    BallTrack,
    BallTrackError,
    Launch,
    load_ball,
    stance_frame,
)
from possession import return_velocity

# NOT `movement_engine.library`, which is only a directory glob but lives in a
# module that imports the solver at its top. Importing it here made this whole
# file fail to LOAD on the hosted runner, so eleven tests became one error —
# the third time that has happened in this repository and the second time to
# me. `ball_track` knows where the movements are and needs no solver.
#
# `test_import_hygiene.py` now asserts every test module imports without one,
# so a fourth instance fails on the machine that writes it.

ARM_CM = 52.7
SECONDS_PER_PHASE = 1.0


def stance():
    return stance_frame(np.array([0.0, 132.0, 5.0]), ARM_CM, 0.0)


def track(release: float, arrival: float, launch: Launch | None = None):
    return BallTrack(
        movement_id="probe",
        radius_fraction=0.0,
        radius_cm=11.0,
        release_phase=release,
        arrival_phase=arrival,
        keys=(
            BallKey(release, "release", BallOffset(0.0, 0.2, 4.0)),
            BallKey(arrival, "arrival", BallOffset(0.0, 0.3, 0.6)),
        ),
        launch=launch,
    )


def written(body: dict) -> Path:
    """A ball file on disk, because `load_ball` reads files."""
    where = Path(tempfile.mkdtemp()) / "probe.ball.json"
    where.write_text(json.dumps(body), encoding="utf-8")
    return where


def minimal(**extra) -> dict:
    body = {
        "movementId": "probe",
        "radiusCm": 11.0,
        "release": {"atPhase": 0.0},
        "arrival": {"atPhase": 0.5},
        "radiusFraction": 0.0,
        "keys": [
            {"atPhase": 0.0, "name": "release",
             "across": 0.0, "up": 0.2, "ahead": 4.0},
            {"atPhase": 0.5, "name": "arrival",
             "across": 0.0, "up": 0.3, "ahead": 0.6},
        ],
    }
    body.update(extra)
    return body


# Which ball files author a launch, by design. Everything else must derive.
#
# This list replaces a blanket "nothing authors one", which was true until the
# pass family arrived and which fired, correctly, on the first pass. The check
# is kept rather than dropped, and it is now stronger: it catches a launch
# APPEARING in a catch drill, where it would silently replace the derived
# return, AND a launch DISAPPEARING from a pass, where the derivation sends the
# ball backwards over her shoulder. Both are the same silent class of fault.
AUTHORS_A_LAUNCH = {"netball_chest_pass.ball.json"}


class ItIsAdditive(unittest.TestCase):
    """The claim that nothing existing changes, measured rather than asserted."""

    def test_only_the_pass_family_authors_a_launch(self) -> None:
        found = 0
        authored = set()
        for path in sorted(MOVEMENT_DIR.glob("*" + BALL_SUFFIX)):
            if load_ball(path).launch is not None:
                authored.add(path.name)
            found += 1
        self.assertGreater(found, 5, "no ball file was read")
        self.assertEqual(
            authored,
            AUTHORS_A_LAUNCH,
            "the set of ball files authoring a launch changed. A launch that "
            "appears in a catch drill silently replaces its derived return; a "
            "launch that disappears from a pass sends the ball backwards over "
            "her shoulder. If the change is intended, update AUTHORS_A_LAUNCH.",
        )

    def test_a_file_without_a_launch_loads_without_one(self) -> None:
        self.assertIsNone(load_ball(written(minimal())).launch)


class WhatALaunchMustSay(unittest.TestCase):
    def test_a_whole_one_loads(self) -> None:
        ball = load_ball(written(minimal(launch={
            "target": {"across": 0.1, "up": 0.2, "ahead": 6.0},
            "speedCmPerSecond": 624.0,
        })))
        self.assertIsNotNone(ball.launch)
        self.assertAlmostEqual(ball.launch.speed_cm_per_second, 624.0)
        self.assertAlmostEqual(ball.launch.target.ahead, 6.0)

    def test_a_launch_with_no_speed_is_refused(self) -> None:
        with self.assertRaises(BallTrackError) as caught:
            load_ball(written(minimal(launch={
                "target": {"across": 0.0, "up": 0.2, "ahead": 6.0}})))
        self.assertIn("speedCmPerSecond", str(caught.exception))

    def test_a_launch_with_no_target_is_refused(self) -> None:
        with self.assertRaises(BallTrackError) as caught:
            load_ball(written(minimal(launch={"speedCmPerSecond": 624.0})))
        self.assertIn("target", str(caught.exception))

    def test_a_speed_that_is_not_a_throw_is_refused(self) -> None:
        for speed in (0.0, -10.0):
            with self.subTest(speed=speed):
                with self.assertRaises(BallTrackError):
                    load_ball(written(minimal(launch={
                        "target": {"across": 0.0, "up": 0.2, "ahead": 6.0},
                        "speedCmPerSecond": speed})))

    def test_a_malformed_target_is_refused(self) -> None:
        with self.assertRaises(BallTrackError):
            load_ball(written(minimal(launch={
                "target": {"across": 0.0, "up": 0.2},  # no ahead
                "speedCmPerSecond": 624.0})))


class TheTwoProbes(unittest.TestCase):
    """The faults that asked for this, kept fixed."""

    def setUp(self) -> None:
        self.stance = stance()
        self.released = self.stance.place(BallOffset(0.0, 0.30, 0.60))
        self.launch = Launch(BallOffset(0.0, 0.10, 6.0), 624.0)

    def ground_speed(self, velocity) -> float:
        return float(np.linalg.norm([velocity[0], 0.0, velocity[2]]))

    def test_a_held_from_zero_drill_no_longer_throws_backwards(self) -> None:
        """Probe one. With release at 0 the derived target is the ball in her
        own hands, and the solved launch is nonsense — not an error, a
        confident wrong answer."""
        derived = return_velocity(
            track(0.0, 0.0001), self.stance, self.released, SECONDS_PER_PHASE)
        authored = return_velocity(
            track(0.0, 0.0001, self.launch), self.stance, self.released,
            SECONDS_PER_PHASE)
        self.assertGreater(
            self.ground_speed(derived), 10_000.0,
            "the derived launch is no longer absurd here, so this probe has "
            "stopped testing what it was written for",
        )
        self.assertGreater(authored[2], 0.0, "the authored pass goes forward")
        self.assertAlmostEqual(
            self.ground_speed(authored), 624.0, delta=1.0)

    def test_the_authored_speed_does_not_depend_on_the_arrival_phase(
        self,
    ) -> None:
        """Probe two. The whole point: an authored throw reads no arrival."""
        speeds = [
            self.ground_speed(return_velocity(
                track(0.0, arrival, self.launch), self.stance, self.released,
                SECONDS_PER_PHASE))
            for arrival in (0.02, 0.10, 0.25, 0.60)
        ]
        for speed in speeds:
            self.assertAlmostEqual(speed, 624.0, delta=1.0)

    def test_the_derived_speed_still_does_depend_on_it(self) -> None:
        """The other half, and the one that keeps the first honest. If
        deriving ever stopped varying with the arrival phase, the test above
        would pass for a reason that has nothing to do with the launch field.
        """
        speeds = [
            self.ground_speed(return_velocity(
                track(0.0, arrival), self.stance, self.released,
                SECONDS_PER_PHASE))
            for arrival in (0.02, 0.10, 0.25, 0.60)
        ]
        self.assertGreater(
            max(speeds) / min(speeds), 5.0,
            f"deriving no longer varies with arrival: {speeds}",
        )


class WhereTheAuthoredPassGoes(unittest.TestCase):
    def test_it_is_aimed_at_the_target_the_file_names(self) -> None:
        """Aimed, not merely fast. A speed with the wrong direction is the
        first probe's fault wearing a correct number."""
        here = stance()
        released = here.place(BallOffset(0.0, 0.30, 0.60))
        for ahead, across in ((6.0, 0.0), (6.0, 2.0), (6.0, -2.0)):
            with self.subTest(across=across):
                launch = Launch(BallOffset(across, 0.10, ahead), 624.0)
                velocity = return_velocity(
                    track(0.0, 0.5, launch), here, released, SECONDS_PER_PHASE)
                target = here.place(launch.target)
                wanted = np.array([target[0] - released[0],
                                   target[2] - released[2]])
                got = np.array([velocity[0], velocity[2]])
                wanted = wanted / np.linalg.norm(wanted)
                got = got / np.linalg.norm(got)
                self.assertAlmostEqual(
                    float(wanted @ got), 1.0, places=6,
                    msg="the launch is not aimed along the ground at its target",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
