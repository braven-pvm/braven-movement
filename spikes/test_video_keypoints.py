"""Tests for the keypoint writer's sync block, the pair table, and the re-stamp.

WHAT THIS FILE IS GUARDING, in the order the faults arrived.

1. `_sync_block` once stamped "no clap exists in this material" into every file
   it wrote — a function that measures an OFFSET asserting what the RECORDING
   CONTAINS, which it never looked at.
2. Set 0.1 as labelled carried +1.0 s, then -0.7295 s graded "shared event".
   Both were withdrawn. The second named a frame in each view where a ball meets
   hands, and they were DIFFERENT CATCHES one toss cycle apart.
3. The cause of all of it: THE FILE NAMES ARE WRONG. `front 0.1.mp4` pairs with
   `side 0.2.mp4`. Nobody was measuring a bad offset; everybody was measuring
   between two files that are not a pair.

So the measurement is now a FRAME COUNT between two named FILES, and the tests
below check that arithmetic against the containers themselves rather than
against anything this repository wrote down.
"""

from __future__ import annotations

import contextlib
import json
import tempfile
import unittest
from pathlib import Path

from video_dry_run import judge_capture, verdict
from video_keypoints import (
    METHOD_KINDS,
    PAIRING_UNKNOWN,
    PAIRS,
    REFERENCE_VIEW,
    SYNC_UNCERTAINTY_SECONDS,
    _sync_block,
    _sync_inputs,
    pair_for,
    restamp,
)

MOVEMENT = "netball_two_hand_snatch_pull_in"
SAMPLES = Path("F:/Repositories/braven-movement/.assets/video-samples/session-1.0")


# THE TESTS READ THE TABLE; THEY DO NOT NAME FILES. Every hard-coded
# "front 0.1 + side 0.2" and "side 0.2.mp4" in this file broke on 2026-09-07,
# when Marius swapped the two side files' names at source and the table
# followed them. Twenty-five tests failed at once on names alone, while the
# thing they check had not moved by a frame. A test that names a file is a
# test that a rename can break without any measurement changing.
THE_PAIR = next(iter(PAIRS))
PAIR = PAIRS[THE_PAIR]
REFERENCE_SET = PAIR["referenceFile"].split(" ", 1)[1].removesuffix(".mp4")
OTHER_SET = PAIR["otherFile"].split(" ", 1)[1].removesuffix(".mp4")
# EMPTY SINCE 2026-09-07: both pairs are established. The tests that need an
# unpaired file skip rather than assert, because "nothing is unpaired" is a
# RESULT and a test that requires one would have to be deleted to record it.
UNPAIRED_SET = (PAIRING_UNKNOWN[1].split(" ", 1)[1].removesuffix(".mp4")
                if PAIRING_UNKNOWN else None)


def block(view: str = "front", set_id: str = "0.1") -> dict:
    return _sync_block(view, set_id, *_sync_inputs(view, set_id))


def keypoint_file(sync: dict, view: str = "front", set_id: str = "0.1") -> Path:
    document = {
        "schemaVersion": "video-keypoints-1",
        "source": {"view": view, "setId": set_id, "videoFile": f"{view} {set_id}.mp4",
                   "videoSha256": "deadbeef", "framesPerSecondMeasured": 30.0},
        "model": {"tool": "mediapipe"},
        "sync": sync,
        "generatedFrom": {"commit": "abc1234", "treeWasClean": True},
        "frames": [{"ptsSeconds": 0.0, "frameIndex": 0, "detected": False}],
    }
    path = Path(tempfile.mkdtemp()) / f"keypoints-{view}-{set_id}.json"
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return path


def pts(file_name: str) -> list[float] | None:
    """The container's own frame timestamps, or None if the asset is absent."""
    import subprocess
    path = SAMPLES / file_name
    if not path.exists():
        return None
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "frame=pts_time", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout
    return [float(v.strip().rstrip(",")) for v in out.split()
            if v.strip().rstrip(",")]


