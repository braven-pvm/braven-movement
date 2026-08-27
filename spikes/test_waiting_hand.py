"""A waiting hand must be able to reach where it is asked to wait.

`toward` places the waiting point at a fixed distance from the MIDPOINT of the
shoulders, and its docstring says "no further out than she reaches". For a
square athlete that is true, because both shoulders are the same distance from
the middle. For a TURNED athlete it is false: on `netball_hooks_outside_hand`,
which starts facing away at -44 degrees, a point 50.8 cm from the midpoint sat
66.4 cm from her left shoulder and 39.1 cm from her right.

She waited with that arm locked out at 0.93 to 0.999 of full extension, where
every other arm in the library waits between 0.33 and 0.89. Worse, a hand
target past full reach has no elbow triangle, so `elbow_poles` skipped that arm
entirely: the elbow was unconstrained for 41 frames, drifted 46 degrees from
where the pole wanted it, and was corrected all at once when the target came
inside her reach. That single frame was the largest step in the library.

The check invents no number. It measures what the library's own arms do while
they wait and requires every arm to stay inside that. A drill that locks an
elbow out fails against its own neighbours rather than against a threshold
somebody chose.

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
class NoHandWaitsPastFullStretch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        character = load_character()
        index = {
            name: number
            for number, name in enumerate(character.skeleton.joint_names)
        }
        cls.reaching: dict[tuple[str, str], float] = {}
        cls.waiting: dict[tuple[str, str], float] = {}
        cls.turned: dict[str, float] = {}
        for movement_id in library():
            if not (has_ball(movement_id) and has_technique(movement_id)):
                continue
            method = load_technique(technique_path(movement_id))
            if not method.possession_ready:
                continue
            result = solve_movement(character, movement_id)
            points = result["points"]
            contact = result["possession"].contact_frame
            arm = float(result["armLengthCm"])
            if contact is None or contact < 1:
                continue
            first = points[0]
            sideways = first[index["l_uparm"]] - first[index["r_uparm"]]
            sideways = sideways / np.linalg.norm(sideways)
            cls.turned[movement_id] = abs(
                float(np.degrees(np.arctan2(sideways[2], sideways[0])))
            )
            for side in ("l", "r"):
                shoulder, wrist = index[f"{side}_uparm"], index[f"{side}_wrist"]
                worst = max(
                    float(np.linalg.norm(frame[wrist] - frame[shoulder])) / arm
                    for frame in points[:contact]
                )
                where = cls.reaching if side in method.sides else cls.waiting
                where[(movement_id, side)] = worst

    def test_the_library_has_a_hand_of_each_kind(self) -> None:
        """Guards the guard. The comparison below is empty without both."""
        self.assertTrue(self.reaching, "no drill reaches for the ball")
        self.assertTrue(self.waiting, "no drill has a hand that waits")

    def test_a_turned_drill_is_among_them(self) -> None:
        """The anti-hollow clause, and the one that matters here.

        The fault only appears on a turned athlete: with square shoulders the
        midpoint is the same distance from both, so the old code was correct by
        accident. A library of square drills passes this file while proving
        nothing.
        """
        self.assertTrue(
            any(degrees > 20.0 for degrees in self.turned.values()),
            "no drill starts turned, so the midpoint and the shoulders agree "
            "and this file cannot see the fault it exists for",
        )

    def test_no_waiting_hand_is_further_out_than_a_reaching_one(self) -> None:
        """The rule, measured against the library rather than a threshold.

        A hand that is reaching for a ball is the most extended a hand has any
        business being before contact. A hand that is merely waiting must not
        beat it.
        """
        furthest = max(self.reaching.values())
        for (movement_id, side), extension in sorted(self.waiting.items()):
            with self.subTest(movement=movement_id, side=side):
                self.assertLessEqual(
                    extension,
                    furthest,
                    f"{movement_id}: the {side} hand waits at {extension:.3f} of "
                    f"full extension, further out than any hand in the library "
                    f"actually reaching for a ball ({furthest:.3f}). A waiting "
                    "arm is being asked for a point it cannot reach.",
                )

    def test_no_hand_at_all_is_locked_out_before_contact(self) -> None:
        """The blunter statement of the same thing, which survives a library
        where every drill went wrong at once and the comparison above stopped
        discriminating. An elbow at full extension cannot give with a ball."""
        for source in (self.reaching, self.waiting):
            for (movement_id, side), extension in sorted(source.items()):
                with self.subTest(movement=movement_id, side=side):
                    self.assertLess(
                        extension,
                        0.99,
                        f"{movement_id}: the {side} arm reaches {extension:.3f} "
                        "of full extension before she has the ball, which is a "
                        "locked elbow rather than a ready one.",
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
