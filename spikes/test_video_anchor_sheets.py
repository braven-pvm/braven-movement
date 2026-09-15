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
TILE_HEIGHT_FOR_TESTS = 360


def recordings_present(pair_key):
    return (SAMPLES / PAIRS[pair_key]["referenceFile"]).exists()


def font_present():
    """THE LABEL FONT IS A PROPERTY OF THE MACHINE, like the recordings.

    It lives at a Windows path, the hosted runner is Linux, and a test that
    needs it must SKIP BY NAME there rather than error. An error on a runner
    is that runner saying a test meant to run and could not, which is a
    different thing from a test that does not apply.
    """
    return sheets.LABEL_FONT.exists()


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

    def test_the_TABLE_ITSELF_is_consistent_with_the_offset_it_carries(self):
        """`centreSideIndex` is `referenceIndex + offset` and the test that
        compares it with `otherIndex` passes just as happily if the code
        copies `otherIndex` straight out of the table. So the table is checked
        HERE, on its own, for every row of every kind including the ones no
        sheet draws: what somebody read off the side recording must equal what
        the recorded offset predicts."""
        for key, pair in PAIRS.items():
            offset = pair["frameOffsetToReference"]
            for kind in ("anchors", "checks"):
                for row in pair[kind]:
                    with self.subTest(pair=key, kind=kind,
                                      index=row["referenceIndex"]):
                        self.assertEqual(row["otherIndex"],
                                         row["referenceIndex"] + offset)

    def test_a_set_aside_row_is_allowed_to_disagree_with_the_offset(self):
        """AND THAT IS THE POINT OF SETTING IT ASIDE. Pair 1's first clap
        reads four frames apart where the offset says five. If a set-aside row
        ever agreed exactly, somebody has quietly resolved an ambiguity the
        entry exists to record."""
        disagreements = 0
        for key, pair in PAIRS.items():
            offset = pair["frameOffsetToReference"]
            for row in pair.get("setAside", ()):
                predicted = row["referenceIndex"] + offset
                if row["otherIndex"] != predicted:
                    disagreements += 1
        self.assertGreater(disagreements, 0,
                           "every set-aside event now agrees with the offset, "
                           "so either one was resolved by picking the frame "
                           "that suits the answer, or it is not set aside")

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

    def test_the_span_is_measured_AT_every_boundary_of_both_views(self):
        """FOUR EDGES, EACH MEASURED ONE FRAME EITHER SIDE OF LEGAL. The old
        pair of tests refused at 3 and at 944 and accepted at 324, which
        leaves the boundaries themselves unmeasured: `first < 0` could have
        been `first < -1`, `last >= frames` could have been `last > frames`,
        and the side recording's far edge was never approached at all. Three
        mutations of exactly that shape survived.

        EACH CASE ISOLATES ONE EDGE, and the fixtures look odd for a reason:
        under a single offset the two views cannot both sit at a boundary, so
        putting one view on its edge requires giving the other room. The
        offset is chosen per case to do that, and the other recording is made
        large enough that it cannot be the one that refuses. My first attempt
        at this test put both views on the edge at once and refused for the
        other view's reason, which would have passed a front-only check.
        """
        cases = {
            # (centre, offset, front frames, side frames, accepted)
            "front first == 0": (6, 0, 946, 2000, True),
            "front first == -1": (5, 1, 946, 2000, False),
            "front last == frames - 1": (939, 0, 946, 2000, True),
            "front last == frames": (940, -1, 946, 2000, False),
            "side first == 0": (10, -4, 2000, 863, True),
            "side first == -1": (10, -5, 2000, 863, False),
            "side last == frames - 1": (1000, -144, 2000, 863, True),
            "side last == frames": (1000, -143, 2000, 863, False),
        }
        for label, (centre, offset, front, side, allowed) in cases.items():
            files = self.files(offset=offset, front_frames=front,
                               side_frames=side)
            view = label.split()[0]
            with self.subTest(case=label, centre=centre, offset=offset):
                if allowed:
                    self.assertEqual(
                        sheets.check_span(files, centre)[sheets.SHEET_HALF],
                        centre)
                else:
                    with self.assertRaises(SystemExit) as refusal:
                        sheets.check_span(files, centre)

                    self.assertIn(view, str(refusal.exception),
                                  f"{label} refused for the other view")

    def test_the_side_runs_out_before_the_front_at_the_near_end(self):
        """A FRONT-ONLY CHECK WOULD MISS IT. Pair 2's side recording is 83
        frames shorter than its front and the offset is -78, so a centre that
        is comfortably inside the front file is off the start of the side."""
        with self.assertRaises(SystemExit) as refusal:
            sheets.check_span(self.files(), 80)

        self.assertIn("side", str(refusal.exception))

    def test_a_refusal_writes_no_sheet_and_no_tile(self):
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        moment = {"kind": "anchor", "event": "e", "referenceIndex": 3,
                  "otherIndex": -75}

        with self.assertRaises(SystemExit):
            sheets.anchor_sheet(self.files(), moment, out)

        self.assertEqual(sorted(p.name for p in out.rglob("*")), [])

    def test_every_real_moment_of_every_pair_fits_its_REAL_recordings(self):
        """The windows in the table are not near an edge today, and if a
        future anchor is, this says so before somebody runs the tool.

        THE REAL FRAME COUNTS, not a 10 000-frame fixture. With the fixture a
        moment at front 5000 passed this and was refused by the recordings,
        which is the opposite of what the test is for."""
        if not all(recordings_present(key) for key in PAIRS):
            self.skipTest("the session 1.0 recordings are not on this machine")
        for key in PAIRS:
            files = sheets.resolve(key)
            for moment in sheets.moments(key):
                with self.subTest(pair=key, index=moment["referenceIndex"]):
                    span = sheets.check_span(files, moment["referenceIndex"])

                    self.assertEqual(len(span), 2 * sheets.SHEET_HALF + 1)
                    self.assertEqual(span[sheets.SHEET_HALF],
                                     moment["referenceIndex"])


