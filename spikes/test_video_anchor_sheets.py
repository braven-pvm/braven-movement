"""A frame offset is a claim about two recordings, and the arithmetic that
produces it agrees with itself whatever it is given. The sheet is the one
check that shares nothing with the fit: a person looks, and the
gap-then-contact transition either falls in the same column in both rows or it
does not.

The instrument that drew those sheets lived outside git, so nothing could say
whether a sheet still showed what it claimed.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

import video_anchor_sheets as sheets
from video_keypoints import PAIRS
from video_section_cuts import SAMPLES

PAIR1 = "front 0.1 + side 0.1"
PAIR2 = "front 0.2 + side 0.2"


def recordings_present(pair_key):
    return (SAMPLES / PAIRS[pair_key]["referenceFile"]).exists()


class TheMomentsComeFromTheTable(unittest.TestCase):
    """THE SCRATCH INSTRUMENT DREW THREE ANCHORS FOR PAIR 2 AND THE TABLE HOLDS
    TWO. Its third sheet is a CHECK: an event the fitted offset had to explain
    afterwards, not one the offset was fitted to. The sheets are the same
    pictures either way, and the difference is what they are evidence of.
    """

    def test_every_anchor_and_check_of_both_pairs_is_drawn(self):
        for key in PAIRS:
            with self.subTest(pair=key):
                wanted = sheets.moments(key)
                table = PAIRS[key]

                self.assertEqual(
                    len(wanted),
                    len(table["anchors"]) + len(table["checks"]))
                self.assertEqual(
                    [m["referenceIndex"] for m in wanted],
                    [row["referenceIndex"] for row in table["anchors"]]
                    + [row["referenceIndex"] for row in table["checks"]])

    def test_an_anchor_is_labelled_an_anchor_and_a_check_a_check(self):
        for key in PAIRS:
            for moment in sheets.moments(key):
                with self.subTest(pair=key, index=moment["referenceIndex"]):
                    self.assertIn(moment["kind"], ("anchor", "check"))
                    self.assertTrue(
                        sheets.sheet_name(moment).startswith(moment["kind"]))

    def test_the_kinds_are_not_all_the_same_kind(self):
        """Without this, `kind` could be the constant "anchor" and every
        assertion above would still pass."""
        for key in PAIRS:
            kinds = {m["kind"] for m in sheets.moments(key)}

            with self.subTest(pair=key):
                self.assertEqual(kinds, {"anchor", "check"})

    def test_a_setAside_event_is_NEVER_drawn(self):
        """Each set-aside event is recorded with the reason it was not used --
        a soft clasp, a one-handed catch that is contact one frame either way.
        Drawing one asks a reader to resolve by eye the ambiguity the entry
        exists to record, and a sheet is exactly what a reader trusts."""
        for key in PAIRS:
            drawn = {m["referenceIndex"] for m in sheets.moments(key)}
            for row in PAIRS[key].get("setAside", ()):
                with self.subTest(pair=key, index=row["referenceIndex"]):
                    self.assertNotIn(row["referenceIndex"], drawn)

    def test_every_pair_HAS_a_set_aside_event_for_that_test_to_exclude(self):
        """A guard whose case does not exist guards nothing. Both pairs carry
        one today; if a pair ever has none, the test above passes vacuously
        for it and this says so."""
        for key in PAIRS:
            with self.subTest(pair=key):
                self.assertTrue(PAIRS[key].get("setAside"))

    def test_the_indices_are_the_tables_and_no_literal_is_typed_here(self):
        for key in PAIRS:
            for moment in sheets.moments(key):
                source = [row for kind in ("anchors", "checks")
                          for row in PAIRS[key][kind]
                          if row["referenceIndex"] == moment["referenceIndex"]]

                with self.subTest(pair=key, index=moment["referenceIndex"]):
                    self.assertEqual(len(source), 1)
                    self.assertEqual(moment["otherIndex"],
                                     source[0]["otherIndex"])
                    self.assertEqual(moment["event"], source[0]["event"])


class TheSheetSpanIsCheckedBeforeAnythingIsWritten(unittest.TestCase):

    def files(self, offset=-78, front_frames=946, side_frames=863):
        return {"offset": offset, "pairKey": "test",
                "front": {"name": "front.mp4", "pts": [0.0] * front_frames},
                "side": {"name": "side.mp4", "pts": [0.0] * side_frames}}

    def test_seven_columns_two_frames_apart_centred_on_the_event(self):
        self.assertEqual(sheets.sheet_indices(324),
                         [318, 320, 322, 324, 326, 328, 330])

    def test_a_window_inside_both_recordings_is_accepted(self):
        self.assertEqual(sheets.check_span(self.files(), 324)[3], 324)

    def test_a_window_off_the_front_of_either_recording_refuses(self):
        for centre, view in ((3, "front"), (80, "side")):
            with self.subTest(centre=centre):
                with self.assertRaises(SystemExit) as refusal:
                    sheets.check_span(self.files(), centre)

                self.assertIn(view, str(refusal.exception))

    def test_a_window_off_the_end_of_either_recording_refuses(self):
        """THE SIDE RUNS OUT FIRST HERE, and a front-only check would miss it.
        Pair 2's side recording is 83 frames shorter than its front and the
        offset is -78, so the far end is the front's to lose; the near end is
        the side's. Both are checked."""
        with self.assertRaises(SystemExit) as refusal:
            sheets.check_span(self.files(), 944)

        self.assertIn("front", str(refusal.exception))

    def test_a_refusal_writes_no_sheet_and_no_tile(self):
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        moment = {"kind": "anchor", "event": "e", "referenceIndex": 3,
                  "otherIndex": -75}

        with self.assertRaises(SystemExit):
            sheets.anchor_sheet(self.files(), moment, out)

        self.assertEqual(sorted(p.name for p in out.rglob("*")), [])

    def test_every_real_moment_of_every_pair_fits_its_recordings(self):
        """The windows in the table are not near an edge today. If a future
        anchor is, this says so before somebody runs the tool."""
        for key in PAIRS:
            pair = PAIRS[key]
            files = {"offset": pair["frameOffsetToReference"],
                     "front": {"pts": [0.0] * 10000},
                     "side": {"pts": [0.0] * 10000}}
            for moment in sheets.moments(key):
                with self.subTest(pair=key, index=moment["referenceIndex"]):
                    span = sheets.check_span(files, moment["referenceIndex"])

                    self.assertEqual(len(span), 2 * sheets.SHEET_HALF + 1)


