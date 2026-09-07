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

from segment_measures import MEASURE_UNITS, STATE_COLUMNS, unit_of

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
        # The ball columns are the possession solver's alone and are expected.
        self.assertEqual(
            sorted(set(only_in_possession) - STATE_COLUMNS), [],
            f"{only_in_possession} is written only by the possession solver "
            "and is not a state column, so a drill without a ball would be "
            "graded on a measure nothing wrote for it",
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
