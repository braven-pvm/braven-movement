"""Tests for the keypoint writer's sync block, and for the re-stamp.

WHY THIS FILE EXISTS. Until 2026-09-04 `_sync_block` stamped "two visual events
matched by eye; no clap exists in this material" into the sync block of every
keypoint file it wrote. Two claps were later found in the front recording of set
0.1, at 5.800 s and 17.835 s, so the writer had been putting a false claim into
new artefacts long after it was known to be false — and it kept doing so while
the documents that corrected it were being merged.

The fault is not the sentence. It is that a function which measures an OFFSET
made an assertion about what the RECORDING CONTAINS, which it never looked at.
The tests below hold the boundary: the block may say what was done, and may not
say what was ruled out.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from video_dry_run import judge_capture, verdict
from video_keypoints import (
    METHOD_KINDS,
    REFERENCE_VIEW,
    SYNC,
    _sync_block,
    _sync_inputs,
    restamp,
)

MOVEMENT = "netball_two_hand_snatch_pull_in"


def block(view: str = "front", set_id: str = "0.1") -> dict:
    return _sync_block(view, set_id, *_sync_inputs(view, set_id))


def keypoint_file(sync: dict, view: str = "front", set_id: str = "0.1") -> Path:
    document = {
        "schemaVersion": "video-keypoints-1",
        "source": {"view": view, "setId": set_id, "videoFile": f"{view} {set_id}.mp4",
                   "videoSha256": "deadbeef", "framesPerSecondMeasured": 30.0},
        "model": {"tool": "mediapipe"},
        "athlete": {"heightMetres": 1.77},
        "sync": sync,
        "generatedFrom": {"commit": "abc1234", "treeWasClean": True},
        "frames": [{"ptsSeconds": 0.0, "frameIndex": 0, "detected": False}],
    }
    path = Path(tempfile.mkdtemp()) / f"keypoints-{view}-{set_id}.json"
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return path


class TheBlockSaysWhatWasDoneAndNotWhatWasRuledOut(unittest.TestCase):

    # THE STALE CLAIM, quoted once so every assertion below uses the same
    # string. A withdrawal has to be allowed to name what it withdraws, so the
    # tests forbid the CLAIM and not the word — an earlier version of this file
    # asserted "no clap" was absent and failed on the sentence withdrawing it.
    STALE = "no clap exists in this material"

    def test_the_asserting_fields_make_no_claim_about_the_recording(self):
        """The exact fault. `_sync_block` measures an offset; whether a clap
        exists is not something it looked at, so its ASSERTIONS may not say.

        `methodNote` is exempt and separately required to mention it: that field
        is the withdrawal, and a withdrawal that cannot name what it withdraws
        leaves the next reader to guess."""
        found = block()

        for field in ("method", "note", "referenceView"):
            self.assertNotIn("clap", str(found.get(field, "")), field)
        self.assertNotIn(self.STALE, json.dumps(found))

    def test_the_method_states_only_the_method(self):
        self.assertEqual(block()["method"], "two visual events matched by eye")

    def test_the_grade_is_a_field_of_its_own(self):
        """A consumer deciding whether to trust a pairing needs the grade, and a
        grade it has to parse out of a sentence is not a field."""
        found = block()

        self.assertEqual(found["methodKind"], "eye")
        self.assertIn(found["methodKind"], METHOD_KINDS)

    def test_an_unmeasured_set_says_unknown_rather_than_nothing(self):
        found = block(set_id="0.2")

        self.assertFalse(found["measured"])
        self.assertEqual(found["methodKind"], "unknown")
        self.assertIn(found["methodKind"], METHOD_KINDS)

    def test_an_unmeasured_set_carries_no_method_and_no_worked_example(self):
        """A set nobody has measured must not carry a worked example of nulls:
        the schema tells a consumer to assert
        thisViewSeconds + offset == referenceViewSeconds on load, and that
        assertion on None is a crash rather than a check."""
        found = block(set_id="0.2")

        self.assertNotIn("method", found)
        self.assertNotIn("worked", found)

    def test_the_note_names_what_was_withdrawn(self):
        """A withdrawal that does not quote what it withdraws leaves the next
        reader to wonder what changed."""
        note = block()["methodNote"]

        self.assertIn("no clap existed", note)
        self.assertIn("5.800", note)
        self.assertIn("17.835", note)

    def test_every_kind_the_writer_can_emit_is_in_the_vocabulary(self):
        for set_id in ("0.1", "0.2"):
            for view in ("front", "side"):
                with self.subTest(view=view, set_id=set_id):
                    self.assertIn(block(view, set_id)["methodKind"], METHOD_KINDS)


class TheReferenceViewsZeroIsADefinition(unittest.TestCase):

    def test_the_reference_view_offset_is_zero(self):
        self.assertEqual(block(REFERENCE_VIEW)["offsetSecondsToReference"], 0.0)

    def test_the_other_view_carries_the_measured_offset(self):
        other = "side" if REFERENCE_VIEW == "front" else "front"

        self.assertEqual(block(other)["offsetSecondsToReference"],
                         SYNC["0.1"]["offsetSecondsToReference"])

    def test_one_definition_serves_both_callers(self):
        """`extract` and `restamp` must derive the block the same way. A
        re-stamp with its own reading of SYNC would drift from the writer the
        first time either changed."""
        path = keypoint_file({"method": "anything at all"})

        self.assertEqual(restamp(path)["after"], block())


class TheRestampTouchesTheSyncBlockAndNothingElse(unittest.TestCase):

    def test_every_other_key_survives_byte_for_byte(self):
        """RE-EXTRACTION WOULD CHANGE MORE THAN THE FAULT. Running MediaPipe
        again over 866 frames to correct a sentence re-derives every landmark
        too. The re-stamp reads, replaces one block, and writes."""
        path = keypoint_file({"method": "two visual events matched by eye; "
                                        "no clap exists in this material"})
        before = json.loads(path.read_text(encoding="utf-8"))
        restamp(path)
        after = json.loads(path.read_text(encoding="utf-8"))

        del before["sync"], after["sync"]
        self.assertEqual(before, after)

    def test_the_claim_is_gone_from_the_file(self):
        stale = "two visual events matched by eye; no clap exists in this material"
        path = keypoint_file({"method": stale})
        restamp(path)
        text = path.read_text(encoding="utf-8")

        self.assertNotIn("no clap exists in this material", text)
        self.assertIn("no claim about what else the recordings contain", text)

    def test_the_offset_and_the_worked_example_are_preserved(self):
        path = keypoint_file({"method": "stale"})
        after = restamp(path)["after"]

        self.assertEqual(after["offsetSecondsToReference"], 0.0)
        self.assertEqual(after["worked"]["referenceViewSeconds"], 9.25)

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
    """THE RE-STAMP EDITS DATA THE GATE READS, so it has to be provably inert.

    `judge_capture` reads `offsetUncertaintySeconds` from the sync block and
    nothing else. This mutates every other field — method, methodKind,
    methodNote, note, referenceView, the worked example — and requires the
    capture verdict to come back identical. The same guard the ball annotation
    carries, applied to the artefact this pack rewrites.
    """

    def evidence(self, sync: dict) -> dict:
        return {"front": {"source": {}}, "side": {"sync": sync},
                "lift": {"rows": [], "residualMetres": {"framePairs": 0}}}

    def test_the_verdict_is_unchanged_by_the_restamp(self):
        stale = {"referenceView": "front", "measured": True,
                 "offsetSecondsToReference": 1.0,
                 "offsetUncertaintySeconds": 0.15,
                 "method": "two visual events matched by eye; "
                           "no clap exists in this material",
                 "worked": {"event": "first catch, seen in both views",
                            "thisViewSeconds": 8.25, "referenceViewSeconds": 9.25}}
        fresh = block("side")

        before = verdict(judge_capture(self.evidence(stale), MOVEMENT))
        after = verdict(judge_capture(self.evidence(fresh), MOVEMENT))

        self.assertEqual(before, after)

    def test_mutating_every_prose_field_moves_nothing(self):
        fresh = block("side")
        mutated = dict(fresh)
        for field in ("method", "methodKind", "methodNote", "note",
                      "referenceView"):
            if field in mutated:
                mutated[field] = "MUTATED, and no verdict may notice."
        mutated["worked"] = {"event": "MUTATED", "thisViewSeconds": None,
                             "referenceViewSeconds": None}

        self.assertEqual(verdict(judge_capture(self.evidence(fresh), MOVEMENT)),
                         verdict(judge_capture(self.evidence(mutated), MOVEMENT)))

    def test_the_uncertainty_is_the_one_field_that_does_move_it(self):
        """The converse, so the test above is not passing for want of anything
        reaching the verdict at all.

        TIGHTENING, not loosening. The written 0.15 s already FAILS the gate's
        one-frame bar, so 5.0 s fails it too and the verdicts match — a first
        version of this test compared two failures and proved nothing. 0.01 s
        passes, which is the only direction that discriminates here."""
        fresh = block("side")
        tightened = {**fresh, "offsetUncertaintySeconds": 0.01}

        self.assertNotEqual(
            verdict(judge_capture(self.evidence(fresh), MOVEMENT)),
            verdict(judge_capture(self.evidence(tightened), MOVEMENT)))


if __name__ == "__main__":
    unittest.main()
