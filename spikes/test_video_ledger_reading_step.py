"""The reading step of a ledger row, and the contact sheet that produces one.

WHY THIS FILE EXISTS. On 2026-09-07 the second camera pair was nearly recorded
as UNPAIRED. Three frame-exact anchors from one view were tested against a
ledger whose events had been sampled at every EIGHTH frame, and the best of all
correspondences spread by 10.8 frames: a confident NO FIT for a pair that is
real at a frame offset of -78.

Nothing in that ledger said its times were eighth-frame samples. They read as
measurements, so the fit consumed them as measurements. Re-read at a step of
one frame the same events give -78 three times.

So the rule is code, not prose: **a row whose reading step is coarser than the
fit's own tolerance cannot anchor that fit**, and a row with no recorded step
is refused too, because an unrecorded step is not evidence of a fine one.

The second half of this file holds the contact sheet those rows are read from,
which had a defect of exactly the same family: it could show a real frame from
elsewhere in the clip under a plausible caption.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from video_event_ledger import (
    ANNOTATION_DIR,
    SAMPLES,
    TOLERANCE_SECONDS,
    contact_sheet,
    fits_one_offset,
    usable_for_a_fit,
)

PERIOD = 1.0 / 30.0


def row(seconds, step=1, kind="catch"):
    found = {"kind": kind, "seconds": seconds}
    if step is not None:
        found["readAtFrameStep"] = step
    return found


class ARowMustDeclareAStepFineEnoughForTheTolerance(unittest.TestCase):

    def test_a_frame_by_frame_row_is_usable_at_one_frame(self):
        keep, refused = usable_for_a_fit([row(1.0, 1)], TOLERANCE_SECONDS)

        self.assertEqual(len(keep), 1)
        self.assertEqual(refused, [])

    def test_an_eighth_frame_row_is_refused_at_one_frame(self):
        """THE EXACT ROW THAT COST A DAY. Eight frames is 0.267 s and the
        tolerance is 0.033 s: the row cannot support a match that fine."""
        keep, refused = usable_for_a_fit([row(1.0, 8)], TOLERANCE_SECONDS)

        self.assertEqual(keep, [])
        self.assertEqual(len(refused), 1)
        self.assertIn("every 8 frames", refused[0])
        self.assertIn("coarser than the tolerance", refused[0])

    def test_a_row_with_no_step_at_all_is_refused(self):
        """An unrecorded step is not evidence of a fine one, and the ledger
        that caused this had no such field on any row."""
        keep, refused = usable_for_a_fit([row(1.0, None)], TOLERANCE_SECONDS)

        self.assertEqual(keep, [])
        self.assertIn("no readAtFrameStep", refused[0])

    def test_an_eighth_frame_row_IS_usable_at_a_tolerance_that_admits_it(self):
        """The rule is a comparison, not a blanket ban on coarse rows. At a
        third of a second an eighth-frame sample is within its own error."""
        keep, refused = usable_for_a_fit([row(1.0, 8)], tolerance=0.34)

        self.assertEqual(len(keep), 1)
        self.assertEqual(refused, [])

    def test_the_refusal_names_the_row_so_it_can_be_found_and_re_read(self):
        keep, refused = usable_for_a_fit([row(13.8611, 8)], TOLERANCE_SECONDS)

        self.assertIn("13.8611", refused[0])


class AFitRefusesRatherThanAnsweringOnRowsItCannotUse(unittest.TestCase):

    def test_a_fit_on_unstepped_rows_is_NOT_MEASURABLE_and_not_NO_FIT(self):
        """THE DISTINCTION THAT WAS MISSING. `False` says the two views do not
        line up; `None` says this instrument cannot tell. The first answer was
        `False` on rows that could not support it, and it was wrong."""
        front = [row(1.0, None), row(12.0, None)]
        side = [row(3.6, None), row(14.6, None)]

        found = fits_one_offset(front, side)

        self.assertIsNone(found["fits"])
        self.assertIn("NOT MEASURABLE", found["why"])
        self.assertIn("not the same as NO FIT", found["why"])
        self.assertTrue(found["refusedRows"])

    def test_the_same_rows_with_a_step_recorded_are_answered(self):
        """The guard refuses on the MISSING STEP, not on the times: the same
        events, declared frame by frame, get a real verdict."""
        front = [row(1.0, 1), row(12.0, 1)]
        side = [row(3.6, 1), row(14.6, 1)]

        found = fits_one_offset(front, side)

        self.assertIn(found["fits"], (True, False))

    def test_the_guard_can_be_turned_off_deliberately(self):
        """Some callers test the fit arithmetic itself on fabricated rows. They
        must say so, rather than the guard being absent by default."""
        front = [row(1.0, None), row(12.0, None)]
        side = [row(3.6, None), row(14.6, None)]

        found = fits_one_offset(front, side, require_frame_step=False)

        self.assertIn(found["fits"], (True, False))

    def test_the_committed_side_ledger_admits_only_its_refined_rows(self):
        """Not a fixture: the real file, which is why this rule exists.

        THIS TEST INVERTED when the four re-read rows were converted to the
        single convention. It used to assert that EVERY row is refused, which
        was true while `frameIndex` held the coarse reading on every row. Now
        `frameIndex` holds the finest reading and four rows carry
        `readAtFrameStep: 1`, so those four are admitted and the rest are not."""
        path = ANNOTATION_DIR / "event-ledger-0.1.json"
        if not path.exists():
            self.skipTest("event-ledger-0.1.json is not present")
        rows = json.loads(path.read_text(encoding="utf-8"))["views"]["side"]["events"]

        keep, refused = usable_for_a_fit(rows, TOLERANCE_SECONDS)

        self.assertEqual([r["frameIndex"] for r in keep], [246, 406, 557, 739])
        self.assertEqual(len(refused), len(rows) - 4)

    def test_the_front_0_2_ledger_admits_exactly_its_refined_rows(self):
        path = ANNOTATION_DIR / "event-ledger-front-0.2.json"
        if not path.exists():
            self.skipTest("event-ledger-front-0.2.json is not present")
        rows = json.loads(path.read_text(encoding="utf-8"))["views"]["front"]["events"]

        keep, _ = usable_for_a_fit(rows, TOLERANCE_SECONDS)

        self.assertEqual([r["frameIndex"] for r in keep], [324, 484, 635, 817])


class EachPairIsReproducibleFromTheCommittedLedgers(unittest.TestCase):
    """THE INSTRUMENT MUST REPRODUCE THE PAIRING, and until 2026-09-07 it could
    not.

    Both offsets were recorded as hand-typed anchors in `PAIRS` and nothing in
    the tree could re-derive them. Worse for pair 1: `git grep 6e8f9fb2` found
    that hash only in prose, in the pair table and in one test string, so the
    8-of-8 result that established it had run on rows that were never
    committed. "Commit the instrument with its numbers", violated twice.

    These two tests load the COMMITTED ledgers, run the fit, and check the
    offset against the frame offset the pair table states. If a ledger is
    edited into disagreement with the table, or a row's reading step is
    changed, these fail.
    """

    PERIOD = {"pair1": 0.033322, "pair2": 0.033322}

    def rows(self, name, view):
        path = ANNOTATION_DIR / name
        if not path.exists():
            self.skipTest(f"{name} is not present")
        return json.loads(path.read_text(encoding="utf-8"))["views"][view]["events"]

    def test_pair_1_reproduces_minus_five_frames(self):
        front = self.rows("event-ledger-0.1.json", "front")
        side = self.rows("event-ledger-pair1.json", "side")

        found = fits_one_offset(front, side)

        self.assertTrue(found["fits"], found["why"])
        expected = -5 * self.PERIOD["pair1"]
        self.assertAlmostEqual(found["bestOffsetSeconds"], expected,
                               delta=self.PERIOD["pair1"],
                               msg="the fit is more than one frame from -5")
        self.assertGreaterEqual(found["spanSeconds"], 10.0)
        self.assertEqual([a["frontSeconds"] for a in found["anchors"]],
                         [9.1333, 20.1667])
        self.assertEqual([a["sideSeconds"] for a in found["anchors"]],
                         [8.963, 19.992])

    def test_pair_2_reproduces_minus_seventy_eight_frames(self):
        front = self.rows("event-ledger-front-0.2.json", "front")
        side = self.rows("event-ledger-0.1.json", "side")

        found = fits_one_offset(front, side)

        self.assertTrue(found["fits"], found["why"])
        expected = -78 * self.PERIOD["pair2"]
        self.assertAlmostEqual(found["bestOffsetSeconds"], expected,
                               delta=self.PERIOD["pair2"],
                               msg="the fit is more than one frame from -78")
        self.assertGreaterEqual(found["spanSeconds"], 10.0)
        self.assertEqual([a["frontSeconds"] for a in found["anchors"]],
                         [10.8, 16.1333, 21.1667, 27.2333])

    def test_every_pair_in_the_table_has_a_ledger_that_reproduces_it(self):
        """THE GUARD AGAINST THE NEXT HAND-TYPED PAIR. A pairing added to the
        table without a ledger fails here by name."""
        from video_keypoints import PAIRS

        ledgers = {
            "front 0.1 + side 0.1": ("event-ledger-0.1.json", "front",
                                     "event-ledger-pair1.json", "side"),
            "front 0.2 + side 0.2": ("event-ledger-front-0.2.json", "front",
                                     "event-ledger-0.1.json", "side"),
        }

        self.assertEqual(set(PAIRS), set(ledgers),
                         "a pair in the table has no ledger named here")

    def test_the_answer_carries_the_rows_it_refused(self):
        """A fit answered on 4 of 10 rows says nothing about the 6 it dropped
        unless it carries them."""
        front = self.rows("event-ledger-front-0.2.json", "front")
        side = self.rows("event-ledger-0.1.json", "side")

        found = fits_one_offset(front, side)

        self.assertTrue(found["fits"])
        self.assertTrue(found["refusedRows"],
                        "the coarse rows were dropped silently")


class TheContactSheetCannotCaptionAFrameWithAGuess(unittest.TestCase):
    """THE DEFECT THIS REPRODUCES. `contact_sheet` globbed its scratch
    directory and never emptied it, so a call selecting 12 frames after a call
    that selected 18 built a sheet of EIGHTEEN tiles: the last six were the
    previous sheet's frames. The caption fell back to an index of `-1`, and
    `times[-1]` is a real timestamp, so those tiles showed a real moment from
    elsewhere in the clip under a plausible caption.

    A ledger is read off these sheets. A sheet that can show the wrong frame
    with a convincing label is worse than no sheet at all.
    """

    def setUp(self):
        if not (SAMPLES / "front 0.1.mp4").exists():
            self.skipTest("the session 1.0 recordings are not on this machine")
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out, ignore_errors=True)

    def tiles(self, path):
        """How many frames the sheet is made of, from its own raw directory."""
        return len(list((self.out / "raw").glob("f-*.png")))

    def test_a_smaller_second_call_does_not_inherit_the_first_sheets_frames(self):
        """18 frames, then 12. The second sheet must be 12."""
        contact_sheet("front", "0.1", 100, 117, 1, self.out, columns=6)
        self.assertEqual(self.tiles(None), 18)

        contact_sheet("front", "0.1", 200, 211, 1, self.out, columns=6)

        self.assertEqual(self.tiles(None), 12,
                         "the second sheet inherited the first sheet's frames")

    def test_the_caption_index_is_not_a_conditional(self):
        """Removed, not guarded, and CHECKED ON THE SYNTAX TREE rather than on
        the text. A first version of this test asserted that "else -1" does not
        appear in the source, and it failed on the COMMENT that quotes the
        removed line. A guard on text is not a guard on code: this walks the
        function and refuses any conditional expression assigned to `index`,
        which is the shape the fallback had."""
        import ast
        import inspect
        import video_event_ledger as module

        tree = ast.parse(inspect.getsource(module.contact_sheet))
        conditional = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "index"
                    for t in node.targets)
            and isinstance(node.value, ast.IfExp)
        ]

        self.assertEqual(conditional, [],
                         "the caption index is chosen by a condition again")

    def test_a_count_mismatch_refuses_rather_than_captioning_a_guess(self):
        """The count check is what makes the unconditional subscript safe, so
        it is checked as CODE too: an `if` comparing the two lengths whose body
        raises. Its absence would make the caption a guess again."""
        import ast
        import inspect
        import video_event_ledger as module

        tree = ast.parse(inspect.getsource(module.contact_sheet))
        raising = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and any(isinstance(b, ast.Raise) for b in node.body)
            and {"files", "wanted"} <= {
                n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        ]

        self.assertTrue(raising,
                        "nothing raises when the frame count and the requested "
                        "count disagree")


if __name__ == "__main__":
    unittest.main()