class TheMeasurementIsAFrameCount(unittest.TestCase):
    """A frame offset does not drift. A number of seconds does."""

    def test_the_paired_files_carry_the_frame_offset_and_its_partner(self):
        reference = block("front", REFERENCE_SET)
        other = block("side", OTHER_SET)

        self.assertEqual(reference["frameOffsetToReference"], 0)
        self.assertEqual(reference["pairedWith"], PAIR["otherFile"])
        self.assertEqual(other["frameOffsetToReference"], -5)
        self.assertEqual(other["pairedWith"], "front 0.1.mp4")

    def test_seconds_are_never_the_measurement(self):
        """`offsetSecondsToReference` is GONE. Two offsets in seconds have been
        published from this material and both were withdrawn; the field that
        carried them does not survive, so nothing can read one by habit."""
        for view in ("front", "side"):
            for set_id in ("0.1", "0.2"):
                with self.subTest(view=view, set_id=set_id):
                    self.assertNotIn("offsetSecondsToReference",
                                     block(view, set_id))

    def test_the_derived_seconds_say_they_are_derived_and_that_they_drift(self):
        note = block("side", OTHER_SET)["derivedNote"]

        self.assertIn("DERIVED", note)
        self.assertIn("drift", note)

    def test_the_two_frame_periods_differ_which_is_why(self):
        pair = PAIR
        periods = set(pair["framePeriodSeconds"].values())

        self.assertEqual(len(periods), 2, "if they were equal there would be "
                                          "no drift and no reason for this test")


class TheIndexArithmeticHoldsOnTheContainers(unittest.TestCase):
    """The anchors are checked against the FILES, not against this repository.

    Every recorded index and second is read back from the container's own pts
    list. A transcription error, a re-encode, or a swapped file fails here —
    and a swapped file is not hypothetical: two of these four are named wrong.
    """

    def setUp(self):
        self.pair = PAIR
        self.reference = pts(self.pair["referenceFile"])
        self.other = pts(self.pair["otherFile"])
        if self.reference is None or self.other is None:
            self.skipTest("the session 1.0 assets are not present")

    def rows(self):
        return self.pair["anchors"] + self.pair["checks"]

    def test_every_anchor_and_check_satisfies_the_index_arithmetic(self):
        offset = self.pair["frameOffsetToReference"]

        for row in self.rows():
            with self.subTest(event=row["event"]):
                self.assertEqual(row["otherIndex"],
                                 row["referenceIndex"] + offset)

    def test_every_recorded_second_is_that_index_own_timestamp(self):
        for row in self.rows():
            with self.subTest(event=row["event"]):
                self.assertAlmostEqual(self.reference[row["referenceIndex"]],
                                       row["referenceSeconds"], places=3)
                self.assertAlmostEqual(self.other[row["otherIndex"]],
                                       row["otherSeconds"], places=3)

    def test_every_derived_offset_is_the_difference_of_those_timestamps(self):
        for row in self.rows():
            with self.subTest(event=row["event"]):
                self.assertAlmostEqual(
                    row["otherSeconds"] - row["referenceSeconds"],
                    row["derivedSecondsOffset"], places=3)

    def test_the_two_anchors_are_at_least_ten_seconds_apart(self):
        """One anchor is always satisfiable — pick any two events and an offset
        exists. It is the SECOND, far away, that a wrong offset cannot survive,
        because a periodic movement only repeats on its own period."""
        seconds = [a["referenceSeconds"] for a in self.pair["anchors"]]

        self.assertGreaterEqual(max(seconds) - min(seconds), 10.0)

    def test_the_derived_offset_drifts_across_the_clip(self):
        """The reason seconds are not the measurement, shown rather than said."""
        first, last = self.pair["anchors"][0], self.pair["anchors"][-1]

        self.assertNotAlmostEqual(first["derivedSecondsOffset"],
                                  last["derivedSecondsOffset"], places=3)
        self.assertLess(abs(first["derivedSecondsOffset"]
                            - last["derivedSecondsOffset"]), 1 / 30)


