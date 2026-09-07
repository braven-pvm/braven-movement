"""Every key a solver WRITES is a declared measure or a named state column.

`test_measure_units` asks whether every measure a checkpoint GRADES has a
declared unit. That is the wrong end of the pipe to stand at. `leftFootHeightCm`
and `rightFootHeightCm` were written by both solvers on every frame of every
drill and declared by neither, so `unit_of` raised for them, and nothing failed
because nothing graded them yet. The first drill to grade a foot height would
have raised instead of grading it.

This guard stands at the writing end. It solves real drills, reads the keys the
solvers actually produced, and requires each one to be either a declared measure
or a named state column. A new key forces a decision.

BOTH WRITERS ARE COVERED, because there are two and they duplicate each other:
`movement_engine.solve` and `possession_solve.solve_movement` each build a
measurement row, and a measure added to one and not the other is a difference
this guard reports rather than hides.
"""

from __future__ import annotations

import unittest

from segment_measures import (
    MEASURE_UNITS,
    POSSESSION_ONLY,
    STATE_COLUMNS,
    unit_of,
)

try:  # pragma: no cover - the import is the check
    import pymomentum  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover
    SOLVER = False

# One drill per writer. `possession_solve` needs a ball and a technique;
# `movement_engine.solve` runs the plain path. Named rather than discovered, so
# a library change that drops a drill fails loudly here instead of quietly
# shrinking the cover.
WITH_A_BALL = "netball_one_hand_high_pass"
WITHOUT_A_BALL = "netball_double_foot_landing"


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class EveryWrittenKeyIsAccountedFor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from movement_engine import load_character

        cls.character = load_character()

    def rows_from_the_possession_solve(self) -> list[dict]:
        from possession_solve import solve_movement

        return solve_movement(self.character, WITH_A_BALL)["measurements"]

    def rows_from_the_plain_solve(self) -> list[dict]:
        from motion_track import load_motion
        from movement_engine import motion_path, solve

        track = load_motion(motion_path(WITHOUT_A_BALL))
        return solve(self.character, track)["measurements"]

    def test_both_writers_actually_produced_rows(self) -> None:
        """Guards the guard. An empty row set accounts for every key in it."""
        for label, rows in (
            ("possession", self.rows_from_the_possession_solve()),
            ("plain", self.rows_from_the_plain_solve()),
        ):
            with self.subTest(writer=label):
                self.assertGreater(len(rows), 10, f"{label} wrote no frames")
                self.assertGreater(len(rows[0]), 5, f"{label} wrote no columns")

    def test_every_key_is_a_declared_measure_or_a_named_state_column(self):
        for label, rows in (
            ("possession", self.rows_from_the_possession_solve()),
            ("plain", self.rows_from_the_plain_solve()),
        ):
            written = {key for row in rows for key in row}
            unaccounted = sorted(written - set(MEASURE_UNITS) - STATE_COLUMNS)
            with self.subTest(writer=label):
                self.assertEqual(
                    unaccounted, [],
                    f"the {label} solver writes {unaccounted} and they are "
                    "neither declared in segment_measures.MEASURE_UNITS nor "
                    "named in STATE_COLUMNS. A consumer reading one of these "
                    "has no way to say what it is in.",
                )

    def test_unit_of_answers_for_every_written_measure(self) -> None:
        """The failure the declaration gap actually produced.

        Set membership and `unit_of` are two questions, and the second is the
        one a consumer asks. This calls it.
        """
        for label, rows in (
            ("possession", self.rows_from_the_possession_solve()),
            ("plain", self.rows_from_the_plain_solve()),
        ):
            written = {key for row in rows for key in row} - STATE_COLUMNS
            for measure in sorted(written):
                with self.subTest(writer=label, measure=measure):
                    self.assertIn(unit_of(measure), ("degrees", "centimetres"))

    def test_the_two_writers_agree_on_what_they_write(self) -> None:
        """They duplicate each other's measure block line for line.

        The foot heights are written twice, in `movement_engine` and again in
        `possession_solve`. A measure added to one and not the other would
        leave a drill graded on a column its own solver never wrote.
        """
        possession = {
            key for row in self.rows_from_the_possession_solve() for key in row
        }
        plain = {key for row in self.rows_from_the_plain_solve() for key in row}
        only_in_possession = sorted(possession - plain)
        only_in_plain = sorted(plain - possession)
        self.assertEqual(
            only_in_plain, [],
            "the plain solver writes something the possession solver does not",
        )
        # THE ASYMMETRY IS NAMED, NOT WAIVED. A ball measure exists on one
        # path and not the other, which is real and correct: a drill without a
        # ball cannot grade one. So the extras must be state columns or
        # measures the table declares POSSESSION_ONLY, and nothing else. The
        # contract was widened for `ballHeightCm` rather than the guard
        # weakened, because "the possession solver may write anything extra"
        # would guard nothing at all.
        self.assertEqual(
            sorted(set(only_in_possession) - STATE_COLUMNS - POSSESSION_ONLY), [],
            f"{only_in_possession} is written only by the possession solver "
            "and is neither a state column nor declared POSSESSION_ONLY, so a "
            "drill without a ball would be graded on a measure nothing wrote "
            "for it",
        )

    def test_every_possession_only_measure_is_declared_and_written(self) -> None:
        """Guards the widened contract from both ends.

        A name in POSSESSION_ONLY that no solver writes is a licence nothing
        uses, and a name with no declared unit is the gap this module exists
        for, moved one table across.
        """
        self.assertTrue(POSSESSION_ONLY, "POSSESSION_ONLY is empty")
        written = {
            key for row in self.rows_from_the_possession_solve() for key in row
        }
        for measure in sorted(POSSESSION_ONLY):
            with self.subTest(measure=measure):
                self.assertIn(measure, MEASURE_UNITS)
                self.assertIn(
                    measure, written,
                    f"{measure} is declared possession-only and the "
                    "possession solver never wrote it",
                )

    def test_no_possession_only_measure_reaches_the_plain_writer(self) -> None:
        """The other direction, which the set difference above cannot see.

        If the plain solver ever wrote `ballHeightCm`, `only_in_possession`
        would simply not contain it and the guard above would pass while a
        ball-less drill carried a ball measure.
        """
        plain = {key for row in self.rows_from_the_plain_solve() for key in row}
        trespassing = sorted(plain & POSSESSION_ONLY)
        self.assertEqual(
            trespassing, [],
            f"the plain solver writes {trespassing}, which is declared "
            "possession-only. A drill with no ball has no ball height.",
        )

    def test_a_length_is_among_them_or_this_guards_only_angles(self) -> None:
        """Guards the guard. The gap this exists for was a LENGTH."""
        written = {
            key for row in self.rows_from_the_possession_solve() for key in row
        } - STATE_COLUMNS
        lengths = {m for m in written if unit_of(m) == "centimetres"}
        self.assertGreaterEqual(
            len(lengths), 3,
            f"only {sorted(lengths)} are lengths, so this guard is watching "
            "almost nothing of what it was written for",
        )


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheBallHeightIsAboveTheCourt(unittest.TestCase):
    """The zero, and the frames the column exists on.

    A height is only as good as what it is measured above, and this engine
    already carries a second, different zero: the three foot heights read from
    the REST ANKLE, which sits 7.3886 cm up. Reading a ball from that zero
    gives 192.56 where the drill's own note says 199.95.
    """

    @classmethod
    def setUpClass(cls) -> None:
        from movement_engine import load_character
        from possession_solve import solve_movement

        cls.result = solve_movement(load_character(), WITH_A_BALL)

    def test_it_is_the_ball_centre_in_world_height(self) -> None:
        """Compared against the solve's own ball, not against a constant."""
        frames = self.result["possession"].frames
        checked = 0
        for number, row in enumerate(self.result["measurements"]):
            if "ballHeightCm" not in row:
                continue
            self.assertAlmostEqual(
                row["ballHeightCm"], float(frames[number].centre[1]), places=2,
                msg=f"frame {number} is not the ball's world height",
            )
            checked += 1
        self.assertGreater(checked, 50, "almost no frame carried the column")

    def test_it_is_not_measured_from_the_ankle_the_foot_heights_use(self):
        """The mutation this measure was most likely to ship with.

        `leftFootHeightCm` reads from the rest `l_foot`. Copying that zero
        here would be silent: every number stays plausible and every one is
        7.39 cm low.
        """
        from movement_engine import joint_positions, load_character

        rest = joint_positions(load_character(), self.result["identity"])
        ankle = float(rest[self.result["index"]["l_foot"]][1])
        self.assertGreater(ankle, 1.0, "the ankle zero is not distinguishable")
        row = next(r for r in self.result["measurements"] if "ballHeightCm" in r)
        frames = self.result["possession"].frames
        number = self.result["measurements"].index(row)
        self.assertNotAlmostEqual(
            row["ballHeightCm"],
            float(frames[number].centre[1]) - ankle, places=2,
        )

    def test_it_is_absent_exactly_when_no_hand_is_on_the_ball(self) -> None:
        """After release the column would measure a parabola."""
        frames = self.result["possession"].frames
        released = 0
        for number, row in enumerate(self.result["measurements"]):
            with self.subTest(frame=number):
                self.assertEqual("ballHeightCm" in row, bool(frames[number].holding))
            released += 0 if frames[number].holding else 1
        self.assertGreater(released, 5, "no released frame, so this guards nothing")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
