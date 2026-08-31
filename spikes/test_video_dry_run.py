"""Contract tests for the dry run.

THE ONE TEST THIS FILE EXISTS FOR IS THAT THE GATE CAN OPEN. On session 1.0 it
shuts, and it shuts for six separate reasons, so a gate hard-wired to "no"
would produce exactly the output the real run produces and nobody would notice.
Every condition therefore has a passing bundle and a single-fault mutation of
it, and the mutation must shut the gate and NAME ITS OWN CONDITION.

No solver, no footage, no OpenCV. Only numpy and scipy, through the alignment
module's featureless share.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_dry_run import (  # noqa: E402
    ILLUSTRATIVE,
    MEANINGFUL_DEGREES,
    condition,
    judge,
    phase_bound_degrees,
    reading,
    render,
    shape_section,
    verdict,
)

MOVEMENT = "netball_two_hand_snatch_pull_in"


def engine_curve(frames: int = 98, flat_share: float = 0.48) -> list[float]:
    curve = np.full(frames, 88.87)
    contact = int(frames * 0.5361)
    flat = min(int(frames * flat_share), contact - 1)
    curve[flat:contact] = np.linspace(88.87, 80.0, contact - flat)
    curve[contact:] = np.linspace(80.0, 145.5, frames - contact)
    return [float(v) for v in curve]


def good(**overrides) -> dict:
    """An evidence bundle in which every condition passes.

    This is the fixture the whole file turns on. If it ever stops passing, the
    single-fault mutations below stop proving anything, so `test_the_gate_can_
    open` is checked first and by name.
    """
    frames = 98
    curve = engine_curve(frames)
    rows = (
        [{"name": "left_shoulder"}] * 700 + [{"name": "left_elbow"}] * 700
        + [{"name": "left_wrist"}] * 700 + [{"name": "right_elbow"}] * 690
        + [{"name": "right_shoulder"}] * 690 + [{"name": "right_wrist"}] * 690
    )
    bundle = {
        "front": {"source": {"usableToSeconds": None}},
        "side": {"sync": {
            "offsetSecondsToReference": 1.0,
            "offsetUncertaintySeconds": 0.004,
            "measured": True,
        }},
        "lift": {"rows": rows, "residualMetres": {"framePairs": 700}},
        "elbow": {"agreementDegrees": {"median": 2.1, "p90": 4.0}},
        "alignment": {
            "askedDrillRanks": [1, 1, 1],
            "askedDrillRanksFirstOn": 3,
            # BUILT ONE AT A TIME, NOT `[{...}] * 3`. The multiplied list holds
            # three references to ONE dict, so a test that sets a different
            # level gap on each row sets the same field three times and the
            # spread comes out zero. That aliasing hid a real assertion once
            # and would have hidden any other per-repetition fault too.
            "alignments": [
                {
                    "window": {"startSeconds": 1.0, "catchSeconds": 9.13,
                               "endSeconds": 2.0, "peakSeconds": 2.0},
                    "agreementPhase": {"median": 0.005, "worst": 0.01},
                    "medianLevelGapDegrees": 1.2,
                    "featurelessSharePhase": 0.48,
                    "handColumns": {
                        "videoBeforeDegrees": 88.0, "engineBeforeDegrees": 88.9,
                        "videoAtContactDegrees": 79.0,
                        "engineAtContactDegrees": 80.0,
                        "videoPullInDegrees": 144.0,
                        "enginePullInDegrees": 145.5,
                    },
                }
                for _ in range(3)
            ],
        },
        "reference": {"movements": {MOVEMENT: {
            "curves": {"leftElbowFlexionDegrees": curve},
            "phase": list(np.linspace(0.0, 1.0, frames)),
            "landmarks": {"contactPhase": 0.5361},
        }}},
        "calibration": {"extrinsics": {
            "separationDegrees": 70.0,
            "worked": {"residualMetres": 0.002},
        }},
    }
    bundle.update(overrides)
    return bundle


def named(conditions: list[dict], name: str) -> dict:
    return next(row for row in conditions if row["name"] == name)


class TheGateCanOpen(unittest.TestCase):
    """First and by name. Everything else in this file depends on it."""

    def test_the_gate_can_open(self):
        found = verdict(judge(good(), MOVEMENT))

        self.assertTrue(found["mayShowNumbers"], found["reason"])
        self.assertEqual(found["blockedBy"], [])
        self.assertIn("each with its uncertainty", found["reason"])

    def test_all_eight_conditions_are_judged(self):
        conditions = judge(good(), MOVEMENT)

        self.assertEqual(len(conditions), 8)
        self.assertEqual(len({row["name"] for row in conditions}), 8)


class OneFaultAtATime(unittest.TestCase):
    """Eight mutations, each of which must shut the gate and NAME ITS OWN
    condition among the blockers.

    MEMBERSHIP, NOT EQUALITY, and an earlier version of this docstring said
    "each breaking exactly one condition", which overstated it. Counted: six of
    the eight block exactly one, and two block two, because the evidence they
    remove feeds two conditions.

        one camera      blocks two views AND sync — the sync block lives in
                        the side view's own keypoint file
        no calibration  blocks calibration AND camera separation — the
                        separation is read from the calibration

    Both second blocks are correct consequences rather than leakage, and a
    test asserting equality would have had to pretend otherwise. What each
    test does assert is the part that matters: the gate shuts, and the
    mutated condition is among the reasons. A gate that shut for the wrong
    reason would pass a test that only checked it shut.
    """

    def shut(self, bundle: dict, name: str):
        conditions = judge(bundle, MOVEMENT)
        found = verdict(conditions)

        self.assertFalse(found["mayShowNumbers"])
        self.assertIn(name, found["blockedBy"])
        self.assertIsNot(named(conditions, name)["passes"], True)
        return found

    def test_one_camera(self):
        self.shut(good(side=None), "two views")

    def test_no_calibration_at_all(self):
        found = self.shut(good(calibration=None), "calibration")

        self.assertIn("calibration", found["unmeasured"])
        self.assertNotIn("calibration", found["failed"])

    def test_the_cameras_are_too_close_together(self):
        bundle = good()
        bundle["calibration"]["extrinsics"]["separationDegrees"] = 20.0

        self.shut(bundle, "camera separation")

    def test_the_sync_is_looser_than_a_frame(self):
        bundle = good()
        bundle["side"]["sync"]["offsetUncertaintySeconds"] = 0.15

        self.shut(bundle, "sync")

    def test_the_two_elbow_readings_disagree(self):
        bundle = good()
        bundle["elbow"]["agreementDegrees"]["median"] = 21.16

        self.shut(bundle, "two instruments agree")

    def test_the_two_alignments_disagree(self):
        bundle = good()
        for row in bundle["alignment"]["alignments"]:
            row["agreementPhase"]["median"] = 0.265

        self.shut(bundle, "alignment agrees")

    def test_the_drill_wins_its_null_test_on_only_some_repetitions(self):
        bundle = good()
        bundle["alignment"]["askedDrillRanks"] = [1, 1, 4]
        bundle["alignment"]["askedDrillRanksFirstOn"] = 2

        self.shut(bundle, "the drill is in the library")

    def test_the_graded_joint_was_barely_seen(self):
        """The 90-degree pair finding, as a gate. On session 1.0 the right
        elbow appears in zero of 735 frame pairs."""
        bundle = good()
        bundle["lift"]["rows"] = [{"name": "left_shoulder"}] * 700 + [
            {"name": "left_elbow"}] * 28 + [{"name": "left_wrist"}] * 700

        self.shut(bundle, "the graded joint was seen")


class UnmeasuredIsNotAPass(unittest.TestCase):
    def test_absent_evidence_is_unmeasured_rather_than_failed(self):
        conditions = judge(good(calibration=None), MOVEMENT)

        self.assertIsNone(named(conditions, "calibration")["passes"])
        self.assertIsNone(named(conditions, "camera separation")["passes"])

    def test_unmeasured_blocks_exactly_as_hard_as_failed(self):
        absent = verdict(judge(good(calibration=None), MOVEMENT))
        broken = good()
        broken["elbow"]["agreementDegrees"]["median"] = 21.16
        failed = verdict(judge(broken, MOVEMENT))

        self.assertFalse(absent["mayShowNumbers"])
        self.assertFalse(failed["mayShowNumbers"])

    def test_the_verdict_says_which_blockers_were_which(self):
        bundle = good(calibration=None)
        bundle["elbow"]["agreementDegrees"]["median"] = 21.16

        found = verdict(judge(bundle, MOVEMENT))

        self.assertIn("two instruments agree", found["failed"])
        self.assertIn("calibration", found["unmeasured"])
        self.assertIn("UNMEASURED", found["reason"])


class ThresholdKindTest(unittest.TestCase):
    def test_every_threshold_declares_where_it_came_from(self):
        for row in judge(good(), MOVEMENT):
            self.assertIn(
                row["thresholdKind"],
                ("measured", "derived", "chosen", "unavailable"), row["name"])
            self.assertTrue(row["thresholdWhy"], row["name"])

    def test_a_threshold_with_no_kind_is_refused(self):
        """The decoy. Without this the field could hold anything at all."""
        with self.assertRaises(ValueError):
            condition("x", "?", 1, "units", 1, "obviously true", "because",
                      True, "why", "instrument")

    def test_at_least_one_of_each_kind_is_present(self):
        kinds = {row["thresholdKind"] for row in judge(good(), MOVEMENT)}

        self.assertIn("measured", kinds)
        self.assertIn("derived", kinds)
        self.assertIn("chosen", kinds)


class DerivedPhaseBoundTest(unittest.TestCase):
    def test_the_bound_comes_from_the_curve_and_the_clinical_threshold(self):
        bound, slope = phase_bound_degrees(engine_curve())

        self.assertIsNotNone(bound)
        self.assertAlmostEqual(bound, MEANINGFUL_DEGREES / slope, places=9)

    def test_a_steeper_reference_demands_a_tighter_alignment(self):
        """The reason it is derived rather than chosen: the bar follows the
        curve. A drill that changes fast cannot tolerate the phase error a slow
        one can."""
        gentle, _ = phase_bound_degrees(engine_curve(flat_share=0.05))
        steep = engine_curve()
        steep[60:] = list(np.linspace(80.0, 400.0, len(steep) - 60))
        tight, _ = phase_bound_degrees(steep)

        self.assertLess(tight, gentle)

    def test_a_flat_reference_yields_no_bound(self):
        bound, slope = phase_bound_degrees([90.0] * 40)

        self.assertIsNone(bound)
        self.assertIsNone(slope)


class ShapeSectionTest(unittest.TestCase):
    def test_it_carries_the_illustrative_phrase(self):
        found = shape_section(good(), MOVEMENT)

        self.assertEqual(found["status"], ILLUSTRATIVE)
        self.assertIn("NEVER A MEASUREMENT", found["status"])

    def test_the_level_gap_carries_an_uncertainty(self):
        bundle = good()
        for gap, row in zip((-47.0, 0.0, 11.5), bundle["alignment"]["alignments"]):
            row["medianLevelGapDegrees"] = gap

        found = shape_section(bundle, MOVEMENT)

        # Half the full range of -47.0 to +11.5 is 29.25, and the report prints
        # one decimal. THE ASSERTION IS ON WHAT A READER SEES, 29.2, rather than
        # on 29.25 within a tolerance — a first version asserted the unrounded
        # value within 0.05 and failed by 7e-16, which is the tolerance arguing
        # with the arithmetic rather than either being wrong.
        self.assertIsNotNone(found["levelGapDegrees"]["uncertainty"])
        self.assertEqual(found["levelGapDegrees"]["uncertainty"], 29.2)

    def test_a_reading_with_no_second_instrument_names_what_is_missing(self):
        """`uncertainty: null` must never mean "small". It means nobody looked,
        and the instrument field has to say so."""
        found = shape_section(good(), MOVEMENT)

        self.assertIsNone(found["featurelessSharePhase"]["uncertainty"])
        self.assertIn("no second instrument",
                      found["featurelessSharePhase"]["instrument"])

    def test_no_alignment_yields_no_shape_rather_than_an_empty_one(self):
        self.assertIsNone(shape_section(good(alignment=None), MOVEMENT))


class ReadingTest(unittest.TestCase):
    def test_an_uncertainty_of_none_still_carries_an_instrument(self):
        found = reading(1.0, None, "degrees", "nothing read this twice")

        self.assertIsNone(found["uncertainty"])
        self.assertTrue(found["instrument"])


class RenderTest(unittest.TestCase):
    def document(self, bundle: dict) -> dict:
        conditions = judge(bundle, MOVEMENT)
        return {
            "set": "0.1", "movement": MOVEMENT,
            "verdict": verdict(conditions), "conditions": conditions,
            "shape": shape_section(bundle, MOVEMENT),
            "provenance": {"front": "abc12345, clean=True, now", "calibration": None},
            "provenanceNote": "more than one build meets here",
            "generatedFrom": {"commit": "abc1234567", "treeWasClean": True},
        }

    def test_the_verdict_comes_before_the_evidence(self):
        text = render(self.document(good(calibration=None)))

        self.assertLess(text.index("## The verdict"), text.index("## The gate"))
        self.assertIn("NO NUMBER MAY BE SHOWN", text)

    def test_an_open_gate_says_so(self):
        text = render(self.document(good()))

        self.assertIn("**NUMBERS MAY BE SHOWN**", text)

    def test_an_absent_artefact_is_named_absent(self):
        text = render(self.document(good(calibration=None)))

        self.assertIn("ABSENT", text)

    def test_the_threshold_kind_reaches_the_table_whole(self):
        """The fault this replaced: the kind was parsed back out of prose by
        splitting on a colon, and a sentence with two colons lost half itself."""
        text = render(self.document(good()))

        self.assertIn("| chosen |", text)
        self.assertIn("| measured |", text)
        self.assertNotIn("| chosen at one frame, because |", text)


if __name__ == "__main__":
    unittest.main()
