"""Tests for the clap evidence detector.

THE FAULT THIS FILE GUARDS is not a wrong detector. It is a right detector whose
numbers lived in one session's scratchpad, so a reviewer reconstructing it by
hand got 25.4 where the author had 26.5 and counts anywhere from zero to
twenty-seven depending on the rule guessed. Every parameter is therefore a named
constant and every published figure comes from `main()`.

The second fault is a sentence: "only seven frames in 785 fall under 0.5", when
fifty-five frames do. Seven was a count of minima after a separation rule,
printed as a count of frames. `together` now returns three counts that cannot be
swapped, and the first test here is the one that keeps them apart.
"""

from __future__ import annotations

import unittest

import numpy as np

from video_clap_evidence import (
    ATTACK_RATIO,
    BLOCK_SECONDS,
    SEPARATION_SECONDS,
    SPIKE_RISE,
    TOGETHER_WIDTHS,
    coincidences,
    high_band_energy,
    spikes,
    together,
    wrist_separation,
)

RATE = 48000


class ThreeCountsAreThreeNumbers(unittest.TestCase):
    """Frames, stretches and minima are different, and a summary that swaps one
    for another is how "fifty-five" was published as "seven"."""

    def series(self):
        # Two separate dips under the bar. The first is long and has TWO local
        # minima in it; the second is short with one. So: 8 frames under, 2
        # stretches, 3 minima — three numbers, all different, none guessable
        # from the others.
        widths = np.array([1.0, 0.4, 0.3, 0.4, 0.2, 0.45, 1.0, 1.0,
                           0.4, 0.3, 0.4, 1.0, 1.0])
        return np.arange(len(widths)) / 30.0, widths

    def test_the_three_counts_are_reported_separately(self):
        found = together(*self.series())

        self.assertEqual(found["framesUnder"], 8)
        self.assertEqual(len(found["stretches"]), 2)
        self.assertEqual(len(found["minima"]), 3)

    def test_no_two_of_them_are_equal_in_this_fixture(self):
        # If a future version returned the same number for two of the three,
        # this fixture makes it fail rather than look plausible.
        found = together(*self.series())
        counts = {found["framesUnder"], len(found["stretches"]),
                  len(found["minima"])}

        self.assertEqual(len(counts), 3)

    def test_the_deepest_frame_is_reported_even_when_it_is_not_a_named_minimum(self):
        """The published seven did not include the deepest frame in the clip.
        The deepest is now its own field and cannot be dropped by a rule."""
        found = together(*self.series())

        self.assertAlmostEqual(found["deepest"]["widths"], 0.2)

    def test_a_stretch_running_to_the_end_is_still_closed(self):
        times = np.arange(5) / 30.0
        found = together(times, np.array([1.0, 1.0, 0.3, 0.3, 0.3]))

        self.assertEqual(len(found["stretches"]), 1)
        self.assertEqual(found["stretches"][0]["frames"], 3)

    def test_the_bar_is_the_named_constant(self):
        times = np.arange(3) / 30.0
        just_over = np.full(3, TOGETHER_WIDTHS + 0.01)
        just_under = np.full(3, TOGETHER_WIDTHS - 0.01)

        self.assertEqual(together(times, just_over)["framesUnder"], 0)
        self.assertEqual(together(times, just_under)["framesUnder"], 3)


