"""The two hands open as mirror images, and the hand actually opens.

`spread_fingers` negated every value on the right until 2026-09-01, on the
stated belief that the two hands fan in opposite directions. The rig disagrees:
the same value on both hands mirrors, and the negation broke the mirror by up
to 80.21 degrees, collapsed the right hand's fan from 14.37 cm to 1.75 and put
its fingertips out of anatomical order. Six pieces of evidence are in
`docs/HAND_MIRROR_EVIDENCE.md`; Marius ruled the fix ships.

This is the regression guard for that fix, and it is written on the RIG rather
than on the code. A test that read the sign out of `SPREAD` would pass for a
function that never applied it. These cases place the hands and measure them.

THE TRAP IN THIS FILE IS THE REST POSE. The rig is symmetric about x = 0 before
anything is set, so a hand that never opened mirrors PERFECTLY and fans
identically on both sides. Every mirror assertion below would therefore pass on
a `spread_fingers` that returned its input untouched. The case that stops that
is `test_the_hand_actually_opened`, and it is not optional decoration: without
it this whole file is satisfied by a function with its body deleted.
"""

from __future__ import annotations

import unittest

try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

# How far the two hands may sit from being reflections of each other. The rest
# pose is symmetric to 0.00005 cm, and the opened pose sets identical values on
# both sides, so anything above this is a real asymmetry rather than arithmetic.
MIRROR_TOLERANCE_CM = 0.01
# Index tip to pinky tip, with the hand open. Measured 14.37 cm on both hands
# after the fix, and 1.75 cm on the right before it.
OPEN_FAN_FLOOR_CM = 12.0


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheHandsOpenAsMirrorImages(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import numpy as np

        from finger_wrap import FINGERS, spread_fingers
        from movement_engine import joint_positions, load_character

        cls.np = np
        cls.fingers = FINGERS
        character = load_character()
        cls.index = {
            name: number
            for number, name in enumerate(character.skeleton.joint_names)
        }
        rest = np.zeros(character.parameter_transform.size, dtype=np.float32)
        cls.rest_points = joint_positions(character, rest)
        cls.open_points = joint_positions(
            character, spread_fingers(character, rest, ("l", "r"))
        )

    def tips(self, points, side: str):
        return [points[self.index[f"{side}_{finger}3"]] for finger in self.fingers]

    def fan_cm(self, points, side: str) -> float:
        found = self.tips(points, side)
        return float(self.np.linalg.norm(found[0] - found[-1]))

    def test_the_hand_actually_opened(self) -> None:
        """THE ANTI-HOLLOW CLAUSE, and the reason it has to be here.

        The rig is symmetric before anything is set. A `spread_fingers` that
        returned its input unchanged would mirror perfectly and fan equally,
        and every other case in this file would pass while the hands stayed
        shut. So the opened hand is compared against the rest pose first.
        """
        for side in ("l", "r"):
            with self.subTest(side=side):
                shut = self.fan_cm(self.rest_points, side)
                opened = self.fan_cm(self.open_points, side)
                self.assertGreater(
                    opened, shut + 1.0,
                    f"the {side} hand fans {opened:.2f} cm open against "
                    f"{shut:.2f} cm at rest, so it did not open and every "
                    "mirror check here passes on the rig's own symmetry",
                )
                self.assertGreater(opened, OPEN_FAN_FLOOR_CM)

    def test_both_hands_fan_by_the_same_amount(self) -> None:
        """The headline number. 14.37 cm on both after the fix; the right read
        1.75 cm before it, which is a hand that is not open."""
        left = self.fan_cm(self.open_points, "l")
        right = self.fan_cm(self.open_points, "r")
        self.assertAlmostEqual(
            left, right, delta=MIRROR_TOLERANCE_CM,
            msg=f"the left hand fans {left:.2f} cm and the right {right:.2f}. "
                "They are the same hand reflected and must agree.",
        )

    def test_every_fingertip_is_the_reflection_of_its_opposite(self) -> None:
        """Stronger than the fan, which is one distance and could agree by
        accident. Left is +X, so a mirrored right tip negates x and matches."""
        for finger, left, right in zip(
            self.fingers,
            self.tips(self.open_points, "l"),
            self.tips(self.open_points, "r"),
        ):
            with self.subTest(finger=finger):
                reflected = self.np.array([-right[0], right[1], right[2]])
                gap = float(self.np.linalg.norm(left - reflected))
                self.assertLess(
                    gap, MIRROR_TOLERANCE_CM,
                    f"the {finger} tips sit {gap:.4f} cm apart once the right "
                    "is reflected, so the hands are not mirror images",
                )


# THE FINGERTIP ORDER IS DELIBERATELY NOT ASSERTED HERE, and this note exists
# so nobody adds it back.
#
# `docs/HAND_MIRROR_EVIDENCE.md` piece 2 reads the four tips across the hand
# and shows the shipped right hand out of order — -42.99, -43.65, -43.27,
# -42.78 — against a rising left. Those figures come from a SOLVED CONTACT
# POSE. At the rest pose with the spread applied, which is what this file
# measures, the tips run 58.85, 62.75, 63.42, 61.28 on the LEFT hand: not
# monotonic, and the left hand is the one that was never in question.
#
# A first version of this file asserted monotonic order and failed on both
# hands, the correct one included. The claim is true where it was measured and
# false here, so asserting it here would be asserting something false about a
# hand that is right. The per-fingertip reflection above is the stronger guard
# in any case: it compares every tip rather than their ordering, and it catches
# the negation returning.


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
