"""Tests that RUN the two consumers of the sync block.

WHY THIS FILE EXISTS, and it is the most useful thing in it. On 2026-09-07 the
field `offsetSecondsToReference` was removed from the sync block and its two
readers were left behind. The spikes suite was 786 tests and green. Running
`video_lift_3d.py --set 0.2` raised `KeyError: 'offsetSecondsToReference'`.

**NOT ONE OF THE 786 TESTS EXECUTED EITHER CONSUMER.** Every test mocked the
sync block and asserted on the mock, so a removed field survived a green suite
and a push. A consumer nothing executes is a consumer nobody has checked.

The tests below run the real entry points as subprocesses and read their exit
codes, because that is the only thing that would have caught it.

THE SECOND FAULT THEY GUARD is subtler and was found in the fix. The first
version of the repaired guard asked `if not side["sync"]["measured"]` — and
`side 0.2.mp4` IS measured, because it is half of the real pair with
`front 0.1.mp4`. So `--set 0.2` loaded front 0.2 against side 0.2, passed the
guard, and wrote a plausible lift from two files that are not a pair. The guard
now asks whether these two files ARE the pair.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from video_keypoints import PAIRING_UNKNOWN, PAIRS

SPIKES = Path(__file__).resolve().parent
OUTPUT = SPIKES / "poc-output" / "video"
CONSUMERS = ("video_lift_3d.py", "video_elbow_curve.py")


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SPIKES / script), *args],
                          capture_output=True, text=True, cwd=SPIKES)


def keypoints_present() -> bool:
    return all((OUTPUT / f"keypoints-{v}-{s}.json").exists()
               for v in ("front", "side") for s in ("0.1", "0.2"))


class EveryConsumerRefusesASetThatIsNotAPair(unittest.TestCase):
    """No set's two same-named files are a pair, so every --set must refuse."""

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not present")

    def test_each_consumer_refuses_each_set_with_a_nonzero_exit(self):
        for script in CONSUMERS:
            for set_id in ("0.1", "0.2"):
                with self.subTest(script=script, set_id=set_id):
                    found = run(script, "--set", set_id)

                    self.assertNotEqual(found.returncode, 0)

    def test_the_refusal_names_the_real_pairing_rather_than_only_failing(self):
        """A refusal that does not say what IS true sends the reader hunting."""
        found = run("video_lift_3d.py", "--set", "0.1")
        said = found.stdout + found.stderr

        self.assertIn("front 0.1.mp4 + side 0.2.mp4", said)
        self.assertIn("FILE NAMES ARE WRONG", said)

    def test_set_0_2_refuses_although_its_side_file_IS_measured(self):
        """THE FAULT THE FIRST FIX HAD. `side 0.2.mp4` carries a sync — it is
        half of the real pair — so a guard asking only "is it measured" let
        front 0.2 be lifted against side 0.2 and wrote the artefact."""
        found = run("video_lift_3d.py", "--set", "0.2")

        self.assertNotEqual(found.returncode, 0)
        self.assertFalse((OUTPUT / "lift-3d-0.2.json").exists(),
                         "a lift was written for two files that are not a pair")

    def test_no_consumer_reads_the_removed_field(self):
        """The exact regression: the field is gone, so no reader may name it."""
        for script in CONSUMERS:
            with self.subTest(script=script):
                text = (SPIKES / script).read_text(encoding="utf-8")
                live = [l for l in text.splitlines()
                        if "offsetSecondsToReference" in l
                        and not l.strip().startswith("#")
                        and '"' not in l.split("offsetSecondsToReference")[0][-2:]]
                self.assertEqual(
                    [l for l in live if "[" in l], [],
                    "a consumer still subscripts the removed field")


class TheRealPairRunsAndItsAnchorsAreAsserted(unittest.TestCase):

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not present")
        self.key = next(iter(PAIRS))

    def test_the_lift_runs_on_the_established_pair(self):
        """The reachable pass. Without it every refusal above proves only that
        the script can exit 1, which a syntax error also achieves."""
        found = run("video_lift_3d.py", "--pair", self.key)

        self.assertEqual(found.returncode, 0, found.stdout + found.stderr)
        self.assertIn("usable frame pairs", found.stdout)

    def test_an_unknown_pair_name_is_refused_and_lists_what_is_known(self):
        found = run("video_lift_3d.py", "--pair", "front 9.9 + side 9.9")

        self.assertNotEqual(found.returncode, 0)
        self.assertIn(self.key, found.stdout + found.stderr)

    def test_neither_unpaired_file_can_be_asked_for_as_a_pair(self):
        for name in PAIRING_UNKNOWN:
            with self.subTest(file=name):
                found = run("video_lift_3d.py", "--pair", name)

                self.assertNotEqual(found.returncode, 0)


if __name__ == "__main__":
    unittest.main()
