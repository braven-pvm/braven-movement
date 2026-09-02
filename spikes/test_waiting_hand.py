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
        """The anti-hollow clause, RESTORED to the real library.

        The fault only appears on a turned athlete: with square shoulders the
        midpoint is the same distance from both, so the old code was correct by
        accident. A library of square drills passes this file while proving
        nothing.

        THIS CLAUSE WAS INVERTED ON 2026-09-01 AND THAT WAS A MISTAKE, though
        an honest one. `hooks_outside_hand` appeared to have stopped turning —
        48.23 degrees down to 15.44 — and it was recorded as a library-content
        gap, with the contract moved to a hand-built fixture.

        The drill had not changed. `l_clavicle_rx` has a range of zero width
        and was enabled for the solver, whose limit term is soft, so the solver
        absorbed her turn into a rotation the body cannot make. Pinning that
        axis returns her to 48.22 degrees, which is where her track always put
        her.

        The synthetic fixture in `ATurnedAthleteIsStillGuarded` is KEPT. It is
        now belt and braces rather than the only case, and it costs nothing to
        hold a contract in two places when one of them is a library that can
        change.
        """
        self.assertTrue(
            any(degrees > 20.0 for degrees in self.turned.values()),
            "no drill starts turned, so the midpoint and the shoulders agree "
            "and this file cannot see the fault it exists for. Before removing "
            "this clause again, check whether a solved pose has absorbed the "
            "turn into a joint the body cannot rotate: that is what happened "
            "the last time it read square.",
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


class ATurnedAthleteIsStillGuarded(unittest.TestCase):
    """The rule pinned on a hand-built athlete, because the library lost its
    turned drill when the hand was fixed.

    Same pattern as the reference-curve floor: where the real library happens
    not to exercise a contract, the contract is pinned on a fixture rather than
    left unguarded or weakened to fit. A fixture is not authored content and no
    movement definition is touched.

    NO SOLVER. `resolve` is geometry: it is handed shoulders and asked where the
    hands wait. That is the whole rule under test.
    """

    ARM_CM = 52.675
    REACH_LIMIT_CM = 62.0
    HALF_SPAN_CM = 18.0
    TURN_DEGREES = 44.0

    def scene(self, with_places: bool):
        """A steadily turned athlete, and the ball flying at her."""
        import json
        import tempfile
        from pathlib import Path as _Path

        from ball_track import BallOffset, load_ball, stance_frame
        from possession import resolve
        from technique import AfterContactKey

        frames = 40
        phases = [n / (frames - 1) for n in range(frames)]
        chest = np.array([0.0, 130.0, 0.0])
        middle = np.array([0.0, 137.0, 0.0])
        radians = np.radians(self.TURN_DEGREES)
        # Shoulders on a line turned about the vertical. A square athlete puts
        # both the same distance from the midpoint; a turned one does not, and
        # that difference is the entire fault.
        offset = self.HALF_SPAN_CM * np.array(
            [np.cos(radians), 0.0, np.sin(radians)]
        )
        places = [{"l": middle + offset, "r": middle - offset} for _ in phases]

        data = {
            "movementId": "turned-fixture",
            "radiusCm": 11.0,
            "release": {"atPhase": 0.1},
            "arrival": {"atPhase": 0.6},
            "keys": [
                {"atPhase": 0.1, "across": 0.0, "up": 0.3, "ahead": 4.0},
                {"atPhase": 0.35, "across": 0.0, "up": 0.4, "ahead": 2.2},
                {"atPhase": 0.6, "across": 0.0, "up": 0.4, "ahead": 0.9},
            ],
        }
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".ball.json", delete=False, encoding="utf-8"
        )
        json.dump(data, handle)
        handle.close()

        return resolve(
            phases=phases,
            ball=load_ball(_Path(handle.name)),
            stance=stance_frame(chest, self.ARM_CM, 0.0),
            athlete_frames=[
                stance_frame(chest, self.ARM_CM, self.TURN_DEGREES)
                for _ in phases
            ],
            shoulder_mids=[middle for _ in phases],
            shoulder_places=places if with_places else None,
            after_contact=(
                AfterContactKey(0.8, "absorb", BallOffset(0.0, 0.3, 0.6)),
                AfterContactKey(1.0, "pull_in", BallOffset(0.0, 0.1, 0.4)),
            ),
            reach_limit_cm=self.REACH_LIMIT_CM,
            arm_length_cm=self.ARM_CM,
            ready_offset=BallOffset(0.0, 0.2, 0.95),
        ), places

    def worst_reach(self, held, places) -> float:
        """The furthest any shoulder has to stretch to a waiting hand, as a
        fraction of the waiting distance the rule allows."""
        from possession import READY_FRACTION

        allowed = READY_FRACTION * self.REACH_LIMIT_CM
        worst = 0.0
        # WHILE THE PASSER STILL HOLDS THE BALL, which is the only window where
        # she is purely waiting. Once he lets go the hands travel to meet the
        # ball, and a hand reaching for a ball is allowed further out than a
        # hand waiting for one — that distinction is the whole subject of this
        # file, so measuring across both would compare the rule against a case
        # it does not govern.
        for frame in held.frames:
            if frame.state != "held":
                continue
            for place in places[frame.number].values():
                span = float(np.linalg.norm(frame.presented - place))
                worst = max(worst, span / allowed)
        return worst

    def test_the_fixture_is_turned_enough_to_show_the_fault(self) -> None:
        """THE ANTI-HOLLOW CLAUSE FOR THE FIXTURE ITSELF, and without it this
        class proves nothing.

        A fixture that is not turned far enough passes the rule for the same
        reason a square drill does: the midpoint and the shoulders agree. So
        the same scene is run with the correction disabled, and it must FAIL
        there. That is what makes passing with it meaningful.

        It reads 1.340 with the correction off and exactly 1.000 with it on.
        The real drill this replaces put a waiting point 66.4 cm from a
        shoulder against a 50.8 cm waiting distance, which is 1.31, so the
        fixture reproduces the fault at its true size rather than an
        exaggerated one.
        """
        held, places = self.scene(with_places=False)
        worst = self.worst_reach(held, places)
        self.assertGreater(
            worst, 1.0,
            f"with the shoulder correction disabled the furthest shoulder "
            f"still only reaches {worst:.3f} of the waiting distance, so this "
            "fixture is not turned far enough to expose the fault and the "
            "case below passes for the wrong reason",
        )

    def test_no_shoulder_is_asked_past_its_reach_on_a_turned_athlete(
        self,
    ) -> None:
        """The rule. Every shoulder must be able to reach the waiting point."""
        held, places = self.scene(with_places=True)
        worst = self.worst_reach(held, places)
        self.assertLessEqual(
            worst, 1.0 + 1e-9,
            f"a shoulder is asked to stretch {worst:.3f} of the waiting "
            "distance on a turned athlete, so the waiting point is outside "
            "its reach and the arm waits locked out",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