class ASpikeIsAnAttackNotALoudMoment(unittest.TestCase):

    def track(self, events, seconds=3.0, noise=0.002, seed=3):
        rng = np.random.default_rng(seed)
        n = int(seconds * RATE)
        x = rng.normal(0, noise, n)
        for at, amp, length in events:
            i = int(at * RATE)
            span = int(length * RATE)
            burst = rng.normal(0, amp, span) * np.exp(-np.linspace(0, 6, span))
            x[i:i + span] += burst
        return x

    def test_a_clap_is_found_and_its_rise_reported(self):
        found = spikes(*high_band_energy(self.track([(1.5, 0.5, 0.02)]), RATE))

        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["seconds"], 1.5, delta=0.02)
        self.assertGreater(found[0]["rise"], SPIKE_RISE)

    def test_sustained_loudness_is_not_a_spike(self):
        # A full second of broadband noise as loud as the clap. It fails the
        # attack test, which is the point: speech is loud and is not a clap.
        found = spikes(*high_band_energy(self.track([(1.0, 0.5, 1.0)]), RATE))

        self.assertEqual(found, [])

    def test_quiet_yields_nothing(self):
        self.assertEqual(spikes(*high_band_energy(self.track([]), RATE)), [])

    def test_two_claps_are_two_spikes(self):
        found = spikes(*high_band_energy(
            self.track([(1.0, 0.5, 0.02), (2.0, 0.5, 0.02)]), RATE))

        self.assertEqual(len(found), 2)
        self.assertAlmostEqual(found[1]["seconds"] - found[0]["seconds"], 1.0,
                               delta=0.03)

    def test_blocks_inside_one_event_collapse_to_its_loudest(self):
        """The separation rule keeps the loudest of a cluster, so a reported
        spike is a CLUSTER and not necessarily an isolated event. Anything
        within 150 ms of a reported spike is inside it, not beside it."""
        found = spikes(*high_band_energy(self.track([(1.5, 0.6, 0.05)]), RATE))

        self.assertEqual(len(found), 1)

    def test_the_bar_is_honoured(self):
        loud = self.track([(1.5, 0.5, 0.02)])
        many = spikes(*high_band_energy(loud, RATE), rise=1.0)
        few = spikes(*high_band_energy(loud, RATE), rise=1000.0)

        self.assertGreaterEqual(len(many), len(few))
        self.assertEqual(few, [])


class TheCoincidenceIsTheArgument(unittest.TestCase):
    """Neither reading identifies a clap alone. She talks with her hands and the
    room is noisy; what is rare is the two at once."""

    def test_a_minimum_with_a_nearby_attack_is_paired(self):
        found = coincidences([{"seconds": 5.867, "widths": 0.249}],
                             [{"seconds": 5.800, "rise": 26.5}])

        self.assertAlmostEqual(found[0]["rise"], 26.5)

    def test_a_minimum_with_no_attack_is_reported_as_none(self):
        found = coincidences([{"seconds": 18.300, "widths": 0.236}],
                             [{"seconds": 5.800, "rise": 26.5}])

        self.assertIsNone(found[0]["rise"])
        self.assertIsNone(found[0]["soundSeconds"])

    def test_an_attack_outside_the_window_does_not_count(self):
        found = coincidences([{"seconds": 5.0, "widths": 0.2}],
                             [{"seconds": 5.3, "rise": 40.0}], window=0.10)

        self.assertIsNone(found[0]["rise"])

    def test_every_minimum_gets_a_row_whether_or_not_it_pairs(self):
        # A row per minimum, so the ten that pair with nothing are visible.
        # Reporting only the pairs is how two coincidences became the whole
        # story without the ten that were not.
        found = coincidences(
            [{"seconds": t, "widths": 0.3} for t in (1.0, 2.0, 3.0)],
            [{"seconds": 2.0, "rise": 20.0}])

        self.assertEqual(len(found), 3)
        self.assertEqual(sum(1 for f in found if f["rise"]), 1)


class TheLandmarkReaderRefusesWhatItCannotSee(unittest.TestCase):

    def frames(self, wrist_visibility=0.9, shoulder_gap=100.0, wrist_gap=50.0):
        out = []
        for i in range(10):
            out.append({"ptsSeconds": i / 30.0, "landmarks": [
                {"name": "left_shoulder", "xPixel": 0.0, "yPixel": 0.0, "visibility": 0.9},
                {"name": "right_shoulder", "xPixel": shoulder_gap, "yPixel": 0.0, "visibility": 0.9},
                {"name": "left_wrist", "xPixel": 0.0, "yPixel": 50.0, "visibility": wrist_visibility},
                {"name": "right_wrist", "xPixel": wrist_gap, "yPixel": 50.0, "visibility": wrist_visibility},
            ]})
        return out

    def test_separation_is_measured_in_shoulder_widths(self):
        _, widths = wrist_separation(self.frames(shoulder_gap=100.0, wrist_gap=50.0))

        self.assertAlmostEqual(float(widths[0]), 0.5)

    def test_the_same_pose_further_away_reads_the_same(self):
        near = wrist_separation(self.frames(shoulder_gap=200.0, wrist_gap=100.0))[1]
        far = wrist_separation(self.frames(shoulder_gap=100.0, wrist_gap=50.0))[1]

        self.assertAlmostEqual(float(near[0]), float(far[0]))

    def test_an_unseen_wrist_drops_the_frame_rather_than_guessing(self):
        times, _ = wrist_separation(self.frames(wrist_visibility=0.1))

        self.assertEqual(len(times), 0)


if __name__ == "__main__":
    unittest.main()
