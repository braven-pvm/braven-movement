"""Contract tests for the dry run.

THE ONE TEST THIS FILE EXISTS FOR IS THAT THE GATE CAN OPEN. On session 1.0 it
shuts, and it shuts for many separate reasons, so a gate hard-wired to "no"
would produce exactly the output the real run produces and nobody would notice.
Every condition therefore has a passing bundle and a single-fault mutation of
it, and the mutation must shut the gate and NAME ITS OWN CONDITION.

THE GATE NOW LOOPS EVERY MEASURE A CHECKPOINT READS, so the conditions split in
two. Five belong to the CAPTURE and are asked once — a second camera and a clap
are not properties of an elbow. Six belong to a MEASURE and are asked per
measure, because the right elbow being invisible says nothing about the left
knee.

WHY THE PASSING BUNDLE NAMES ITS MEASURE. `judge_measure` asks whether evidence
exists FOR THIS MEASURE rather than whether this measure is the elbow. That is
what lets a synthetic bundle open the gate for any measure, and it is what will
let a future knee reader open it for the knee without a line changing in the
gate. A first version asked the hard-coded question and could never have been
tested here at all.

No solver, no footage, no OpenCV.
"""

import unittest

import numpy as np

from video_dry_run import (
    ILLUSTRATIVE,
    MEANINGFUL_DEGREES,
    condition,
    graded_measures,
    instrument_readings,
    judge_capture,
    judge_measure,
    phase_bound_degrees,
    reading,
    render,
    shape_section,
    tally,
    verdict,
)
from video_measures import CENTIMETRES, DEGREES

MOVEMENT = "netball_two_hand_snatch_pull_in"
# The measure the passing bundle is built around. It is the one the pipeline
# can genuinely read today, so a bundle that opens the gate for it is a bundle
# that could exist after a proper shoot rather than only on paper.
MEASURE = "leftElbowFlexionDegrees"


def engine_curve(frames: int = 98, flat_share: float = 0.48) -> list[float]:
    curve = np.full(frames, 88.87)
    contact = int(frames * 0.5361)
    flat = min(int(frames * flat_share), contact - 1)
    curve[flat:contact] = np.linspace(88.87, 80.0, contact - flat)
    curve[contact:] = np.linspace(80.0, 145.5, frames - contact)
    return [float(v) for v in curve]