class TheDisagreementIsRecordedRatherThanResolved(unittest.TestCase):

    def test_the_soft_anchor_is_set_aside_with_its_frame_difference(self):
        """The FIRST clap gives 4, not 5. Calling the side one frame earlier
        would make it agree, and that is exactly why it is not an anchor."""
        aside = PAIR["setAside"]

        self.assertEqual(len(aside), 1)
        self.assertEqual(aside[0]["frameDifference"], 4)
        self.assertIn("soft", aside[0]["why"].lower())

    def test_the_set_aside_row_does_not_satisfy_the_arithmetic(self):
        """If it ever does, someone has changed a number to make it fit."""
        pair = PAIR
        row = pair["setAside"][0]

        self.assertNotEqual(row["otherIndex"],
                            row["referenceIndex"] + pair["frameOffsetToReference"])

    def test_a_clap_is_never_an_anchor(self):
        """A ball meeting hands is a one-frame transition with no judgement in
        it. A clasp is not, and both claps are checks or set aside."""
        pair = PAIR

        for anchor in pair["anchors"]:
            self.assertIn("ball into hands", anchor["event"])
        for row in pair["checks"] + pair["setAside"]:
            self.assertIn("clap", row["event"])


class WhatIsNotEstablishedSaysSo(unittest.TestCase):

    def test_no_file_is_both_paired_and_unpaired(self):
        """PAIRING_UNKNOWN is empty now, and the invariant still has to hold:
        a file cannot appear in the pair table AND in the unpaired list."""
        paired = {f for p in PAIRS.values()
                  for f in (p["referenceFile"], p["otherFile"])}

        self.assertEqual(paired & set(PAIRING_UNKNOWN), set())

    def test_every_recording_appears_in_exactly_one_pair(self):
        """The result of 2026-09-07: all four files are accounted for."""
        seen = [f for p in PAIRS.values()
                for f in (p["referenceFile"], p["otherFile"])]

        self.assertEqual(len(seen), len(set(seen)), "a file is in two pairs")
        self.assertEqual(set(seen) | set(PAIRING_UNKNOWN), {
            "front 0.1.mp4", "front 0.2.mp4", "side 0.1.mp4", "side 0.2.mp4"})

    def test_an_unmeasured_file_would_still_say_so_honestly(self):
        """Every file has an established partner since 2026-09-07, so no real
        file reaches the unmeasured note. THE GUARD IS STILL WANTED for the
        next file that has no partner yet.

        A FIRST VERSION OF THIS TEST GREPPED THE MODULE SOURCE, which is a
        guard on text and not on code: it would pass on the words sitting in a
        comment while the writer emitted something else. This patches
        `PAIRING_UNKNOWN` to a fabricated file, CALLS the writer, and reads the
        note it actually produces."""
        import unittest.mock as mock
        import video_keypoints as module

        with mock.patch.object(module, "PAIRING_UNKNOWN", ("side 9.9.mp4",)):
            found = module._sync_block("side", "9.9", False,
                                       {"file": "side 9.9.mp4"})

        note = found["note"]
        self.assertIn("NO PARTNER IS ESTABLISHED", note)
        self.assertIn("not a claim that it has none", note)
        self.assertIn("side 9.9.mp4", note)
        # It must name what IS established rather than leave a reader hunting.
        for pair in PAIRS.values():
            self.assertIn(pair["referenceFile"], note)


class TheBlockSaysWhatWasDoneAndNotWhatWasRuledOut(unittest.TestCase):

    STALE = "no clap exists in this material"

    def test_the_asserting_fields_make_no_claim_about_the_recording(self):
        found = block("side", "0.2")

        for field in ("method", "note", "referenceView"):
            self.assertNotIn("clap", str(found.get(field, "")), field)
        self.assertNotIn(self.STALE, json.dumps(found))

    def test_the_withdrawal_names_all_three_claims(self):
        note = block("side", OTHER_SET)["methodNote"]

        self.assertIn("no clap existed", note)
        self.assertIn("+1.0 s", note)
        self.assertIn("-0.7295", note)
        # The fourth withdrawal is the mislabel itself, and it now reads as a
        # correction that HAS been made rather than as a fault still standing.
        self.assertIn("renamed", note.lower())

    def test_every_kind_the_writer_emits_is_in_the_vocabulary(self):
        for view in ("front", "side"):
            for set_id in ("0.1", "0.2"):
                with self.subTest(view=view, set_id=set_id):
                    self.assertIn(block(view, set_id)["methodKind"],
                                  METHOD_KINDS)

    def test_pair_for_finds_a_file_by_name_not_by_set(self):
        """The whole point: a set id is a label and the label is wrong."""
        key, pair = pair_for("side", OTHER_SET)

        self.assertEqual(key, THE_PAIR)
        # A set id that names no file at all still resolves to nothing.
        self.assertEqual(pair_for("side", "9.9"), (None, None))


