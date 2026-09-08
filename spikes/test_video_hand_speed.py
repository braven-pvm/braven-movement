"""The band another lane cites, and the guards that keep it honest.

Every number here rests on artefacts that are not in git: the recordings and
the keypoint files. So every test that needs one SKIPS BY NAME where it is
absent. A test that asserts a property of THIS machine and raises where the
property is missing is an error on the hosted runner, which is that runner
saying a test meant to run and could not.
"""

from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

import video_hand_speed as speed


def keypoints_present() -> bool:
    return all(speed.keypoint_path(r.view, r.setId).exists()
               for r in speed.RELEASES)


def receipt_present() -> bool:
    return (speed.LIBRARY / "netball_two_hand_snatch_pull_in.reach.json").exists()


class TheReleasesAreReadOnThePicturesAndRecordedAsSuch(unittest.TestCase):
    """No test here finds a release. They are read at a step of one by the
    rule in the module docstring, and this only checks the record is coherent
    with what the footage can support."""

    def test_every_release_names_a_view_a_set_and_a_reading(self):
        for release in speed.RELEASES:
            with self.subTest(release=release.frame):
                self.assertIn(release.view, ("front", "side"))
                self.assertIn(release.setId, ("0.1", "0.2"))
                self.assertIn(release.reading, ("crisp", "soft"))
                self.assertGreater(release.frame, 0)

    def test_both_readings_are_used_so_the_field_is_not_a_constant(self):
        """`soft` marks the two releases where the ball blurs at separation
        and the frame could be one either way. If every row said `crisp` the
        field would be decoration."""
        readings = {r.reading for r in speed.RELEASES}

        self.assertEqual(readings, {"crisp", "soft"})

    def test_run_2_has_NINE_releases_and_the_tenth_possession_is_explained(self):
        """She catches ten times and lets go nine. The tenth possession ends
        with her walking out of the drill holding the ball, which the event
        ledger says in words. A missing row with no reason is a hole; this one
        has a reason."""
        run2 = [r for r in speed.RELEASES if r.setId == "0.2"]

        self.assertEqual(len(run2), 9)
        self.assertIn(("side", "0.2"), speed.NO_RELEASE)
        frame, why = speed.NO_RELEASE[("side", "0.2")]
        self.assertEqual(frame, 739)
        self.assertIn("carries the ball", why)

    def test_the_held_repetition_is_excluded_BY_NAME_and_still_measured(self):
        """It is a different movement, not an outlier, so it is named rather
        than cut by a threshold — and it still appears in the table."""
        self.assertIn(speed.HELD_REPETITION[2],
                      [r.frame for r in speed.RELEASES])

    def test_the_exclusion_FOLLOWS_THE_NAME_and_is_not_a_threshold(self):
        """`inBand` was indistinguishable from `handImage > 2.5`, which is
        the fastest way for a named exclusion to become a silent filter.
        Point the name at another repetition and the exclusion must move with
        it, leaving the slow one in.
        """
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")
        elsewhere = ("side", "0.2", 646)
        with mock.patch.object(speed, "HELD_REPETITION", elsewhere):
            rows = {r["frame"]: r for r in speed.band_rows()}

        self.assertFalse(rows[646]["inBand"], "the named row stayed in")
        self.assertTrue(rows[593]["inBand"],
                        "the slow row stayed out, so a threshold is doing "
                        "the work and not the name")


class TheNullIsSearchedAndNotChosen(unittest.TestCase):
    """My first null was a stretch I believed was a stand. It held a 3.03 m/s
    frame and would have put the floor forty times too high."""

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")

    def test_the_searched_null_is_quieter_than_a_stretch_picked_by_eye(self):
        d, index = speed.load("side", "0.2")

        found = speed.search_null(d, index)
        by_eye = speed.speed_rows(d, index, 620)
        eye_peak = max(r["handImage"] for r in by_eye
                       if r["handImage"] is not None)

        self.assertLess(found["peak"], eye_peak)
        self.assertLess(found["peak"], 0.5,
                        "the quietest window in the recording is not quiet")

    def test_the_null_floor_is_far_below_every_release_peak(self):
        """A floor is only worth having while the signal clears it. Here the
        release peaks are tens of times the floor, which is the opposite of
        the wrist ANGLE, where the floor swallowed the signal."""
        rows = speed.band_rows()
        for row in rows:
            with self.subTest(release=row["frame"]):
                self.assertGreater(row["handImage"], row["nullImage"] * 10)


