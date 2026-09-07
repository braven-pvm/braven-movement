"""The section cutter: what it refuses, and what it derives rather than takes.

WHAT THESE GUARD. A section is cut from two views so a coach can see one moment
from two angles. If the two clips do not show the same instants, the pair is
worse than either clip alone, because a viewer will read two movements as one.

So the three things that could make that happen are the three things tested
here: cutting from the wrong FILE, cutting a window that does not exist in both
views, and letting a caller choose the side window by hand.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

import video_section_cuts as cuts
from video_keypoints import PAIRS

THE_PAIR = next(iter(PAIRS))


class TheFilesAreResolvedByHashAndNotByName(unittest.TestCase):
    """ON 2026-09-07 THESE TWO RECORDINGS' NAMES WERE SWAPPED AT SOURCE and a
    suite of fifty tests did not notice, because the only field that told them
    apart was written into every artefact and read by nothing. A cut made from
    the wrong file produces a clip that looks perfectly ordinary."""

    def setUp(self):
        if not (cuts.SAMPLES / PAIRS[THE_PAIR]["referenceFile"]).exists():
            self.skipTest("the session 1.0 recordings are not on this machine")

    def test_the_established_pair_resolves(self):
        found = cuts.resolve(THE_PAIR)

        self.assertTrue(found["front"]["sha256"].startswith(
            PAIRS[THE_PAIR]["referenceSha256"]))
        self.assertTrue(found["side"]["sha256"].startswith(
            PAIRS[THE_PAIR]["otherSha256"]))
        self.assertEqual(found["offset"], PAIRS[THE_PAIR]["frameOffsetToReference"])

    def test_a_hash_that_does_not_match_the_file_refuses(self):
        """The exact event of 2026-09-07, made mechanical."""
        wrong = {k: dict(v) for k, v in PAIRS.items()}
        wrong[THE_PAIR]["otherSha256"] = "0" * 12

        with mock.patch.object(cuts, "PAIRS", wrong):
            with self.assertRaises(SystemExit) as refusal:
                cuts.resolve(THE_PAIR)

        message = str(refusal.exception)
        self.assertIn("NAME AND THE CONTENT DISAGREE", message)
        self.assertIn("000000000000", message)

    def test_an_unknown_pair_refuses_and_lists_what_is_known(self):
        with self.assertRaises(SystemExit) as refusal:
            cuts.resolve("front 9.9 + side 9.9")

        self.assertIn(THE_PAIR, str(refusal.exception))


class TheSideWindowIsDerivedAndNeverGiven(unittest.TestCase):
    """A CALLER CANNOT PASS A SIDE WINDOW. `cut_section` takes a FRONT window
    and maps it through the table's own frame offset, so a section cannot be
    cut against a side range somebody chose because it looked right. That is
    how -0.7295 s was published: a catch found where an offset predicted a
    catch is not evidence in a clip of catches."""

    def files(self, offset=-5, front_frames=900, side_frames=1000):
        return {"offset": offset, "pairKey": "test",
                "front": {"name": "front.mp4", "pts": [0.0] * front_frames},
                "side": {"name": "side.mp4", "pts": [0.0] * side_frames}}

    def test_the_side_window_is_the_front_window_plus_the_table_offset(self):
        found = cuts.side_window(self.files(offset=-5), 258, 312)

        self.assertEqual(found, (253, 307))

    def test_it_follows_the_table_rather_than_a_constant(self):
        """At -78 the same front window maps somewhere else. If this ever
        returns -5's answer, the offset has been hard-coded."""
        found = cuts.side_window(self.files(offset=-78), 258, 312)

        self.assertEqual(found, (180, 234))

    def test_cut_section_takes_no_side_argument_at_all(self):
        """The strongest form of the guard: the parameter does not exist, so a
        caller cannot pass one even by mistake."""
        import inspect

        names = set(inspect.signature(cuts.cut_section).parameters)

        self.assertEqual(names, {"files", "name", "start", "end", "out_dir"})

    def test_every_real_pair_maps_a_window_by_its_own_offset(self):
        for key, pair in PAIRS.items():
            with self.subTest(pair=key):
                offset = pair["frameOffsetToReference"]
                files = self.files(offset=offset, front_frames=1000,
                                   side_frames=1000)

                first, last = cuts.side_window(files, 300, 350)

                self.assertEqual((first, last), (300 + offset, 350 + offset))


