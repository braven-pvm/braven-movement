"""Every ball a drill has reaches the library, not only the plain one.

`netball_two_hand_snatch_pull_in` has four balls. Three of them solved, graded
and receipted correctly and reached NOTHING until 2026-09-02: `build_library`
did not contain the word `variant`, so the library and its index described one
ball and said nothing about the others.

A variant is graded against the SAME checkpoints, which is a measurement and
not a convenience. Refer to `build_one`'s docstring and to "Three solvable
balls are invisible to the library" in docs/KNOWN_ISSUES.md.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ball_track import ball_variants  # noqa: E402

try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

WITH_VARIANTS = "netball_two_hand_snatch_pull_in"


class BallsAreFoundWithoutTheSolver(unittest.TestCase):
    def test_the_drill_that_found_this_still_has_its_four_balls(self):
        """Guards the guard. Every claim below is empty on a one-ball drill."""
        found = ball_variants(WITH_VARIANTS)

        self.assertEqual(found, [None, "high", "low", "wide"])

    def test_a_one_ball_drill_reads_as_one_ball(self):
        self.assertEqual(ball_variants("netball_chest_pass"), [None])


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class AVariantIsReceiptedUnderTheSameCheckpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from build_library import build_one
        from movement_engine import load_character

        character = load_character()
        cls.plain = build_one(character, WITH_VARIANTS, None)
        cls.high = build_one(character, WITH_VARIANTS, "high")

    def test_a_receipt_names_the_ball_it_was_solved_against(self):
        """Without this a variant receipt is indistinguishable from the plain
        one, which is how three of them went unnoticed."""
        self.assertIsNone(self.plain["variant"])
        self.assertEqual(self.high["variant"], "high")

    def test_both_are_graded_against_the_same_checkpoints(self):
        """THE RULING THIS IMPLEMENTS. No per-variant bands.

        Eight of the eleven move by 0.02 degrees or less across a ball that
        moves 0.78 arm lengths in height, so a separate band would be a number
        invented for a difference that is not there.
        """
        plain = self.plain["coaching"]["phases"]
        high = self.high["coaching"]["phases"]

        self.assertEqual(sorted(plain), sorted(high))
        for phase, rows in plain.items():
            self.assertEqual(
                [(row["measure"], tuple(row["band"])) for row in rows],
                [(row["measure"], tuple(row["band"])) for row in high[phase]],
                phase,
            )

    def test_the_ball_moves_the_contact_and_leaves_the_rest_alone(self):
        """The one thing a variant tests, asserted rather than described."""

        def reading(receipt, phase, measure):
            rows = receipt["coaching"]["phases"][phase]
            return next(row["measured"] for row in rows if row["measure"] == measure)

        moved = abs(
            reading(self.plain, "contact", "leftShoulderElevationDegrees")
            - reading(self.high, "contact", "leftShoulderElevationDegrees")
        )
        held = abs(
            reading(self.plain, "ready", "leftKneeFlexionDegrees")
            - reading(self.high, "ready", "leftKneeFlexionDegrees")
        )

        self.assertGreater(moved, 5.0, "the high ball must move the contact")
        self.assertLess(held, 0.5, "and must not move the pose before it")


if __name__ == "__main__":
    unittest.main()