class TheTwoScalesAreKeptApart(unittest.TestCase):

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")

    def test_the_image_scale_follows_her_size_in_the_picture(self):
        d, index = speed.load("side", "0.2")
        near = speed.metres_per_pixel(d["frames"][423], index,
                                      speed.athlete_height(d))

        self.assertIsNotNone(near)
        self.assertGreater(near, 0.001)
        self.assertLess(near, 0.02)

    def test_the_two_scales_agree_on_shape_and_differ_on_size(self):
        """They share no arithmetic: one converts pixels by her own height,
        the other reads the model's metres. Agreement on the peak's position
        is evidence; agreement on its value would be surprising."""
        rows = speed.band_rows()
        for row in rows:
            with self.subTest(release=row["frame"]):
                self.assertLessEqual(abs(row["atImage"] - row["atWorld"]),
                                     speed.BEFORE + speed.AFTER)
                self.assertGreater(row["handWorld"], 0.4 * row["handImage"])
                self.assertLess(row["handWorld"], 1.6 * row["handImage"])

    def test_the_athletes_arm_is_never_spent_on_the_engines_unit(self):
        """ONE WORD, TWO ARMS. The clip's arm lengths are the ENGINE's arm;
        converting them with the athlete's inflates every engine metre by
        1.46. This module holds the athlete's figure and READS the engine's,
        so the two cannot be confused by a typo."""
        if not receipt_present():
            self.skipTest("the engine's reach receipt is not on this machine")
        engine, receipt = speed.engine_arm_metres()

        self.assertNotAlmostEqual(engine, speed.ATHLETE_ARM_METRES, places=2)
        self.assertAlmostEqual(
            engine,
            json.loads(receipt.read_text(encoding="utf-8"))["armLengthCm"] / 100.0)


class TheEnginesArmIsReadAndNotTyped(unittest.TestCase):
    """No recording is needed for this, so it runs where the artefacts do not
    reach: the receipt it reads is written by the test itself."""

    def test_the_engine_arm_MOVES_when_the_receipt_says_something_else(self):
        """Proved by a run, not by searching the source for a number. A
        typed `52.68 / 100.0` passed the old text guard, because the string
        it searched for was `0.5268`."""
        with tempfile.TemporaryDirectory() as tmp:
            elsewhere = Path(tmp)
            (elsewhere / "netball_two_hand_snatch_pull_in.reach.json").write_text(
                json.dumps({"armLengthCm": 61.5}), encoding="utf-8")
            with mock.patch.object(speed, "LIBRARY", elsewhere):
                arm, receipt = speed.engine_arm_metres()

        self.assertAlmostEqual(arm, 0.615)
        self.assertEqual(receipt.parent, elsewhere)