class AWindowThatDoesNotExistInBothViewsRefuses(unittest.TestCase):
    """CLAMPING WOULD BE WORSE THAN REFUSING. A clamped window returns a clip
    shorter than asked for with nothing saying so, and the two views would then
    hold different numbers of frames -- the one property this tool exists to
    guarantee."""

    def files(self, offset=-5, front_frames=900, side_frames=1000):
        return {"offset": offset, "pairKey": "test",
                "front": {"name": "front.mp4", "pts": [0.0] * front_frames},
                "side": {"name": "side.mp4", "pts": [0.0] * side_frames}}

    def test_a_window_inside_both_files_is_accepted(self):
        self.assertEqual(cuts.check_window(self.files(), 258, 312), (253, 307))

    def test_a_window_past_the_end_of_the_front_file_refuses(self):
        with self.assertRaises(SystemExit) as refusal:
            cuts.check_window(self.files(front_frames=300), 258, 312)

        self.assertIn("outside", str(refusal.exception))
        self.assertIn("300 frames", str(refusal.exception))

    def test_a_window_before_the_start_refuses(self):
        with self.assertRaises(SystemExit):
            cuts.check_window(self.files(), -3, 40)

    def test_a_window_whose_MAPPED_side_range_runs_off_the_end_refuses(self):
        """THE CASE A FRONT-ONLY CHECK MISSES. The front window is entirely
        inside the front file; it is the mapped side range that does not
        exist. At an offset of -5 a window starting at index 2 maps to -3."""
        with self.assertRaises(SystemExit) as refusal:
            cuts.check_window(self.files(), 2, 40)

        message = str(refusal.exception)
        self.assertIn("maps to side", message)
        self.assertIn("same instants", message)

    def test_the_mapped_side_range_at_the_far_end_is_checked_too(self):
        with self.assertRaises(SystemExit) as refusal:
            cuts.check_window(self.files(offset=+200, side_frames=500),
                              400, 450)

        self.assertIn("maps to side", str(refusal.exception))

    def test_a_window_that_ends_before_it_starts_refuses(self):
        with self.assertRaises(SystemExit) as refusal:
            cuts.check_window(self.files(), 300, 200)

        self.assertIn("ends before it starts", str(refusal.exception))


