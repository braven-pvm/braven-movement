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
import subprocess
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

    def test_a_wrong_hash_that_SHARES_the_real_ones_opening_refuses(self):
        """THE STRENGTH OF THE CHECK, not only its presence. The stamp is a
        12-character prefix, so the comparison is a `startswith` and what it is
        worth is the number of characters compared. Shortened to four it is a
        16-bit check, and the only wrong hash offered above -- twelve zeros --
        cannot tell the difference. This one shares the real hash's first four
        characters and differs at the fifth."""
        real = PAIRS[THE_PAIR]["otherSha256"]
        near = real[:4] + ("f" if real[4] != "f" else "0") + real[5:]
        self.assertNotEqual(near, real)
        self.assertEqual(near[:4], real[:4])
        wrong = {k: dict(v) for k, v in PAIRS.items()}
        wrong[THE_PAIR]["otherSha256"] = near

        with mock.patch.object(cuts, "PAIRS", wrong):
            with self.assertRaises(SystemExit) as refusal:
                cuts.resolve(THE_PAIR)

        self.assertIn("NAME AND THE CONTENT DISAGREE", str(refusal.exception))

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

        self.assertEqual(names, {"files", "name", "start", "end", "out_dir",
                                 "what", "poster", "poster_what"})

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
        with Image.open(sheet["path"]) as image:
            width = image.width

        # Four instants, front over side: the sheet is four tiles wide and two
        # tall. Its width divides by the tile width exactly four times.
        self.assertEqual(width % cuts.PROOF_TILE_WIDTH, 0)
        self.assertEqual(width // cuts.PROOF_TILE_WIDTH, 4)

    def test_a_different_request_gives_a_different_sheet(self):
        """If the width did not follow the request, the assertion above would
        pass on a fixed-size sheet."""
        from PIL import Image

        made = cuts.proof_sheet(self.files, "a", 258, 312,
                                self.out / "a.png", instants=4)
        with Image.open(made["path"]) as sheet:
            four = sheet.width
        made = cuts.proof_sheet(self.files, "b", 258, 312,
                                self.out / "b.png", instants=6)
        with Image.open(made["path"]) as sheet:
            six = sheet.width

        self.assertEqual(six, four * 6 // 4)

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


class EveryClipCutSectionWritesHoldsTheFramesItClaims(unittest.TestCase):
    """THE TOOL'S DEFINING PROPERTY, CHECKED THROUGH THE TOOL AND ON BOTH VIEWS.

    Two failings of the first version, and the second is the worse:

    1. It used an ABSOLUTE PSNR FLOOR of 36 dB, measured on one section-view
       and spent on eight. Re-measured everywhere, a wrong-by-one frame passes
       36 dB on five of them, and on `ready-between` side the best WRONG frame
       (41.50) beats the worst RIGHT frame (41.21): the populations overlap and
       no absolute floor can exist there. That section is her stance between
       repetitions, nearly still, so the neighbour frame is nearly the frame.
       A constant measured in one regime and spent in another.

    2. It called `cuts.cut` on a window it built itself, so THE SIDE PATH OF
       `cut_section` WAS NEVER DRIVEN. The only test that saw the side clip
       compared against an artefact at an absolute path outside git and skipped
       wherever that path is absent, which is every machine but one. Cutting
       the side clip from the FRONT file, and shifting it by one, both survived
       everything else.

    So the criterion is RELATIVE -- frame k must be closer to source `start+k`
    than to either neighbour -- and every clip here comes out of `cut_section`.
    """

    @classmethod
    def setUpClass(cls):
        cls.ready = (cuts.SAMPLES / PAIRS[THE_PAIR]["referenceFile"]).exists()
        if not cls.ready:
            return
        cls.out = Path(tempfile.mkdtemp())
        cls.files = cuts.resolve(THE_PAIR)
        cls.entries = {}
        cls.refusal = ""
        # A REFUSAL HERE MUST NOT KILL THE RUNNER. cut_section refuses with
        # SystemExit, and unittest wraps setUpClass in "except Exception", so
        # a refusal escaped the runner entirely: two mutations of the trim
        # window ended the log mid-suite with the message, and the forty later
        # tests never ran at all. Carried into setUp instead, where it becomes
        # one failure per test and the rest of the module still reports.
        try:
            for s in cuts.PAIR1_SECTIONS:
                cls.entries[s.name] = cuts.cut_section(
                    cls.files, s.name, s.start, s.end, cls.out, what=s.what,
                    poster=s.poster, poster_what=s.posterWhat)
        except SystemExit as refused:
            cls.refusal = str(refused)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "ready", False):
            shutil.rmtree(cls.out, ignore_errors=True)

    def setUp(self):
        if not self.ready:
            self.skipTest("the session 1.0 recordings are not on this machine")
        if self.refusal:
            self.fail(f"cutting the four sections refused: {self.refusal}")

    def windows(self, name):
        for s in cuts.PAIR1_SECTIONS:
            if s.name == name:
                side_first, side_last = cuts.side_window(self.files, s.start,
                                                         s.end)
                return {"front": (s.start, s.end),
                        "side": (side_first, side_last)}
        raise AssertionError(name)

    def test_every_frame_of_every_clip_beats_both_of_its_neighbours(self):
        """THE SWEEP, over four sections and both views: 440 frames. One
        section is one point, and this repository's own rule is that a mutation
        proof is a sweep, because a single point can be a basin."""
        worst = None
        for name in self.entries:
            for view in ("front", "side"):
                a, b = self.windows(name)[view]
                clip = self.out / self.entries[name][view]["file"]

                rows = cuts.clip_alignment(self.files, view, clip, a, b)
                stray = cuts.frames_out_of_alignment(rows)

                with self.subTest(section=name, view=view):
                    self.assertEqual(len(rows), b - a + 1)
                    self.assertEqual(stray, [],
                                     f"{name} {view}: frames {stray} are no "
                                     "closer to what they claim than to a "
                                     "neighbour")
                margins = [r["margin"] for r in rows
                           if r["margin"] != float("inf")]
                if margins:
                    here = min(margins)
                    worst = here if worst is None else min(worst, here)
        self.assertIsNotNone(worst)
        self.assertGreaterEqual(
            worst, cuts.RELATIVE_MARGIN_DB,
            f"the smallest winning margin anywhere is now {worst:.2f} dB")

    def test_the_measured_headroom_has_not_been_eaten(self):
        """THE RECORDED MEASUREMENT IS READ BACK, not only stored. The module
        carries the smallest margin found anywhere in the sweep; a number in a
        comment that nothing reads is how the last threshold went wrong. If a
        future encoder setting narrows the gap, this moves a number in the log
        rather than quietly leaving the check unable to tell a frame from its
        neighbour."""
        name = "ready-between"
        a, b = self.windows(name)["side"]
        clip = self.out / self.entries[name]["side"]["file"]

        rows = cuts.clip_alignment(self.files, "side", clip, a, b)
        margins = [r["margin"] for r in rows if r["margin"] != float("inf")]

        self.assertGreater(
            cuts.MEASURED_MIN_MARGIN_DB, cuts.RELATIVE_MARGIN_DB,
            "the recorded measurement is not above the bar it gives headroom "
            "over, so the bar is not below anything")
        self.assertAlmostEqual(
            min(margins), cuts.MEASURED_MIN_MARGIN_DB, delta=0.05,
            msg="the tightest section-view no longer measures what the module "
                "records for it; re-measure across all eight before moving "
                "the constant")

    def test_an_absolute_floor_would_not_have_worked_here(self):
        """THE MEASUREMENT THAT KILLED THE OLD CRITERION, kept as a test so it
        cannot come back. On this section-view a wrong-by-one frame scores
        ABOVE what the old 36 dB floor allowed."""
        name = "ready-between"
        a, b = self.windows(name)["side"]
        clip = self.out / self.entries[name]["side"]["file"]

        rows = cuts.clip_alignment(self.files, "side", clip, a, b)
        wrong = [max(r for r in (row["before"], row["after"]) if r is not None)
                 for row in rows]

        self.assertGreater(max(wrong), 36.0,
                           "a wrong-by-one frame no longer beats the old "
                           "floor, so this section-view is no longer the case "
                           "that disproves it; find the one that is")

    def test_the_first_and_last_frames_are_named_and_not_their_neighbours(self):
        """A SHIFTED WINDOW KEEPS ITS FRAME COUNT, so only naming the frame
        finds it. Both edges, both views, every section."""
        for name in self.entries:
            for view in ("front", "side"):
                a, b = self.windows(name)[view]
                clip = self.out / self.entries[name][view]["file"]
                rows = cuts.clip_alignment(self.files, view, clip, a, b)

                with self.subTest(section=name, view=view):
                    self.assertGreater(rows[0]["at"], rows[0]["before"],
                                       "frame 0 is closer to the frame BEFORE "
                                       "the window start")
                    self.assertGreater(rows[-1]["at"], rows[-1]["after"],
                                       "the last frame is closer to the frame "
                                       "AFTER the window end")

    def test_both_clips_of_a_section_start_at_zero_and_run_equally_long(self):
        """LOCKSTEP, MEASURED. Without `setpts` the side clip keeps the source's
        own timestamps and starts at 8.433 s while the front starts at 8.600: a
        player that syncs on timestamps puts them 167 ms apart, and every
        frame-count assertion still passes."""
        for name in self.entries:
            with self.subTest(section=name):
                stamps = {}
                for view in ("front", "side"):
                    clip = self.out / self.entries[name][view]["file"]
                    stamps[view] = cuts.pts(clip)

                    self.assertAlmostEqual(stamps[view][0], 0.0, places=6,
                                           msg=f"{view} does not start at zero")
                self.assertEqual(len(stamps["front"]), len(stamps["side"]))
                self.assertAlmostEqual(
                    stamps["front"][-1], stamps["side"][-1], places=6,
                    msg="the two clips end at different times")

    def test_the_manifest_pts_are_the_files_own_and_not_the_other_views(self):
        """The side window's seconds must come from the SIDE file's pts list.
        Written from the front's they are wrong by the offset, and they look
        entirely ordinary."""
        for name, entry in self.entries.items():
            with self.subTest(section=name):
                windows = self.windows(name)
                for view in ("front", "side"):
                    a, b = windows[view]
                    own = self.files[view]["pts"]

                    self.assertAlmostEqual(entry[view]["ptsStart"], own[a],
                                           places=3)
                    self.assertAlmostEqual(entry[view]["ptsEnd"], own[b],
                                           places=3)

    def test_the_proof_sheets_side_tiles_are_the_MAPPED_frames(self):
        """A side tile taken at the UNMAPPED index, captioned to match, is
        internally consistent and wrong -- the contact-sheet fault of this same
        pack. The sheet reports the indices it drew, so they can be checked."""
        for name, entry in self.entries.items():
            with self.subTest(section=name):
                front_indices = entry["proofFrontIndices"]
                side_indices = entry["proofSideIndices"]

                self.assertEqual(len(front_indices), cuts.PROOF_INSTANTS)
                self.assertEqual(
                    side_indices,
                    [k + self.files["offset"] for k in front_indices],
                    "the sheet's side tiles are not the mapped frames")

    def test_the_sheets_cut_section_writes_are_SIX_instants_wide(self):
        """The sheet tests pass `instants` explicitly, so the DEFAULT was
        asserted nowhere and lowering it changed every shipped sheet in
        silence.

        SIX IS WRITTEN OUT HERE, not read from `PROOF_INSTANTS`. Comparing the
        sheet against the constant that made it is the same instrument twice:
        lower the constant and both move together, which is how this mutation
        survived its first guard. What the pack promises a coach is a
        six-instant sheet per section, so six is what the test says, and
        changing the shipped shape means changing the promise."""
        from PIL import Image

        self.assertEqual(cuts.PROOF_INSTANTS, 6)
        for name, entry in self.entries.items():
            with self.subTest(section=name):
                sheet = self.out / entry["proofSheet"]
                with Image.open(sheet) as image:
                    columns = image.width // cuts.PROOF_TILE_WIDTH

                self.assertEqual(columns, 6)
                self.assertEqual(len(entry["proofFrontIndices"]), 6)
                self.assertEqual(len(entry["proofSideIndices"]), 6)

    def test_every_entry_carries_the_reason_its_section_exists(self):
        """It used to live only in the source table, asserted on its length and
        consumed by nothing. A coach reading the manifest can see it now."""
        reasons = {s.name: s.what for s in cuts.PAIR1_SECTIONS}
        for name, entry in self.entries.items():
            with self.subTest(section=name):
                self.assertEqual(entry["what"], reasons[name])
                self.assertIn("section", entry["what"])

    def test_every_clip_is_keyed_by_what_it_shows(self):
        """The sources are named by full sha256 and the outputs were named only
        by file name, so a clip swapped in the directory read as the manifest's
        own."""
        for name, entry in self.entries.items():
            for view in ("front", "side"):
                with self.subTest(section=name, view=view):
                    digests = entry[view]["frameDigests"]
                    clip = self.out / entry[view]["file"]

                    self.assertEqual(len(digests), entry["frames"])
                    self.assertEqual(digests, cuts.frame_digests(clip))

    def test_every_poster_is_the_frame_ITS_TABLE_ROW_NAMES(self):
        """The indices come back from the render loop, not from a sum done
        afterwards. The side index is checked against one computed here from
        the pair table, so the two are not the same arithmetic twice."""
        for s in cuts.PAIR1_SECTIONS:
            entry = self.entries[s.name]
            with self.subTest(section=s.name):
                self.assertEqual(entry["posterFrontIndex"], s.poster)
                self.assertEqual(entry["posterSideIndex"],
                                 s.poster + self.files["offset"])

    def test_every_poster_matches_the_digest_committed_for_it(self):
        """The eight posters already on Erin's page, pinned as the DECODED
        pixels of each JPEG. The file bytes are not the thing to pin: a
        different quality setting changes every byte while showing the same
        picture, and re-encoding the same wrong frame changes none of them."""
        missing = []
        for s in cuts.PAIR1_SECTIONS:
            entry = self.entries[s.name]
            for view in ("front", "side"):
                pinned = cuts.reference_digests("pair1", s.name,
                                                f"{view}-poster")
                if pinned is None:
                    missing.append(f"{s.name}-{view}")
                    continue
                with self.subTest(section=s.name, view=view):
                    self.assertEqual(len(pinned), 1)
                    self.assertEqual(entry["posters"][view]["frameDigest"],
                                     pinned[0],
                                     "this poster shows a different frame "
                                     "from the one committed for it")
        self.assertEqual(missing, [],
                         "no digests are committed for these posters")

    def test_a_poster_ONE_FRAME_LATER_is_a_different_picture(self):
        """THE COMPARISON MUST HAVE THE RESOLUTION TO SEE THE LIKELY ERROR.
        Pinning a digest proves nothing unless a neighbouring frame would fail
        it, and the section this pack learned that on is nearly still. Checked
        on every section and both views."""
        scratch = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        for s in cuts.PAIR1_SECTIONS:
            later = cuts.posters(self.files, f"{s.name}-later", s.poster + 1,
                                 scratch)
            for view in ("front", "side"):
                with self.subTest(section=s.name, view=view):
                    self.assertNotEqual(
                        cuts.frame_digests(later["files"][view])[0],
                        self.entries[s.name]["posters"][view]["frameDigest"],
                        "the next frame hashes the same as this one, so the "
                        "pinned digest cannot tell them apart")

    def test_the_poster_comes_from_the_RECORDING_and_not_from_the_clip(self):
        """A poster taken out of the clip is a re-encode of a re-encode, and
        it is addressed by a DIFFERENT NUMBER: frame `poster - start` of the
        clip rather than frame `poster` of the recording. Rendered here with
        the same JPEG settings, so a difference in the digest is a difference
        in the pixels rather than in the encoder."""
        scratch = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        for s in cuts.PAIR1_SECTIONS:
            for view in ("front", "side"):
                clip = self.out / self.entries[s.name][view]["file"]
                inside = s.poster - s.start
                out = scratch / f"{s.name}-{view}-from-the-clip.jpg"
                subprocess.run(
                    ["ffmpeg", "-v", "error", "-y", "-i", str(clip),
                     "-vf", rf"select='eq(n\,{inside})'",
                     "-fps_mode", "passthrough", "-frames:v", "1",
                     "-q:v", str(cuts.POSTER_QUALITY), str(out)], check=True)

                with self.subTest(section=s.name, view=view):
                    self.assertNotEqual(
                        cuts.frame_digests(out)[0],
                        self.entries[s.name]["posters"][view]["frameDigest"],
                        "the poster hashes the same as the same frame taken "
                        "out of the clip, so nothing here says which file it "
                        "came from")

    def test_the_manifest_carries_each_poster_by_name_and_by_two_hashes(self):
        """The file hash finds a poster swapped in the directory. The frame
        digest finds a poster that shows the wrong instant. Neither answers
        the other's question."""
        for s in cuts.PAIR1_SECTIONS:
            entry = self.entries[s.name]
            for view in ("front", "side"):
                with self.subTest(section=s.name, view=view):
                    written = entry["posters"][view]
                    on_disk = self.out / written["file"]

                    self.assertTrue(on_disk.exists())
                    self.assertEqual(written["file"],
                                     f"{s.name}-{view}-poster.jpg")
                    self.assertEqual(written["sha256"], cuts.sha256(on_disk))
                    self.assertEqual(written["frameDigest"],
                                     cuts.frame_digests(on_disk)[0])

    def test_every_entry_carries_the_reason_ITS_POSTER_is_the_one(self):
        """It lives in the table, and a coach reads the manifest."""
        for s in cuts.PAIR1_SECTIONS:
            with self.subTest(section=s.name):
                self.assertEqual(self.entries[s.name]["posterWhat"],
                                 s.posterWhat)

    def test_every_clip_matches_the_digests_committed_for_it(self):
        """THE EARLIER INSTRUMENT'S CLIPS, PINNED IN GIT. This comparison used
        to read an absolute path outside the repository and skip wherever that
        path was absent, which is every machine but one -- so the two mutations
        of the side path survived everywhere else. The digests live under
        spikes/video-annotations/section-cuts/ now, so it runs wherever the
        recordings do, and it never skips part way through a loop."""
        missing = []
        for name, entry in self.entries.items():
            for view in ("front", "side"):
                pinned = cuts.reference_digests("pair1", name, view)
                if pinned is None:
                    missing.append(f"{name}-{view}")
                    continue
                with self.subTest(section=name, view=view):
                    self.assertEqual(entry[view]["frameDigests"], pinned,
                                     "this clip shows different frames from "
                                     "the ones committed for it")
        self.assertEqual(missing, [],
                         "no digests are committed for these clips")


class TheFourSectionsOfPair1AreNamedInTheTool(unittest.TestCase):
    """THE WINDOWS LIVE IN THE TOOL, NOT IN A SCRATCH SCRIPT. They were cut
    once by an instrument outside the repository, and anything nobody else can
    run is not a result. These assert the four windows and the reason beside
    each one.

    The identity against that earlier run is asserted elsewhere, on the
    per-frame digests committed under video-annotations/section-cuts/. It used
    to read the earlier clips at an absolute path outside the repository and
    skip wherever they were absent, which is every machine but one.
    """

    def test_the_four_windows_are_the_ones_that_were_cut(self):
        self.assertEqual(
            [(s.name, s.start, s.end) for s in cuts.PAIR1_SECTIONS],
            [("catch-rep01", 258, 312), ("release-rep09", 598, 653),
             ("hold-rep09", 654, 715), ("ready-between", 538, 584)])

    def test_every_window_carries_what_the_section_is_for(self):
        """A window with no reason attached is a number somebody will change."""
        for s in cuts.PAIR1_SECTIONS:
            with self.subTest(section=s.name):
                self.assertIn("section", s.what)
                self.assertGreater(len(s.what), 30)


class TheBarSitsBetweenAMeasurementAndZero(unittest.TestCase):
    """`RELATIVE_MARGIN_DB` IS A NUMBER SOMEBODY CAN LOWER, and lowering the
    old absolute floor is exactly the mutation that killed three tests. The
    relative bar had no such guard: every test that reads it compares a real
    measurement against it, and a real measurement passes a LOWER bar just as
    happily. So the value is pinned here, on constructed rows and from BOTH
    sides, because one side is not a comparison -- at zero the criterion
    accepts a frame indistinguishable from its neighbour, and above the
    measured minimum it refuses real footage.

    The rows are built, not found. A case that has to exist in the recordings
    is a case that can stop existing.
    """

    def rows(self, margin):
        return [{"clipFrame": 0, "sourceIndex": 258, "at": 40.0,
                 "before": 40.0 - margin, "after": 30.0, "margin": margin}]

    def test_a_frame_that_only_TIES_its_neighbour_is_out_of_alignment(self):
        """Nothing separates it from the frame beside it, so nothing shows it
        is the frame it claims."""
        self.assertEqual(cuts.frames_out_of_alignment(self.rows(0.0)), [0])

    def test_the_bar_is_above_zero_and_refuses_half_of_itself(self):
        self.assertGreater(cuts.RELATIVE_MARGIN_DB, 0.0)

        self.assertEqual(
            cuts.frames_out_of_alignment(self.rows(cuts.RELATIVE_MARGIN_DB / 2)),
            [0], "a margin below the bar is being accepted")

    def test_the_bar_is_below_what_the_recordings_measure(self):
        """Set above the measured minimum it refuses the real clips, and the
        pack then cannot cut its own sections."""
        self.assertLess(cuts.RELATIVE_MARGIN_DB, cuts.MEASURED_MIN_MARGIN_DB)

        self.assertEqual(
            cuts.frames_out_of_alignment(self.rows(cuts.MEASURED_MIN_MARGIN_DB)),
            [], "the tightest measurement in the pack is being refused")

    def test_a_frame_with_no_measurable_neighbour_is_not_called_wrong(self):
        """`margin` is infinite when both neighbours fall outside the decoded
        range. Unmeasured must not read as out of alignment by an arithmetic
        accident; the window checks refuse such a window long before this."""
        rows = [{"clipFrame": 0, "sourceIndex": 0, "at": 40.0, "before": None,
                 "after": None, "margin": float("inf")}]

        self.assertEqual(cuts.frames_out_of_alignment(rows), [])


class EveryPosterIsAFrameInsideItsOwnWindow(unittest.TestCase):
    """THE POSTER IS THE ONLY FRAME A COACH IS CERTAIN TO SEE. It is what the
    page shows before she presses play, and on a page of eight clips most of
    them are never played at all. A poster from outside its window shows a
    moment the clip never reaches, and nothing about the page looks wrong.
    """

    def files(self, offset=-5, front_frames=900, side_frames=1000):
        return {"offset": offset, "pairKey": "test",
                "front": {"name": "front.mp4", "pts": [0.0] * front_frames},
                "side": {"name": "side.mp4", "pts": [0.0] * side_frames}}

    def test_every_poster_index_lies_inside_its_window(self):
        for s in cuts.PAIR1_SECTIONS:
            with self.subTest(section=s.name):
                self.assertGreaterEqual(s.poster, s.start)
                self.assertLessEqual(s.poster, s.end)

    def test_every_section_says_why_its_poster_is_the_one(self):
        """A frame index with no reason beside it is a number somebody will
        change, and this one is a coaching choice rather than a measurement.
        The reason must also be its OWN sentence: repeating the section's
        reason says nothing about which frame was picked out of the window."""
        for s in cuts.PAIR1_SECTIONS:
            with self.subTest(section=s.name):
                self.assertGreater(len(s.posterWhat), 30)
                self.assertNotEqual(s.posterWhat, s.what)

    def test_a_poster_outside_its_window_refuses_at_either_end(self):
        for outside in (257, 313):
            with self.subTest(poster=outside):
                with self.assertRaises(SystemExit) as refusal:
                    cuts.check_poster("t", 258, 312, outside)

                self.assertIn("outside the window", str(refusal.exception))

    def test_the_window_EDGES_are_allowed_as_posters(self):
        """Inclusive at both ends, like the window itself. Without this the
        check could be `start < poster < end` and the refusals above would
        still pass, while the first and last frames of every clip became
        illegal posters."""
        for edge in (258, 312):
            with self.subTest(poster=edge):
                self.assertEqual(cuts.check_poster("t", 258, 312, edge), edge)

    def test_cut_section_refuses_a_poster_before_it_writes_anything(self):
        """A refusal that has already cut two clips and drawn a sheet is not
        a refusal. The fixture has no file paths at all, so reaching the cut
        would raise something other than this."""
        with self.assertRaises(SystemExit) as refusal:
            cuts.cut_section(self.files(), "t", 258, 312, Path("nowhere"),
                             poster=313)

        self.assertIn("outside the window", str(refusal.exception))


class TheCommandLineRefusesBeforeItCuts(unittest.TestCase):

    def test_a_section_without_a_window_refuses(self):
        with self.assertRaises(SystemExit) as refusal:
            cuts.parse_section("catch-rep01")

        self.assertIn("name=start:end", str(refusal.exception))

    def test_a_window_that_is_not_a_number_refuses(self):
        with self.assertRaises(SystemExit):
            cuts.parse_section("catch-rep01=8.6:10.4")

    def test_a_window_is_read_as_two_front_indices_and_maybe_a_poster(self):
        """No poster reads as None, not as a frame in the middle. A default
        poster would sit in a manifest as though somebody had chosen it."""
        self.assertEqual(cuts.parse_section("catch-rep01=258:312"),
                         ("catch-rep01", 258, 312, None))
        self.assertEqual(cuts.parse_section("catch-rep01=258:312@276"),
                         ("catch-rep01", 258, 312, 276))

    def test_pair1_sections_carries_every_window_AND_every_poster(self):
        """A ROUND TRIP THROUGH THE REAL PARSER, not a match on the strings.
        `--pair1-sections` writes its own arguments, and dropping the poster
        from them would take the poster off every shipped section while every
        poster test, which calls cut_section directly, went on passing."""
        built = cuts.pair1_arguments()

        self.assertEqual(len(built), len(cuts.PAIR1_SECTIONS))
        for text, s in zip(built, cuts.PAIR1_SECTIONS):
            with self.subTest(section=s.name):
                self.assertEqual(cuts.parse_section(text),
                                 (s.name, s.start, s.end, s.poster))

    def test_a_poster_that_is_not_a_whole_number_refuses(self):
        """Seconds, for example. The windows are indices and so is this."""
        with self.assertRaises(SystemExit):
            cuts.parse_section("catch-rep01=258:312@9.2")

    def test_main_cuts_the_window_it_is_given_and_writes_the_manifest(self):
        """`main` had no test at all: the arguments, the section list and the
        manifest write were exercised by hand only, and a tool nobody runs in
        a suite is a tool nobody has checked. A five-frame window, so this
        costs seconds."""
        if not (cuts.SAMPLES / PAIRS[THE_PAIR]["referenceFile"]).exists():
            self.skipTest("the session 1.0 recordings are not on this machine")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)

        code = cuts.main(["video_section_cuts.py", "--pair", THE_PAIR,
                          "--section", "t=258:262", "--out", str(out)])

        self.assertEqual(code, 0)
        manifest = json.loads(
            (out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["pair"], THE_PAIR)
        self.assertTrue(manifest["front"]["sha256"].startswith(
            PAIRS[THE_PAIR]["referenceSha256"]))
        self.assertEqual(len(manifest["sections"]), 1)
        entry = manifest["sections"][0]

        self.assertEqual((entry["section"], entry["frames"]), ("t", 5))
        self.assertEqual(entry["front"]["indexStart"], 258)
        self.assertEqual(entry["side"]["indexStart"],
                         258 + PAIRS[THE_PAIR]["frameOffsetToReference"])
        for view in ("front", "side"):
            with self.subTest(view=view):
                self.assertTrue((out / entry[view]["file"]).exists())
                self.assertEqual(len(entry[view]["frameDigests"]), 5)

    def test_main_refuses_when_no_section_is_named(self):
        """Without this the tool writes an empty manifest and exits 0, which
        reads as a successful run that cut nothing."""
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)

        with self.assertRaises(SystemExit) as refusal:
            cuts.main(["video_section_cuts.py", "--pair", THE_PAIR,
                       "--out", str(out)])

        self.assertIn("--pair1-sections", str(refusal.exception))


if __name__ == "__main__":
    unittest.main()
