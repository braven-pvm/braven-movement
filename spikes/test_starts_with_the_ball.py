"""A drill that starts with the ball must never show the ball flying to her.

THE FAULT THIS CATCHES IS SILENT AND IT IS EASY TO WRITE. `load_ball` requires
an `arrival`, because for six years every drill in this library was a catch and
every catch has one. A pass has none: the athlete already has the ball. An
author who reads that requirement literally invents an incoming flight to
satisfy it, and nothing complains — the file loads, the drill solves, the
receipt looks healthy, and the athlete spends the first sixth of the movement
in a `flight` state she is never in. It would be drawn.

The honest authoring puts BOTH ball keys where the ball actually is, in her
hands, and names the smallest tidy arrival. Contact then resolves to frame 0
and no flight state is ever computed. Measured across four cases before this
guard was written:

    first key           arrival   contact    ball states
    ahead 1.20          0.02      frame 0    carried, released
    ahead 4.00          0.20      frame 16   FLIGHT, carried, released
    ahead 0.55 (hands)  0.02      frame 0    carried, released
    ahead 0.55 (hands)  0.50      frame 0    carried, released

`netball_chest_pass.ball.json` carries that rule as prose in its
`startsWithTheBallNote`. A COMMENT IS NOT A TEST, so it is also here.

This module needs a solver, because the fault is in the solved state sequence
and not in the file. It therefore SKIPS without one rather than failing to
load. Refer to `test_import_hygiene`.
"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from ball_track import BALL_SUFFIX, MOVEMENT_DIR, load_ball

# Guarded exactly as the other solver tests are: the module must LOAD on a
# runner without pymomentum, and skip there.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    from movement_engine import load_character
    from possession_solve import solve_movement


def authored_launch_movements() -> list[str]:
    """Every movement whose ball file says where its own pass goes.

    Read from the files rather than listed, so a new pass is covered the day
    it is authored and not the day someone remembers to add it here.
    """
    found = []
    for path in sorted(MOVEMENT_DIR.glob("*" + BALL_SUFFIX)):
        if load_ball(path).launch is None:
            continue
        # "<id>.ball.json", and variants are "<id>.<variant>.ball.json".
        stem = path.name[: -len(BALL_SUFFIX)]
        if "." in stem:
            continue
        found.append(stem)
    return found


def flight_frames_before_she_has_it(states: list[str]) -> int | None:
    """How many frames the ball spends flying before she first carries it.

    None where she never carries it at all, which is a dropped ball and a
    different fault with its own report.
    """
    first_carried = next(
        (number for number, state in enumerate(states) if state == "carried"),
        None,
    )
    if first_carried is None:
        return None
    return sum(1 for state in states[:first_carried] if state == "flight")


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class ADrillThatStartsWithTheBallNeverFliesIt(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()

    def states_for(self, movement_id: str) -> list[str]:
        result = solve_movement(self.character, movement_id)
        return [frame["ballState"] for frame in result["measurements"]]

    def test_the_library_has_at_least_one_to_check(self) -> None:
        """Without this the guard below passes by iterating nothing, which is
        the way a guard dies quietly when a file is renamed."""
        self.assertTrue(
            authored_launch_movements(),
            "no movement authors a launch, so the guard below checks nothing",
        )

    def test_no_authored_launch_drill_shows_a_flight_before_she_has_the_ball(
        self,
    ) -> None:
        for movement_id in authored_launch_movements():
            with self.subTest(movement=movement_id):
                flying = flight_frames_before_she_has_it(self.states_for(movement_id))
                self.assertIsNotNone(
                    flying, f"{movement_id}: she never carries the ball at all"
                )
                self.assertEqual(
                    flying,
                    0,
                    f"{movement_id} spends {flying} frames in a flight state "
                    "before she first carries the ball. An invented incoming "
                    "flight is visible: it puts the athlete in a flight state "
                    "she is never in. Put both ball keys where the ball "
                    "actually is, in her hands, and name the smallest tidy "
                    "arrival.",
                )


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheGuardCanFail(unittest.TestCase):
    """A guard is not done until a mutation has failed it.

    The mutation is the exact fault the guard names: a pass whose ball file
    invents an incoming flight to satisfy `arrival`.
    """

    SOURCE = "netball_chest_pass"
    PROBE = "netball_chest_pass_fictional_flight"

    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()

    def setUp(self) -> None:
        self.addCleanup(self.remove_probe)
        for suffix in (".json", ".motion.json", ".technique.json"):
            shutil.copyfile(
                MOVEMENT_DIR / f"{self.SOURCE}{suffix}",
                MOVEMENT_DIR / f"{self.PROBE}{suffix}",
            )
        for suffix in (".json", ".motion.json", ".technique.json"):
            path = MOVEMENT_DIR / f"{self.PROBE}{suffix}"
            body = json.loads(path.read_text(encoding="utf-8"))
            body["movementId"] = self.PROBE
            path.write_text(json.dumps(body), encoding="utf-8")
        # THE MUTATION: an incoming flight that does not happen. The first key
        # is four arm lengths out, where a passer would stand, and she "takes"
        # the ball a fifth of the way through a drill she began holding it.
        honest = json.loads(
            (MOVEMENT_DIR / f"{self.SOURCE}{BALL_SUFFIX}").read_text(encoding="utf-8")
        )
        honest["movementId"] = self.PROBE
        honest["arrival"] = {"atPhase": 0.20}
        honest["keys"] = [
            {"atPhase": 0.0, "name": "invented", "across": 0.0, "up": 0.36, "ahead": 4.0},
            {"atPhase": 0.20, "name": "in_hands", "across": 0.0, "up": 0.12, "ahead": 0.55},
        ]
        (MOVEMENT_DIR / f"{self.PROBE}{BALL_SUFFIX}").write_text(
            json.dumps(honest), encoding="utf-8"
        )

    def remove_probe(self) -> None:
        for path in MOVEMENT_DIR.glob(f"{self.PROBE}*"):
            path.unlink()

    def test_the_mutant_is_picked_up_as_an_authored_launch_drill(self) -> None:
        """Half the guard is the list. A mutation the list misses is not
        caught however good the assertion is."""
        self.assertIn(self.PROBE, authored_launch_movements())

    def test_the_mutant_shows_the_flight_the_guard_refuses(self) -> None:
        result = solve_movement(self.character, self.PROBE)
        states = [frame["ballState"] for frame in result["measurements"]]
        flying = flight_frames_before_she_has_it(states)
        self.assertIsNotNone(flying, "the mutant never carries the ball")
        self.assertGreater(
            flying,
            0,
            "the mutation no longer produces a flight state, so this guard has "
            "stopped testing what it was written for. Either the possession "
            "model changed or the mutation stopped being the fault.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
