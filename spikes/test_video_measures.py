"""Contract tests for the video measure registry.

THE TEST THIS FILE EXISTS FOR IS THE COMPLETENESS GUARD: every measure any
checkpoint in the library grades must be in the registry. Without it the gate
covers whatever somebody remembered to add, while reporting on "every graded
measure" — which is the hollow-coverage fault this repository keeps meeting,
one level up from a skipped test.

IT READS THE LIBRARY WITHOUT A SOLVER, and that is not incidental.
`movement_engine.library` is a directory glob living in a module whose first job
is to import `pymomentum`, and importing it from a test turned eleven checks
into one error twice. `MOVEMENT_DIR` comes from `ball_track`, which is the route
`test_authored_launch` already established after that fault.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from ball_track import MOVEMENT_DIR
from movement_definition import load as load_definition
from video_measures import (
    CENTIMETRES,
    DEGREES,
    MEASURES,
    MIDPOINTS,
    MeasureError,
    measure,
    scarcest_landmark,
)

# A plausible standing pose in the lift's own frame — across, up, ahead — in
# metres. Nothing here is anatomically precise; what matters is that no two
# joints coincide, so every angle is defined and every perturbation can move it.
POSE = {
    "left_shoulder": (-0.14, 1.40, 0.00),
    "right_shoulder": (0.14, 1.40, 0.02),
    "left_elbow": (-0.20, 1.12, 0.05),
    "right_elbow": (0.20, 1.13, 0.06),
    "left_wrist": (-0.24, 0.86, 0.10),
    "right_wrist": (0.24, 0.87, 0.11),
    "left_hip": (-0.10, 0.92, 0.00),
    "right_hip": (0.10, 0.92, 0.01),
    "left_knee": (-0.11, 0.50, 0.04),
    "right_knee": (0.11, 0.50, 0.03),
    "left_ankle": (-0.11, 0.08, 0.00),
    "right_ankle": (0.11, 0.06, 0.00),
}


def definition_paths() -> list[Path]:
    """Every movement definition, found without importing a solver.

    A definition is `<id>.json`. The companions are `<id>.ball.json`,
    `<id>.motion.json` and `<id>.technique.json`, so a definition is the one
    whose stem carries no further dot.
    """
    return sorted(
        path for path in MOVEMENT_DIR.glob("*.json") if "." not in path.stem
    )


def graded_measures_in_library() -> dict[str, set[str]]:
    """Which movements grade each measure, from the definition's OWN accessor.

    `MovementDefinition.graded_measures()`, not a walk over `phase.checkpoints`
    written here. A first version of this file did write that walk, and it was
    the hand-rolled rule the movement lane had already been asked for: the same
    fault as reimplementing `separation`, one layer up. When the definition
    changes what it counts as graded, this follows without being edited.
    """
    found: dict[str, set[str]] = {}
    for path in definition_paths():
        for name in load_definition(path).graded_measures():
            found.setdefault(name, set()).add(path.stem)
    return found


class CompletenessTest(unittest.TestCase):
    """The anti-hollow guard. Everything else here is detail beside it."""

    def test_the_library_has_definitions_to_check(self):
        """Guards the guard. A glob that matches nothing passes everything."""
        paths = definition_paths()

        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            self.assertNotIn(".", path.stem, path.name)

    def test_every_graded_measure_is_in_the_registry(self):
        graded = graded_measures_in_library()

        self.assertTrue(graded, "no checkpoint graded anything")
        missing = sorted(set(graded) - set(MEASURES))
        self.assertEqual(
            missing, [],
            f"the library grades {missing} and the registry has never heard of "
            "them, so the gate would report on 'every graded measure' while "
            "silently covering fewer")

    def test_the_registry_holds_nothing_the_library_does_not_grade(self):
        """The other direction. A registry entry nothing grades is dead weight
        that will be maintained as though it mattered."""
        graded = graded_measures_in_library()

        stray = sorted(set(MEASURES) - set(graded))
        self.assertEqual(stray, [])

    def test_every_PHASE_of_every_drill_is_covered_too(self):
        """The gate asks per movement today and will ask per phase when a
        checkpoint's phase decides which conditions apply. `Phase` has its own
        accessor, so the registry is checked against that as well rather than
        against the union alone — a measure graded only at one phase is still a
        measure the gate must know."""
        for path in definition_paths():
            for phase in load_definition(path).phases:
                for name in phase.graded_measures():
                    self.assertIn(name, MEASURES, f"{path.stem}/{phase.name}")

    def test_an_unknown_measure_is_refused_by_name(self):
        """Not skipped. Skipping is how a gate covers less than it claims."""
        with self.assertRaises(MeasureError) as raised:
            measure("leftPinkyWaggleDegrees")
        self.assertIn("registry", str(raised.exception))


class UnitTest(unittest.TestCase):
    def test_one_graded_measure_is_not_an_angle(self):
        """The reason units travel at all. If every measure were degrees the
        unit field would be decoration and would rot untested."""
        units = {entry.unit for entry in MEASURES.values()}

        self.assertIn(DEGREES, units)
        self.assertIn(CENTIMETRES, units)

    def test_the_foot_gap_is_centimetres_and_the_angles_are_degrees(self):
        self.assertEqual(measure("footHeightGapCm").unit, CENTIMETRES)
        for name in ("leftElbowFlexionDegrees", "trunkLeanDegrees"):
            self.assertEqual(measure(name).unit, DEGREES)

    def test_the_foot_gap_reads_in_centimetres_not_metres(self):
        """The lift is in metres and this measure is not. Two centimetres of
        difference must read as 2, not 0.02."""
        value = measure("footHeightGapCm").read(POSE)

        self.assertAlmostEqual(value, 2.0, places=6)


class CarriableTest(unittest.TestCase):
    def test_the_track_measure_is_not_carriable_and_says_why(self):
        entry = measure("trunkTurnDegrees")

        self.assertFalse(entry.carriable)
        self.assertIn("POSE and not a position in the gym", entry.unreadable_because)

    def test_reading_it_raises_rather_than_returning_a_number(self):
        """A number here would be the worst outcome: a plausible value for a
        quantity the modality does not contain."""
        with self.assertRaises(MeasureError):
            measure("trunkTurnDegrees").read(POSE)

    def test_every_other_measure_is_carriable(self):
        for name, entry in MEASURES.items():
            if name == "trunkTurnDegrees":
                continue
            self.assertTrue(entry.carriable, name)


class ReadTest(unittest.TestCase):
    def test_every_carriable_measure_reads_a_finite_number(self):
        for name, entry in MEASURES.items():
            if not entry.carriable:
                continue
            value = entry.read(POSE)
            self.assertIsNotNone(value, name)
            self.assertEqual(value, value, name)

    def test_a_missing_landmark_gives_None_and_not_zero(self):
        """None means nobody saw it. Zero is a real reading — a straight arm.
        A gate that could not tell them apart would grade an absence."""
        entry = measure("leftElbowFlexionDegrees")
        without = {k: v for k, v in POSE.items() if k != "left_wrist"}

        self.assertIsNone(entry.read(without))

    def test_a_straight_arm_reads_zero_in_the_engine_convention(self):
        """THE CONVENTION GUARD. `elbow_flexion_degrees` is `180 - included`,
        so a straight arm is ZERO and a folded one is large. A video curve
        carrying the included angle would be the opposite convention, reading
        in the same units, and the first version of the elbow spike had it."""
        straight = dict(POSE)
        straight["left_shoulder"] = (0.0, 1.40, 0.0)
        straight["left_elbow"] = (0.0, 1.10, 0.0)
        straight["left_wrist"] = (0.0, 0.80, 0.0)

        self.assertAlmostEqual(measure("leftElbowFlexionDegrees").read(straight),
                               0.0, places=6)

    def test_a_folded_arm_reads_large(self):
        """The decoy for the test above. A reader stuck at zero would pass it."""
        folded = dict(POSE)
        folded["left_shoulder"] = (0.0, 1.40, 0.0)
        folded["left_elbow"] = (0.0, 1.10, 0.0)
        folded["left_wrist"] = (0.0, 1.38, 0.05)

        self.assertGreater(measure("leftElbowFlexionDegrees").read(folded), 150.0)

    def test_the_midpoint_joints_are_derived_and_not_demanded(self):
        """`pelvis` and `neck` are engine joints the pose model has no landmark
        for. They are built from the two hips and the two shoulders, which is
        the same pair video_lift_3d already ties its scale by."""
        entry = measure("trunkLeanDegrees")

        self.assertNotIn("pelvis", entry.landmarks)
        self.assertIn("left_hip", entry.landmarks)
        self.assertIsNotNone(entry.read(POSE))

    def test_losing_one_hip_loses_the_midpoint_and_the_measure(self):
        entry = measure("trunkLeanDegrees")
        without = {k: v for k, v in POSE.items() if k != "right_hip"}

        self.assertIsNone(entry.read(without))


class LandmarksAreAccurateTest(unittest.TestCase):
    """Every declared landmark must actually move its measure.

    A `landmarks` tuple is used by the gate to decide whether a measure could
    be read at all, so a tuple listing a joint the reader ignores would block a
    measure for a reason that is not true, and a tuple missing one the reader
    uses would let a measure through on evidence it does not have. Perturbing
    each declared landmark and requiring the value to move tests the first;
    `test_a_missing_landmark_gives_None_and_not_zero` tests the second.
    """

    def test_each_declared_landmark_changes_its_measure(self):
        for name, entry in MEASURES.items():
            if not entry.carriable:
                continue
            before = entry.read(POSE)
            for landmark in entry.landmarks:
                moved = dict(POSE)
                moved[landmark] = tuple(
                    value + 0.25 for value in POSE[landmark])
                after = entry.read(moved)
                self.assertNotAlmostEqual(
                    before, after, places=3,
                    msg=f"{name} declares {landmark} and does not use it")


class ScarcestLandmarkTest(unittest.TestCase):
    def test_it_returns_the_rarest_and_not_the_average(self):
        """A measure is only as available as its rarest joint. On session 1.0
        the right shoulder appears 735 times and the right elbow zero, so an
        average would call rightElbowFlexionDegrees well seen."""
        counts = {"right_shoulder": 735, "right_elbow": 0, "right_wrist": 28}

        joint, seen = scarcest_landmark(measure("rightElbowFlexionDegrees"), counts)

        self.assertEqual(joint, "right_elbow")
        self.assertEqual(seen, 0)

    def test_a_landmark_absent_from_the_counts_reads_zero(self):
        """Absent from the tally is absent from the footage, not unknown."""
        joint, seen = scarcest_landmark(
            measure("leftElbowFlexionDegrees"), {"left_shoulder": 700})

        self.assertEqual(seen, 0)
        self.assertIn(joint, ("left_elbow", "left_wrist"))

    def test_midpoint_joints_are_counted_by_their_real_landmarks(self):
        """`pelvis` is never in a landmark tally, so a measure needing it must
        be counted by the hips it is built from."""
        counts = {"left_hip": 735, "right_hip": 12,
                  "left_shoulder": 735, "right_shoulder": 735}

        joint, seen = scarcest_landmark(measure("trunkLeanDegrees"), counts)

        self.assertEqual(joint, "right_hip")
        self.assertEqual(seen, 12)

    def test_no_midpoint_name_survives_into_the_counted_set(self):
        for name, entry in MEASURES.items():
            for joint in entry.landmarks:
                self.assertNotIn(joint, MIDPOINTS, f"{name} declares {joint}")


if __name__ == "__main__":
    unittest.main()
