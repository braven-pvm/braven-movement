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
        reference, other = block("front", "0.1"), block("side", "0.2")

        self.assertEqual(reference["frameOffsetToReference"], 0)
        self.assertEqual(reference["pairedWith"], "side 0.2.mp4")
        self.assertEqual(other["frameOffsetToReference"], -5)
        self.assertEqual(other["pairedWith"], "front 0.1.mp4")

    def test_seconds_are_never_the_measurement(self):
        """`offsetSecondsToReference` is GONE. Two offsets in seconds have been
        published from this material and both were withdrawn; the field that
        carried them does not survive, so nothing can read one by habit."""
        for view, set_id in (("front", "0.1"), ("side", "0.2"),
                             ("front", "0.2"), ("side", "0.1")):
            with self.subTest(view=view, set_id=set_id):
                self.assertNotIn("offsetSecondsToReference", block(view, set_id))

    def test_the_derived_seconds_say_they_are_derived_and_that_they_drift(self):
        note = block("side", "0.2")["derivedNote"]

        self.assertIn("DERIVED", note)
        self.assertIn("drift", note)

    def test_the_two_frame_periods_differ_which_is_why(self):
        pair = PAIRS["front 0.1 + side 0.2"]
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
        self.pair = PAIRS["front 0.1 + side 0.2"]
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
        aside = PAIRS["front 0.1 + side 0.2"]["setAside"]

        self.assertEqual(len(aside), 1)
        self.assertEqual(aside[0]["frameDifference"], 4)
        self.assertIn("soft", aside[0]["why"].lower())

    def test_the_set_aside_row_does_not_satisfy_the_arithmetic(self):
        """If it ever does, someone has changed a number to make it fit."""
        pair = PAIRS["front 0.1 + side 0.2"]
        row = pair["setAside"][0]

        self.assertNotEqual(row["otherIndex"],
                            row["referenceIndex"] + pair["frameOffsetToReference"])

    def test_a_clap_is_never_an_anchor(self):
        """A ball meeting hands is a one-frame transition with no judgement in
        it. A clasp is not, and both claps are checks or set aside."""
        pair = PAIRS["front 0.1 + side 0.2"]

        for anchor in pair["anchors"]:
            self.assertIn("ball into hands", anchor["event"])
        for row in pair["checks"] + pair["setAside"]:
            self.assertIn("clap", row["event"])


class WhatIsNotEstablishedSaysSo(unittest.TestCase):

    def test_the_other_two_files_carry_no_offset_and_no_partner(self):
        for view, set_id in (("front", "0.2"), ("side", "0.1")):
            with self.subTest(view=view, set_id=set_id):
                found = block(view, set_id)

                self.assertFalse(found["measured"])
                self.assertIsNone(found["pairedWith"])
                self.assertIsNone(found["frameOffsetToReference"])
                self.assertEqual(found["methodKind"], "unknown")

    def test_they_are_named_as_unknown_rather_than_unpaired(self):
        self.assertEqual(set(PAIRING_UNKNOWN),
                         {"front 0.2.mp4", "side 0.1.mp4"})

    def test_the_note_says_the_names_are_wrong_and_not_that_a_partner_is_absent(self):
        note = block("front", "0.2")["note"]

        self.assertIn("NO PARTNER IS ESTABLISHED", note)
        self.assertIn("not a claim that it has none", note)
        self.assertIn("the file names are wrong", note.lower())

    def test_no_elimination_argument_is_made_anywhere(self):
        """"There are four files, so the other two must pair" is a guess."""
        import inspect, video_keypoints as module
        text = inspect.getsource(module)

        self.assertIn("NO ELIMINATION ARGUMENT IS MADE", text)

    def test_the_failed_attempt_is_recorded_with_its_readings(self):
        import inspect, video_keypoints as module
        text = inspect.getsource(module)

        self.assertIn("77 and 75", text)
        self.assertIn("two-handed", text)
        self.assertIn("is not evidence in a clip of", text)


class TheBlockSaysWhatWasDoneAndNotWhatWasRuledOut(unittest.TestCase):

    STALE = "no clap exists in this material"

    def test_the_asserting_fields_make_no_claim_about_the_recording(self):
        found = block("side", "0.2")

        for field in ("method", "note", "referenceView"):
            self.assertNotIn("clap", str(found.get(field, "")), field)
        self.assertNotIn(self.STALE, json.dumps(found))

    def test_the_withdrawal_names_all_three_claims(self):
        note = block("side", "0.2")["methodNote"]

        self.assertIn("no clap existed", note)
        self.assertIn("+1.0 s", note)
        self.assertIn("-0.7295", note)
        self.assertIn("the file names are wrong", note.lower())

    def test_every_kind_the_writer_emits_is_in_the_vocabulary(self):
        for view, set_id in (("front", "0.1"), ("side", "0.2"),
                             ("front", "0.2"), ("side", "0.1")):
            with self.subTest(view=view, set_id=set_id):
                self.assertIn(block(view, set_id)["methodKind"], METHOD_KINDS)

    def test_pair_for_finds_a_file_by_name_not_by_set(self):
        """The whole point: a set id is a label and the label is wrong."""
        key, pair = pair_for("side", "0.2")

        self.assertEqual(key, "front 0.1 + side 0.2")
        self.assertEqual(pair_for("side", "0.1"), (None, None))


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
        path = keypoint_file({"measured": True,
                              "offsetSecondsToReference": -0.7295,
                              "worked": {"thisViewSeconds": 9.8628}},
                             view="side", set_id="0.1")
        after = restamp(path)["after"]

        self.assertFalse(after["measured"])
        self.assertNotIn("-0.7295", path.read_text(encoding="utf-8"))

    def test_a_paired_file_gains_its_frame_offset(self):
        path = keypoint_file({"method": "stale"}, view="side", set_id="0.2")
        after = restamp(path)["after"]

        self.assertEqual(after["frameOffsetToReference"], -5)
        self.assertEqual(after["pairedWith"], "front 0.1.mp4")

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
