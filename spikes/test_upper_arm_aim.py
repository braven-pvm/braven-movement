"""The upper arm aim term rests on two facts about the model. Guard both.

`contact_solve.upper_arm_aim` hardcodes the humerus axis in the shoulder's
local frame, and reads the joint rotations the solver produces. Neither is
obvious from reading the code, and a model change would break them silently:
the athlete would still solve, still grade, and quietly put her elbows back
against her ribs.

These run only where the solver is installed, which is the pixi environment.
"""

from __future__ import annotations

import unittest

import numpy as np

try:
    import pymomentum.geometry as geometry

    import possession_solve
    from contact_solve import UPPER_ARM_AIM_WEIGHT, UPPER_ARM_LOCAL_AXIS
    from movement_engine import load_character

    SOLVER = True
except Exception:  # pragma: no cover - exercised only without the solver
    SOLVER = False


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class UpperArmAimAssumptions(unittest.TestCase):
    def setUp(self) -> None:
        self.character = load_character()
        self.index = {
            name: number
            for number, name in enumerate(self.character.skeleton.joint_names)
        }
        zero = np.zeros(self.character.parameter_transform.size, dtype=np.float32)
        self.rest = np.asarray(
            geometry.model_parameters_to_skeleton_state(self.character, zero)
        ).reshape(-1, 8)

    @staticmethod
    def rotation(quaternion: np.ndarray) -> np.ndarray:
        """The skeleton state stores a quaternion as x, y, z, w.

        Checked against the other order on a posed frame: this one reproduces
        the world bone direction to six decimal places and the other misses by
        up to 1.44.
        """
        x, y, z, w = quaternion
        return np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
            ]
        )

    def test_upper_arm_axis_is_local_x(self) -> None:
        """The humerus points along local X, mirrored on the right.

        This is what `UPPER_ARM_LOCAL_AXIS` asserts. If a model change moves it,
        the aim term points the arm somewhere else entirely and nothing else in
        the suite notices.
        """
        for side, sign in (("l", 1.0), ("r", -1.0)):
            shoulder = self.index[f"{side}_uparm"]
            elbow = self.index[f"{side}_lowarm"]
            world = self.rest[elbow, :3] - self.rest[shoulder, :3]
            world = world / np.linalg.norm(world)
            local = self.rotation(self.rest[shoulder, 3:7]).T @ world
            wanted = sign * np.asarray(UPPER_ARM_LOCAL_AXIS, dtype=np.float64)
            np.testing.assert_allclose(local, wanted, atol=5e-3)

    def test_the_shoulders_are_mirrored(self) -> None:
        """Left is positive X. Getting this backwards crosses the arms."""
        left = self.rest[self.index["l_uparm"], 0]
        right = self.rest[self.index["r_uparm"], 0]
        self.assertGreater(left, 0.0)
        self.assertLess(right, 0.0)
        self.assertAlmostEqual(left, -right, places=3)


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheElbowsStayOut(unittest.TestCase):
    """The outcome, not the mechanism.

    Everything above guards a fact about the model. None of it notices if the
    term is switched off: set the weight to zero and the whole suite still
    passes while the elbows quietly return to the ribs, which is the defect
    this work exists to fix. A solve costs about a second, and that is worth
    paying to catch a silent revert.
    """

    def test_the_term_carries_weight(self) -> None:
        self.assertGreater(
            UPPER_ARM_AIM_WEIGHT,
            0.0,
            "the aim term is switched off, so the elbows are back at the ribs",
        )

    def test_a_chest_catch_holds_its_elbows_off_the_ribs(self) -> None:
        """This drill measured 14.0 cm between the elbows before the aim term.

        It is the one that moved furthest, so it is the one that shows a revert
        soonest. The threshold is deliberately far below the 39.6 cm it now
        makes: this asks whether the arms are held out at all, not whether a
        particular number was preserved. Pinning the number would turn a real
        check into a change detector.
        """
        character = load_character()
        index = {
            name: number
            for number, name in enumerate(character.skeleton.joint_names)
        }
        result = possession_solve.solve_movement(
            character, "netball_two_hand_catch_chest"
        )
        points = result["points"][result["possession"].contact_frame]
        apart = float(
            np.linalg.norm(
                points[index["l_lowarm"]] - points[index["r_lowarm"]]
            )
        )
        self.assertGreater(apart, 25.0, f"elbows only {apart:.1f} cm apart")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
