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
from technique import has_technique, load_technique, technique_path

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


def possession_movements() -> list[str]:
    """Every drill the possession model solves, read from the files.

    Deliberately wider than `authored_launch_movements`. The guard below is
    about drills that FORGOT a launch, so it cannot start from the ones that
    have one.
    """
    found = []
    for path in sorted(MOVEMENT_DIR.glob("*" + BALL_SUFFIX)):
        stem = path.name[: -len(BALL_SUFFIX)]
        if "." in stem:  # a variant ball, not its own movement
            continue
        if not has_technique(stem):
            continue
        if not load_technique(technique_path(stem)).possession_ready:
            continue
        found.append(stem)
    return found


def ever_in_flight(states: list[str]) -> bool:
    """Whether the ball is ever a thing in the air in this drill.

    READ FROM THE SOLVE, not computed from the file, and the difference is not
    pedantry. `BallTrack.state_at` calls a phase "flight" whenever it lies
    between release and arrival, so on the chest pass, whose arrival is 0.02
    over 96 frames, the TRACK calls frames 0 and 1 flight. The SOLVE calls
    neither, because contact resolves to frame 0 and possession transfers
    there. The solved state is the thing the drill actually lacks, and the
    arithmetic on the file disagrees with it.
    """
    return "flight" in states


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
class ADrillWithNoFlightMustSayWhereItsPassGoes(unittest.TestCase):
    """The other half, and the other failure mode.

    The guard above catches a pass that INVENTS a flight. This one catches a
    pass that is authored honestly and then forgets to say where the ball goes.
    Without a launch the engine DERIVES the throw from the incoming flight, and
    a drill with no incoming flight has nothing to derive from. Both outcomes
    are silent and both are wrong, measured on the chest pass's own geometry:

        honest keys, both in her hands, no launch -> [0, 0, 0], 0.00 m/s.
            The ball stops dead in her hands and hangs in mid air.
        the same keys nudged 0.05 apart, no launch -> 0.84 m/s backwards.
            A distance that small over 0.02 of a phase is not a throw.

    Against the 6.00 m/s the library authors its passes at. Neither raises.

    This class needs a solver and therefore SKIPS on the hosted runner. That is
    stated rather than left implied: on CI these two rules are unchecked, and
    the file-level half of the question cannot stand in for them, because
    `ever_in_flight` explains why the arithmetic on the file disagrees with the
    solve on exactly the drill this guards.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()

    def test_the_library_has_both_kinds(self) -> None:
        """The anti-hollow clause. A rule about drills with no flight is a
        comment while every drill has one, and it would pass forever."""
        movements = possession_movements()
        self.assertTrue(movements, "no drill is solved by the possession model")
        states = {
            movement_id: [
                frame["ballState"]
                for frame in solve_movement(self.character, movement_id)["measurements"]
            ]
            for movement_id in movements
        }
        without = [m for m, s in states.items() if not ever_in_flight(s)]
        self.assertTrue(
            without,
            "every drill has a flight, so the rule below reaches nothing. If "
            "the pass family is gone, delete this class; if a pass is present "
            "and its ball is flying, that is the other guard's fault.",
        )
        self.assertTrue(
            [m for m, s in states.items() if ever_in_flight(s)],
            "no drill has a flight at all, which is not a library of catches",
        )

    def test_a_drill_whose_ball_never_flies_authors_its_launch(self) -> None:
        for movement_id in possession_movements():
            states = [
                frame["ballState"]
                for frame in solve_movement(self.character, movement_id)["measurements"]
            ]
            if ever_in_flight(states):
                continue
            with self.subTest(movement=movement_id):
                self.assertIsNotNone(
                    load_ball(MOVEMENT_DIR / f"{movement_id}{BALL_SUFFIX}").launch,
                    f"{movement_id}'s ball never enters a flight state, so it "
                    "starts with the ball, and it does not author a launch. "
                    "The engine will derive the throw from an incoming flight "
                    "that never happened: the ball stops dead in her hands, or "
                    "leaves at a speed the gap between two keys invented. "
                    "Author a launch with a target and a speed.",
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

    def test_a_pass_with_its_launch_removed_is_caught(self) -> None:
        """The mutation for the SECOND guard, and the fixture is the real
        file with one key deleted.

        `setUp` has already planted a mutant, so this rewrites its ball with
        the honest keys and no `launch`. That is a drill whose ball never
        flies and which does not say where its pass goes, which is exactly
        what `test_a_drill_whose_ball_never_flies_authors_its_launch` refuses.
        """
        honest = json.loads(
            (MOVEMENT_DIR / f"{self.SOURCE}{BALL_SUFFIX}").read_text(encoding="utf-8")
        )
        honest["movementId"] = self.PROBE
        del honest["launch"]
        (MOVEMENT_DIR / f"{self.PROBE}{BALL_SUFFIX}").write_text(
            json.dumps(honest), encoding="utf-8"
        )

        self.assertIn(self.PROBE, possession_movements())
        states = [
            frame["ballState"]
            for frame in solve_movement(self.character, self.PROBE)["measurements"]
        ]
        self.assertFalse(
            ever_in_flight(states),
            "the fixture's ball flies, so it is not the case this guards",
        )
        self.assertIsNone(
            load_ball(MOVEMENT_DIR / f"{self.PROBE}{BALL_SUFFIX}").launch,
            "the fixture still authors a launch, so it cannot fail the guard",
        )

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
