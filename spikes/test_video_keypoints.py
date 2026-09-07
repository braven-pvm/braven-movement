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

import contextlib
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


@contextlib.contextmanager
def measured(set_id="0.9", offset=-0.7295, this=9.8628, reference=9.1333):
    """A measured set, injected for the duration of one test.

    THE TESTS BELOW USED TO READ SYNC DIRECTLY, and every one of them broke the
    day both real offsets were withdrawn and SYNC went empty. A test of the
    WRITER should not depend on what has been measured: the writer's job is to
    render whatever it is given, and what has been measured is data.
    """
    import video_keypoints as module
    module.SYNC[set_id] = {"offsetSecondsToReference": offset,
                           "thisViewSeconds": this,
                           "referenceViewSeconds": reference}
    try:
        yield set_id
    finally:
        del module.SYNC[set_id]


def keypoint_file(sync: dict, view: str = "front", set_id: str = "0.1") -> Path:
    """A minimal keypoint document for the re-stamp to work on."""
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
        with measured() as sid:
            found = block("side", sid)

        for field in ("method", "note", "referenceView"):
            self.assertNotIn("clap", str(found.get(field, "")), field)
        self.assertNotIn(self.STALE, json.dumps(found))

    def test_the_method_states_only_the_method(self):
        with measured() as sid:
            found = block("side", sid)
        self.assertEqual(
            found["method"],
            "the frame the ball first meets her hands on the first catch, "
            "read in both views by container timestamp")

    def test_the_grade_is_a_field_of_its_own(self):
        """A consumer deciding whether to trust a pairing needs the grade, and a
        grade it has to parse out of a sentence is not a field."""
        with measured() as sid:
            found = block("side", sid)

        self.assertEqual(found["methodKind"], "shared-event")
        self.assertIn(found["methodKind"], METHOD_KINDS)

    def test_an_unmeasured_set_says_unknown_rather_than_nothing(self):
        # A set NOT in SYNC. Both 0.1 and 0.2 are measured since 2026-09-07, so
        # this asks for one that is not rather than assuming 0.2 still is.
        self.assertNotIn("0.3", SYNC)
        found = block(set_id="0.3")

        self.assertFalse(found["measured"])
        self.assertEqual(found["methodKind"], "unknown")
        self.assertIn(found["methodKind"], METHOD_KINDS)

    def test_an_unmeasured_set_carries_no_method_and_no_worked_example(self):
        """A set nobody has measured must not carry a worked example of nulls:
        the schema tells a consumer to assert
        thisViewSeconds + offset == referenceViewSeconds on load, and that
        assertion on None is a crash rather than a check."""
        found = block(set_id="0.3")

        self.assertNotIn("method", found)
        self.assertNotIn("worked", found)

    def test_the_note_names_what_was_withdrawn(self):
        """A withdrawal that does not quote what it withdraws leaves the next
        reader to wonder what changed."""
        with measured() as sid:
            note = block("side", sid)["methodNote"]

        self.assertIn("no clap existed", note)
        self.assertIn("5.800", note)
        self.assertIn("17.835", note)

    def test_every_worked_example_satisfies_the_arithmetic(self):
        """THE SCHEMA TELLS A CONSUMER TO ASSERT THIS ON LOAD, so a worked
        example that does not satisfy it is worse than none.

        The offsets are the difference between two real container timestamps.
        An earlier version quoted midpoints between frames, which cannot
        satisfy the assertion and which no reader could reproduce from the
        file."""
        with measured() as injected:
            for set_id in list(SYNC) + [injected]:
                for view in ("front", "side"):
                    with self.subTest(view=view, set_id=set_id):
                        found = block(view, set_id)
                        worked = found["worked"]
                        self.assertAlmostEqual(
                            worked["thisViewSeconds"]
                            + found["offsetSecondsToReference"],
                            worked["referenceViewSeconds"], places=6)

    def test_no_set_carries_a_measured_offset(self):
        """BOTH OFFSETS FOR SET 0.1 ARE WITHDRAWN (2026-09-07) and neither is
        replaced: the event ledger finds no constant offset that beats chance,
        so the two files are not a synchronous pair. Set 0.2's ledger is not
        read. An empty SYNC is the honest state and this pins it, so that a
        number cannot creep back without a ledger behind it."""
        self.assertEqual(SYNC, {})
        for set_id in ("0.1", "0.2"):
            for view in ("front", "side"):
                with self.subTest(view=view, set_id=set_id):
                    found = block(view, set_id)
                    self.assertFalse(found["measured"])
                    self.assertEqual(found["methodKind"], "unknown")
                    self.assertNotIn("worked", found)

    def test_the_withdrawal_of_both_offsets_is_recorded_beside_SYNC(self):
        """A withdrawal that does not name what it withdraws leaves the next
        reader to rediscover it. Both numbers and the reason are in the source."""
        import inspect, video_keypoints as module
        text = inspect.getsource(module)

        self.assertIn("-0.7295", text)
        self.assertIn("+1.0 s", text)
        self.assertIn("THEY ARE NOT THE SAME CATCH", text)

    def test_every_kind_the_writer_can_emit_is_in_the_vocabulary(self):
        for set_id in ("0.1", "0.2", "0.3"):
            for view in ("front", "side"):
                with self.subTest(view=view, set_id=set_id):
                    self.assertIn(block(view, set_id)["methodKind"], METHOD_KINDS)


