"""Tests that RUN the two consumers of the sync block.

WHY THIS FILE EXISTS, and it is the most useful thing in it. On 2026-09-07 the
field `offsetSecondsToReference` was removed from the sync block and its two
readers were left behind. The spikes suite was 786 tests and green. Running
`video_lift_3d.py --set 0.2` raised `KeyError: 'offsetSecondsToReference'`.

**NOT ONE OF THE 786 TESTS EXECUTED EITHER CONSUMER.** Every test mocked the
sync block and asserted on the mock, so a removed field survived a green suite
and a push. A consumer nothing executes is a consumer nobody has checked.

Writing this file then found two more faults in the same blind spot:

1. `video_elbow_curve.py` compared `side` against `front` on a line ABOVE the
   one that loads `front`. Every call raised UnboundLocalError. THIS ONE WAS
   MINE, hours old: the first repair introduced it. The pack first filed it
   among the faults that did not come from the change, and the review checked
   the commits and corrected the dating.
2. `reference-curves.json` went to schema version 2, where a curve became
   `{"unit": ..., "values": [...]}` instead of a bare list. The elbow curve
   still iterated it, so it built an array of the words "unit" and "values",
   and so did `video_phase_align.py`. That contract is now held in one
   place: refer to `test_reference_curves.py`.

THE FIRST VERSION OF THIS FILE MISSED BOTH, because its refusal tests asserted
only that the exit code was not zero, and a crash is not zero either. A refusal
test must read the refusal. `refused()` below therefore requires exit 1 AND the
absence of a traceback, and every reachable path is run to exit 0.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from video_keypoints import (PAIRING_UNKNOWN, PAIRS, frame_offset_of,
                             load_keypoints, pair_key_of_set, pair_slug,
                             source_matches)

SPIKES = Path(__file__).resolve().parent
OUTPUT = SPIKES / "poc-output" / "video"
CONSUMERS = ("video_lift_3d.py", "video_elbow_curve.py")
THE_PAIR = next(iter(PAIRS))


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SPIKES / script), *args],
                          capture_output=True, text=True, cwd=SPIKES)


def keypoints_present() -> bool:
    """The keypoint artefacts are in .gitignore, so a hosted runner has none of
    them. The tests that need footage skip there and hold on a machine that has
    it. The tests above them need no footage and hold everywhere."""
    return all((OUTPUT / f"keypoints-{v}-{s}.json").exists()
               for v in ("front", "side") for s in ("0.1", "0.2"))


class RefusalMixin:

    def refused(self, found: subprocess.CompletedProcess) -> str:
        """A REFUSAL, not merely a failure. Requiring only a non-zero exit is
        what let an UnboundLocalError pass for a guard: both are non-zero."""
        said = found.stdout + found.stderr
        self.assertEqual(found.returncode, 1, said)
        self.assertNotIn("Traceback", said,
                         "this is a crash wearing the exit code of a refusal")
        return said


class EveryConsumerRefusesWithoutReadingAnyFootage(unittest.TestCase,
                                                   RefusalMixin):
    """These need no artefacts, so they run on the hosted runner too. They are
    the only part of this file a runner can hold, and they hold what a runner
    is best at: that both scripts still import and still parse."""

    def test_an_unknown_pair_name_is_refused_and_lists_what_is_known(self):
        for script in CONSUMERS:
            with self.subTest(script=script):
                said = self.refused(
                    run(script, "--pair", "front 9.9 + side 9.9"))

                self.assertIn(THE_PAIR, said)

    def test_neither_unpaired_file_can_be_asked_for_as_a_pair(self):
        for script in CONSUMERS:
            for name in PAIRING_UNKNOWN:
                with self.subTest(script=script, file=name):
                    self.refused(run(script, "--pair", name))

    def test_no_argument_is_refused_rather_than_defaulting_to_a_pairing(self):
        """The elbow curve used to default to `--set 0.1`, so a bare call
        analysed one particular pairing without being asked, and that pairing
        is the one now known to be wrong."""
        for script in CONSUMERS:
            with self.subTest(script=script):
                said = self.refused(run(script))

                self.assertIn("--pair", said)

    def test_no_consumer_reads_the_removed_field(self):
        """The exact regression: the field is gone, so no reader may name it."""
        for script in CONSUMERS:
            with self.subTest(script=script):
                text = (SPIKES / script).read_text(encoding="utf-8")
                live = [line for line in text.splitlines()
                        if "offsetSecondsToReference" in line
                        and not line.strip().startswith("#")]
                self.assertEqual(
                    [line for line in live if "[" in line], [],
                    "a consumer still subscripts the removed field")


class TheAnchorCheckIsHeldWhereAMutationCanReachIt(unittest.TestCase):
    """THE CHECK EXISTED IN BOTH CONSUMERS AND NOTHING HELD IT. Each consumer
    read the offset out of a written artefact, so changing the offset in PAIRS
    reached neither of them: both consumers passed with the offset set to -4
    and to -6. The check now lives in one function, and these are the
    mutations that fail it."""

    def block(self, offset: int, other: int = 100) -> dict:
        return {"frameOffsetToReference": offset,
                "anchors": [{"event": "a clap", "referenceIndex": 105,
                             "otherIndex": other}],
                "checks": [{"event": "a catch", "referenceIndex": 205,
                            "otherIndex": 200}]}

    def test_a_block_whose_anchors_agree_returns_the_offset(self):
        self.assertEqual(frame_offset_of(self.block(-5)), -5)

    def test_an_offset_one_frame_out_in_either_direction_is_refused(self):
        for wrong in (-4, -6):
            with self.subTest(offset=wrong):
                with self.assertRaises(SystemExit) as raised:
                    frame_offset_of(self.block(wrong))

                self.assertIn("a clap", str(raised.exception))

    def test_a_check_row_is_read_too_and_not_only_the_anchors(self):
        """The checks are the rows the offset was NOT fitted on. A guard that
        reads only the anchors cannot fail on the evidence held back."""
        block = self.block(-5)
        block["checks"][0]["otherIndex"] = 199

        with self.assertRaises(SystemExit) as raised:
            frame_offset_of(block)

        self.assertIn("a catch", str(raised.exception))

    def frames(self, count=210, period=0.033322):
        return [{"frameIndex": i, "ptsSeconds": round(i * period, 4)}
                for i in range(count)]

    def block_with_seconds(self, other_seconds):
        block = self.block(-5)
        block["anchors"][0]["otherSeconds"] = other_seconds
        block["checks"] = []
        return block

    def test_with_the_frames_it_checks_the_seconds_the_row_records(self):
        """THE CHECK THE SCHEMA STATES, which the code did not do. It compared
        integers only, so a block whose indices are right and whose seconds
        came from somewhere else passed."""
        frames = self.frames()
        right = frames[100]["ptsSeconds"]

        self.assertEqual(frame_offset_of(self.block_with_seconds(right),
                                         frames), -5)

    def test_seconds_that_belong_to_a_different_frame_are_refused(self):
        frames = self.frames()
        wrong = frames[104]["ptsSeconds"]

        with self.assertRaises(SystemExit) as raised:
            frame_offset_of(self.block_with_seconds(wrong), frames)

        self.assertIn("disagree", str(raised.exception))

    def test_a_row_pointing_past_the_end_of_the_paired_file_is_refused(self):
        with self.assertRaises(SystemExit) as raised:
            frame_offset_of(self.block_with_seconds(3.3322), self.frames(50))

        self.assertIn("outside the paired file", str(raised.exception))

    def test_without_the_frames_the_index_check_still_runs(self):
        """A caller that has no frame list still gets the arithmetic check.
        The seconds check is the addition, not a replacement."""
        with self.assertRaises(SystemExit):
            frame_offset_of(self.block(-4))

    def test_the_real_pair_in_PAIRS_satisfies_its_own_offset(self):
        """The recorded pairing must pass its own check. If this ever fails,
        the sync block in the writer contradicts itself."""
        for key, pair in PAIRS.items():
            with self.subTest(pair=key):
                self.assertEqual(frame_offset_of(pair),
                                 pair["frameOffsetToReference"])


class TheWrittenArtefactsStillAgreeWithTheTable(unittest.TestCase):
    """NOTHING HELD THE ARTEFACTS TO `PAIRS`, and the gap was visible in a
    mutation. With the offset in `PAIRS` changed to -4 both consumers still ran
    to exit 0, because they read the offset out of a WRITTEN keypoint file and
    that file still said -5. So a changed table plus un-restamped artefacts
    gives a green suite and a lift computed on the old offset.

    These need the footage, because they read what the writer wrote."""

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not present")

    def artefact(self, video_name):
        return load_keypoints(video_name)

    def test_each_paired_file_carries_the_offset_the_table_states(self):
        for key, pair in PAIRS.items():
            with self.subTest(pair=key):
                side = self.artefact(pair["otherFile"])

                self.assertEqual(side["sync"]["frameOffsetToReference"],
                                 pair["frameOffsetToReference"],
                                 "the artefact is stale; re-run --restamp")
                self.assertEqual(side["sync"]["pairedWith"],
                                 pair["referenceFile"])

    def test_each_anchor_and_check_in_the_artefact_equals_the_table(self):
        """Not only the offset. A row could be edited in the file alone."""
        for key, pair in PAIRS.items():
            with self.subTest(pair=key):
                side = self.artefact(pair["otherFile"])
                for kind in ("anchors", "checks"):
                    written = [(r["event"], r["referenceIndex"], r["otherIndex"])
                               for r in side["sync"][kind]]
                    table = [(r["event"], r["referenceIndex"], r["otherIndex"])
                             for r in pair[kind]]

                    self.assertEqual(written, table)

    def test_the_artefacts_own_anchors_hold_against_its_own_frames(self):
        """The check the schema states, run on the file rather than the table:
        the frame each row names must carry the seconds the row records."""
        for key, pair in PAIRS.items():
            with self.subTest(pair=key):
                side = self.artefact(pair["otherFile"])

                found = frame_offset_of(side["sync"], side["frames"])

                self.assertEqual(found, pair["frameOffsetToReference"])

    def test_an_unpaired_file_claims_no_offset_at_all(self):
        for name in PAIRING_UNKNOWN:
            with self.subTest(file=name):
                sync = self.artefact(name)["sync"]

                self.assertFalse(sync.get("measured"))
                self.assertIsNone(sync.get("frameOffsetToReference"))
                self.assertIsNone(sync.get("pairedWith"))


class ASetIsRefusedONLYWhenItIsNotAPair(unittest.TestCase, RefusalMixin):
    """THIS CLASS HAS BEEN WRONG TWICE, IN OPPOSITE DIRECTIONS, and each time
    because it asserted a fact about the data rather than about the rule.

    It first asserted that EVERY --set refuses. That was true while the two
    side files' names were swapped and no set's two same-named files were one
    take. Marius renamed them on 2026-09-07 and set 0.1 became the established
    pair, so the blanket refusal would have refused the one thing that worked.

    It was then rewritten to assert that EXACTLY ONE set is a pair. Later the
    same day the second pairing was established at -78, and both sets became
    pairs, so that assertion failed too.

    The rule does not change: a set is answered THROUGH THE PAIR TABLE. What
    changes is what the table holds. So the tests below read the table and
    assert the behaviour, and none of them counts pairs.
    """

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not present")
        self.paired = [s for s in ("0.1", "0.2") if pair_key_of_set(s)]
        self.unpaired = [s for s in ("0.1", "0.2") if not pair_key_of_set(s)]

    def test_a_set_that_names_no_pair_is_refused_by_both_consumers(self):
        """`--set 9.9` names two files that do not exist, so it can never be a
        pair whatever the table holds. It is the refusal path's reachable case
        now that both real sets resolve."""
        for script in CONSUMERS:
            with self.subTest(script=script):
                said = self.refused(run(script, "--set", "9.9"))

                self.assertIn("not an established pair", said)
                for pair in PAIRS.values():
                    self.assertIn(pair["referenceFile"], said)

    def test_the_refusal_no_longer_says_the_file_names_are_wrong(self):
        """They were, and Marius corrected them. A refusal that repeats a
        withdrawn diagnosis sends the reader to fix something already fixed."""
        said = self.refused(run("video_lift_3d.py", "--set", "9.9"))

        self.assertNotIn("FILE NAMES ARE WRONG", said)

    def test_every_set_the_table_calls_a_pair_runs_and_is_named_for_it(self):
        """It resolves to the PAIR KEY, so --set and --pair write one artefact
        under one name rather than two under two."""
        for set_id in self.paired:
            with self.subTest(set_id=set_id):
                found = run("video_lift_3d.py", "--set", set_id)

                self.assertEqual(found.returncode, 0,
                                 found.stdout + found.stderr)
                self.assertIn(pair_key_of_set(set_id), found.stdout)

    def test_every_set_the_table_does_not_call_a_pair_refuses(self):
        for script in CONSUMERS:
            for set_id in self.unpaired:
                with self.subTest(script=script, set_id=set_id):
                    self.refused(run(script, "--set", set_id))

    def test_an_artefact_whose_hash_does_not_match_its_file_stops_the_run(self):
        """THE CHECK THAT WAS MISSING WHEN THE RENAME HAPPENED. Every artefact
        has carried `source.videoSha256` from the first one written, and
        nothing read it: the two side files were swapped and 50 tests stayed
        green, because the only other identity check is index-against-pts and
        the two side files carry IDENTICAL pts at every shared index."""
        document = load_keypoints(PAIRS[THE_PAIR]["otherFile"])
        agrees, why = source_matches(document)

        self.assertTrue(agrees, why)

        document["source"]["videoSha256"] = "0" * 64
        agrees, why = source_matches(document)

        self.assertFalse(agrees)
        self.assertIn("NAME AND THE CONTENT DISAGREE", why)

    def test_a_file_absent_from_this_machine_is_unmeasured_not_failed(self):
        """Three-valued. A runner has no footage, and that is not a fault."""
        document = load_keypoints(PAIRS[THE_PAIR]["otherFile"])
        document["source"]["videoFile"] = "not-a-file.mp4"

        agrees, why = source_matches(document)

        self.assertIsNone(agrees)
        self.assertIn("not on this machine", why)




class EveryPairRunsAndItsAnchorsAreAsserted(unittest.TestCase):
    """The reachable pass, for BOTH consumers and now for BOTH pairs. Without
    it every refusal above proves only that a script can exit 1, which a syntax
    error also achieves. The elbow curve proves the point: it had no passing
    path at all, and two crashes lived behind its refusals until this class ran
    it.

    THE ORDER MATTERS AND THAT IS WHY THE RUNS ARE IN setUpClass. unittest runs
    a class's methods in alphabetical order, and the elbow curve READS the
    lift's artefact. With one method per run, the elbow test and the name test
    sorted BEFORE the lift test, so on a poc-output holding only the keypoint
    files this class failed three tests on the first run, one on the second,
    and passed only on the third. It was green then only because both artefacts
    already existed from earlier runs by hand: the class was reading its own
    leftovers.

    So every pair-named artefact is DELETED first, then the lift and the elbow
    curve are run once each per pair, in order, and the tests read those
    results. The pass is proven from a clean state rather than from a survivor.
    """

    runs: dict = {}

    @classmethod
    def setUpClass(cls):
        if not keypoints_present():
            return
        for stem in ("lift-3d", "elbow-curve"):
            for path in OUTPUT.glob(f"{stem}-*.json"):
                path.unlink()
        cls.runs = {}
        for key in PAIRS:
            cls.runs[key] = {
                "lift": run("video_lift_3d.py", "--pair", key),
                "elbow": run("video_elbow_curve.py", "--pair", key),
            }

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not present")

    def test_the_lift_runs_on_every_established_pair(self):
        for key in PAIRS:
            with self.subTest(pair=key):
                found = type(self).runs[key]["lift"]

                self.assertEqual(found.returncode, 0,
                                 found.stdout + found.stderr)
                self.assertIn("usable frame pairs", found.stdout)

    def test_the_elbow_curve_runs_on_every_established_pair(self):
        """Each ran AFTER its lift, from a state where no lift artefact
        existed until that lift wrote one. A pass here is a pass on the pair,
        not on a file left behind by an earlier run."""
        for key in PAIRS:
            with self.subTest(pair=key):
                found = type(self).runs[key]["elbow"]

                self.assertEqual(found.returncode, 0,
                                 found.stdout + found.stderr)
                self.assertIn("LEFT elbow", found.stdout)

    def test_no_artefact_is_named_for_anything_but_a_pair(self):
        """A set-named artefact is a claim about a pairing that is not true.

        THIS ASSERTION USED TO BE INERT, then it was too strict. It first
        named `lift-3d-0.2.json`, which no code path writes, so the mutant that
        lifted two unpaired files wrote `lift-3d-set_0.2.json` and sailed past.
        The glob that replaced it then forbade every name but ONE pair's, and
        failed the moment a second pair was established. It allows exactly the
        names the table can produce, and nothing else."""
        allowed = {f"{stem}-{pair_slug(key)}.json"
                   for key in PAIRS for stem in ("lift-3d", "elbow-curve")}
        for key in PAIRS:
            with self.subTest(pair=key):
                for stem in ("lift-3d", "elbow-curve"):
                    self.assertTrue(
                        (OUTPUT / f"{stem}-{pair_slug(key)}.json").exists())

        found = {p.name for stem in ("lift-3d", "elbow-curve")
                 for p in OUTPUT.glob(f"{stem}-*.json")}

        self.assertEqual(found - allowed, set(),
                         "an artefact is named for something that is not a pair")


if __name__ == "__main__":
    unittest.main()
