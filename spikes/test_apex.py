"""How high the outgoing ball gets, computed from the launch.

The engine solved the outgoing velocity and threw it away: it was a local in
`possess`, used to walk the ball forward and then discarded. So nothing could
ask where the ball ENDS UP, and every question about the library's one ball
speed has been answered by hand arithmetic outside the engine.

The apex must come from the launch and not from the frames. Every clip in this
library ends while its ball is still in the air, so a peak read off the drawn
frames would be the peak of the part that happens to be drawn.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ball_track import GRAVITY_CM  # noqa: E402

try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheApexComesFromTheLaunch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from movement_engine import load_character
        from possession_solve import solve_movement

        character = load_character()
        cls.solve = {
            name: solve_movement(character, name)
            for name in (
                "netball_chest_pass",
                "netball_overhead_pass",
                "netball_hooks_jump_pull_in",
                "netball_two_hand_snatch_pull_in",
            )
        }

    def apex(self, name):
        return self.solve[name]["possession"].apex()

    def test_a_drill_that_never_lets_go_has_no_apex(self):
        """`None` rather than zero, because a zero would read as a ball that
        goes nowhere.

        THE DRILL HAD TO BE CHOSEN CAREFULLY. A first version used
        `netball_two_hand_catch_chest` on the assumption that a catch keeps the
        ball. It does not: six of the ten drills return it to the passer, and
        that one launches at 108 cm/s. `two_hand_snatch_pull_in` pulls the ball
        in and holds it, which is what this needs.
        """
        catch = self.solve["netball_two_hand_snatch_pull_in"]["possession"]

        self.assertIsNone(catch.launch_velocity)
        self.assertIsNone(catch.apex())

    def test_a_pass_publishes_the_launch_the_engine_solved(self):
        """The velocity used to be discarded. This is the whole fix."""
        passing = self.solve["netball_chest_pass"]["possession"]

        self.assertIsNotNone(passing.launch_from)
        self.assertIsNotNone(passing.launch_velocity)
        self.assertAlmostEqual(
            float(np.linalg.norm(passing.launch_velocity[[0, 2]])), 600.0, places=3
        )

    def test_the_apex_is_the_closed_form(self):
        for name in ("netball_chest_pass", "netball_hooks_jump_pull_in"):
            found = self.apex(name)
            start = found["releaseHeightCm"]
            rise = found["verticalSpeedCmPerSecond"]

            self.assertAlmostEqual(
                found["apexHeightCm"],
                start + rise * rise / (2 * GRAVITY_CM),
                places=1,
                msg=name,
            )
            self.assertAlmostEqual(
                found["apexSeconds"], rise / GRAVITY_CM, places=3, msg=name
            )

    def test_a_scan_of_the_drawn_frames_would_be_wrong_and_by_how_much(self):
        """The reason the closed form is used, asserted on the drill it bites.

        A FIRST VERSION OF THIS TEST COULD NOT DETECT A FRAME SCAN. It asserted
        on `netball_chest_pass`, whose ball peaks 0.07 s after release — and a
        scan of that drill reads 145.02 against the closed form's 145.04. Two
        hundredths of a centimetre. A frame-scanning `apex()` passed every
        assertion in the file.

        `netball_hooks_jump_pull_in` is where it bites: its ball is STILL
        RISING at the last drawn frame, so the highest frame is 1.29 cm below
        the real peak and no number of frames would fix it. The clip simply
        ends before the ball does.
        """
        found = self.apex("netball_hooks_jump_pull_in")
        possession = self.solve["netball_hooks_jump_pull_in"]["possession"]
        centres = np.asarray(possession.centres())
        release = [f.number for f in possession.frames if f.state == "released"][0]
        flown = centres[release:]

        self.assertGreater(
            flown[-1][1], flown[-2][1], "the ball must still be rising at the end"
        )
        self.assertGreater(
            found["apexHeightCm"] - float(np.max(flown[:, 1])),
            1.0,
            "a scan of the drawn frames must be wrong by more than a centimetre "
            "here, or this test cannot tell a closed form from a scan",
        )

    def test_a_ball_thrown_downward_peaks_where_it_leaves(self):
        """`netball_overhead_pass` releases 54 cm ABOVE its target — 180.4 cm
        against 126.32 — so the engine launches it downward at 39 cm/s. Its
        highest point is the release, and the arithmetic must not return a
        negative rise."""
        found = self.apex("netball_overhead_pass")

        self.assertLess(found["verticalSpeedCmPerSecond"], 0.0)
        self.assertEqual(found["apexHeightCm"], found["releaseHeightCm"])
        self.assertEqual(found["apexSeconds"], 0.0)

    def test_the_launch_aims_at_the_trunk_PLACEMENT_not_the_solved_chest(self):
        """Two chest heights sit a millimetre apart and only one is read.

        `stance_frame` is built from `trunk_frame`'s placement of the REST
        `c_spine3` — 126.403 on both passes. The SOLVED frame-0 `c_spine3` is
        126.3242 and 126.3170, because the solver moves the chest 0.08 cm over
        the solve, and nothing in the launch path reads it.

        An earlier ledger entry quoted the solved one. The error survived being
        checked, because it was checked by INVERTING the engine's velocity —
        and that inversion computes its horizontal run from the same wrong
        anchor, so the mistake cancelled itself. This reads the placement
        directly and requires the wrong quantity to give a DIFFERENT answer,
        which is the half an inversion could not supply.
        """
        import finger_wrap
        import motion_track
        import movement_engine
        from ball_track import ball_path, load_ball, solve_launch
        from possession_solve import stance_frame
        from technique import load_technique, technique_path

        character = movement_engine.load_character()
        index = {n: i for i, n in enumerate(character.skeleton.joint_names)}

        for name in ("netball_chest_pass", "netball_overhead_pass"):
            solved = self.solve[name]
            track = solved["track"]
            method = load_technique(technique_path(name))
            zeros = np.zeros(len(character.parameter_transform.names))
            rest = finger_wrap.spread_fingers(character, zeros, method.every_side)
            rest_positions = movement_engine.joint_positions(character, rest)
            arm = motion_track.arm_length(rest_positions, index)
            placed = movement_engine.trunk_frame(
                track, 0.0, rest_positions, index, arm, track.turn_at(0.0)
            )
            stance = stance_frame(placed.chest, arm, track.turn_at(0.0))
            target = np.asarray(
                stance.place(load_ball(ball_path(name)).launch.target), dtype=float
            )
            release = np.asarray(solved["possession"].launch_from, dtype=float)
            engine = float(solved["possession"].launch_velocity[1])

            self.assertAlmostEqual(float(target[1]), 126.403, places=2, msg=name)
            self.assertAlmostEqual(
                float(solve_launch(release, target, 600.0)[1][1]),
                engine,
                places=4,
                msg=f"{name}: the placement must reproduce the engine exactly",
            )

            # THE HALF THAT MAKES THIS A TEST. The solved chest is a millimetre
            # away, so an assertion that only checks the right answer would
            # pass on the wrong one too.
            wrong = target.copy()
            wrong[1] = float(solved["points"][0][index["c_spine3"]][1])
            self.assertNotAlmostEqual(
                float(solve_launch(release, wrong, 600.0)[1][1]),
                engine,
                places=4,
                msg=f"{name}: the solved chest must NOT reproduce the engine",
            )

    def test_no_shipped_pass_goes_over_a_goalpost(self):
        """A netball goalpost is 305 cm. Recorded so that the day one does,
        this says so rather than a person noticing."""
        for name in ("netball_chest_pass", "netball_overhead_pass"):
            self.assertLess(self.apex(name)["apexHeightCm"], 305.0, name)


if __name__ == "__main__":
    unittest.main()
