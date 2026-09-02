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

    def test_the_apex_is_the_closed_form_and_not_a_sampled_maximum(self):
        """Guards against anyone replacing this with a scan of the frames.

        The chest pass's ball leaves at 142.4 cm rising at 71.5 cm/s, so it
        peaks 2.6 cm higher, 0.07 s later — between two frames at 60 fps. A
        sampled maximum cannot see that peak at all.
        """
        found = self.apex("netball_chest_pass")
        start = found["releaseHeightCm"]
        rise = found["verticalSpeedCmPerSecond"]

        self.assertAlmostEqual(
            found["apexHeightCm"], start + rise * rise / (2 * GRAVITY_CM), places=1
        )
        self.assertAlmostEqual(found["apexSeconds"], rise / GRAVITY_CM, places=3)
        self.assertLess(
            found["apexSeconds"],
            1.0 / 60.0 * 5,
            "the peak falls within a few frames of the release, so a frame scan "
            "would report the release height and call it the peak",
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

    def test_no_shipped_pass_goes_over_a_goalpost(self):
        """A netball goalpost is 305 cm. Recorded so that the day one does,
        this says so rather than a person noticing."""
        for name in ("netball_chest_pass", "netball_overhead_pass"):
            self.assertLess(self.apex(name)["apexHeightCm"], 305.0, name)


if __name__ == "__main__":
    unittest.main()
