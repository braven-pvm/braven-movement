"""Tests for putting a hand on a ball.

Built on a synthetic hand rather than the real athlete, so they run without the
solver. The real athlete's grip is checked by contact_solve.py, which measures
it rather than asserting it.
"""

from __future__ import annotations

import math
import unittest

import numpy as np

from grip import (
    CARRIED,
    PALM_SKIN_CM,
    GripError,
    contacts,
    grip_targets,
    hand_axes,
    measure_hand,
    palm_skin,
    reconstruct,
)

# A flat right handed hand lying in the world XY plane: the wrist at the origin,
# the fingers along +Y, the palm facing +Z, the index side at +X.
HAND = {
    "l_wrist": [0.0, 0.0, 0.0],
    "l_middle1": [0.0, 8.2, 0.0],
    "l_index1": [3.0, 8.0, 0.0],
    "l_pinky1": [-3.2, 7.4, 0.0],
    "l_ring1": [-1.4, 8.1, 0.0],
    "l_thumb1": [3.4, 2.4, 2.3],
    "l_middle3": [0.0, 17.3, 0.6],
    "l_index3": [3.2, 16.4, 0.6],
    "l_ring3": [-1.5, 16.2, 0.6],
    "l_pinky3": [-3.6, 14.0, 0.6],
    "l_thumb3": [6.4, 5.0, 4.7],
}


def synthetic():
    names = sorted(HAND)
    points = np.array([HAND[name] for name in names], dtype=np.float64)
    return points, {name: number for number, name in enumerate(names)}


class AxesTest(unittest.TestCase):
    def setUp(self):
        self.points, self.index = synthetic()
        self.axes = hand_axes(
            wrist=np.array(HAND["l_wrist"]),
            middle_knuckle=np.array(HAND["l_middle1"]),
            index_knuckle=np.array(HAND["l_index1"]),
            pinky_knuckle=np.array(HAND["l_pinky1"]),
            middle_tip=np.array(HAND["l_middle3"]),
        )

    def test_the_frame_is_orthonormal(self):
        np.testing.assert_allclose(self.axes @ self.axes.T, np.eye(3), atol=1e-9)

    def test_the_frame_is_right_handed(self):
        self.assertAlmostEqual(float(np.linalg.det(self.axes)), 1.0, places=9)

    def test_the_first_axis_runs_along_the_hand(self):
        np.testing.assert_allclose(self.axes[0], [0.0, 1.0, 0.0], atol=1e-9)

    def test_the_palm_faces_the_way_the_fingers_curl(self):
        """The fingertip is bent toward +Z, so the palm must face +Z."""
        self.assertGreater(float(self.axes[1] @ np.array([0.0, 0.0, 1.0])), 0.9)

    def test_a_hand_curling_the_other_way_faces_the_other_way(self):
        axes = hand_axes(
            wrist=np.array(HAND["l_wrist"]),
            middle_knuckle=np.array(HAND["l_middle1"]),
            index_knuckle=np.array(HAND["l_index1"]),
            pinky_knuckle=np.array(HAND["l_pinky1"]),
            middle_tip=np.array([0.0, 17.3, -0.6]),
        )
        self.assertLess(float(axes[1] @ np.array([0.0, 0.0, 1.0])), -0.9)


