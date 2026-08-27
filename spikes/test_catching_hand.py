"""The hand that is catching the ball must go out to meet it.

`possession_solve.py` sent BOTH hands to the waiting position before contact on
any drill that joins a second hand, because the test above that line asks only
whether she is holding the ball yet and never which hand is doing the
catching. So the catching hand waited too, and then arrived on the ball in one
frame: 19.9 cm of wrist travel on `netball_hooks_outside_hand`, 17.0 cm on
`netball_one_hand_snatch_to_other_hand`, against 1.7 to 4.2 cm on every drill
without a second hand. The upper arm swung 48.1 degrees following it, which was
the largest single-frame step anywhere in the library.

The comment directly above that line already said the catching hand goes out to
meet the ball. The code did not do what the comment said, and no test asked.

The check invents no number. It measures the drills that never had the defect
and requires the drills that did to behave no worse than the worst of them.
Pinning a centimetre figure would be a change detector; this asks whether the
catching hand reaches at all.

These run only where the solver is installed, which is the pixi environment.
A green system-python run says nothing about them.
"""

from __future__ import annotations

import unittest

import numpy as np

# Only a genuinely absent solver may skip. Catching every exception here would
# swallow a break in the code under test and skip the guard in silence.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    from ball_track import has_ball
    from movement_engine import library, load_character
    from possession_solve import solve_movement
    from technique import has_technique, load_technique, technique_path


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheCatchingHandReachesForTheBall(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()
        cls.index = {
            name: number
            for number, name in enumerate(cls.character.skeleton.joint_names)
        }
        cls.joins: dict[str, float] = {}
        cls.plain: dict[str, float] = {}
        for movement_id in library():
            if not (has_ball(movement_id) and has_technique(movement_id)):
                continue
            method = load_technique(technique_path(movement_id))
            if not method.possession_ready:
                continue
            result = solve_movement(cls.character, movement_id)
            points = result["points"]
            contact = result["possession"].contact_frame
            if contact is None or contact < 1:
                continue
            worst = 0.0
            for side in method.sides:
                wrist = cls.index[f"{side}_wrist"]
                worst = max(
                    worst,
                    float(
                        np.linalg.norm(points[contact][wrist] - points[contact - 1][wrist])
                    ),
                )
            target = cls.joins if method.second_hand_phase is not None else cls.plain
            target[movement_id] = worst

    def test_the_library_has_both_kinds_of_drill(self) -> None:
        """Guards the guard. The comparison below is empty without both."""
        self.assertTrue(self.joins, "no drill joins a second hand")
        self.assertTrue(self.plain, "no drill catches with its hands already out")

    def test_a_joining_drill_does_not_arrive_in_one_frame(self) -> None:
        """The rule, measured against the library rather than against a number.

        A drill that joins a second hand must move its catching wrist across
        contact no more than the worst drill that never had the defect. The
        allowance is generous on purpose: the question is whether the hand
        reached, not whether a figure was preserved.
        """
        allowed = max(self.plain.values())
        for movement_id, step in sorted(self.joins.items()):
            with self.subTest(movement=movement_id):
                self.assertLessEqual(
                    step,
                    allowed,
                    f"{movement_id} moves its catching wrist {step:.2f} cm in "
                    f"the frame it takes the ball, against {allowed:.2f} cm on "
                    "the worst drill whose hands were already reaching. The "
                    "catching hand is waiting instead of going out to meet it.",
                )

    def test_the_catching_hand_is_already_closing_before_contact(self) -> None:
        """The same fault stated the other way round, so that a change which
        hides the step by moving the ball instead cannot pass quietly."""
        for movement_id in sorted(self.joins):
            method = load_technique(technique_path(movement_id))
            result = solve_movement(self.character, movement_id)
            contact = result["possession"].contact_frame
            frames = result["possession"].frames
            points = result["points"]
            for side in method.sides:
                wrist = self.index[f"{side}_wrist"]
                before = float(
                    np.linalg.norm(
                        points[contact - 1][wrist] - np.array(frames[contact - 1].centre)
                    )
                )
                at = float(
                    np.linalg.norm(
                        points[contact][wrist] - np.array(frames[contact].centre)
                    )
                )
                with self.subTest(movement=movement_id, side=side):
                    self.assertLess(
                        before,
                        at * 2.0,
                        f"{movement_id}: the {side} wrist is {before:.1f} cm "
                        f"from the ball the frame before it takes it and "
                        f"{at:.1f} cm on the frame it does, so it is not "
                        "closing on the ball, it is jumping to it.",
                    )


    def test_the_free_hand_still_waits(self) -> None:
        """The other half of the same rule, and the half a fix can break.

        Sending BOTH hands out to meet the ball also removes the one-frame
        step, and it is wrong for the reason the comment gives: on a one hand
        drill the free hand is not catching anything yet. Without this clause
        that mutation passes.

        Stated as a comparison rather than a distance, so it holds whatever the
        drill or the body: while she is still reaching, the hand that is not
        catching must be further from the ball than the hand that is.
        """
        for movement_id in sorted(self.joins):
            method = load_technique(technique_path(movement_id))
            result = solve_movement(self.character, movement_id)
            contact = result["possession"].contact_frame
            frames = result["possession"].frames
            points = result["points"]
            free = [
                side for side in ("l", "r") if side not in method.sides
            ]
            self.assertTrue(free, f"{movement_id} has no free hand to check")
            # A little before contact, while she is still reaching for it.
            number = max(0, contact - 3)
            centre = np.array(frames[number].centre)
            catching = min(
                float(np.linalg.norm(points[number][self.index[f"{s}_wrist"]] - centre))
                for s in method.sides
            )
            for side in free:
                waiting = float(
                    np.linalg.norm(
                        points[number][self.index[f"{side}_wrist"]] - centre
                    )
                )
                with self.subTest(movement=movement_id, side=side):
                    self.assertGreater(
                        waiting,
                        catching,
                        f"{movement_id}: the {side} hand is {waiting:.1f} cm "
                        f"from the ball and the catching hand is "
                        f"{catching:.1f} cm, so the free hand is reaching for "
                        "a ball this drill does not give it yet.",
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