class TheLabelFontIsPartOfThePinnedPixels(unittest.TestCase):
    """`drawtext` renders the label into the tile, so the committed digests
    depend on the font file as much as on the frame. ffmpeg falling back to
    another face would fail every pinned tile with a message about the
    picture, which is the wrong thing to go looking at."""

    def needs_font(self):
        if not font_present():
            self.skipTest(f"the label font {sheets.LABEL_FONT} is not on "
                          "this machine")

    def test_a_missing_font_refuses_and_says_what_it_would_have_broken(self):
        with mock.patch.object(sheets, "LABEL_FONT",
                               Path("C:/nowhere/arialbd.ttf")):
            with self.assertRaises(SystemExit) as refusal:
                sheets.check_font()

        message = str(refusal.exception)
        self.assertIn("nowhere", message)
        self.assertIn("right frames", message)

    def test_the_font_this_machine_pinned_with_is_present(self):
        """Or says by name that it is not. `check_font()` raises SystemExit
        where the file is absent, so calling it unguarded turned this into an
        ERROR on the hosted runner -- a test that meant to run and could not."""
        self.needs_font()

        self.assertTrue(sheets.check_font().exists())

    def test_a_missing_font_refuses_BEFORE_anything_is_written(self):
        """The span refusal is measured on an empty directory and this one was
        not, so `check_font()` could have moved below the first write and
        nothing would have said so."""
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        moment = {"kind": "anchor", "event": "e", "referenceIndex": 324,
                  "otherIndex": 246}
        files = {"offset": -78, "pairKey": "test",
                 "front": {"name": "f.mp4", "pts": [0.0] * 946},
                 "side": {"name": "s.mp4", "pts": [0.0] * 863}}

        with mock.patch.object(sheets, "LABEL_FONT",
                               Path("C:/nowhere/arialbd.ttf")):
            with self.assertRaises(SystemExit):
                sheets.anchor_sheet(files, moment, out)

        self.assertEqual(sorted(p.name for p in out.rglob("*")), [])


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
        cls.ready = (all(recordings_present(key) for key in PAIRS)
                     and font_present())
        if not cls.ready:
            return
        cls.out = Path(tempfile.mkdtemp())
        cls.refusal = ""
        try:
            cls.files = {}
            cls.entries = {}
            for key in PAIRS:
                cls.files[key] = sheets.resolve(key)
                folder = cls.out / sheets.pair_folder(key)
                for moment in sheets.moments(key):
                    entry = sheets.anchor_sheet(cls.files[key], moment, folder)
                    cls.entries[(key, entry["sheet"])] = entry
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
            self.skipTest("the session 1.0 recordings or the label font are "
                          "not on this machine")
        if self.refusal:
            self.fail(f"drawing the sheets refused: {self.refusal}")

    def test_every_sheet_matches_the_tiles_committed_for_it(self):
        missing = []
        for (key, name), entry in self.entries.items():
            pinned = sheets.pinned_tiles(sheets.pair_folder(key),
                                         Path(name).stem)
            if pinned is None:
                missing.append(f"{sheets.pair_folder(key)}/{name}")
                continue
            with self.subTest(pair=key, sheet=name):
                self.assertEqual(len(pinned), 14)
                self.assertEqual(entry["tileDigests"], pinned,
                                 "this sheet shows different pictures from "
                                 "the one that was confirmed")
        self.assertEqual(missing, [],
                         "no tiles are committed for these sheets")

    def test_BOTH_pairs_are_pinned_and_neither_is_taken_on_trust(self):
        """Six sheets, 84 tiles. Pinning one of two shipped pairs guards half
        the tool, and the half left out is the one a later change breaks."""
        counted = 0
        for key in PAIRS:
            for moment in sheets.moments(key):
                pinned = sheets.pinned_tiles(sheets.pair_folder(key),
                                             sheets.sheet_name(moment))
                with self.subTest(pair=key, sheet=sheets.sheet_name(moment)):
                    self.assertIsNotNone(pinned)
                    self.assertEqual(len(pinned), 14)
                counted += len(pinned or [])
        self.assertEqual(counted, 84)

    def test_a_SHIFTED_OFFSET_changes_every_side_tile_and_no_front_tile(self):
        """THE MEASUREMENT THE SHEET EXISTS TO CHECK. If the offset moved by
        one and the sheet did not, the sheet could not show a wrong offset at
        all. Seven side tiles must all change and seven front tiles must not:
        one direction alone would pass on a sheet that redrew everything."""
        moment = sheets.moments(PAIR2)[0]
        pinned = sheets.pinned_tiles("pair2", sheets.sheet_name(moment))
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)
        files = self.files[PAIR2]
        wrong = dict(files, offset=files["offset"] + 1)

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
        for (key, name), entry in self.entries.items():
            with self.subTest(pair=key, sheet=name):
                self.assertEqual(len(entry["frontIndices"]), columns)
                self.assertEqual(len(entry["sideIndices"]), columns)
                self.assertEqual(len(entry["tileDigests"]), 2 * columns)

    def test_the_side_row_is_the_MAPPED_row(self):
        for (key, name), entry in self.entries.items():
            with self.subTest(pair=key, sheet=name):
                self.assertEqual(
                    entry["sideIndices"],
                    [k + self.files[key]["offset"]
                     for k in entry["frontIndices"]])

    def test_the_centre_agrees_with_the_index_THE_TABLE_RECORDED(self):
        """NOT THE SAME ARITHMETIC TWICE. `centreSideIndex` is
        `referenceIndex + offset`, a computation. `otherIndex` is what somebody
        read off the side recording when the pairing was made. They must
        agree, and if they ever stop agreeing the table is inconsistent with
        the offset it also carries."""
        for key in PAIRS:
            for moment in sheets.moments(key):
                entry = self.entries[(key, f"{sheets.sheet_name(moment)}.png")]
                with self.subTest(pair=key,
                                  index=moment["referenceIndex"]):
                    self.assertEqual(entry["centreSideIndex"],
                                     moment["otherIndex"])

    def test_EVERY_centre_tile_shows_the_frame_it_is_labelled_with(self):
        """THE ONLY CHECK HERE THAT LOOKS AT A PICTURE, and the one a pair
        with no pins would depend on entirely. Every sheet of every pair in
        the table, both rows, so run 2's sheets are covered the day they
        exist. The source frame is resized by a DIFFERENT resampler, so this
        is not swscale agreeing with itself."""
        worst = None
        for (key, name), entry in self.entries.items():
            sheet = self.out / sheets.pair_folder(key) / name
            for view in ("front", "side"):
                row = sheets.centre_tile_alignment(self.files[key], sheet,
                                                   entry, view)
                with self.subTest(pair=key, sheet=name, view=view):
                    self.assertGreater(
                        row["margin"], sheets.TILE_MARGIN_DB,
                        f"{name} {view}: the centre tile is no closer to "
                        f"frame {row['centreIndex']} than to a neighbour")
                if row["margin"] != float("inf"):
                    worst = (row["margin"] if worst is None
                             else min(worst, row["margin"]))
        self.assertIsNotNone(worst)
        self.assertAlmostEqual(
            worst, sheets.MEASURED_MIN_TILE_MARGIN_DB, delta=0.5,
            msg="the tightest centre tile no longer measures what the module "
                "records for it; re-measure all twelve before moving the "
                "constant")

    def test_the_centre_side_index_is_COMPUTED_and_not_copied(self):
        """R11 SURVIVED THE FIRST FOLD, and the reason is worth writing down.

        `centreSideIndex` should be `centre + offset`. Copying the table's
        `otherIndex` instead gives the identical number on every real row --
        because the fold above added a test proving the table is consistent,
        which turns that mutation into an equivalent mutant everywhere the
        table can reach. The case cannot be found in the data; it has to be
        BUILT.

        So this hands `anchor_sheet` a moment whose `otherIndex` is
        deliberately wrong. The pictures drawn are still the mapped ones -- the
        drawing loop uses the offset -- and a manifest field that follows the
        fabricated number instead would now disagree with them.
        """
        files = self.files[PAIR2]
        real = sheets.moments(PAIR2)[0]
        lying = dict(real, otherIndex=real["otherIndex"] + 40)
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)

        entry = sheets.anchor_sheet(files, lying, out)

        self.assertEqual(entry["centreSideIndex"],
                         entry["centreFrontIndex"] + files["offset"])
        self.assertNotEqual(entry["centreSideIndex"], lying["otherIndex"])
        # And the pictures did not follow the lie either.
        self.assertEqual(entry["sideIndices"],
                         [k + files["offset"] for k in entry["frontIndices"]])
        self.assertEqual(entry["tileDigests"],
                         sheets.pinned_tiles("pair2",
                                             sheets.sheet_name(real)))

    def test_the_manifest_names_both_recordings_by_hash_and_the_font(self):
        for key in PAIRS:
            entries = [e for (pair, _), e in self.entries.items()
                       if pair == key]
            manifest = sheets.manifest_for(self.files[key], entries)

            with self.subTest(pair=key):
                self.assertTrue(manifest["front"]["sha256"].startswith(
                    PAIRS[key]["referenceSha256"]))
                self.assertTrue(manifest["side"]["sha256"].startswith(
                    PAIRS[key]["otherSha256"]))
                self.assertEqual(manifest["sideIndexEqualsFrontIndexPlus"],
                                 PAIRS[key]["frameOffsetToReference"])
                for entry in entries:
                    self.assertEqual(
                        entry["centreSideIndex"],
                        entry["centreFrontIndex"]
                        + PAIRS[key]["frameOffsetToReference"])
                self.assertEqual(manifest["labelFont"]["sha256"],
                                 sheets.sha256(sheets.LABEL_FONT))
                self.assertIn("setAside", manifest["whatIsNotHere"])