class TheNearArmIsMeasuredNotAssumed(unittest.TestCase):

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")

    def test_the_camera_sees_the_left_arm_in_BOTH_runs(self):
        """A side view occludes one arm behind the other, and the model's
        guess at the hidden one is smooth — so the wrong choice would look
        like a clean slow trace rather than an error."""
        for view, set_id, centre in (("side", "0.2", 423),
                                     ("side", "0.1", 615)):
            d, index = speed.load(view, set_id)
            with self.subTest(run=set_id):
                self.assertEqual(speed.check_near_arm(d, index, centre),
                                 speed.NEAR_ARM)

    def test_asking_for_the_arm_the_camera_does_NOT_see_is_refused(self):
        """The check has to REFUSE, not report. Until 2026-09-08 it only
        reported, and nothing but a test ever called it."""
        d, index = speed.load("side", "0.2")

        speed.gate_near_arm(d, index, 423, side="left")
        with self.assertRaises(SystemExit) as refusal:
            speed.gate_near_arm(d, index, 423, side="right")

        self.assertIn("left arm nearer", str(refusal.exception))
        self.assertIn("right", str(refusal.exception))

    def test_the_BAND_itself_stops_when_the_near_arm_disagrees(self):
        """Pinned by a RUN. Delete the call from `band_rows` and this fails.

        The case cannot be found in the footage, because both recordings put
        the same arm nearest. So it is BUILT: the check is made to answer
        `right` and the band must then refuse to report a number.
        """
        with mock.patch.object(speed, "check_near_arm", return_value="right"):
            with self.assertRaises(SystemExit) as refusal:
                speed.band_rows()

        self.assertIn("right arm nearer", str(refusal.exception))

    def test_EVERY_release_is_gated_and_not_just_the_first(self):
        """A gate handed the same frame every time checks one release of
        twelve. The case is built: the check is made to answer `right` for
        the SECOND release only, which is in the same recording as the first,
        so neither a fixed frame nor one check per recording can pass."""
        second = speed.RELEASES[1]
        self.assertEqual((second.view, second.setId),
                         (speed.RELEASES[0].view, speed.RELEASES[0].setId),
                         "this test needs two releases in one recording")

        def only_for_the_second(d, index, centre):
            return "right" if centre == second.frame else "left"

        with mock.patch.object(speed, "check_near_arm", only_for_the_second):
            with self.assertRaises(SystemExit) as refusal:
                speed.band_rows()

        self.assertIn(f"frame {second.frame}", str(refusal.exception))

    def test_the_gate_reads_the_recording_and_is_not_a_constant(self):
        """A gate that answers the same way whatever it is given guards
        nothing. Feed it a recording whose right wrist tracks better and it
        must say so."""
        d, index = speed.load("side", "0.2")
        swapped = json.loads(json.dumps(
            {"source": d["source"], "frames": d["frames"][400:440]}))
        left, right = index["left_wrist"], index["right_wrist"]
        for frame in swapped["frames"]:
            if frame["detected"]:
                marks = frame["landmarks"]
                marks[left]["visibility"], marks[right]["visibility"] = (
                    marks[right]["visibility"], marks[left]["visibility"])

        self.assertEqual(speed.check_near_arm(swapped, index, 23), "right")


class TheBandIsWhatAnotherLaneQuotes(unittest.TestCase):

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")

    def test_the_band_spans_both_scales_and_excludes_the_held_repetition(self):
        rows = speed.band_rows()
        low, high = speed.band(rows)
        held = [r for r in rows if r["frame"] == speed.HELD_REPETITION[2]][0]

        self.assertFalse(held["inBand"])
        self.assertLess(held["handWorld"], low,
                        "the held repetition is inside the band, so excluding "
                        "it changes nothing and the exclusion is decoration")
        self.assertAlmostEqual(low, 2.5, delta=0.1)
        self.assertAlmostEqual(high, 5.4, delta=0.1)

    def test_soft_readings_are_outside_the_band(self):
        rows = speed.band_rows()
        for row in rows:
            if row["reading"] == "soft":
                with self.subTest(release=row["frame"]):
                    self.assertFalse(row["inBand"])

    def test_THE_DOC_EQUALS_THE_INSTRUMENT_ROW_FOR_ROW(self):
        """The movement lane cites the document, so the document is checked
        against the code that made it. A table copied once and then edited is
        how a number gets two values in two files."""
        self.assertTrue(speed.BAND_DOC.exists(), speed.BAND_DOC)
        text = speed.BAND_DOC.read_text(encoding="utf-8")
        written = re.findall(
            r"^\| (0\.\d) \| (\d+) \| (crisp|soft) \| ([\d.]+) \| ([+-]\d+) \| "
            r"([\d.]+) \| ([+-]\d+) \| ([\d.]+) \|$", text, re.M)
        rows = speed.band_rows()

        self.assertEqual(len(written), len(rows))
        for got, row in zip(written, rows):
            with self.subTest(release=row["frame"]):
                self.assertEqual(got, (
                    row["setId"], str(row["frame"]), row["reading"],
                    f"{row['handImage']:.2f}", f"{row['atImage']:+d}",
                    f"{row['handWorld']:.2f}", f"{row['atWorld']:+d}",
                    f"{row['nullImage']:.2f}"))

    def test_the_docs_band_sentence_is_the_instruments_band(self):
        low, high = speed.band()
        text = speed.BAND_DOC.read_text(encoding="utf-8")
        said = re.search(r"band is ([\d.]+) to ([\d.]+) m/s", text)

        self.assertIsNotNone(said)
        self.assertAlmostEqual(float(said.group(1)), low, places=1)
        self.assertAlmostEqual(float(said.group(2)), high, places=1)


