"""Which moment a clip is judged against.

A clip declares ONE moment and the possession model derives TWO frames. The
verifier reported every clip against `contactFrame` until 2026-09-02, so a
`release` clip was asked when she CAUGHT the ball. On the two passes in the
library that read -1.267 seconds on a 1.6 second clip, against -0.017 to -0.034
for every catch, and it sat in the baseline unremarked.

These run without the solver on purpose. The rule is a decision about two
fields and needs no pose, so it lives in clip_geometry.py beside the CLASSES
table that names the moments, where a system python can reach it. Putting it in
the verifier put it behind a pymomentum import for no reason.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clip_geometry import RELEASE_MOMENT, moment_frame  # noqa: E402


def clip(**overrides) -> dict:
    """A clip with only the fields this rule reads."""
    base = {
        "clipId": "pass.netball.chest-pass",
        "hitPhase": RELEASE_MOMENT,
        "contactFrame": 0,
        "releaseFrame": 76,
    }
    base.update(overrides)
    return base


class MomentFrameTest(unittest.TestCase):
    def test_a_release_moment_reads_the_release_frame(self):
        self.assertEqual(moment_frame(clip()), 76)

    def test_a_contact_moment_reads_the_contact_frame(self):
        self.assertEqual(
            moment_frame(clip(hitPhase="contact", contactFrame=52)), 52
        )

    def test_a_landing_moment_reads_the_contact_frame(self):
        """A landing is not a release, and its gap to the catch is the finding.

        `double_foot_landing` differs from its catch by 0.32 s BECAUSE she
        takes the ball in flight and lands later. That must keep reading the
        contact frame.
        """
        self.assertEqual(moment_frame(clip(hitPhase="land", contactFrame=52)), 52)

    def test_the_two_frames_disagree_on_the_drills_this_was_found_on(self):
        """Guards the guard.

        Both passes start with the ball, so `contactFrame` is 0 and the two
        answers are as far apart as they can be. If they ever agreed, the
        tests above would pass while reading the wrong field.
        """
        one = clip()

        self.assertNotEqual(one["contactFrame"], one["releaseFrame"])
        self.assertNotEqual(moment_frame(one), one["contactFrame"])

    def test_a_release_clip_with_no_release_frame_is_refused(self):
        """It must not fall back. Falling back IS the defect being replaced."""
        with self.assertRaises(ValueError) as raised:
            moment_frame(clip(releaseFrame=None))

        self.assertIn("releaseFrame", str(raised.exception))
        self.assertIn("pass.netball.chest-pass", str(raised.exception))

    def test_a_catch_needs_no_release_frame(self):
        """Every catch in the library ends holding the ball and has none."""
        self.assertEqual(
            moment_frame(clip(hitPhase="contact", contactFrame=52, releaseFrame=None)),
            52,
        )


if __name__ == "__main__":
    unittest.main()
