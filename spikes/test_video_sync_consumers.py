"""Tests that RUN the two consumers of the sync block.

WHY THIS FILE EXISTS, and it is the most useful thing in it. On 2026-09-07 the
field `offsetSecondsToReference` was removed from the sync block and its two
readers were left behind. The spikes suite was 786 tests and green. Running
`video_lift_3d.py --set 0.2` raised `KeyError: 'offsetSecondsToReference'`.

**NOT ONE OF THE 786 TESTS EXECUTED EITHER CONSUMER.** Every test mocked the
sync block and asserted on the mock, so a removed field survived a green suite
and a push. A consumer nothing executes is a consumer nobody has checked.

Writing this file then found two more faults in the same blind spot, and
neither was caused by the change it was written for:

1. `video_elbow_curve.py` compared `side` against `front` on a line ABOVE the
   one that loads `front`. Every call raised UnboundLocalError.
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
                             pair_slug)

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

    def test_the_real_pair_in_PAIRS_satisfies_its_own_offset(self):
        """The recorded pairing must pass its own check. If this ever fails,
        the sync block in the writer contradicts itself."""
        for key, pair in PAIRS.items():
            with self.subTest(pair=key):
                self.assertEqual(frame_offset_of(pair),
                                 pair["frameOffsetToReference"])


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

        self.assertFalse((OUTPUT / "lift-3d-0.2.json").exists(),
                         "a lift was written for two files that are not a pair")


class TheRealPairRunsAndItsAnchorsAreAsserted(unittest.TestCase):
    """The reachable pass, for BOTH consumers. Without it every refusal above
    proves only that a script can exit 1, which a syntax error also achieves.
    The elbow curve proves the point: it had no passing path at all, and two
    crashes lived behind its refusals until this class ran it."""

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not present")

    def test_the_lift_runs_on_the_established_pair(self):
        found = run("video_lift_3d.py", "--pair", THE_PAIR)

        self.assertEqual(found.returncode, 0, found.stdout + found.stderr)
        self.assertIn("usable frame pairs", found.stdout)

    def test_the_elbow_curve_runs_on_the_established_pair(self):
        found = run("video_elbow_curve.py", "--pair", THE_PAIR)

        self.assertEqual(found.returncode, 0, found.stdout + found.stderr)
        self.assertIn("LEFT elbow", found.stdout)

    def test_both_artefacts_are_named_for_the_pair_not_for_a_set(self):
        """A set-named artefact is a claim about a pairing that is not true."""
        slug = pair_slug(THE_PAIR)
        for stem in ("lift-3d", "elbow-curve"):
            with self.subTest(stem=stem):
                self.assertTrue((OUTPUT / f"{stem}-{slug}.json").exists())
                for set_id in ("0.1", "0.2"):
                    self.assertFalse(
                        (OUTPUT / f"{stem}-{set_id}.json").exists(),
                        "an artefact of the mislabelled pairing survives")


if __name__ == "__main__":
    unittest.main()
