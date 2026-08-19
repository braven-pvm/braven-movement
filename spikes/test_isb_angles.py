"""Contract tests for the ISB angle measurement layer.

Each test builds a pose whose correct answer a person can verify by hand, then
confirms the module reports that answer.
"""

import math
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from isb_angles import (  # noqa: E402
    AAOS_LIMITS,
    IsbAngleError,
    JointAngles,
    build_segment_frame,
    build_thorax_frame,
    check_ranges,
    elbow_angles,
    euler_yxy_degrees,
    euler_zxy_degrees,
    frame_from_axes,
    knee_angles,
    relative_rotation,
    shoulder_angles,
)


def rotation_z(degrees: float):
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return ((cosine, -sine, 0.0), (sine, cosine, 0.0), (0.0, 0.0, 1.0))


def rotation_x(degrees: float):
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return ((1.0, 0.0, 0.0), (0.0, cosine, -sine), (0.0, sine, cosine))


def rotation_y(degrees: float):
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return ((cosine, 0.0, sine), (0.0, 1.0, 0.0), (-sine, 0.0, cosine))


def multiply(left, right):
    return tuple(
        tuple(
            sum(left[row][index] * right[index][column] for index in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


class EulerDecompositionTest(unittest.TestCase):
    def test_zxy_recovers_the_angles_that_built_the_rotation(self):
        rotation = multiply(
            rotation_z(35.0), multiply(rotation_x(-12.0), rotation_y(20.0))
        )

        first, second, third = euler_zxy_degrees(rotation)

        self.assertAlmostEqual(first, 35.0, places=6)
        self.assertAlmostEqual(second, -12.0, places=6)
        self.assertAlmostEqual(third, 20.0, places=6)

    def test_yxy_recovers_the_angles_that_built_the_rotation(self):
        rotation = multiply(
            rotation_y(40.0), multiply(rotation_x(75.0), rotation_y(-25.0))
        )

        first, second, third = euler_yxy_degrees(rotation)

        self.assertAlmostEqual(first, 40.0, places=6)
        self.assertAlmostEqual(second, 75.0, places=6)
        self.assertAlmostEqual(third, -25.0, places=6)

    def test_zxy_rejects_a_degenerate_rotation(self):
        with self.assertRaises(IsbAngleError):
            euler_zxy_degrees(rotation_x(90.0))

    def test_yxy_rejects_a_degenerate_rotation(self):
        with self.assertRaises(IsbAngleError):
            euler_yxy_degrees(IDENTITY)


class SegmentFrameTest(unittest.TestCase):
    def test_limb_frame_axes_are_orthonormal_and_right_handed(self):
        frame = build_segment_frame(
            distal_point=(0.0, 0.0, 0.0),
            proximal_point=(0.0, 0.3, 0.0),
            lateral_point=(0.05, 0.0, 0.0),
            name="test",
        )

        columns = [tuple(frame[row][column] for row in range(3)) for column in range(3)]
        for column in columns:
            self.assertAlmostEqual(math.dist(column, (0.0, 0.0, 0.0)), 1.0, places=9)
        for first in range(3):
            for second in range(first + 1, 3):
                dot = sum(
                    columns[first][index] * columns[second][index] for index in range(3)
                )
                self.assertAlmostEqual(dot, 0.0, places=9)
        x_axis, y_axis, z_axis = columns
        expected_z = (
            x_axis[1] * y_axis[2] - x_axis[2] * y_axis[1],
            x_axis[2] * y_axis[0] - x_axis[0] * y_axis[2],
            x_axis[0] * y_axis[1] - x_axis[1] * y_axis[0],
        )
        for index in range(3):
            self.assertAlmostEqual(z_axis[index], expected_z[index], places=9)

    def test_limb_frame_rejects_collinear_landmarks(self):
        with self.assertRaises(IsbAngleError):
            build_segment_frame(
                distal_point=(0.0, 0.0, 0.0),
                proximal_point=(0.0, 0.3, 0.0),
                lateral_point=(0.0, 0.1, 0.0),
                name="test",
            )

    def test_thorax_frame_points_up_and_to_the_right(self):
        frame = build_thorax_frame(
            suprasternale=(0.08, 1.40, 0.0),
            c7=(-0.08, 1.42, 0.0),
            xiphoid=(0.07, 1.15, 0.0),
            t8=(-0.07, 1.16, 0.0),
        )

        y_axis = (frame[0][1], frame[1][1], frame[2][1])
        z_axis = (frame[0][2], frame[1][2], frame[2][2])
        self.assertGreater(y_axis[1], 0.9)
        self.assertGreater(z_axis[2], 0.9)


class ElbowTest(unittest.TestCase):
    def test_a_straight_arm_reports_zero_flexion(self):
        humerus = IDENTITY
        forearm = IDENTITY

        result = elbow_angles(humerus=humerus, forearm=forearm)

        self.assertAlmostEqual(result.as_dict()["flexion"], 0.0, places=6)

    def test_a_ninety_degree_bend_reports_ninety_degrees_of_flexion(self):
        humerus = IDENTITY
        forearm = rotation_z(90.0)

        result = elbow_angles(humerus=humerus, forearm=forearm)

        self.assertAlmostEqual(result.as_dict()["flexion"], 90.0, places=6)

    def test_forearm_twist_is_reported_as_pronation_not_as_flexion(self):
        humerus = IDENTITY
        forearm = multiply(rotation_z(100.0), rotation_y(60.0))

        result = elbow_angles(humerus=humerus, forearm=forearm)

        angles = result.as_dict()
        self.assertAlmostEqual(angles["flexion"], 100.0, places=6)
        self.assertAlmostEqual(angles["pronation"], 60.0, places=6)


class ShoulderTest(unittest.TestCase):
    def test_pure_elevation_in_the_sagittal_plane(self):
        thorax = IDENTITY
        humerus = multiply(rotation_y(0.0), rotation_x(90.0))

        result = shoulder_angles(thorax=thorax, humerus=humerus)

        angles = result.as_dict()
        self.assertAlmostEqual(angles["elevation"], 90.0, places=6)
        self.assertAlmostEqual(angles["planeOfElevation"], 0.0, places=6)

    def test_plane_of_elevation_is_recovered(self):
        thorax = IDENTITY
        humerus = multiply(rotation_y(45.0), rotation_x(120.0))

        result = shoulder_angles(thorax=thorax, humerus=humerus)

        angles = result.as_dict()
        self.assertAlmostEqual(angles["planeOfElevation"], 45.0, places=6)
        self.assertAlmostEqual(angles["elevation"], 120.0, places=6)


class RangeCheckTest(unittest.TestCase):
    def test_an_in_range_pose_reports_no_violation(self):
        angles = [
            JointAngles("elbow", "zxy", ("flexion", "carryingAngle", "pronation"), (120.0, 5.0, 30.0)),
            JointAngles("knee", "zxy", ("flexion", "adduction", "internalRotation"), (40.0, 2.0, 5.0)),
        ]

        self.assertEqual(check_ranges(angles), [])

    def test_a_hyperextended_elbow_is_reported_with_its_source(self):
        angles = [
            JointAngles("elbow", "zxy", ("flexion", "carryingAngle", "pronation"), (-25.0, 0.0, 0.0)),
        ]

        violations = check_ranges(angles)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].key, "elbow.flexion")
        self.assertEqual(violations[0].limit.source, "AAOS")
        self.assertIn("outside", violations[0].describe())

    def test_every_limit_key_names_a_joint_and_an_angle(self):
        for key in AAOS_LIMITS:
            joint, _, angle = key.partition(".")
            self.assertTrue(joint)
            self.assertTrue(angle)


class KneeTest(unittest.TestCase):
    def test_knee_flexion_matches_the_built_rotation(self):
        result = knee_angles(femur=IDENTITY, tibia=rotation_z(65.0))

        self.assertAlmostEqual(result.as_dict()["flexion"], 65.0, places=6)

    def test_relative_rotation_is_identity_for_aligned_segments(self):
        rotation = relative_rotation(rotation_z(30.0), rotation_z(30.0))

        for row in range(3):
            for column in range(3):
                expected = 1.0 if row == column else 0.0
                self.assertAlmostEqual(rotation[row][column], expected, places=9)


if __name__ == "__main__":
    unittest.main()