class TheBarForATileSitsBetweenAMeasurementAndZero(unittest.TestCase):
    """`TILE_MARGIN_DB` is a number somebody can lower, and every test that
    reads it compares a real measurement against it -- which passes at any
    lower value. Pinned from both sides on constructed rows, because one side
    is not a comparison."""

    def test_the_bar_is_above_zero(self):
        """At zero a tile indistinguishable from its neighbour passes, and the
        sheet could not show a wrong offset at all."""
        self.assertGreater(sheets.TILE_MARGIN_DB, 0.0)

    def test_the_bar_is_below_what_the_sheets_measure(self):
        """Above the measured minimum it refuses the real sheets, and the tool
        cannot draw its own pairs."""
        self.assertLess(sheets.TILE_MARGIN_DB,
                        sheets.MEASURED_MIN_TILE_MARGIN_DB)

    def test_the_label_band_clears_the_label(self):
        """Compared whole, a correct tile scores 20.9 dB against its own
        source frame -- the tile has a label burned in and the frame has none.
        Below the band it is 49.6. A band of zero makes every correct tile
        look wrong."""
        self.assertGreaterEqual(sheets.TILE_LABEL_BAND, 30)
        self.assertLess(sheets.TILE_LABEL_BAND, TILE_HEIGHT_FOR_TESTS // 4)


class TheCommandLineDrawsWhatTheTableHolds(unittest.TestCase):

    def test_main_draws_every_moment_of_a_pair_and_writes_the_manifest(self):
        if not recordings_present(PAIR2):
            self.skipTest("the session 1.0 recordings are not on this machine")
        if not font_present():
            self.skipTest(f"the label font {sheets.LABEL_FONT} is not on "
                          "this machine")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, ignore_errors=True)

        code = sheets.main(["video_anchor_sheets.py", "--pair", PAIR2,
                            "--out", str(out)])

        self.assertEqual(code, 0)
        manifest = json.loads(
            (out / "manifest.json").read_text(encoding="utf-8"))
        wanted = sheets.moments(PAIR2)

        # AGAINST THE TABLE AND THE PINS, NOT AGAINST THE FILE JUST WRITTEN.
        # This used to compare the manifest's digests with `sheet_tiles()` on
        # the sheet that produced them -- an artefact checked against the
        # value that produced it. Zeroing the offset in `main` then wrote
        # unmapped side rows, a manifest saying the offset was 0, and a green
        # suite.
        offset = PAIRS[PAIR2]["frameOffsetToReference"]
        self.assertEqual(manifest["sideIndexEqualsFrontIndexPlus"], offset)
        self.assertEqual(len(manifest["sheets"]), len(wanted))
        for entry, moment in zip(manifest["sheets"], wanted):
            with self.subTest(sheet=entry["sheet"]):
                self.assertEqual(entry["sheet"],
                                 f"{sheets.sheet_name(moment)}.png")
                self.assertTrue((out / entry["sheet"]).exists())
                self.assertEqual(entry["kind"], moment["kind"])
                self.assertEqual(entry["centreFrontIndex"],
                                 moment["referenceIndex"])
                self.assertEqual(
                    entry["sideIndices"],
                    [k + offset for k in entry["frontIndices"]])
                self.assertEqual(
                    entry["tileDigests"],
                    sheets.pinned_tiles("pair2", Path(entry["sheet"]).stem),
                    "the sheet main wrote is not the one that was confirmed")

    def test_an_unknown_pair_refuses_and_lists_what_is_known(self):
        """THE SAME ANSWER ON EVERY MACHINE. `main` used to check the font
        first, so on a machine without it this refused with a message about a
        Windows font path instead of the list of pairs -- the same wrong
        argument, a different answer, depending on where it ran."""
        with self.assertRaises(SystemExit) as refusal:
            sheets.main(["video_anchor_sheets.py", "--pair", "front 9.9",
                         "--out", "nowhere"])

        message = str(refusal.exception)
        self.assertIn(PAIR1, message)
        self.assertNotIn("font", message)

    def test_the_pair_refusal_is_the_same_WITHOUT_the_font(self):
        """Measured with the font patched away, which is what the hosted
        runner is."""
        with mock.patch.object(sheets, "LABEL_FONT",
                               Path("/nowhere/arialbd.ttf")):
            with self.assertRaises(SystemExit) as refusal:
                sheets.main(["video_anchor_sheets.py", "--pair", "front 9.9",
                             "--out", "nowhere"])

        self.assertIn(PAIR1, str(refusal.exception))

    def test_a_pair_folder_is_read_from_the_tables_order(self):
        self.assertEqual(sheets.pair_folder(PAIR1), "pair1")
        self.assertEqual(sheets.pair_folder(PAIR2), "pair2")