def good(**overrides) -> dict:
    """An evidence bundle in which every condition passes for MEASURE.

    This is the fixture the whole file turns on. If it ever stops passing, the
    single-fault mutations below stop proving anything, so
    `test_the_gate_can_open` is checked first and by name.
    """
    rows = (
        [{"name": "left_shoulder"}] * 700 + [{"name": "left_elbow"}] * 700
        + [{"name": "left_wrist"}] * 700 + [{"name": "right_elbow"}] * 690
        + [{"name": "right_shoulder"}] * 690 + [{"name": "right_wrist"}] * 690
        + [{"name": "left_hip"}] * 700 + [{"name": "right_hip"}] * 700
        + [{"name": "left_knee"}] * 700 + [{"name": "left_ankle"}] * 700
    )
    bundle = {
        "front": {"source": {"usableToSeconds": None}},
        "side": {"sync": {
            "offsetSecondsToReference": 1.0,
            "offsetUncertaintySeconds": 0.004,
            "measured": True,
        }},
        "lift": {"rows": rows, "residualMetres": {"framePairs": 700}},
        # NAMED, so the reading is attached to a measure rather than inferred
        # from which file it arrived in.
        "elbow": {"measure": MEASURE, "arm": "left",
                  "agreementDegrees": {"median": 2.1, "p90": 4.0}},
        "alignment": {
            "askedDrillRanks": [1, 1, 1],
            "askedDrillRanksFirstOn": 3,
            # Built one at a time, not `[{...}] * 3`. The multiplied list holds
            # three references to ONE dict, so a test setting a different value
            # on each row sets the same field three times and any per-repetition
            # fault hides.
            "alignments": [
                {
                    "measure": MEASURE,
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
        # The WIDENED shape, with a unit per curve. The gate reads both shapes;
        # this fixture uses the one the widening designs, because a bundle that
        # cannot declare a unit cannot pass the unit condition.
        "reference": {"movements": {MOVEMENT: {
            "curves": {MEASURE: {"unit": DEGREES, "values": engine_curve()}},
            "phase": list(np.linspace(0.0, 1.0, 98)),
            "landmarks": {"contactPhase": 0.5361},
        }}},
        "calibration": {"extrinsics": {
            "separationDegrees": 70.0,
            "worked": {"residualMetres": 0.002},
        }},
    }
    bundle.update(overrides)
    return bundle


def both(bundle: dict, name: str = MEASURE) -> list[dict]:
    """Capture-wide and per-measure conditions together, as the verdict uses."""
    return judge_capture(bundle, MOVEMENT) + judge_measure(bundle, MOVEMENT, name)


def named(conditions: list[dict], name: str) -> dict:
    return next(row for row in conditions if row["name"] == name)


class TheGateCanOpen(unittest.TestCase):
    """First and by name. Everything else in this file depends on it."""

    def test_the_gate_can_open(self):
        found = verdict(both(good()))

        self.assertTrue(found["mayShowNumbers"], found["reason"])
        self.assertEqual(found["blockedBy"], [])
        self.assertIn("each with its uncertainty", found["reason"])

    def test_five_capture_conditions_and_six_per_measure(self):
        capture = judge_capture(good(), MOVEMENT)
        per_measure = judge_measure(good(), MOVEMENT, MEASURE)

        self.assertEqual(len(capture), 5)
        self.assertEqual(len(per_measure), 6)
        self.assertEqual(len({row["name"] for row in capture + per_measure}), 11)


class TheLoopCoversWhatIsGraded(unittest.TestCase):
    def test_the_measures_come_from_the_definition(self):
        """Not from a list written in the gate. Four consumers each picked
        their own set and none was reconciled with what is graded."""
        found = graded_measures(MOVEMENT)

        self.assertEqual(found, sorted(found), "returned in a stable order")
        self.assertIn("leftKneeFlexionDegrees", found)
        self.assertIn(MEASURE, found)

    def test_every_graded_measure_can_be_judged(self):
        """A measure the registry lacks raises rather than being skipped, so
        this also guards the registry against the library moving."""
        bundle = good()

        for name in graded_measures(MOVEMENT):
            rows = judge_measure(bundle, MOVEMENT, name)
            self.assertEqual(len(rows), 6, name)

    def test_an_unreadable_movement_is_refused_rather_than_guessed(self):
        with self.assertRaises(SystemExit):
            graded_measures("netball_no_such_drill")


class InstrumentReadingsTest(unittest.TestCase):
    """The lookup that replaced 'is this the elbow'."""

    def test_a_reading_is_attached_to_the_measure_it_names(self):
        found = instrument_readings(good())

        self.assertIn(MEASURE, found)
        self.assertAlmostEqual(found[MEASURE]["agreementDegrees"], 2.1)
        self.assertAlmostEqual(found[MEASURE]["alignmentPhase"], 0.005)

    def test_a_measure_nothing_read_is_simply_absent(self):
        found = instrument_readings(good())

        self.assertNotIn("leftKneeFlexionDegrees", found)

    def test_the_arm_is_translated_when_no_measure_is_named(self):
        """The shipped elbow curve names its arm, not its measure. The
        translation happens once, here, rather than at each use."""
        bundle = good()
        bundle["elbow"] = {"arm": "right", "agreementDegrees": {"median": 3.0}}

        found = instrument_readings(bundle)

        self.assertIn("rightElbowFlexionDegrees", found)

    def test_the_worst_alignment_across_repetitions_is_the_one_kept(self):
        bundle = good()
        for value, row in zip((0.005, 0.31, 0.02), bundle["alignment"]["alignments"]):
            row["agreementPhase"]["median"] = value

        found = instrument_readings(bundle)

        self.assertAlmostEqual(found[MEASURE]["alignmentPhase"], 0.31)


class OneFaultAtATime(unittest.TestCase):
    """Eleven mutations, each of which must shut the gate and NAME ITS OWN
    condition among the blockers.

    MEMBERSHIP, NOT EQUALITY, and the spread is wider than "one, sometimes
    two". Counted across the thirteen mutations below: TEN block exactly one,
    TWO block two, and ONE blocks FOUR.

        one camera      2 — two views AND sync; the sync block lives in the
                        side view's own keypoint file
        no calibration  2 — calibration AND camera separation; the separation
                        is read from the calibration
        the knee        4 — judged on a bundle built for the elbow, the knee
                        has no engine curve, so it also has no unit to compare
                        against, no second reader and no alignment. One absent
                        artefact leaves four conditions unreadable.

    A measure the modality cannot carry at all is further still: judged on its
    own, `trunkTurnDegrees` blocks ALL SIX per-measure conditions, because
    nothing downstream of "there is no reader" can be answered either.

    None of these is leakage. Each extra block is a correct consequence of the
    same missing evidence, which is why the assertions test MEMBERSHIP — that
    the mutated condition is among the blockers — and never equality.
    """

    def shut(self, bundle: dict, name: str, measure: str = MEASURE):
        conditions = both(bundle, measure)
        found = verdict(conditions)

        self.assertFalse(found["mayShowNumbers"])
        self.assertIn(name, [row.split(" (")[0] for row in found["blockedBy"]])
        self.assertIsNot(named(conditions, name)["passes"], True)
        return found

    # --- the capture ---

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

    def test_the_drill_wins_its_null_test_on_only_some_repetitions(self):
        bundle = good()
        bundle["alignment"]["askedDrillRanks"] = [1, 1, 4]
        bundle["alignment"]["askedDrillRanksFirstOn"] = 2

        self.shut(bundle, "the drill is in the library")

    # --- the measure ---

    def test_a_measure_the_modality_cannot_carry(self):
        """`trunkTurnDegrees` is the athlete's facing along the drill's track.
        No camera quality supplies it, so this can never pass for any footage."""
        conditions = judge_measure(good(), MOVEMENT, "trunkTurnDegrees")

        self.assertIs(named(conditions, "the modality carries it")["passes"], False)
        self.assertIn("POSE and not a position in the gym",
                      named(conditions, "the modality carries it")["why"])

    def test_the_graded_joint_was_barely_seen(self):
        bundle = good()
        bundle["lift"]["rows"] = [
            {"name": "left_shoulder"}] * 700 + [{"name": "left_elbow"}] * 28 + [
            {"name": "left_wrist"}] * 700

        self.shut(bundle, "the graded joint was seen")

    def test_no_engine_curve_for_this_measure(self):
        """The knee is graded by every drill in the library and is not in the
        reference export. Until the widening lands this is its real state."""
        self.shut(good(), "the engine half exists", measure="leftKneeFlexionDegrees")

    def test_the_engine_curve_declares_a_different_unit(self):
        """Two lanes spelling a unit independently is where this fault lives."""
        bundle = good()
        bundle["reference"]["movements"][MOVEMENT]["curves"][MEASURE]["unit"] = CENTIMETRES

        found = self.shut(bundle, "the units agree")

        self.assertIn("the units agree", found["failed"])

    def test_an_undeclared_unit_is_unmeasured_and_not_a_pass(self):
        """The flat curve shape, which is what ships today. A gate that read a
        missing unit as agreement would assume the thing the widening exists
        to stop assuming."""
        bundle = good()
        bundle["reference"]["movements"][MOVEMENT]["curves"][MEASURE] = engine_curve()

        found = self.shut(bundle, "the units agree")

        self.assertIn("the units agree", found["unmeasured"])

    def test_the_two_readings_of_this_measure_disagree(self):
        bundle = good()
        bundle["elbow"]["agreementDegrees"]["median"] = 21.16

        self.shut(bundle, "two instruments agree")

    def test_no_second_reader_exists_for_this_measure(self):
        bundle = good()
        bundle["elbow"] = None

        found = self.shut(bundle, "two instruments agree")

        self.assertIn("two instruments agree", found["unmeasured"])
        self.assertIn("the instrument that does not exist",
                      named(both(bundle), "two instruments agree")["instrument"])

    def test_the_two_alignments_disagree(self):
        bundle = good()
        for row in bundle["alignment"]["alignments"]:
            row["agreementPhase"]["median"] = 0.265

        self.shut(bundle, "alignment agrees")

    def test_no_alignment_exists_for_this_measure(self):
        bundle = good()
        for row in bundle["alignment"]["alignments"]:
            row["measure"] = "leftKneeFlexionDegrees"

        found = self.shut(bundle, "alignment agrees")

        self.assertIn("alignment agrees", found["unmeasured"])

    # --- the counts this class's docstring claims, held rather than asserted ---

    def test_one_absent_artefact_leaves_four_conditions_unreadable(self):
        """The knee judged on a bundle built for the elbow. No engine curve
        means no unit to compare against either, and nothing has read the knee,
        so four conditions go unread from ONE missing artefact. A count line in
        a docstring is prose; this is the reading behind it."""
        found = verdict(both(good(), "leftKneeFlexionDegrees"))
        blocked = {row.split(" (")[0] for row in found["blockedBy"]}

        self.assertEqual(blocked, {
            "the engine half exists", "the units agree",
            "two instruments agree", "alignment agrees"})

    def test_a_measure_the_modality_cannot_carry_blocks_all_six(self):
        """Nothing downstream of "there is no reader" can be answered either."""
        rows = judge_measure(good(), MOVEMENT, "trunkTurnDegrees")
        blocked = [row["name"] for row in rows if row["passes"] is not True]

        self.assertEqual(len(blocked), 6)
        self.assertEqual(len(rows), 6, "every one of them, not merely most")

    def test_the_units_instrument_names_the_missing_declaration(self):
        """The reviewer's second fold. `thresholdWhy` said the curve declares
        no unit and `instrument` named only the two sources, so a reader who
        looked at the instrument field alone could not tell which side was
        silent."""
        bundle = good()
        bundle["reference"]["movements"][MOVEMENT]["curves"][MEASURE] = engine_curve()

        row = named(both(bundle), "the units agree")

        self.assertIsNone(row["passes"])
        self.assertIn("INSTRUMENT THAT DOES NOT EXIST", row["instrument"])
        self.assertIn("declares none", row["instrument"])

    def test_a_declared_unit_names_both_sources_instead(self):
        """The decoy. If the instrument field always carried the missing-
        declaration wording it would be wrong whenever a unit exists."""
        row = named(both(good()), "the units agree")

        self.assertIs(row["passes"], True)
        self.assertNotIn("DOES NOT EXIST", row["instrument"])


class UnmeasuredIsNotAPass(unittest.TestCase):
    def test_absent_evidence_is_unmeasured_rather_than_failed(self):
        conditions = both(good(calibration=None))

        self.assertIsNone(named(conditions, "calibration")["passes"])
        self.assertIsNone(named(conditions, "camera separation")["passes"])

    def test_unmeasured_blocks_exactly_as_hard_as_failed(self):
        absent = verdict(both(good(calibration=None)))
        broken = good()
        broken["elbow"]["agreementDegrees"]["median"] = 21.16

        self.assertFalse(absent["mayShowNumbers"])
        self.assertFalse(verdict(both(broken))["mayShowNumbers"])

    def test_the_verdict_says_which_blockers_were_which(self):
        bundle = good(calibration=None)
        bundle["elbow"]["agreementDegrees"]["median"] = 21.16

        found = verdict(both(bundle))

        self.assertIn("two instruments agree", found["failed"])
        self.assertIn("calibration", found["unmeasured"])
        self.assertIn("UNMEASURED", found["reason"])


class TallyTest(unittest.TestCase):
    """The same condition is now asked of every measure, so the summary must
    not repeat itself once per measure."""

    def test_a_repeated_blocker_is_named_once_with_its_count(self):
        rows = [
            condition("a", "?", 1, "u", 1, "chosen", "w", None, "y", "i"),
            condition("a", "?", 1, "u", 1, "chosen", "w", None, "y", "i"),
            condition("b", "?", 1, "u", 1, "chosen", "w", None, "y", "i"),
        ]

        self.assertEqual(tally(rows, None), ["a (x2)", "b"])

    def test_it_keeps_the_order_it_first_saw_them(self):
        rows = [
            condition("z", "?", 1, "u", 1, "chosen", "w", False, "y", "i"),
            condition("a", "?", 1, "u", 1, "chosen", "w", False, "y", "i"),
        ]

        self.assertEqual(tally(rows, False), ["z", "a"])

    def test_a_passing_condition_is_not_tallied_as_a_blocker(self):
        rows = [condition("a", "?", 1, "u", 1, "chosen", "w", True, "y", "i")]

        self.assertEqual(tally(rows, None), [])
        self.assertEqual(tally(rows, False), [])


class ThresholdKindTest(unittest.TestCase):
    def test_every_threshold_declares_where_it_came_from(self):
        for row in both(good()):
            self.assertIn(
                row["thresholdKind"],
                ("measured", "derived", "chosen", "unavailable"), row["name"])
            self.assertTrue(row["thresholdWhy"], row["name"])

    def test_a_threshold_with_no_kind_is_refused(self):
        with self.assertRaises(ValueError):
            condition("x", "?", 1, "units", 1, "obviously true", "because",
                      True, "why", "instrument")

    def test_at_least_one_of_each_kind_is_present(self):
        kinds = {row["thresholdKind"] for row in both(good())}

        self.assertIn("measured", kinds)
        self.assertIn("derived", kinds)
        self.assertIn("chosen", kinds)


class DerivedPhaseBoundTest(unittest.TestCase):
    def test_the_bound_comes_from_the_curve_and_the_clinical_threshold(self):
        bound, slope = phase_bound_degrees(engine_curve())

        self.assertIsNotNone(bound)
        self.assertAlmostEqual(bound, MEANINGFUL_DEGREES / slope, places=9)

    def test_a_steeper_reference_demands_a_tighter_alignment(self):
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

        self.assertIsNotNone(found["levelGapDegrees"]["uncertainty"])
        self.assertEqual(found["levelGapDegrees"]["uncertainty"], 29.2)

    def test_a_reading_with_no_second_instrument_names_what_is_missing(self):
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
        capture = judge_capture(bundle, MOVEMENT)
        measures = {
            name: judge_measure(bundle, MOVEMENT, name)
            for name in (MEASURE, "leftKneeFlexionDegrees")
        }
        return {
            "set": "0.1", "movement": MOVEMENT,
            "verdict": verdict(capture + [r for rows in measures.values() for r in rows]),
            "capture": capture,
            "measures": {
                name: {"unit": DEGREES, "carriable": True,
                       "verdict": verdict(capture + rows), "conditions": rows}
                for name, rows in measures.items()
            },
            "measuresNote": "the measures this drill grades",
            "shape": shape_section(bundle, MOVEMENT),
            "provenance": {"front": "abc12345, clean=True, now", "calibration": None},
            "provenanceNote": "more than one build meets here",
            "generatedFrom": {"commit": "abc1234567", "treeWasClean": True},
        }

    def test_the_verdict_comes_before_the_evidence(self):
        text = render(self.document(good(calibration=None)))

        self.assertLess(text.index("## The verdict"), text.index("## The capture"))
        self.assertIn("NO NUMBER MAY BE SHOWN", text)

    def test_every_graded_measure_gets_its_own_section(self):
        text = render(self.document(good()))

        self.assertIn(f"### {MEASURE}", text)
        self.assertIn("### leftKneeFlexionDegrees", text)
        self.assertIn("| measure | unit | verdict | blocked by |", text)

    def test_a_measure_that_cannot_be_shown_says_withheld(self):
        text = render(self.document(good()))

        self.assertIn("withheld", text)

    def test_an_absent_artefact_is_named_absent(self):
        text = render(self.document(good(calibration=None)))

        self.assertIn("ABSENT", text)

    def test_the_threshold_kind_reaches_the_table_whole(self):
        text = render(self.document(good()))

        self.assertIn("| chosen |", text)
        self.assertIn("| measured |", text)
        self.assertNotIn("| chosen at one frame, because |", text)

    def test_each_bar_is_explained_once_and_not_once_per_measure(self):
        """Eleven conditions across three sections would otherwise print the
        same explanation four times."""
        text = render(self.document(good()))

        self.assertEqual(text.count("**the units agree** —"), 1)


if __name__ == "__main__":
    unittest.main()
