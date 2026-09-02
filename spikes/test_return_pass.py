"""A released ball must answer the pass it came from.

Before this, `possession.py` read the release velocity from a one-frame
difference of the carry path. The carry is almost stationary at that moment,
so the ball left her hands at 0.13 to 0.57 m/s against an incoming pass of
about 6.3 m/s, and then drifted. It graded 8 of 8 and passed every test,
because nothing asked how fast the ball left.

The engine now solves the return: back to the passer who threw it, at the
horizontal speed the passer used. Both ends and the duration are already
authored in the incoming track, so no number is typed.

What is PROVISIONAL is the reading, not the arithmetic. That she returns the
ball to the passer comes from the manual's cues and no coach has confirmed it.
The ball files say so, and one test below keeps them saying it.

These run only where the solver is installed, which is the pixi environment.
A green system-python run says nothing about them.
"""

from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
MOVEMENTS = SPIKE_DIR / "movements"
GRAVITY_CM = 981.0

# Only a genuinely absent solver may skip. Catching every exception here would
# swallow a break in the code under test and skip the guard in silence.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    from ball_track import MOVEMENT_DIR
    from motion_track import load_motion
    from movement_engine import load_character
    from possession_solve import solve_movement


def releasing_drills() -> list[str]:
    """Every drill whose technique lets go of the ball."""
    return [
        path.name.replace(".technique.json", "")
        for path in sorted(MOVEMENTS.glob("*.technique.json"))
        if "release" in json.loads(path.read_text(encoding="utf-8"))
    ]


def authors_its_launch(movement_id: str) -> bool:
    """Whether the drill says where its own pass goes.

    A drill without this derives both the target and the speed from the
    incoming flight, which is what everything in this file was written about.
    A drill WITH it has no incoming flight to mirror, and the two classes are
    measured differently below rather than averaged into one rule.
    """
    ball = MOVEMENTS / f"{movement_id}.ball.json"
    if not ball.is_file():
        return False
    return "launch" in json.loads(ball.read_text(encoding="utf-8"))


def deriving_releasing_drills() -> list[str]:
    """Releasing drills whose return is derived from the pass that came in."""
    return [
        movement_id
        for movement_id in releasing_drills()
        if not authors_its_launch(movement_id)
    ]