class TheLabelFontIsPartOfThePinnedPixels(unittest.TestCase):
    """`drawtext` renders the label into the tile, so the committed digests
    depend on the font file as much as on the frame. ffmpeg falling back to
    another face would fail every pinned tile with a message about the
    picture, which is the wrong thing to go looking at."""

    def test_a_missing_font_refuses_and_says_what_it_would_have_broken(self):
        with mock.patch.object(sheets, "LABEL_FONT",
                               Path("C:/nowhere/arialbd.ttf")):
            with self.assertRaises(SystemExit) as refusal:
                sheets.check_font()

        message = str(refusal.exception)
        self.assertIn("nowhere", message)
        self.assertIn("right frames", message)

    def test_the_font_this_machine_pinned_with_is_present(self):
        self.assertTrue(sheets.check_font().exists())


class TheSheetsReproduceTheOnesAPersonConfirmed(unittest.TestCase):
    """PAIR 2'S PAIRING WAS CONFIRMED ON THREE SHEETS, read by the orchestrator
    outside this repository. Their 42 tiles are committed here as digests, so
    the sheets this tool draws are compared against the pictures somebody
    actually looked at rather than against themselves.

    The digests are cropped out of a FINISHED SHEET by `sheet_tiles`, which is
    the same measurement on their PNG and on ours. Hashing an intermediate
    file only this pipeline produces would have made that comparison
    impossible.
    """

    @classmethod
    def setUpClass(cls):
        cls.ready = recordings_present(PAIR2)
        if not cls.ready:
            return
        cls.out = Path(tempfile.mkdtemp())
        cls.refusal = ""
        try:
            cls.files = sheets.resolve(PAIR2)
            cls.entries = {}
            for moment in sheets.moments(PAIR2):
                entry = sheets.anchor_sheet(cls.files, moment, cls.out)
                cls.entries[entry["sheet"]] = entry
        except SystemExit as refused:
            cls.refusal = str(refused)
        except Exception as broken:
            cls.refusal = f"{type(broken).__name__}: {broken}"

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "ready", False):
            shutil.rmtree(cls.out, ignore_errors=True)

    def setUp(self):
        if not self.ready:
            self.skipTest("the session 1.0 recordings are not on this machine")
        if self.refusal:
            self.fail(f"drawing the sheets refused: {self.refusal}")

    def test_every_sheet_matches_the_tiles_committed_for_it(self):
        missing = []
        for name, entry in self.entries.items():
            pinned = sheets.pinned_tiles("pair2", Path(name).stem)
            if pinned is None:
                missing.append(name)
                continue
            with self.subTest(sheet=name):
                self.assertEqual(len(pinned), 14)
                self.assertEqual(entry["tileDigests"], pinned,
                                 "this sheet shows different pictures from "
                                 "the one that was confirmed")
        self.assertEqual(missing, [],
                         "no tiles are committed for these sheets")

    def test_a_SHIFTED_OFFSET_changes_every_side_tile_and_no_front_tile(self):
        """THE MEASUREMENT THE SHEET EXISTS TO CHECK. If the offset moved by
        one and the sheet did not, the sheet could not show a wrong offset at
        all. Seven side tiles must all change and seven front tiles must not:
        one direction alone would pass on a sheet that redrew everything."""
        moment = sheets.moments(PAIR2)[0]
        pinned = sheets.pinned_tiles("pair2", sheets.sheet_name(moment))
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        wrong = dict(self.files, offset=self.files["offset"] + 1)

        drawn = sheets.anchor_sheet(wrong, moment, out)["tileDigests"]

        columns = 2 * sheets.SHEET_HALF + 1
        self.assertEqual(drawn[:columns], pinned[:columns],
                         "the front row moved, and the offset is not a front "
                         "index")
        for column in range(columns):
            with self.subTest(column=column):
                self.assertNotEqual(drawn[columns + column],
                                    pinned[columns + column])

    def test_each_sheet_holds_the_columns_that_were_asked_for(self):
        columns = 2 * sheets.SHEET_HALF + 1
        for name, entry in self.entries.items():
            with self.subTest(sheet=name):
                self.assertEqual(len(entry["frontIndices"]), columns)
                self.assertEqual(len(entry["sideIndices"]), columns)
                self.assertEqual(len(entry["tileDigests"]), 2 * columns)

    def test_the_side_row_is_the_MAPPED_row(self):
        for name, entry in self.entries.items():
            with self.subTest(sheet=name):
                self.assertEqual(
                    entry["sideIndices"],
                    [k + self.files["offset"] for k in entry["frontIndices"]])

    def test_the_centre_agrees_with_the_index_THE_TABLE_RECORDED(self):
        """NOT THE SAME ARITHMETIC TWICE. `centreSideIndex` is
        `referenceIndex + offset`, a computation. `otherIndex` is what somebody
        read off the side recording when the pairing was made. They must
        agree, and if they ever stop agreeing the table is inconsistent with
        the offset it also carries."""
        for moment in sheets.moments(PAIR2):
            entry = self.entries[f"{sheets.sheet_name(moment)}.png"]
            with self.subTest(index=moment["referenceIndex"]):
                self.assertEqual(entry["centreSideIndex"],
                                 moment["otherIndex"])

    def test_the_manifest_names_both_recordings_by_hash_and_the_font(self):
        manifest = sheets.manifest_for(self.files, list(self.entries.values()))

        self.assertTrue(manifest["front"]["sha256"].startswith(
            PAIRS[PAIR2]["referenceSha256"]))
        self.assertTrue(manifest["side"]["sha256"].startswith(
            PAIRS[PAIR2]["otherSha256"]))
        self.assertEqual(manifest["sideIndexEqualsFrontIndexPlus"],
                         self.files["offset"])
        self.assertEqual(len(manifest["labelFont"]["sha256"]), 64)
        self.assertIn("setAside", manifest["whatIsNotHere"])


