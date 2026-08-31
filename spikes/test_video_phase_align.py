"""Contract tests for the phase alignment.

Synthetic throughout, and for a reason beyond convenience: on real footage
there is no true phase to compare against, so the only place the alignment can
be checked at all is against a warp somebody chose. A curve is built by pushing
a reference through a KNOWN time warp, and the instruments have to find that
warp back.

THE REFUSAL PATH IS TESTED HERE BECAUSE THE DATA NEVER REACHES IT. On session
1.0 all twelve pull-ins are accepted and nothing is refused, so every refusal
in `find_repetitions` would be unexercised code shipped behind a green suite.
That is the regression class this repository keeps meeting.

No solver and no footage. It needs numpy and scipy.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_phase_align import (  # noqa: E402
    FEATURELESS_TOLERANCE_DEGREES,
    AlignmentError,
    anchored_phase,
    featureless_share,
    find_repetitions,
    informative_distance,
    pull_in_onset,
    rank_against_library,
    smooth,
    warped_phase,
    z_normalise,
)

FRAMES = 98
CONTACT_PHASE = 0.5361


def reference_curve(
    rest: float = 88.87, dip: float = 80.0, peak: float = 145.5,
    flat_share: float = 0.48, frames: int = FRAMES,
) -> np.ndarray:
    """A curve shaped like the engine's: flat, a shallow dip, then a fold.

    The flat lead is the point. A reference that starts moving at once would
    hide every fault this module exists to measure.
    """
    curve = np.full(frames, rest, dtype=np.float64)
    contact = int(frames * CONTACT_PHASE)
    flat = min(int(frames * flat_share), contact - 1)
    curve[flat:contact] = np.linspace(rest, dip, contact - flat)
    curve[contact:] = np.linspace(dip, peak, frames - contact)
    return curve


def warped_copy(curve: np.ndarray, power: float, samples: int) -> np.ndarray:
    """The same curve read through a known monotone warp of its phase."""
    read_at = np.linspace(0.0, 1.0, samples) ** power
    return np.interp(read_at, np.linspace(0.0, 1.0, len(curve)), curve)


def library(**curves) -> dict:
    return {
        "measures": ["leftElbowFlexionDegrees"],
        "movements": {
            name: {
                "phase": list(np.linspace(0.0, 1.0, len(curve))),
                "curves": {"leftElbowFlexionDegrees": [float(v) for v in curve]},
                "landmarks": {"contactPhase": CONTACT_PHASE},
            }
            for name, curve in curves.items()
        },
    }


class SmoothTest(unittest.TestCase):
    def test_the_ends_are_not_dragged_toward_zero(self):
        """The documented fault in `np.convolve(..., 'same')`. On an angle curve
        it puts a false dip exactly where a repetition may start."""
        flat = np.full(40, 90.0)

        eased = smooth(flat, 9)

        self.assertAlmostEqual(float(eased[0]), 90.0, places=6)
        self.assertAlmostEqual(float(eased[-1]), 90.0, places=6)

    def test_a_naive_convolution_would_fail_that(self):
        """The decoy, so the test above is not passing by accident."""
        flat = np.full(40, 90.0)

        naive = np.convolve(flat, np.ones(9) / 9, mode="same")

        self.assertLess(float(naive[0]), 60.0)

    def test_a_window_wider_than_the_curve_changes_nothing(self):
        short = np.array([1.0, 2.0, 3.0])

        self.assertTrue(np.allclose(smooth(short, 9), short))


class ZNormaliseTest(unittest.TestCase):
    def test_a_flat_curve_gives_zeros_rather_than_nan(self):
        found = z_normalise(np.full(20, 7.0))

        self.assertTrue(np.all(np.isfinite(found)))
        self.assertTrue(np.allclose(found, 0.0))

    def test_level_is_thrown_away_and_shape_is_kept(self):
        curve = reference_curve()

        self.assertTrue(np.allclose(z_normalise(curve), z_normalise(curve + 50.0)))


class FeaturelessShareTest(unittest.TestCase):
    def test_it_reads_the_flat_lead(self):
        share = featureless_share(reference_curve(flat_share=0.48))

        self.assertAlmostEqual(share, 0.48, delta=0.06)

    def test_a_curve_that_never_moves_is_wholly_featureless(self):
        self.assertEqual(featureless_share(np.full(50, 90.0)), 1.0)

    def test_a_curve_that_moves_at_once_is_not(self):
        rising = np.linspace(0.0, 100.0, 50)

        self.assertLess(featureless_share(rising), 0.1)

    def test_it_is_a_LEADING_run_and_not_a_count_of_flat_samples(self):
        """A curve that moves, then pauses, then moves is informative
        throughout. Counting flat samples anywhere would call it featureless."""
        curve = np.concatenate([
            np.linspace(0.0, 50.0, 20), np.full(60, 50.0), np.linspace(50.0, 90.0, 20)])

        self.assertLess(featureless_share(curve), 0.1)


class OnsetTest(unittest.TestCase):
    def test_the_onset_sits_at_the_foot_of_the_rise(self):
        curve = np.concatenate([np.full(20, 60.0), np.linspace(60.0, 140.0, 20)])

        found = pull_in_onset(curve, peak=39, lookback=30)

        self.assertIsNotNone(found)
        self.assertLess(abs(found - 19), 4)

    def test_a_curve_that_never_sits_low_is_refused(self):
        """None is a refusal, not a fallback: there is no onset in the window."""
        climbing = np.linspace(100.0, 140.0, 30)

        self.assertIsNone(pull_in_onset(climbing, peak=29, lookback=3))

    def test_it_survives_a_dip_too_small_to_be_a_turning_point(self):
        """The reason the turning-point definition was abandoned. This curve
        has the sample's own problem: noise larger than the dip."""
        rng = np.random.default_rng(4)
        curve = np.concatenate([np.full(20, 60.0), np.linspace(60.0, 140.0, 20)])
        noisy = smooth(curve + rng.normal(0.0, 4.0, len(curve)))

        found = pull_in_onset(noisy, peak=39, lookback=30)

        self.assertIsNotNone(found)
        self.assertLess(abs(found - 19), 6)


