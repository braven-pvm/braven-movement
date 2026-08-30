"""The hand that is NOT on the ball stays on its own side of her body.

Erin Burger graded the library blind on 2026-08-30 and wrote the same thing
about both one-handed drills without being asked the same question twice. On
`netball_hooks_outside_hand`: "touch and control ball to pull ball in to other
hand and to chest." On `netball_one_hand_snatch_to_other_hand`: "Don't want
other hand to go away from centre of body towards ball."

`test_waiting_hand.py` already asks whether a waiting hand is further out than
a reaching one. It passed throughout, because the free hand sat at 0.69 of full
extension and the reaching hand goes to 0.89. That test is not hollow; it is
not tight enough. A hand can be inside every reach limit and still be in the
wrong place.

The rule here needs no threshold and no tuned constant. Her left hand belongs
on her left and her right on her right. A waiting hand that crosses the midline
of her own chest has gone somewhere a coach can see is wrong, and on the
outside-hand hooks it did: the free wrist ran from 15.1 cm on her right to
7.1 cm on her left, 22.1 cm across, because it was aimed at a passer she starts
with her back to and her own turn carried it over her.
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
    from motion_track import turn_matrix
    from movement_engine import library, load_character
    from possession_solve import solve_movement
    from technique import has_technique, load_technique, technique_path


def in_her_frame(points, index, turn_degrees: float, joint: str) -> np.ndarray:
    """Return a joint about her shoulder midpoint, in her own axes.

    MHR is Y up and her left is positive X, which makes her front positive Z.
    `clip_geometry.athlete_frame` states exactly that. At a turn of t degrees
    her axes are the columns of `turn_matrix(t)`, so reading a world point
    through the transpose returns across, up and ahead.

    Measuring in world axes instead would report her turn as a sweep, which is
    the mistake this file exists to avoid making about itself.
    """
    left = np.asarray(points[index["l_uparm"]], dtype=np.float64)
    right = np.asarray(points[index["r_uparm"]], dtype=np.float64)
    if left[0] <= right[0]:
        raise ValueError(
            "the athlete's left is not positive X, so across has the wrong "
            "sign and every reading here is mirrored"
        )
    middle = (left + right) / 2.0
    rotation = turn_matrix(turn_degrees)
    return rotation.T @ (
        np.asarray(points[index[joint]], dtype=np.float64) - middle
    )


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class AWaitingHandStaysOnItsOwnSide(unittest.TestCase):
    """Solves the library, so it is one of the slow ones. It is worth it: the
    fault it guards was invisible to every faster test in the folder."""

    @classmethod
    def setUpClass(cls) -> None:
        character = load_character()
        cls.index = {
            name: number
            for number, name in enumerate(character.skeleton.joint_names)
        }
        cls.across: dict[tuple[str, str], list[float]] = {}
        cls.turned: dict[str, float] = {}
        cls.shoulder_width: dict[str, float] = {}
        for movement_id in sorted(library()):
            if not (has_ball(movement_id) and has_technique(movement_id)):
                continue
            if not load_technique(technique_path(movement_id)).possession_ready:
                continue
            result = solve_movement(character, movement_id)
            points, turns = result["points"], result["turns"]
            first = points[0]
            cls.shoulder_width[movement_id] = float(
                np.linalg.norm(
                    first[cls.index["l_uparm"]] - first[cls.index["r_uparm"]]
                )
            )
            readings: dict[str, list[float]] = {}
            seen: list[float] = []
            for frame in result["possession"].frames:
                free = [s for s in ("l", "r") if s not in frame.sides]
                if len(free) != 1:
                    continue
                side = free[0]
                readings.setdefault(side, []).append(
                    float(
                        in_her_frame(
                            points[frame.number],
                            cls.index,
                            turns[frame.number],
                            f"{side}_wrist",
                        )[0]
                    )
                )
                seen.append(abs(float(turns[frame.number])))
            for side, values in readings.items():
                cls.across[(movement_id, side)] = values
            if seen:
                cls.turned[movement_id] = max(seen)

    def test_the_library_has_a_hand_that_waits(self) -> None:
        """Guards the guard. Every assertion below is empty without one."""
        self.assertTrue(
            self.across,
            "no drill in the library leaves a hand off the ball, so this file "
            "proves nothing",
        )

    def test_a_turned_drill_is_among_them(self) -> None:
        """The anti-hollow clause, and the one that matters here.

        The fault needs a turn. With her shoulders square, a point aimed at
        the passer sits in front of her and the free hand is merely too far
        out. She has to turn for that same fixed point to cross her body, and
        only `netball_hooks_outside_hand` turns.
        """
        self.assertTrue(
            any(degrees > 20.0 for degrees in self.turned.values()),
            "no drill turns while a hand waits, so a target fixed in the world "
            "cannot cross her and this file cannot see the fault it exists for",
        )

    def test_no_waiting_hand_crosses_the_midline(self) -> None:
        """The rule. Her left hand belongs on her left.

        Zero is the midline of her own chest, so this needs no threshold and
        no tuned constant. It is stated as a sign, and a sign cannot be nudged
        to make a drill pass.
        """
        for (movement_id, side), values in sorted(self.across.items()):
            with self.subTest(movement=movement_id, side=side):
                worst = min(values) if side == "l" else max(values)
                crossed = worst < 0.0 if side == "l" else worst > 0.0
                self.assertFalse(
                    crossed,
                    f"{movement_id}: the waiting {side} hand reaches "
                    f"{worst:.1f} cm across her chest, on the wrong side of "
                    f"her own midline. Its range over the wait is "
                    f"{min(values):.1f} to {max(values):.1f} cm. A hand that "
                    "waits does not travel across her.",
                )

    def test_a_waiting_hand_does_not_travel_across_her(self) -> None:
        """The blunter statement, which survives a library where every free
        hand went wrong on the same side and so never crossed zero.

        The bound is her own shoulders rather than a number: a hand that
        wanders further sideways than her shoulders are wide is not waiting.
        """
        for (movement_id, side), values in sorted(self.across.items()):
            width = self.shoulder_width[movement_id]
            with self.subTest(movement=movement_id, side=side):
                self.assertGreater(width, 1.0, "the shoulders have no width")
                travelled = max(values) - min(values)
                self.assertLess(
                    travelled,
                    width,
                    f"{movement_id}: the waiting {side} hand travels "
                    f"{travelled:.1f} cm sideways in her own frame, against "
                    f"shoulders {width:.1f} cm wide.",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