class NoDegreesColumnAnywhere(unittest.TestCase):
    """The forearm-to-hand angle is not measurable from this footage: the hand
    is about twenty pixels across, one pixel is 2.0 to 3.3 degrees, and a
    still arm reads 11 to 22 degrees of swing. Its absence is the finding, so
    it is guarded rather than left to memory."""

    def test_the_module_reports_no_angle(self):
        source = Path(speed.__file__).read_text(encoding="utf-8")
        code = "\n".join(line for line in source.splitlines()
                         if not line.strip().startswith("#"))

        for banned in ("math.acos", "math.atan2", "degrees("):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, code)

    def test_no_row_carries_an_angle(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")
        d, index = speed.load("side", "0.2")

        keys = set(speed.speed_rows(d, index, 423)[0])

        # `degraded` is the per-frame quality flag and matches a careless
        # substring test for "deg"; my first version of this guard failed on
        # it. Match the words an angle column would actually use.
        angleish = [k for k in keys
                    if "angle" in k.lower()
                    or k.lower().endswith(("deg", "degrees"))]

        self.assertFalse(angleish, angleish)
        self.assertIn("degraded", keys,
                      "the frame-quality flag is gone, so the case that "
                      "caught my careless guard no longer exists")


class TheReleaseFrameIsTheOneThatWasRead(unittest.TestCase):

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")

    def test_a_release_one_frame_out_moves_the_row(self):
        """If the table were insensitive to the release frame, the reading
        that produced it would not matter and the pictures need not have been
        read at all."""
        d, index = speed.load("side", "0.2")
        here = speed.speed_rows(d, index, 423)
        shifted = speed.speed_rows(d, index, 424)

        self.assertNotEqual([r["frame"] for r in here],
                            [r["frame"] for r in shifted])
        peak_here = max(r["handImage"] for r in here
                        if r["handImage"] is not None)
        peak_shifted = max(r["handImage"] for r in shifted
                           if r["handImage"] is not None)
        offsets_here = [r["offset"] for r in here
                        if r["handImage"] == peak_here]
        offsets_shifted = [r["offset"] for r in shifted
                           if r["handImage"] == peak_shifted]

        self.assertNotEqual(offsets_here, offsets_shifted,
                            "the peak sits at the same offset either way, so "
                            "the release frame is not being used")

    def test_every_window_is_the_length_the_module_says(self):
        d, index = speed.load("side", "0.2")

        rows = speed.speed_rows(d, index, 423)

        self.assertEqual(len(rows), speed.BEFORE + speed.AFTER + 1)
        self.assertEqual(rows[0]["offset"], -speed.BEFORE)
        self.assertEqual(rows[-1]["offset"], speed.AFTER)


class TheBandCarriesItsInputsAndIsPinnedByHash(unittest.TestCase):
    """A band without its inputs cannot be checked by anyone, and these two
    recordings have already been renamed once at source. A filename does not
    say which recording this is; a hash does."""

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")

    def written_inputs(self) -> dict[str, list[str]]:
        text = speed.BAND_DOC.read_text(encoding="utf-8")
        start = text.index("| recording | keypoints sha256 |")
        block = text[start:text.index("\n\n", start)]
        rows = {}
        for line in block.splitlines()[2:]:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows[cells[0].strip("`")] = cells[1:]
        return rows

    def test_BAND_DOC_carries_the_hashes_of_the_files_IT_JUST_READ(self):
        """Hashed here, now, from the files on disk. A hash copied into a
        document once is a hash that will outlive the file it describes."""
        written = self.written_inputs()
        checked = 0
        for row in speed.provenance_rows():
            key = f"{row['view']} {row['setId']}"
            with self.subTest(recording=key):
                cells = written[key]

                self.assertEqual(cells[0], row["keypointsSha256"])
                self.assertEqual(cells[1], row["videoSha256"])
                self.assertEqual(cells[2].lower(),
                                 row["modelSha256"].lower())
                self.assertEqual(cells[3],
                                 str(row["framesPerSecondMeasured"]))
                self.assertEqual(cells[4], str(row["frames"]))
                checked += 1

        self.assertEqual(checked, len(speed.recordings()))
        self.assertEqual(sorted(written), sorted(
            f"{v} {s}" for v, s in speed.recordings()))

    def test_the_recorded_frame_rate_is_the_file_s_own_and_not_a_nominal_30(self):
        """30.012 against 30.0 is 0.04 per cent and invisible at two decimals,
        so a constant 30 passed every test. It is pinned here instead: the
        two recordings do not even agree with each other."""
        rates = {row["framesPerSecondMeasured"]
                 for row in speed.provenance_rows()}

        self.assertNotIn(30.0, rates)
        self.assertEqual(len(rates), len(speed.recordings()),
                         "the two recordings should carry different measured "
                         "rates; a shared one suggests a typed value")

    def test_a_keypoint_file_that_is_not_the_pinned_one_is_REFUSED(self):
        """The case is built, because every file on this machine matches."""
        wrong = speed.Artefact("0" * 64,
                               speed.EXPECTED[("side", "0.2")].videoSha256)
        with mock.patch.dict(speed.EXPECTED, {("side", "0.2"): wrong}):
            with self.assertRaises(SystemExit) as refusal:
                speed.load("side", "0.2")

        self.assertIn("is pinned to 000000000000", str(refusal.exception))
        self.assertIn("renamed at source", str(refusal.exception))

    def test_a_file_describing_ANOTHER_recording_is_REFUSED(self):
        wrong = speed.Artefact(
            speed.EXPECTED[("side", "0.2")].keypointsSha256, "1" * 64)
        with mock.patch.dict(speed.EXPECTED, {("side", "0.2"): wrong}):
            with self.assertRaises(SystemExit) as refusal:
                speed.load("side", "0.2")

        self.assertIn("describes video", str(refusal.exception))

    def test_THE_TWO_SIDE_FILES_SWAPPED_BY_NAME_ARE_REFUSED(self):
        """This is the failure the source rename made real, and before the
        hashes it was caught only by the numbers coming out different — and
        only on a machine that has the files at all."""
        def swapped(view, set_id):
            other = {"0.1": "0.2", "0.2": "0.1"}[set_id]
            return speed.KEYPOINTS / f"keypoints-{view}-{other}.json"

        with mock.patch.object(speed, "keypoint_path", swapped):
            with self.assertRaises(SystemExit) as refusal:
                speed.load("side", "0.2")

        self.assertIn("is not the one this band was measured on",
                      str(refusal.exception))

    def test_a_recording_with_no_recorded_hash_is_REFUSED(self):
        """The front recordings are not measured here and are not pinned. The
        module must say so rather than measure them."""
        with self.assertRaises(SystemExit) as refusal:
            speed.load("front", "0.2")

        self.assertIn("no hash is recorded", str(refusal.exception))

    def test_the_athlete_figures_are_READ_and_a_disagreement_REFUSES(self):
        """They sit in every keypoint file. Typing them here is the pattern
        this module condemns two paragraphs later for the engine's arm."""
        d, _ = speed.load("side", "0.2")

        self.assertAlmostEqual(speed.athlete_height(d),
                               speed.ATHLETE_HEIGHT_METRES)
        self.assertAlmostEqual(d["athlete"]["oneArmReachMetres"],
                               speed.ATHLETE_ARM_METRES)

        with mock.patch.object(speed, "ATHLETE_HEIGHT_METRES", 1.60):
            with self.assertRaises(SystemExit) as refusal:
                speed.load("side", "0.2")

        self.assertIn("calibrated on 1.6", str(refusal.exception))

    def test_the_image_scale_FOLLOWS_the_height_the_file_carries(self):
        """Proved by a run: give the file a taller athlete and every image
        speed must rise in proportion."""
        d, index = speed.load("side", "0.2")
        taller = copy.deepcopy(d)
        taller["athlete"]["heightMetres"] = 2 * d["athlete"]["heightMetres"]

        was = speed.speed_rows(d, index, 423)
        now = speed.speed_rows(taller, index, 423)
        pairs = [(a["handImage"], b["handImage"])
                 for a, b in zip(was, now)
                 if a["handImage"] is not None and b["handImage"] is not None]

        self.assertTrue(pairs)
        for a, b in pairs:
            self.assertAlmostEqual(b, 2 * a, places=6)

    def test_the_world_speed_uses_the_file_s_own_frame_rate(self):
        """A nominal 30 is 0.04 per cent out and invisible in the table. Move
        the file's rate and the speeds must move with it."""
        d, index = speed.load("side", "0.2")
        doubled = copy.deepcopy(d)
        doubled["source"]["framesPerSecondMeasured"] *= 2

        was = speed.speed_rows(d, index, 423)
        now = speed.speed_rows(doubled, index, 423)

        self.assertTrue(was)
        for a, b in zip(was, now):
            self.assertAlmostEqual(b["handWorld"], 2 * a["handWorld"],
                                   places=6)


class TheNullSearchIgnoresAnUntrackedWrist(unittest.TestCase):
    """R08: the visibility filter changed nothing on this footage, because
    the quietest window passes it anyway. A guard whose case cannot be found
    in the data has to have its case BUILT."""

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")

    def frozen(self) -> tuple[dict, dict, int]:
        """A recording with a stretch where the hand does not move at all and
        the wrist is barely tracked: exactly what an untracked wrist looks
        like, and the quietest window in the file by a distance."""
        d, index = speed.load("side", "0.2")
        made = copy.deepcopy(d)
        start, length = 200, speed.BEFORE + speed.AFTER + 3
        still = copy.deepcopy(made["frames"][start]["landmarks"])
        for n in range(start, start + length):
            frame = made["frames"][n]
            frame["detected"] = True
            frame["degraded"] = False
            frame["landmarks"] = copy.deepcopy(still)
            frame["landmarks"][index[f"{speed.NEAR_ARM}_wrist"]]["visibility"] = 0.5
        return made, index, start

    def test_the_filter_CHANGES_which_window_is_chosen(self):
        made, index, start = self.frozen()

        kept = speed.search_null(made, index)
        with mock.patch.object(speed, "NULL_MIN_VISIBILITY", 0.0):
            taken = speed.search_null(made, index)

        self.assertAlmostEqual(taken["peak"], 0.0, places=9)
        self.assertGreaterEqual(taken["start"], start)
        self.assertGreater(kept["peak"], 0.0)
        self.assertNotEqual(kept["start"], taken["start"])

    def test_the_filter_leaves_the_real_recording_alone(self):
        """It must not be doing work on the real files: the searched null is
        the same window with the filter off, which is why the case above had
        to be built."""
        d, index = speed.load("side", "0.2")

        kept = speed.search_null(d, index)
        with mock.patch.object(speed, "NULL_MIN_VISIBILITY", 0.0):
            taken = speed.search_null(d, index)

        self.assertEqual(kept["start"], taken["start"])


class ItRefusesRatherThanGuessesWhenAnArtefactIsAbsent(unittest.TestCase):

    def test_a_missing_keypoint_file_refuses_by_name(self):
        with mock.patch.object(speed, "KEYPOINTS", Path("C:/nowhere")):
            with self.assertRaises(SystemExit) as refusal:
                speed.load("side", "0.2")

        self.assertIn("keypoints-side-0.2.json", str(refusal.exception))

    def test_a_missing_reach_receipt_refuses_rather_than_typing_an_arm(self):
        with mock.patch.object(speed, "LIBRARY", Path("C:/nowhere")):
            with self.assertRaises(SystemExit) as refusal:
                speed.engine_arm_metres()

        self.assertIn("will not type one in", str(refusal.exception))


if __name__ == "__main__":
    unittest.main()