class AnchoredPhaseTest(unittest.TestCase):
    def test_the_three_instants_land_on_their_three_phases(self):
        times = np.linspace(0.0, 2.0, 61)

        phase = anchored_phase(times, 0.0, 1.0, 2.0, CONTACT_PHASE)

        self.assertAlmostEqual(float(phase[0]), 0.0, places=6)
        self.assertAlmostEqual(float(phase[-1]), 1.0, places=6)
        self.assertAlmostEqual(
            float(np.interp(1.0, times, phase)), CONTACT_PHASE, places=6)

    def test_it_never_goes_backwards(self):
        times = np.linspace(0.0, 2.0, 61)

        phase = anchored_phase(times, 0.0, 0.4, 2.0, CONTACT_PHASE)

        self.assertTrue(np.all(np.diff(phase) >= -1e-12))

    def test_instants_out_of_order_are_refused(self):
        times = np.linspace(0.0, 2.0, 61)

        with self.assertRaises(AlignmentError):
            anchored_phase(times, 1.0, 1.0, 2.0, CONTACT_PHASE)

    def test_a_contact_phase_outside_the_movement_is_refused(self):
        times = np.linspace(0.0, 2.0, 61)

        with self.assertRaises(AlignmentError):
            anchored_phase(times, 0.0, 1.0, 2.0, 1.0)


