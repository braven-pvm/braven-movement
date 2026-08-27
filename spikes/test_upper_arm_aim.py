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

    from contact_solve import UPPER_ARM_LOCAL_AXIS
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