class TheReferenceViewsZeroIsADefinition(unittest.TestCase):

    def test_the_reference_view_offset_is_zero(self):
        with measured() as sid:
            self.assertEqual(
                block(REFERENCE_VIEW, sid)["offsetSecondsToReference"], 0.0)

    def test_the_other_view_carries_the_measured_offset(self):
        other = "side" if REFERENCE_VIEW == "front" else "front"

        with measured(offset=-0.7295) as sid:
            self.assertEqual(block(other, sid)["offsetSecondsToReference"],
                             -0.7295)

    def test_one_definition_serves_both_callers(self):
        """`extract` and `restamp` must derive the block the same way. A
        re-stamp with its own reading of SYNC would drift from the writer the
        first time either changed."""
        with measured() as sid:
            path = keypoint_file({"method": "anything at all"}, set_id=sid)

            self.assertEqual(restamp(path)["after"], block("front", sid))


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
        with measured() as sid:
            path = keypoint_file({"method": stale}, set_id=sid)
            restamp(path)
            text = path.read_text(encoding="utf-8")

        self.assertNotIn("no clap exists in this material", text)
        self.assertIn("no claim about what else the recordings contain", text)

    def test_an_unmeasured_block_carries_no_claim_either(self):
        """The note on an unmeasured set says only that nothing was measured
        and why. An earlier version told every reader "Only set 0.1 has two
        matched events", which stopped being true the moment 0.2 was added and
        stayed in the file through two more offsets."""
        path = keypoint_file({"method": "stale"})
        restamp(path)
        text = path.read_text(encoding="utf-8")

        self.assertNotIn("Only set 0.1 has two matched events", text)
        self.assertIn("not a synchronous pair", text)

    def test_the_offset_and_the_worked_example_come_from_SYNC(self):
        """Not "are preserved" — the re-stamp REPLACES them from SYNC, which is
        the point of running it after a re-measurement OR a withdrawal."""
        with measured() as sid:
            path = keypoint_file({"method": "stale", "worked":
                                  {"referenceViewSeconds": 9.25}}, set_id=sid)
            after = restamp(path)["after"]

            self.assertEqual(after["offsetSecondsToReference"], 0.0)
            self.assertEqual(after["worked"]["referenceViewSeconds"], 9.1333)

    def test_a_withdrawal_strips_the_offset_from_an_existing_file(self):
        """THE RE-STAMP'S NEW JOB. When a measurement is withdrawn, every
        artefact carrying it has to lose it — and this is how the four keypoint
        files stopped claiming -0.7295 s without being re-extracted."""
        path = keypoint_file({"measured": True,
                              "offsetSecondsToReference": -0.7295,
                              "offsetUncertaintySeconds": 0.0333,
                              "method": "shared event",
                              "worked": {"thisViewSeconds": 9.8628,
                                         "referenceViewSeconds": 9.1333}})
        after = restamp(path)["after"]

        self.assertFalse(after["measured"])
        self.assertEqual(after["methodKind"], "unknown")
        self.assertNotIn("worked", after)
        self.assertNotIn("-0.7295", path.read_text(encoding="utf-8"))

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

    def test_the_restamp_moves_the_verdict_ONLY_through_the_uncertainty(self):
        """THE RE-STAMP IS NO LONGER INERT ON THIS ARTEFACT, and pretending it
        is would be the wrong guard.

        Until 2026-09-07 it only rewrote prose. It now also carries a corrected
        MEASUREMENT: the uncertainty falls from 0.15 s to one frame, which the
        gate reads, so the sync condition goes from FAIL to pass. That is the
        offset genuinely improving and the verdict should move.

        What must still hold is that it moves for that reason and no other. So
        the stale block with the fresh uncertainty must equal the fresh block:
        every remaining difference between them is inert."""
        stale = {"referenceView": "front", "measured": True,
                 "offsetSecondsToReference": 1.0,
                 "offsetUncertaintySeconds": 0.15,
                 "method": "two visual events matched by eye; "
                           "no clap exists in this material",
                 "worked": {"event": "first catch, seen in both views",
                            "thisViewSeconds": 8.25, "referenceViewSeconds": 9.25}}
        with measured() as sid:
            fresh = block("side", sid)
        bridged = {**stale,
                   "offsetUncertaintySeconds": fresh["offsetUncertaintySeconds"]}

        self.assertNotEqual(verdict(judge_capture(self.evidence(stale), MOVEMENT)),
                            verdict(judge_capture(self.evidence(fresh), MOVEMENT)))
        self.assertEqual(verdict(judge_capture(self.evidence(bridged), MOVEMENT)),
                         verdict(judge_capture(self.evidence(fresh), MOVEMENT)))

    def test_mutating_every_prose_field_moves_nothing(self):
        with measured() as sid:
            fresh = block("side", sid)
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

        LOOSENING, and it used to have to be tightening. While the written
        uncertainty was 0.15 s it already FAILED the gate's one-frame bar, so
        only tightening discriminated. The measured 0.0333 s now PASSES, so
        only loosening does. The direction that discriminates is a property of
        the current reading, not of the test."""
        with measured() as sid:
            fresh = block("side", sid)
        loosened = {**fresh, "offsetUncertaintySeconds": 5.0}

        self.assertNotEqual(
            verdict(judge_capture(self.evidence(fresh), MOVEMENT)),
            verdict(judge_capture(self.evidence(loosened), MOVEMENT)))


if __name__ == "__main__":
    unittest.main()