class TheReturnIsMarkedProvisional(unittest.TestCase):
    """Reads authored files only, so it runs without the solver."""

    def test_a_drill_releases_the_ball(self) -> None:
        """Guards the guard. With no releasing drill the rule below is empty."""
        self.assertTrue(releasing_drills(), "no drill releases the ball")

    def test_the_deriving_restriction_excludes_something(self) -> None:
        """The anti-hollow clause for `deriving_releasing_drills`.

        Two tests in this file mirror the outgoing pass against the incoming
        one, and a drill with no incoming pass cannot be measured that way. The
        restriction that excludes those would become a silent no-op if the pass
        family were removed, and the two tests would then be claiming to check
        something they no longer reach. Both lists are asserted non-empty so
        that either half disappearing is loud.
        """
        deriving = deriving_releasing_drills()
        self.assertTrue(deriving, "no releasing drill derives its return")
        authored = set(releasing_drills()) - set(deriving)
        self.assertTrue(
            authored,
            "no releasing drill authors its launch, so the restriction in "
            "deriving_releasing_drills excludes nothing and the two mirror "
            "tests below are back to iterating every releasing drill",
        )

    def test_every_releasing_drill_says_its_return_is_provisional(self) -> None:
        """The rule is unchanged: a drill must say that where it sends the ball
        is a reading no coach has confirmed. WHICH FIELD carries that sentence
        depends on how the drill decides, so the check now reads the field that
        applies instead of one field that used to be the only kind."""
        for movement_id in releasing_drills():
            ball = json.loads(
                (MOVEMENTS / f"{movement_id}.ball.json").read_text(encoding="utf-8")
            )
            if authors_its_launch(movement_id):
                # An authored launch states a target AND a speed, and both are
                # choices a coach owns, so both must say so. This is stricter
                # than the derived case, which has one note for both.
                notes = {
                    "launchTargetNote": ball.get("launchTargetNote", ""),
                    "launchSpeedNote": ball.get("launchSpeedNote", ""),
                }
            else:
                notes = {"returnNote": ball.get("returnNote", "")}
            for field, note in notes.items():
                with self.subTest(movement=movement_id, field=field):
                    self.assertIn(
                        "PROVISIONAL",
                        note,
                        f"{movement_id} decides where the ball goes on a "
                        f"reading no coach has confirmed, and its {field} does "
                        "not say so.",
                    )


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheReturnMirrorsThePassItAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()

    @staticmethod
    def release_velocity(movement_id: str) -> np.ndarray:
        """Recovered from the released path, with gravity undone.

        The timestep is 1 over the motion's own frame rate. It is NOT
        `result["solveSecondsPerFrame"]`, which is the solver's cost and
        has produced two wrong readings of this number.
        """
        step = 1.0 / load_motion(
            MOVEMENT_DIR / f"{movement_id}.motion.json"
        ).frames_per_second
        frames = solve_movement(
            load_character(), movement_id
        )["possession"].frames
        first = next(n for n, f in enumerate(frames) if f.state == "released")
        after = np.array(frames[first + 1].centre)
        velocity = (after - np.array(frames[first].centre)) / step
        velocity[1] += 0.5 * GRAVITY_CM * step
        return velocity

    def test_the_horizontal_speed_matches_the_pass_that_came_in(self) -> None:
        """The mechanism, and the tightest thing here.

        Horizontal rather than total, because the launch angle differs at the
        two ends: she releases from higher than the passer does, so the same
        corridor needs a flatter arc. Matching the total would be wrong.
        """
        for movement_id in deriving_releasing_drills():
            flight = json.loads(
                (MOVEMENTS / f"{movement_id}.ball.json").read_text(encoding="utf-8")
            )["flight"]
            incoming = flight["launchSpeedMetresPerSecond"] * math.cos(
                math.radians(flight["launchAngleDegrees"])
            )
            velocity = self.release_velocity(movement_id)
            outgoing = float(np.hypot(velocity[0], velocity[2])) / 100.0
            with self.subTest(movement=movement_id):
                self.assertAlmostEqual(
                    outgoing,
                    incoming,
                    delta=0.1,
                    msg=f"{movement_id} returns the ball at {outgoing:.2f} m/s "
                    f"against a pass that came in at {incoming:.2f}",
                )

    def test_the_ball_leaves_faster_than_a_walk(self) -> None:
        """The outcome, not the mechanism.

        The defect was a ball that left her hands and drifted. Deliberately a
        floor far below the 6 m/s this now produces: the question is whether
        the ball is thrown at all, not whether a number was preserved.
        """
        for movement_id in releasing_drills():
            speed = float(np.linalg.norm(self.release_velocity(movement_id))) / 100.0
            with self.subTest(movement=movement_id):
                self.assertGreater(
                    speed, 3.0, f"{movement_id} releases the ball at {speed:.2f} m/s"
                )

    def test_it_goes_back_toward_the_passer(self) -> None:
        """Speed alone would pass if the ball were fired anywhere at 6 m/s.

        Frame 0 is the passer's hand. The ball holds the near end of the
        flight before release, so on every one of these drills, whose passes
        leave after phase 0, the first frame is where the passer is holding it.
        """
        for movement_id in deriving_releasing_drills():
            result = solve_movement(self.character, movement_id)
            frames = result["possession"].frames
            self.assertEqual(
                frames[0].state,
                "held",
                f"{movement_id} does not start with the passer holding the "
                "ball, so frame 0 is not the passer's hand",
            )
            first = next(n for n, f in enumerate(frames) if f.state == "released")
            passer = np.array(frames[0].centre, dtype=np.float64)
            toward = passer - np.array(frames[first].centre)
            toward[1] = 0.0
            velocity = self.release_velocity(movement_id)
            velocity[1] = 0.0
            cosine = float(
                np.dot(toward, velocity)
                / (np.linalg.norm(toward) * np.linalg.norm(velocity))
            )
            with self.subTest(movement=movement_id):
                self.assertGreater(
                    cosine,
                    0.99,
                    f"{movement_id} sends the ball "
                    f"{math.degrees(math.acos(min(1.0, cosine))):.0f} degrees "
                    "away from the passer who threw it",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class TheSolversCostIsNotTheAnimationTimestep(unittest.TestCase):
    """One name held two quantities and cost two published readings.

    `solveSecondsPerFrame` is `time.perf_counter()` over the frame count. The
    animation timestep is 1 over the track's own `frames_per_second`. Dividing
    an angle by the first produced "degrees per second of computer time" twice,
    and both readings reached documents before they were caught.

    THE SIZES NO LONGER SEPARATE THEM. The ledger said the two "differ by more
    than a factor of two". On this machine today the ratio is 1.19 — the solve
    got faster — so a reader comparing the two numbers cannot tell them apart
    by eye any more. That makes the confusion MORE dangerous, not less.

    What does separate them is that one is a MEASUREMENT OF THE MACHINE and the
    other is a property of the file. The cost changes between two solves of the
    same drill; the timestep cannot. That is asserted here because it holds on
    any machine at any speed.
    """

    @unittest.skipUnless(SOLVER, "needs pymomentum")
    def test_the_old_name_is_gone(self):
        from movement_engine import load_character
        from possession_solve import solve_movement

        result = solve_movement(load_character(), "netball_two_hand_catch_chest")

        self.assertNotIn("secondsPerFrame", result)
        self.assertIn("solveSecondsPerFrame", result)

    @unittest.skipUnless(SOLVER, "needs pymomentum")
    def test_the_cost_moves_between_runs_and_the_timestep_does_not(self):
        from movement_engine import load_character
        from possession_solve import solve_movement

        character = load_character()
        runs = [
            solve_movement(character, "netball_two_hand_catch_chest")
            for _ in range(2)
        ]
        costs = [run["solveSecondsPerFrame"] for run in runs]
        timesteps = [1.0 / run["track"].frames_per_second for run in runs]

        self.assertEqual(timesteps[0], timesteps[1], "the timestep is a file's")
        self.assertNotEqual(
            costs[0],
            costs[1],
            "two solves of one drill returned the same cost to full precision. "
            "Either the field stopped measuring wall-clock time, or this "
            "machine is impossibly steady. Read it before relaxing this.",
        )
