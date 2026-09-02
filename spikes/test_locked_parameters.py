"""The solver may not move a parameter the model has locked shut.

A parameter whose own range is zero wide is locked: the body says it must be
exactly zero. The limit term is SOFT — it pulls a parameter towards its range
rather than holding it there — so a locked parameter left enabled sits wherever
the other terms drag it, and the size of the breach is simply the size of the
pull.

Four were in that state: `l_clavicle_rx`, `r_clavicle_rx`, `l_foot_lean1` and
`r_foot_lean1`. On `netball_hooks_outside_hand`, the turned drill whose free arm
pulls hardest, the left clavicle sat 2.34 degrees outside a range of ZERO on all
98 of its frames. Every other drill pulled the same parameter 0.06 to 0.10
degrees and stayed under the reporting tolerance, which is why it read as one
drill's problem for weeks rather than as a rule being broken everywhere.

Nothing here is tuned. Excluding a locked parameter REMOVES freedom; it does not
add a constraint, and it touches no weight.
"""

from __future__ import annotations

import unittest

try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class NoLockedParameterIsHandedToTheSolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from athlete import minmax_limits
        from movement_engine import ZERO_WIDTH_RADIANS, enabled_parameters, load_character

        cls.zero_width = ZERO_WIDTH_RADIANS
        character = load_character()
        cls.names = list(character.parameter_transform.names)
        cls.limits = minmax_limits(character)
        cls.enabled = enabled_parameters(character)
        cls.locked = {
            name
            for name, (low, high) in cls.limits.items()
            if abs(high - low) < ZERO_WIDTH_RADIANS
        }

    def test_the_model_actually_locks_some_parameters(self) -> None:
        """THE ANTI-HOLLOW CLAUSE. If the model locked nothing, the rule below
        would exclude nothing and pass on a body it had never read."""
        self.assertTrue(
            self.locked,
            "no parameter has a zero-width range, so the rule under test "
            "excludes nothing and this file is checking a body it did not read",
        )

    def test_no_enabled_parameter_has_a_zero_width_range(self) -> None:
        """The rule."""
        handed_out = sorted(
            name
            for number, name in enumerate(self.names)
            if self.enabled[number] and name in self.locked
        )
        self.assertEqual(
            handed_out, [],
            f"{handed_out} have a range of zero and are enabled for the solver. "
            "The limit term is soft, so each one will sit wherever the other "
            "terms pull it and the breach will be as large as the pull.",
        )

    def test_the_solver_still_has_the_joints_it_needs(self) -> None:
        """The other half. A rule that disabled everything would satisfy the
        case above and leave nothing to solve with."""
        enabled = {n for i, n in enumerate(self.names) if self.enabled[i]}
        self.assertGreater(len(enabled), 40, f"only {len(enabled)} parameters enabled")
        for needed in ("uparm", "lowarm", "wrist", "clavicle", "knee", "root"):
            with self.subTest(joint=needed):
                self.assertTrue(
                    any(needed in name for name in enabled),
                    f"nothing containing {needed!r} is enabled, so the solver "
                    "cannot move that joint at all",
                )

    def test_the_clavicles_keep_the_axes_they_do_have(self) -> None:
        """Only the locked axis goes. The clavicle still rotates on the two
        axes the model gives it, so this removes freedom that does not exist
        rather than freedom the movement uses."""
        enabled = {n for i, n in enumerate(self.names) if self.enabled[i]}
        for side in ("l", "r"):
            with self.subTest(side=side):
                self.assertNotIn(f"{side}_clavicle_rx", enabled)
                self.assertIn(f"{side}_clavicle_ry", enabled)
                self.assertIn(f"{side}_clavicle_rz", enabled)


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheLibraryStaysInsideItsOwnJointLimits(unittest.TestCase):
    """The statement on the solved poses rather than on the enabled set.

    The case above is about which parameters are handed out. This one is about
    what the athlete actually does with them, and it is the one that would have
    caught the original fault: `check_joint_limits` reported it for weeks and
    nothing in the suite read that report.
    """

    def test_no_solved_pose_leaves_a_joint_outside_its_range(self) -> None:
        import numpy as np

        from check_joint_limits import TOLERANCE_DEGREES, minmax_limits, overshoots
        from movement_engine import library, load_character
        from possession_solve import solve_movement
        from ball_track import has_ball
        from technique import has_technique, load_technique, technique_path

        character = load_character()
        limits = minmax_limits(character)
        drills = [
            m for m in sorted(library())
            if has_ball(m) and has_technique(m)
            and load_technique(technique_path(m)).possession_ready
        ]
        self.assertGreaterEqual(len(drills), 8, "the library was not read")

        for movement_id in drills:
            motion = np.asarray(solve_movement(character, movement_id)["motion"])
            worst, where, over = 0.0, "-", 0
            for parameters in motion:
                found = overshoots(character, parameters, limits)
                past = max(found.values(), default=0.0)
                if past > TOLERANCE_DEGREES:
                    over += 1
                if past > worst:
                    worst, where = past, max(found, key=found.get)
            with self.subTest(movement=movement_id):
                self.assertEqual(
                    over, 0,
                    f"{movement_id}: {over} of {len(motion)} frames put a joint "
                    f"more than {TOLERANCE_DEGREES} degrees past its own limit, "
                    f"worst {worst:.4f} on {where}",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