class TheCommandLineDrawsWhatTheTableHolds(unittest.TestCase):

    def test_main_draws_every_moment_of_a_pair_and_writes_the_manifest(self):
        if not recordings_present(PAIR2):
            self.skipTest("the session 1.0 recordings are not on this machine")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)

        code = sheets.main(["video_anchor_sheets.py", "--pair", PAIR2,
                            "--out", str(out)])

        self.assertEqual(code, 0)
        manifest = json.loads(
            (out / "manifest.json").read_text(encoding="utf-8"))
        wanted = sheets.moments(PAIR2)

        self.assertEqual(len(manifest["sheets"]), len(wanted))
        for entry, moment in zip(manifest["sheets"], wanted):
            with self.subTest(sheet=entry["sheet"]):
                self.assertEqual(entry["sheet"],
                                 f"{sheets.sheet_name(moment)}.png")
                self.assertTrue((out / entry["sheet"]).exists())
                self.assertEqual(entry["kind"], moment["kind"])
                self.assertEqual(entry["tileDigests"],
                                 sheets.sheet_tiles(out / entry["sheet"]))

    def test_an_unknown_pair_refuses_and_lists_what_is_known(self):
        with self.assertRaises(SystemExit) as refusal:
            sheets.main(["video_anchor_sheets.py", "--pair", "front 9.9",
                         "--out", "nowhere"])

        self.assertIn(PAIR1, str(refusal.exception))

    def test_a_pair_folder_is_read_from_the_tables_order(self):
        self.assertEqual(sheets.pair_folder(PAIR1), "pair1")
        self.assertEqual(sheets.pair_folder(PAIR2), "pair2")


if __name__ == "__main__":
    unittest.main()