class WarpTest(unittest.TestCase):
    def test_a_known_warp_is_recovered(self):
        """THE ROUND TRIP. The video is the reference read through phase^1.4, so
        the true phase of video sample n is known, and the warp has to find it."""
        curve = reference_curve()
        samples = 70
        video = warped_copy(curve, power=1.4, samples=samples)
        truth = np.linspace(0.0, 1.0, samples) ** 1.4

        phase, _, _ = warped_phase(video, curve, np.linspace(0.0, 1.0, len(curve)))

        # Judged where the reference has something to say. Over the flat lead
        # any phase is as good as any other and the module says so.
        informative = truth > featureless_share(curve)
        self.assertLess(float(np.abs(phase - truth)[informative].max()), 0.15)

    def test_the_recovered_phase_never_goes_backwards(self):
        curve = reference_curve()
        video = warped_copy(curve, power=1.4, samples=70)

        phase, _, _ = warped_phase(video, curve, np.linspace(0.0, 1.0, len(curve)))

        self.assertTrue(np.all(np.diff(phase) >= -1e-12))

    def test_the_wrong_shape_costs_more_than_the_right_one(self):
        """Without this the distance could be a constant and every ranking in
        the module would be meaningless."""
        curve = reference_curve()
        video = warped_copy(curve, power=1.2, samples=70)
        wrong = reference_curve(rest=40.0, dip=120.0, peak=45.0, flat_share=0.1)

        _, right_cost, _ = warped_phase(
            video, curve, np.linspace(0.0, 1.0, len(curve)))
        _, wrong_cost, _ = warped_phase(
            video, wrong, np.linspace(0.0, 1.0, len(wrong)))

        self.assertGreater(wrong_cost, right_cost * 3.0)

    def test_a_curve_of_one_sample_is_refused(self):
        with self.assertRaises(AlignmentError):
            warped_phase(np.array([1.0]), reference_curve(),
                         np.linspace(0.0, 1.0, FRAMES))


class InformativeDistanceTest(unittest.TestCase):
    def test_a_reference_that_never_moves_returns_nothing(self):
        """None rather than zero. A flat reference has no informative stretch,
        and a zero would read as a perfect match."""
        flat = np.full(40, 90.0)
        video = np.linspace(0.0, 10.0, 40)
        _, _, path = warped_phase(video, flat, np.linspace(0.0, 1.0, 40))

        self.assertIsNone(informative_distance(path, flat))

    def test_it_ignores_the_flat_lead_that_the_whole_curve_counts(self):
        curve = reference_curve(flat_share=0.6)
        video = warped_copy(curve, power=1.0, samples=70)
        _, whole, path = warped_phase(
            video, curve, np.linspace(0.0, 1.0, len(curve)))

        found = informative_distance(path, curve)

        self.assertIsNotNone(found)
        self.assertNotAlmostEqual(found, whole, places=6)

    def test_the_tolerance_is_the_one_the_module_names(self):
        """A curve that moves by less than the threshold has not moved."""
        barely = np.concatenate([
            np.full(20, 90.0),
            np.linspace(90.0, 90.0 + FEATURELESS_TOLERANCE_DEGREES * 0.5, 20)])

        self.assertEqual(featureless_share(barely), 1.0)


class RankingTest(unittest.TestCase):
    """The null test, and it must be able to name the wrong drill."""

    def setUp(self):
        self.snatch = reference_curve()
        self.other = reference_curve(rest=40.0, dip=35.0, peak=130.0, flat_share=0.1)
        self.shelf = np.concatenate([np.full(80, 90.0), np.linspace(90.0, 150.0, 18)])
        self.library = library(
            snatch=self.snatch, other=self.other, shelf=self.shelf)

    def test_a_curve_taken_from_one_drill_ranks_that_drill_first(self):
        video = warped_copy(self.snatch, power=1.15, samples=70)

        ranking = rank_against_library(video, self.library)

        self.assertEqual(ranking[0]["movement"], "snatch")

    def test_a_curve_taken_from_another_drill_does_not(self):
        """THE DECOY, AND IT IS REACHABLE. If the ranking always answered
        'snatch' the test above would pass and mean nothing."""
        video = warped_copy(self.other, power=1.15, samples=70)

        ranking = rank_against_library(video, self.library)

        self.assertEqual(ranking[0]["movement"], "other")

    def test_both_distances_travel_so_the_bias_stays_visible(self):
        video = warped_copy(self.snatch, power=1.15, samples=70)

        ranking = rank_against_library(video, self.library)

        for row in ranking:
            self.assertIn("warpDistance", row)
            self.assertIn("informativeWarpDistance", row)
            self.assertIn("featurelessSharePhase", row)

    def test_the_ranking_is_sorted_on_the_informative_distance(self):
        """Which of the two numbers orders the list is a decision, so it is a
        test. On session 1.0 the two orderings disagree on four of the twelve
        repetitions; no three-drill synthetic library reproduced a disagreement,
        which is itself a reason not to claim the effect is simple."""
        video = warped_copy(self.snatch, power=1.15, samples=70)

        ranking = rank_against_library(video, self.library)
        scores = [row["informativeWarpDistance"] for row in ranking]

        self.assertEqual(scores, sorted(scores))


