"""Contract tests for the frame-free joint measures."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from segment_measures import (  # noqa: E402
    SegmentMeasureError,
    elbow_flexion_degrees,
    hip_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
    trunk_lean_degrees,
)


class ElbowTest(unittest.TestCase):
    def test_a_straight_arm_is_zero_flexion(self):
        flexion = elbow_flexion_degrees(
            shoulder=(0.0, 1.0, 0.0), elbow=(0.0, 0.0, 0.0), wrist=(0.0, -1.0, 0.0)
        )

        self.assertAlmostEqual(flexion, 0.0, places=6)

    def test_a_right_angle_is_ninety_degrees(self):
        flexion = elbow_flexion_degrees(
            shoulder=(0.0, 1.0, 0.0), elbow=(0.0, 0.0, 0.0), wrist=(1.0, 0.0, 0.0)
        )

        self.assertAlmostEqual(flexion, 90.0, places=6)

    def test_a_fully_closed_arm_approaches_one_hundred_and_eighty(self):
        flexion = elbow_flexion_degrees(
            shoulder=(0.0, 1.0, 0.0), elbow=(0.0, 0.0, 0.0), wrist=(0.0, 0.99, 0.05)
        )

        self.assertGreater(flexion, 170.0)

    def test_the_two_arms_report_different_angles(self):
        """The failure this module exists to prevent."""
        left = elbow_flexion_degrees(
            shoulder=(-0.2, 1.0, 0.0), elbow=(-0.2, 0.0, 0.0), wrist=(-0.6, 0.4, 0.0)
        )
        right = elbow_flexion_degrees(
            shoulder=(0.2, 1.0, 0.0), elbow=(0.2, 0.0, 0.0), wrist=(0.2, -0.9, 0.3)
        )

        self.assertGreater(abs(left - right), 30.0)

    def test_a_collapsed_segment_is_rejected(self):
        with self.assertRaises(SegmentMeasureError):
            elbow_flexion_degrees(
                shoulder=(0.0, 0.0, 0.0), elbow=(0.0, 0.0, 0.0), wrist=(1.0, 0.0, 0.0)
            )

    def test_flexion_is_unchanged_when_the_whole_arm_rotates(self):
        """A measure a coach trusts must not depend on the camera angle."""
        angle = math.radians(37.0)
        cosine, sine = math.cos(angle), math.sin(angle)

        def rotate(point):
            x, y, z = point
            return (x * cosine - z * sine, y, x * sine + z * cosine)

        shoulder, elbow, wrist = (0.0, 1.0, 0.0), (0.0, 0.0, 0.0), (0.7, 0.3, 0.0)
        before = elbow_flexion_degrees(shoulder=shoulder, elbow=elbow, wrist=wrist)
        after = elbow_flexion_degrees(
            shoulder=rotate(shoulder), elbow=rotate(elbow), wrist=rotate(wrist)
        )

        self.assertAlmostEqual(before, after, places=6)


class ShoulderTest(unittest.TestCase):
    def test_an_arm_beside_the_trunk_is_zero_elevation(self):
        elevation = shoulder_elevation_degrees(
            pelvis=(0.0, 0.0, 0.0),
            neck=(0.0, 1.0, 0.0),
            shoulder=(0.2, 0.9, 0.0),
            elbow=(0.2, 0.6, 0.0),
        )

        self.assertAlmostEqual(elevation, 0.0, places=6)

    def test_an_arm_straight_overhead_is_one_hundred_and_eighty(self):
        elevation = shoulder_elevation_degrees(
            pelvis=(0.0, 0.0, 0.0),
            neck=(0.0, 1.0, 0.0),
            shoulder=(0.2, 0.9, 0.0),
            elbow=(0.2, 1.3, 0.0),
        )

        self.assertAlmostEqual(elevation, 180.0, places=6)

    def test_elevation_follows_the_trunk_when_the_athlete_leans(self):
        upright = shoulder_elevation_degrees(
            pelvis=(0.0, 0.0, 0.0),
            neck=(0.0, 1.0, 0.0),
            shoulder=(0.0, 0.9, 0.0),
            elbow=(0.3, 0.9, 0.0),
        )
        leaning = shoulder_elevation_degrees(
            pelvis=(0.0, 0.0, 0.0),
            neck=(0.3, 1.0, 0.0),
            shoulder=(0.3, 0.9, 0.0),
            elbow=(0.6, 0.9 + 0.3, 0.0),
        )

        self.assertAlmostEqual(upright, 90.0, places=6)
        self.assertNotAlmostEqual(leaning, 90.0, places=1)


class LowerBodyTest(unittest.TestCase):
    def test_a_straight_leg_is_zero_knee_flexion(self):
        flexion = knee_flexion_degrees(
            hip=(0.0, 1.0, 0.0), knee=(0.0, 0.5, 0.0), ankle=(0.0, 0.0, 0.0)
        )

        self.assertAlmostEqual(flexion, 0.0, places=6)

    def test_standing_upright_is_zero_hip_flexion(self):
        flexion = hip_flexion_degrees(
            neck=(0.0, 1.5, 0.0), pelvis=(0.0, 1.0, 0.0), knee=(0.0, 0.5, 0.0)
        )

        self.assertAlmostEqual(flexion, 0.0, places=6)

    def test_trunk_lean_is_measured_from_the_given_up_direction(self):
        lean = trunk_lean_degrees(
            pelvis=(0.0, 0.0, 0.0), neck=(1.0, 1.0, 0.0), up=(0.0, 1.0, 0.0)
        )

        self.assertAlmostEqual(lean, 45.0, places=6)


if __name__ == "__main__":
    unittest.main()