class TheRestampTouchesTheSyncBlockAndNothingElse(unittest.TestCase):

    def test_every_other_key_survives_byte_for_byte(self):
        path = keypoint_file({"method": "stale"})
        before = json.loads(path.read_text(encoding="utf-8"))
        restamp(path)
        after = json.loads(path.read_text(encoding="utf-8"))

        del before["sync"], after["sync"]
        self.assertEqual(before, after)

    def test_a_withdrawn_offset_is_stripped_from_an_existing_file(self):
        """How the artefacts stopped claiming -0.7295 without re-extraction."""
        # RUN ON A FABRICATED UNPAIRED FILE, NOT SKIPPED. Every real file has
        # had a partner since 2026-09-07, so this guarded nothing and would
        # have skipped for ever. The behaviour it holds is real: the re-stamp
        # STRIPS a withdrawn offset from a file that already carries one, which
        # is how the artefacts stopped claiming -0.7295 without re-extraction.
        import unittest.mock as mock
        import video_keypoints as module

        path = keypoint_file({"measured": True,
                              "offsetSecondsToReference": -0.7295,
                              "worked": {"thisViewSeconds": 9.8628}},
                             view="side", set_id="9.9")
        with mock.patch.object(module, "PAIRING_UNKNOWN", ("side 9.9.mp4",)):
            after = restamp(path)["after"]

        self.assertFalse(after["measured"])
        self.assertNotIn("-0.7295", path.read_text(encoding="utf-8"))

    def test_a_paired_file_gains_its_frame_offset(self):
        path = keypoint_file({"method": "stale"}, view="side",
                             set_id=OTHER_SET)
        after = restamp(path)["after"]

        self.assertEqual(after["frameOffsetToReference"],
                         PAIR["frameOffsetToReference"])
        self.assertEqual(after["pairedWith"], PAIR["referenceFile"])

    def test_running_it_twice_changes_nothing_the_second_time(self):
        path = keypoint_file({"method": "stale"})
        restamp(path)
        once = path.read_text(encoding="utf-8")
        restamp(path)

        self.assertEqual(once, path.read_text(encoding="utf-8"))

    def test_a_file_with_no_source_is_refused_rather_than_guessed(self):
        path = keypoint_file({"method": "stale"})
        document = json.loads(path.read_text(encoding="utf-8"))
        del document["source"]["view"]
        path.write_text(json.dumps(document), encoding="utf-8")

        with self.assertRaises(ValueError):
            restamp(path)


class NoProseInTheSyncBlockCanMoveAVerdict(unittest.TestCase):
    """The re-stamp edits data the gate reads, so it has to be provably inert
    in everything except the reading the gate is entitled to."""

    def evidence(self, sync: dict) -> dict:
        return {"front": {"source": {}}, "side": {"sync": sync},
                "lift": {"rows": [], "residualMetres": {"framePairs": 0}}}

    def test_mutating_every_prose_field_moves_nothing(self):
        fresh = block("side", "0.2")
        mutated = dict(fresh)
        for field in ("method", "methodKind", "methodNote", "note",
                      "referenceView", "pairedWith", "derivedNote"):
            if field in mutated:
                mutated[field] = "MUTATED, and no verdict may notice."

        self.assertEqual(verdict(judge_capture(self.evidence(fresh), MOVEMENT)),
                         verdict(judge_capture(self.evidence(mutated), MOVEMENT)))

    def test_the_uncertainty_is_the_one_field_that_does_move_it(self):
        fresh = block("side", "0.2")
        loosened = {**fresh, "offsetUncertaintySeconds": 5.0}

        self.assertNotEqual(
            verdict(judge_capture(self.evidence(fresh), MOVEMENT)),
            verdict(judge_capture(self.evidence(loosened), MOVEMENT)))

    def test_the_uncertainty_is_one_frame(self):
        self.assertAlmostEqual(SYNC_UNCERTAINTY_SECONDS, 1 / 30, places=3)


if __name__ == "__main__":
    unittest.main()