class NothingInThisModuleERRORS_WithoutTheFont(unittest.TestCase):
    """WHAT THE HOSTED RUNNER SEES, run here rather than guessed at.

    The runner is Linux and has no `C:/Windows/Fonts/arialbd.ttf`. Three
    checks went red on it while every check on this machine was green, and the
    reason was not that the code was wrong there: a test asserted a property
    of THIS machine and raised where the property was absent, an import
    hygiene guard counted that error, and `main` refused an unknown pair with
    a message about a font instead of the list of pairs.

    So this loads every other test in this module, patches the font away, runs
    them, and requires ZERO ERRORS. Failures are not tolerated either -- what
    is allowed is a pass or a skip that names its reason.

    A machine property is a skip, never an error. An error on a runner is that
    runner saying a test meant to run and could not.
    """

    def test_every_other_test_here_passes_or_skips_with_no_font(self):
        import io

        loader = unittest.TestLoader()
        suite = unittest.TestSuite(
            case for case in _flatten(loader.loadTestsFromModule(
                __import__(__name__ if __name__ != "__main__"
                           else "test_video_anchor_sheets")))
            if not isinstance(case, NothingInThisModuleERRORS_WithoutTheFont))

        with mock.patch.object(sheets, "LABEL_FONT",
                               Path("/nowhere/arialbd.ttf")):
            outcome = unittest.TextTestRunner(
                stream=io.StringIO(), verbosity=0).run(suite)

        self.assertEqual(
            [f"{case}: {trace.splitlines()[-1]}"
             for case, trace in outcome.errors], [],
            "these ERRORED with the font absent; a machine property is a skip")
        self.assertEqual(
            [str(case) for case, _ in outcome.failures], [],
            "these FAILED with the font absent")
        self.assertGreater(outcome.testsRun, 20)
        self.assertGreater(len(outcome.skipped), 0,
                           "nothing skipped, so nothing was actually gated on "
                           "the font and this test proves nothing")


def _flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


if __name__ == "__main__":
    unittest.main()
