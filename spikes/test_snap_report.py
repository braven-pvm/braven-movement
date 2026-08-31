"""The snap statistic, tested on series where the right answer is known.

The instrument was faulty for months and nothing said so, because it had no
test. That is the reason this file exists more than any individual case in it.

Two faults were recorded against the old version and both are here as cases:
it divided by the MEAN of two neighbours, which has a breakdown point of zero,
so one small neighbour flagged an ordinary step; and its gates exempted a stall
entirely, so the one shape the contact hand-over actually produces was
invisible.

A third fault was found while fixing those, and it is the sharpest case below.
A stall test with no further condition flags EVERY TURNING POINT in the
library: an angle that reverses has a step through zero at the reversal. The
first version of the fix did exactly that, on five drills of eleven, and the
discriminator is the SIGN of the steps either side.

No solver here. `snap_report.py` is stdlib only so this runs wherever the tests
run, which for an instrument matters more than for most code.
"""

from __future__ import annotations

import unittest

from movement_definition import MINIMUM_MEANINGFUL_BAND_DEGREES
from snap_report import (
    MINIMUM_MEANINGFUL_BAND_DEGREES as OWN_MINIMUM,
    SNAP_FLOOR_DEGREES,
    SNAP_WINDOW,
    spike_report,
)

# The threshold the reports gate on. Restated rather than imported: `proof.py`
# pulls in the solver, and this file must run without one.
SNAP_RATIO = 3.0


def series(values: list[float]) -> list[dict]:
    """A measurements list carrying one angle, which is all this reads."""
    return [{"leftElbowFlexionDegrees": float(v)} for v in values]


def walk(steps: list[float], start: float = 90.0) -> list[dict]:
    """A series built from the steps between its frames, which is how every
    case below is easier to state."""
    values = [start]
    for step in steps:
        values.append(values[-1] + step)
    return series(values)


class TheConstantsAgreeWithTheirSource(unittest.TestCase):
    """`snap_report` restates `MINIMUM_MEANINGFUL_BAND_DEGREES` rather than
    importing it, because importing `movement_definition` would drag the solver
    back in and this instrument must be testable without one. A restated
    constant is two things to keep in step, so this keeps them."""

    def test_the_minimum_band_matches(self) -> None:
        self.assertEqual(OWN_MINIMUM, MINIMUM_MEANINGFUL_BAND_DEGREES)


class WhatItShouldFlag(unittest.TestCase):
    def test_a_jump_among_steady_steps(self) -> None:
        found = spike_report(walk([-4.0] * 6 + [-20.0] + [-4.0] * 6))
        self.assertGreater(found["worstNeighbourRatio"], SNAP_RATIO)
        self.assertEqual(found["at"]["kind"], "jump")
        self.assertEqual(found["at"]["frame"], 7)

    def test_a_one_frame_stall_in_the_middle_of_a_movement(self) -> None:
        """The shape the contact hand-over produces, and the one the old
        statistic could not see at all: its significance gate required the STEP
        to be large, which a stall never is."""
        found = spike_report(walk([-8.0] * 6 + [-0.3] + [-8.0] * 6))
        self.assertGreater(found["worstNeighbourRatio"], SNAP_RATIO)
        self.assertEqual(found["at"]["kind"], "stall")
        self.assertEqual(found["at"]["frame"], 7)

    def test_a_stall_is_flagged_even_though_its_own_step_is_tiny(self) -> None:
        """Stated separately because it is the exact gate that used to exempt
        it. The step is 0.3 degrees, far under the meaningful band; the
        NEIGHBOURHOOD is what makes the frame worth judging."""
        found = spike_report(walk([-8.0] * 6 + [-0.3] + [-8.0] * 6))
        self.assertLess(found["at"]["stepDegrees"], MINIMUM_MEANINGFUL_BAND_DEGREES)
        self.assertGreater(found["at"]["neighbourMedianDegrees"],
                           MINIMUM_MEANINGFUL_BAND_DEGREES)


