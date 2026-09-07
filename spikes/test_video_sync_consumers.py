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
                             load_keypoints, pair_slug)

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


class EveryConsumerRefusesASetThatIsNotAPair(unittest.TestCase, RefusalMixin):
    """No set's two same-named files are a pair, so every --set must refuse.
    These read the keypoint artefacts, so they need footage."""

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not present")

    def test_each_consumer_refuses_each_set_and_names_the_real_pairing(self):
        for script in CONSUMERS:
            for set_id in ("0.1", "0.2"):
                with self.subTest(script=script, set_id=set_id):
                    said = self.refused(run(script, "--set", set_id))

                    self.assertIn("front 0.1.mp4 + side 0.2.mp4", said)
                    self.assertIn("FILE NAMES ARE WRONG", said)

    def test_set_0_2_refuses_although_its_side_file_IS_measured(self):
        """THE FAULT THE FIRST FIX HAD. `side 0.2.mp4` carries a sync, because
        it is half of the real pair, so a guard asking only "is it measured"
        let front 0.2 be lifted against side 0.2 and wrote the artefact."""
        self.refused(run("video_lift_3d.py", "--set", "0.2"))

        # THE NAME MATTERS. This used to assert on `lift-3d-0.2.json`, which no
        # code path writes: `--set 0.2` slugs to `set_0.2`. The mutant that
        # lifted two unpaired files wrote `lift-3d-set_0.2.json` and the
        # assertion stayed inert; only the exit code failed the test. A glob
        # names nothing, so nothing escapes it.
        stray = [p.name for p in OUTPUT.glob("lift-3d-*.json")
                 if not p.name.endswith(f"-{pair_slug(THE_PAIR)}.json")]
        self.assertEqual(stray, [],
                         "a lift was written for two files that are not a pair")


class TheRealPairRunsAndItsAnchorsAreAsserted(unittest.TestCase):
    """The reachable pass, for BOTH consumers. Without it every refusal above
    proves only that a script can exit 1, which a syntax error also achieves.
    The elbow curve proves the point: it had no passing path at all, and two
    crashes lived behind its refusals until this class ran it.

    THE ORDER MATTERS AND THAT IS WHY THE RUNS ARE IN setUpClass. unittest runs
    a class's methods in alphabetical order, and the elbow curve READS the lift's
    artefact. With one method per run, `test_the_elbow_curve_runs` and
    `test_both_artefacts` sorted BEFORE `test_the_lift_runs`, so on a poc-output
    holding only the keypoint files this class failed three tests on the first
    run, one on the second, and passed only on the third. It was green here only
    because both artefacts already existed from earlier runs by hand: the class
    was reading its own leftovers. That is exactly "the run owns the working
    tree", turned on the test itself.

    So the pair-named artefacts are DELETED first, then the lift and the elbow
    curve are run once each, in order, and the three tests read those two
    results. The pass is proven from a clean state rather than from a survivor.
    """

    lift = None
    elbow = None

    @classmethod
    def setUpClass(cls):
        if not keypoints_present():
            return
        slug = pair_slug(THE_PAIR)
        for stem in ("lift-3d", "elbow-curve"):
            (OUTPUT / f"{stem}-{slug}.json").unlink(missing_ok=True)
        cls.lift = run("video_lift_3d.py", "--pair", THE_PAIR)
        cls.elbow = run("video_elbow_curve.py", "--pair", THE_PAIR)

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not present")

    def test_the_lift_runs_on_the_established_pair(self):
        found = type(self).lift

        self.assertEqual(found.returncode, 0, found.stdout + found.stderr)
        self.assertIn("usable frame pairs", found.stdout)

    def test_the_elbow_curve_runs_on_the_established_pair(self):
        """It ran AFTER the lift, from a state where no lift artefact existed
        until the lift wrote one. A pass here is a pass on the pair, not on a
        file left behind by an earlier run."""
        found = type(self).elbow

        self.assertEqual(found.returncode, 0, found.stdout + found.stderr)
        self.assertIn("LEFT elbow", found.stdout)

    def test_no_artefact_is_named_for_a_SET_rather_than_for_the_pair(self):
        """A set-named artefact is a claim about a pairing that is not true.

        THIS ASSERTION USED TO BE INERT. It named `lift-3d-0.2.json`, and no
        code path writes that: a `--set 0.2` label slugs to `set_0.2`, so the
        mutant that lifted two unpaired files wrote `lift-3d-set_0.2.json` and
        sailed past the check. The glob names nothing, so nothing can be missed.
        """
        wanted = f"-{pair_slug(THE_PAIR)}.json"
        for stem in ("lift-3d", "elbow-curve"):
            with self.subTest(stem=stem):
                self.assertTrue((OUTPUT / f"{stem}{wanted}").exists())

                stray = [p.name for p in OUTPUT.glob(f"{stem}-*.json")
                         if not p.name.endswith(wanted)]
                self.assertEqual(stray, [],
                                 "an artefact not named for the pair exists")


if __name__ == "__main__":
    unittest.main()