class MeasureTest(unittest.TestCase):
    def setUp(self):
        self.points, self.index = synthetic()
        self.shape = measure_hand(self.points, self.index, "l")

    def test_every_carried_joint_is_measured(self):
        self.assertEqual(sorted(self.shape.local), sorted(CARRIED))

    def test_placing_the_hand_back_where_it_was_reproduces_it(self):
        axes = hand_axes(
            wrist=np.array(HAND["l_wrist"]),
            middle_knuckle=np.array(HAND["l_middle1"]),
            index_knuckle=np.array(HAND["l_index1"]),
            pinky_knuckle=np.array(HAND["l_pinky1"]),
            middle_tip=np.array(HAND["l_middle3"]),
        )
        knuckles = np.mean(
            [np.array(HAND[f"l_{n}"]) for n in ("index1", "middle1", "ring1", "pinky1")],
            axis=0,
        )
        origin = (np.array(HAND["l_wrist"]) + knuckles) / 2.0
        placed = self.shape.place(origin, axes)
        for name in CARRIED:
            np.testing.assert_allclose(
                placed[f"l_{name}"], HAND[f"l_{name}"], atol=1e-9
            )

    def test_the_frame_can_be_read_back_from_where_the_joints_landed(self):
        """The solver need not hit its targets, so the pose has to be read."""
        origin = np.array([12.0, 140.0, 30.0])
        turn = math.radians(37.0)
        axes = np.array(
            [
                [math.cos(turn), math.sin(turn), 0.0],
                [-math.sin(turn), math.cos(turn), 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        placed = self.shape.place(origin, axes)
        found_origin, found_axes = reconstruct(placed, self.shape)
        np.testing.assert_allclose(found_origin, origin, atol=1e-6)
        np.testing.assert_allclose(found_axes, axes, atol=1e-6)

    def test_the_reconstruction_never_turns_a_hand_inside_out(self):
        origin = np.zeros(3)
        axes = np.eye(3)
        placed = self.shape.place(origin, axes)
        _, found = reconstruct(placed, self.shape)
        self.assertGreater(float(np.linalg.det(found)), 0.0)


class ContactTest(unittest.TestCase):
    def setUp(self):
        self.centre = np.array([0.0, 145.0, 40.0])
        self.radius = 11.0
        self.found = contacts(
            ball_centre=self.centre,
            radius_cm=self.radius,
            toward_catcher=np.array([0.0, -5.0, -40.0]),
            up=np.array([0.0, 1.0, 0.0]),
            spread_degrees=90.0,
        )

    def test_the_skin_touches_the_ball(self):
        for contact in self.found.values():
            self.assertAlmostEqual(
                float(np.linalg.norm(contact.skin - self.centre)), self.radius, places=9
            )

    def test_every_palm_faces_the_ball_centre(self):
        for contact in self.found.values():
            toward = self.centre - contact.skin
            toward = toward / np.linalg.norm(toward)
            self.assertAlmostEqual(float(contact.palm_normal @ toward), 1.0, places=9)

    def test_the_palms_are_spread_as_far_apart_as_asked(self):
        cosine = float(self.found["l"].palm_normal @ self.found["r"].palm_normal)
        self.assertAlmostEqual(math.degrees(math.acos(cosine)), 90.0, places=6)

    def test_the_left_hand_goes_to_the_athletes_left(self):
        """MHR puts the left side at positive X, and the grip follows suit."""
        self.assertGreater(self.found["l"].skin[0], self.found["r"].skin[0])

    def test_the_palm_centroid_sits_outside_the_skin(self):
        for contact in self.found.values():
            self.assertAlmostEqual(
                float(np.linalg.norm(contact.origin - self.centre)),
                self.radius + PALM_SKIN_CM,
                places=9,
            )
            np.testing.assert_allclose(
                palm_skin(contact.origin, contact.axes), contact.skin, atol=1e-9
            )

    def test_the_fingers_point_up(self):
        for contact in self.found.values():
            self.assertGreater(float(contact.axes[0] @ np.array([0.0, 1.0, 0.0])), 0.5)

    def test_one_hand_takes_only_its_own_contact(self):
        found = contacts(
            ball_centre=self.centre,
            radius_cm=self.radius,
            toward_catcher=np.array([0.0, 0.0, -40.0]),
            up=np.array([0.0, 1.0, 0.0]),
            spread_degrees=90.0,
            sides=("r",),
        )
        self.assertEqual(sorted(found), ["r"])

    def test_a_ball_straight_overhead_has_no_left_and_right(self):
        with self.assertRaises(GripError):
            contacts(
                ball_centre=self.centre,
                radius_cm=self.radius,
                toward_catcher=np.array([0.0, -1.0, 0.0]),
                up=np.array([0.0, 1.0, 0.0]),
                spread_degrees=90.0,
            )


class TargetTest(unittest.TestCase):
    def test_targets_cover_every_carried_joint_of_every_hand(self):
        points, index = synthetic()
        shapes = {"l": measure_hand(points, index, "l")}
        found = contacts(
            ball_centre=np.array([0.0, 145.0, 40.0]),
            radius_cm=11.0,
            toward_catcher=np.array([0.0, 0.0, -1.0]),
            up=np.array([0.0, 1.0, 0.0]),
            spread_degrees=90.0,
            sides=("l",),
        )
        targets = grip_targets(shapes, found)
        self.assertEqual(
            sorted(targets), sorted(f"l_{name}" for name in CARRIED)
        )


if __name__ == "__main__":
    unittest.main()