class TheProofSheetHoldsExactlyWhatWasAskedFor(unittest.TestCase):
    """THE CONTACT-SHEET LESSON, APPLIED BEFORE IT COSTS ANYTHING. A sheet in
    this repository silently held six tiles from a previous call, captioned
    with a fallback index that resolves to a real timestamp, and a person read
    a ledger off it. A sheet whose tile count can differ from its request is a
    sheet nobody can trust."""

    def setUp(self):
        if not (cuts.SAMPLES / PAIRS[THE_PAIR]["referenceFile"]).exists():
            self.skipTest("the session 1.0 recordings are not on this machine")
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out, ignore_errors=True)
        self.files = cuts.resolve(THE_PAIR)

    def test_it_draws_two_rows_of_the_requested_instants(self):
        from PIL import Image

        sheet = cuts.proof_sheet(self.files, "t", 258, 312,
                                 self.out / "t-proof.png", instants=4)
        image = Image.open(sheet)

        # Four instants, front over side: the sheet is four tiles wide and two
        # tall. Its width divides by the tile width exactly four times.
        self.assertEqual(image.width % cuts.PROOF_TILE_WIDTH, 0)
        self.assertEqual(image.width // cuts.PROOF_TILE_WIDTH, 4)

    def test_a_different_request_gives_a_different_sheet(self):
        """If the width did not follow the request, the assertion above would
        pass on a fixed-size sheet."""
        from PIL import Image

        four = Image.open(cuts.proof_sheet(self.files, "a", 258, 312,
                                           self.out / "a.png", instants=4))
        six = Image.open(cuts.proof_sheet(self.files, "b", 258, 312,
                                          self.out / "b.png", instants=6))

        self.assertEqual(six.width, four.width * 6 // 4)

    def test_it_leaves_no_scratch_frames_behind(self):
        """The contact sheet's defect was a scratch directory it never
        emptied, so a later call inherited an earlier call's frames."""
        cuts.proof_sheet(self.files, "t", 258, 312, self.out / "t.png",
                         instants=3)

        self.assertEqual(list(self.out.glob("_raw-*")), [])

    def test_fewer_than_two_instants_refuses(self):
        with self.assertRaises(SystemExit):
            cuts.proof_sheet(self.files, "t", 258, 312, self.out / "t.png",
                             instants=1)


class ASectionIsCutFromBothViewsWithEqualFrameCounts(unittest.TestCase):
    """The reachable pass. Every refusal above proves only that the tool can
    exit 1, which a syntax error also achieves."""

    SECTION = ("catch-rep01", 258, 312)

    def setUp(self):
        if not (cuts.SAMPLES / PAIRS[THE_PAIR]["referenceFile"]).exists():
            self.skipTest("the session 1.0 recordings are not on this machine")
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out, ignore_errors=True)

    def test_both_clips_hold_the_frame_count_that_was_asked_for(self):
        files = cuts.resolve(THE_PAIR)
        name, start, end = self.SECTION

        entry = cuts.cut_section(files, name, start, end, self.out)

        wanted = end - start + 1
        self.assertEqual(entry["frames"], wanted)
        for view in ("front", "side"):
            with self.subTest(view=view):
                clip = self.out / entry[view]["file"]
                self.assertEqual(cuts.frame_count(clip), wanted)

    def test_the_manifest_names_both_files_by_hash_and_by_window(self):
        files = cuts.resolve(THE_PAIR)
        name, start, end = self.SECTION
        entry = cuts.cut_section(files, name, start, end, self.out)

        found = cuts.manifest_for(files, [entry])

        self.assertEqual(found["sideIndexEqualsFrontIndexPlus"], files["offset"])
        for view in ("front", "side"):
            self.assertEqual(len(found[view]["sha256"]), 64)
        section = found["sections"][0]
        self.assertEqual(section["front"]["indexStart"], start)
        self.assertEqual(section["side"]["indexStart"], start + files["offset"])
        # Windows by INDEX and by PTS, because a reader of the manifest who has
        # only seconds cannot re-cut the same frames from a variable-rate file.
        for view in ("front", "side"):
            for field in ("indexStart", "indexEnd", "ptsStart", "ptsEnd"):
                self.assertIn(field, section[view])


class EachClipHoldsTheSourceFramesItClaims(unittest.TestCase):
    """THE QUESTION AGREEMENT CANNOT ANSWER.

    Comparing this tool's clips against clips made by another instrument proves
    only that the two AGREE. If both mapped an index wrongly, every frame would
    still match and every row would read zero. These compare a clip against the
    RECORDING, so a shared error has nowhere to hide.

    THE SOURCE FRAMES ARE SELECTED BY A DIFFERENT FILTER FROM THE ONE UNDER
    TEST. The cut uses `trim=start_frame:end_frame`, whose end is EXCLUSIVE and
    whose off-by-one at either edge is the fault this tool exists to prevent.
    The check uses `select='between(n,start,end)'`, inclusive at both ends,
    sharing no arithmetic with it. Checking trim with trim would agree with
    itself.

    THE FLOOR IS 36 dB AND IT IS MEASURED, not chosen for looking round:
    correctly aligned frames score 39.9 dB at worst, one frame out scores 33.2
    at best. Six decibels separate them.
    """

    SECTION = ("catch-rep01", 258, 312)

    def setUp(self):
        if not (cuts.SAMPLES / PAIRS[THE_PAIR]["referenceFile"]).exists():
            self.skipTest("the session 1.0 recordings are not on this machine")
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out, ignore_errors=True)
        self.files = cuts.resolve(THE_PAIR)
        _, self.start, self.end = self.SECTION
        self.first, self.last = cuts.check_window(self.files, self.start, self.end)

    def clip_for(self, view):
        window = ((self.start, self.end) if view == "front"
                  else (self.first, self.last))
        path = self.out / f"{view}.mp4"
        cuts.cut(self.files[view]["path"], window[0], window[1], path)
        return path, window

    def test_no_frame_of_either_view_is_below_the_floor(self):
        """The assertion the orchestrator asked for: zero frames below."""
        for view in ("front", "side"):
            with self.subTest(view=view):
                clip, (a, b) = self.clip_for(view)

                scores = cuts.clip_against_source(self.files, view, clip, a, b)
                below = cuts.frames_below_floor(scores)

                self.assertEqual(len(scores), b - a + 1)
                self.assertEqual(below, [],
                                 f"{view}: frames {below} are not the source "
                                 "frames the clip claims to hold")

    def test_the_FIRST_frame_is_the_window_start_and_not_its_neighbour(self):
        """NAMES THE FRAME, because a window shifted by one keeps its count and
        a count assertion cannot see it. Frame 0 of the clip is compared with
        source `start`, and separately with `start - 1`, which must be worse."""
        clip, (a, b) = self.clip_for("front")

        right = cuts.clip_against_source(self.files, "front", clip, a, b)
        shifted = cuts.clip_against_source(self.files, "front", clip,
                                           a - 1, b - 1)

        self.assertGreaterEqual(right[0], cuts.PSNR_FLOOR_DB)
        self.assertLess(shifted[0], cuts.PSNR_FLOOR_DB,
                        "frame 0 matches the frame BEFORE the window start, so "
                        "the cut begins one frame early")

    def test_the_LAST_frame_is_the_window_end_and_not_its_neighbour(self):
        """`end_frame` is EXCLUSIVE in ffmpeg's trim, so the cut passes
        `end + 1`. Dropping that `+ 1` loses the last frame; shifting the
        window keeps the count. Both are caught by naming the last frame."""
        clip, (a, b) = self.clip_for("front")

        right = cuts.clip_against_source(self.files, "front", clip, a, b)
        shifted = cuts.clip_against_source(self.files, "front", clip,
                                           a + 1, b + 1)

        self.assertGreaterEqual(right[-1], cuts.PSNR_FLOOR_DB)
        self.assertLess(shifted[-1], cuts.PSNR_FLOOR_DB,
                        "the last frame matches the frame AFTER the window "
                        "end, so the cut runs one frame long")

    def test_the_floor_sits_between_a_right_frame_and_a_wrong_one(self):
        """The floor is only meaningful if the two populations are separated.
        If a future encoder setting closes that gap, this fails rather than the
        checks above quietly becoming unable to tell."""
        clip, (a, b) = self.clip_for("front")

        right = cuts.clip_against_source(self.files, "front", clip, a, b)
        wrong = cuts.clip_against_source(self.files, "front", clip, a + 1, b + 1)
        worst_right = min(right)
        best_wrong = max(w for w in wrong[:-1])

        self.assertGreater(worst_right, cuts.PSNR_FLOOR_DB)
        self.assertLess(best_wrong, cuts.PSNR_FLOOR_DB)
        self.assertGreater(worst_right - best_wrong, 3.0,
                           "a right frame and a wrong one are no longer "
                           "separated, so the floor cannot tell them apart")