class WhatItShouldNotFlag(unittest.TestCase):
    def test_a_steady_ramp(self) -> None:
        self.assertLessEqual(
            spike_report(walk([-6.0] * 14))["worstNeighbourRatio"], SNAP_RATIO
        )

    def test_a_turning_point(self) -> None:
        """THE CASE THAT WOULD HAVE SHIPPED. An angle that reverses has a step
        through zero at the reversal, so a stall test with no further condition
        flags every turn. The first version of the fix scored 32.75 on a
        landing drill for exactly this, where the elbow simply stopped folding
        and began to open."""
        found = spike_report(walk([-8.0, -6.0, -4.0, -2.0, -0.2,
                                   2.0, 4.0, 6.0, 8.0]))
        self.assertLessEqual(
            found["worstNeighbourRatio"],
            SNAP_RATIO,
            f"a turning point was reported as {found['at']}",
        )

    def test_a_reversal_on_the_last_frame(self) -> None:
        """The edge form of the same thing. The jump-and-pull-in hooks ends
        with steps of -14.67 and then +1.56, and an earlier version returned
        `same direction` wherever a neighbour was missing, so it reported that
        turn as a stall of ratio 7.74 on the drill's very last frame."""
        found = spike_report(walk([-12.0] * 6 + [1.5]))
        self.assertLessEqual(
            found["worstNeighbourRatio"],
            SNAP_RATIO,
            f"an end-of-drill reversal was reported as {found['at']}",
        )

    def test_a_reversal_on_the_first_frame(self) -> None:
        """The MIRROR of the test above, and it is here because the mirror was
        not.

        The end edge was fixed and the start edge was not, so an identical
        series reversed at its opening read a stall of 8.00 where reversed at
        its close it read 1.00 — while the docstring said the one neighbour
        that exists decides at an edge. No drill in the library opens with a
        reversal, which is why an asymmetry in a rule survived a pack, a review
        and a merge.

        A rule stated for both ends wants a case at both ends.
        """
        found = spike_report(walk([1.5] + [-12.0] * 6))
        self.assertLessEqual(
            found["worstNeighbourRatio"],
            SNAP_RATIO,
            f"an opening reversal was reported as {found['at']}",
        )

    def test_the_two_edges_agree(self) -> None:
        """Stated as an equality, so neither edge can be fixed alone again.

        The same steps, reversed. Nothing about a snap depends on which way
        time runs through a series, so the two must read alike.
        """
        forward = [1.5] + [-12.0] * 6
        backward = [-one for one in reversed(forward)]
        self.assertAlmostEqual(
            spike_report(walk(forward))["worstNeighbourRatio"],
            spike_report(walk(backward))["worstNeighbourRatio"],
            places=6,
        )

    def test_a_still_series(self) -> None:
        """Nothing is moving, so nothing can snap. The floor is what stops a
        near-zero denominator inventing a ratio here."""
        self.assertEqual(
            spike_report(walk([0.05] * 14))["worstNeighbourRatio"], 0.0
        )


class TheDenominatorIsRobust(unittest.TestCase):
    """The original complaint, as a test.

    The old statistic divided by the mean of the two IMMEDIATE neighbours,
    which has a breakdown point of zero: one small neighbour drags the ratio
    wherever it likes. A median over a window either side cannot be moved by
    one value, and that is the whole reason for the change.
    """

    def test_a_brisk_step_beside_a_turn_is_not_flagged_for_being_beside_it(
        self,
    ) -> None:
        """The recorded complaint, in the one shape that discriminates.

        TWO EARLIER VERSIONS OF THIS TEST DID NOT DISCRIMINATE, and the second
        failure is the instructive one. Both put the brisk step next to a
        STALL — and a stall outscores everything, so `at` named the stall
        under either statistic and the mutation survived. `spike_report`
        reports only its worst frame, so a case whose worst frame is the same
        either way cannot tell two denominators apart, however different they
        are on the frame being argued about.

        The small neighbour here is a TURNING POINT instead. A turn is
        excluded from flagging by the sign rule, so it cannot outscore
        anything, and the brisk step beside it becomes the worst frame — but
        only if the denominator lets it be.

        The step is 10 against a neighbourhood of 6, brisk but ordinary. Under
        the old two-value mean its neighbours are 0.2 and 6, so it reads
        10 / 3.1 = 3.2 and IS flagged. Under a median of six it reads
        10 / 6 = 1.7 and is not. That gap is the breakdown point, made visible.
        """
        steps = [-6.0, -6.0, -6.0, -2.0, 0.2, 10.0, 6.0, 6.0, 6.0]
        found = spike_report(walk(steps))
        self.assertLessEqual(
            found["worstNeighbourRatio"],
            SNAP_RATIO,
            "a brisk step next to a turning point was flagged for the "
            f"company it keeps: {found['at']}",
        )

    def test_the_window_is_wider_than_one_either_side(self) -> None:
        """Guards the guard above. With a window of one the median IS the mean
        of two and nothing is gained."""
        self.assertGreaterEqual(SNAP_WINDOW, 2)

    def test_the_floor_replaces_a_gate_that_skipped_the_interesting_case(
        self,
    ) -> None:
        """The old code skipped any frame whose neighbours summed under 0.2,
        which is exactly a snap out of stillness. The floor keeps the frame and
        bounds the denominator instead."""
        found = spike_report(walk([0.0] * 6 + [-20.0] + [0.0] * 6))
        self.assertGreater(found["worstNeighbourRatio"], SNAP_RATIO)
        self.assertEqual(found["at"]["kind"], "jump")
        self.assertGreater(SNAP_FLOOR_DEGREES, 0.0)


class WhatItReports(unittest.TestCase):
    def test_it_names_the_measure_the_frame_and_the_kind(self) -> None:
        found = spike_report(walk([-4.0] * 6 + [-20.0] + [-4.0] * 6))["at"]
        self.assertEqual(found["measure"], "leftElbowFlexionDegrees")
        self.assertIn(found["kind"], ("jump", "stall"))
        self.assertIn("stepDegrees", found)
        self.assertIn("neighbourMedianDegrees", found)

    def test_a_series_with_nothing_in_it_reports_nothing(self) -> None:
        found = spike_report(series([90.0, 90.0, 90.0]))
        self.assertEqual(found["worstNeighbourRatio"], 0.0)
        self.assertIsNone(found["at"])

    def test_a_non_angle_field_is_ignored(self) -> None:
        """Only keys ending in Degrees are angles. A ball state or a frame
        count sharing the dictionary must not be differenced."""
        rows = [{"ballState": "flight", "handsOnTheBall": n} for n in range(9)]
        self.assertEqual(spike_report(rows)["worstNeighbourRatio"], 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