class FindRepetitionsTest(unittest.TestCase):
    @staticmethod
    def cycles(count: int, seconds: float = 1.5, rate: float = 30.0,
               amplitude: float = 70.0, noise: float = 0.0, seed: int = 3):
        rng = np.random.default_rng(seed)
        per = int(seconds * rate)
        one = np.concatenate([
            np.full(per // 3, 70.0),
            np.linspace(70.0, 60.0, per // 3),
            np.linspace(60.0, 60.0 + amplitude, per - 2 * (per // 3)),
        ])
        values = np.tile(one, count)
        times = np.arange(len(values)) / rate
        return times, values + rng.normal(0.0, noise, len(values))

    def test_clean_cycles_are_found_and_the_first_one_is_not(self):
        """Five tiled cycles give four peaks, and the FIRST is refused.

        Its window can only open at the curve's own start, 0.433 s before the
        peak, which is inside the rise — so there is no onset to anchor to and
        the guard says so. That is right rather than unfortunate: the first
        repetition in a clip has no predecessor to measure a lead against. The
        expectation in a first version of this test was four accepted, and the
        code was correct and the expectation was not.
        """
        times, values = self.cycles(5)

        accepted, refused = find_repetitions(times, values)

        self.assertEqual(len(accepted), 3)
        self.assertEqual(len(refused), 1)
        self.assertIsNone(refused[0]["catchSeconds"])
        self.assertLess(refused[0]["peakSeconds"], accepted[0]["peakSeconds"])

    def test_every_accepted_window_has_three_instants_in_order(self):
        times, values = self.cycles(5)

        accepted, _ = find_repetitions(times, values)

        for row in accepted:
            start, catch, peak, end = row["indices"]
            self.assertLess(start, catch)
            self.assertLess(catch, peak)
            self.assertEqual(peak, end)

    def test_a_flat_signal_yields_nothing(self):
        times = np.arange(300) / 30.0

        accepted, refused = find_repetitions(times, np.full(300, 80.0))

        self.assertEqual(accepted, [])
        self.assertEqual(refused, [])

    def test_the_peak_to_noise_guard_can_actually_fire(self):
        """THE GUARD THAT IS DORMANT AT THE DEFAULTS, AND THE MEASUREMENT THAT
        FOUND IT. Swept over amplitudes 27 to 70 and noise 0 to 20, the default
        prominence of 25 degrees admits nothing whose peak stands under twelve
        times the curve's own noise, so the bar of three never binds. It binds
        for a caller who lowers the prominence, which is the caller it protects,
        and that is the only way to reach it."""
        times, values = self.cycles(6, amplitude=70.0, noise=20.0, seed=11)

        accepted, refused = find_repetitions(times, values, prominence=5.0)

        self.assertTrue(refused, "the guard must be reachable through the API")
        self.assertTrue(any("noise" in row["reason"] for row in refused))
        self.assertTrue(accepted, "and it must not refuse everything")

    def test_the_default_prominence_leaves_that_guard_dormant(self):
        """The other half of the measurement, so the claim above is a reading
        rather than an anecdote."""
        times, values = self.cycles(6, amplitude=70.0, noise=20.0, seed=11)

        _, refused = find_repetitions(times, values)

        self.assertEqual(refused, [])

    def test_a_refusal_carries_the_reading_that_caused_it(self):
        times, values = self.cycles(6, amplitude=70.0, noise=20.0, seed=11)

        _, refused = find_repetitions(times, values, prominence=5.0)

        for row in refused:
            self.assertIn("peakToNoise", row)
            self.assertIn("stepNoiseDegrees", row)

    def test_mismatched_inputs_are_refused(self):
        with self.assertRaises(AlignmentError):
            find_repetitions(np.arange(10) / 30.0, np.zeros(9))


if __name__ == "__main__":
    unittest.main()