class TheFourSectionsOfPair1AreNamedAndReproduce(unittest.TestCase):
    """THE WINDOWS LIVE IN THE TOOL, NOT IN A SCRATCH SCRIPT. They were cut
    once by an instrument outside the repository; anything nobody else can run
    is not a result. These assert the four windows and that cutting them
    produces clips identical FRAME BY FRAME to that earlier run.

    Identity is checked on DECODED FRAMES, never on file bytes: two encodes of
    the same pictures differ in bytes for reasons that have nothing to do with
    what they show, so a byte comparison answers a different question.
    """

    EARLIER = Path("F:/Repositories/braven-movement/.remember/extraction/pair1")

    def test_the_four_windows_are_the_ones_that_were_cut(self):
        self.assertEqual(
            [(n, a, b) for n, a, b, _ in cuts.PAIR1_SECTIONS],
            [("catch-rep01", 258, 312), ("release-rep09", 598, 653),
             ("hold-rep09", 654, 715), ("ready-between", 538, 584)])

    def test_every_window_carries_what_the_section_is_for(self):
        """A window with no reason attached is a number somebody will change."""
        for name, _, _, why in cuts.PAIR1_SECTIONS:
            with self.subTest(section=name):
                self.assertIn("section", why)
                self.assertGreater(len(why), 30)

    def test_each_section_reproduces_the_earlier_cut_frame_for_frame(self):
        if not (cuts.SAMPLES / PAIRS[THE_PAIR]["referenceFile"]).exists():
            self.skipTest("the session 1.0 recordings are not on this machine")
        if not self.EARLIER.exists():
            self.skipTest("the earlier cuts are not on this machine")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        files = cuts.resolve(THE_PAIR)

        for name, start, end, _ in cuts.PAIR1_SECTIONS:
            entry = cuts.cut_section(files, name, start, end, out)
            for view in ("front", "side"):
                earlier = self.EARLIER / f"{name}-{view}.mp4"
                if not earlier.exists():
                    self.skipTest(f"{earlier.name} is not present")
                with self.subTest(section=name, view=view):
                    mine = out / entry[view]["file"]

                    self.assertEqual(cuts.frame_count(mine),
                                     cuts.frame_count(earlier))
                    self.assertEqual(cuts.frame_digests(mine),
                                     cuts.frame_digests(earlier),
                                     "the clips show different frames")


class TheCommandLineRefusesBeforeItCuts(unittest.TestCase):

    def test_a_section_without_a_window_refuses(self):
        with self.assertRaises(SystemExit) as refusal:
            cuts.parse_section("catch-rep01")

        self.assertIn("name=start:end", str(refusal.exception))

    def test_a_window_that_is_not_a_number_refuses(self):
        with self.assertRaises(SystemExit):
            cuts.parse_section("catch-rep01=8.6:10.4")

    def test_a_window_is_read_as_two_front_indices(self):
        self.assertEqual(cuts.parse_section("catch-rep01=258:312"),
                         ("catch-rep01", 258, 312))


if __name__ == "__main__":
    unittest.main()
