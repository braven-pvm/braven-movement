"""Contract tests for the capture verdict.

The verdict is the safety rule of the whole product: it decides whether a coach
is shown a number or only a shape. It is tested without a solver present, so it
cannot quietly stop working when an environment lacks pymomentum.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from multi_camera_fit import (  # noqa: E402
    MEANINGFUL_DEGREES,
    MINIMUM_SEPARATION_DEGREES,
    Camera,
    View,
    judge,
)


def camera(name: str, azimuth: float) -> Camera:
    return Camera(
        name=name,
        azimuth_degrees=azimuth,
        height_cm=0.0,
        distance_cm=300.0,
        width_px=1080,
        height_px=1920,
    )


def view(name: str, azimuth: float) -> View:
    return View(camera=camera(name, azimuth), landmarks={"l_wrist": (10.0, 20.0)})


class VerdictTest(unittest.TestCase):
    def test_one_camera_may_never_measure(self):
        """The single most important rule in the product."""
        result = judge([view("only", 0.0)])

        self.assertFalse(result.measurement_valid)
        self.assertEqual(result.cameras, 1)
        self.assertIn("withhold", result.reason)

    def test_no_cameras_may_never_measure(self):
        self.assertFalse(judge([]).measurement_valid)

    def test_two_cameras_far_enough_apart_may_measure(self):
        result = judge([view("a", -30.0), view("b", 30.0)])

        self.assertTrue(result.measurement_valid)
        self.assertAlmostEqual(result.separation_degrees, 60.0, places=6)

    def test_two_cameras_side_by_side_may_not_measure(self):
        """Spike I: below 45 degrees both cameras see the same thing."""
        result = judge([view("a", -10.0), view("b", 10.0)])

        self.assertFalse(result.measurement_valid)
        self.assertIn("same", result.reason)

    def test_the_boundary_is_the_measured_one(self):
        just_under = judge([view("a", 0.0), view("b", MINIMUM_SEPARATION_DEGREES - 1)])
        just_over = judge([view("a", 0.0), view("b", MINIMUM_SEPARATION_DEGREES + 1)])

        self.assertFalse(just_under.measurement_valid)
        self.assertTrue(just_over.measurement_valid)

    def test_separation_is_measured_between_the_widest_pair(self):
        result = judge([view("a", 0.0), view("b", 20.0), view("c", 80.0)])

        self.assertAlmostEqual(result.separation_degrees, 60.0, places=6)
        self.assertTrue(result.measurement_valid)

    def test_three_bunched_cameras_still_may_not_measure(self):
        """Three phones in a row is not better than one phone."""
        result = judge([view("a", 0.0), view("b", 10.0), view("c", 20.0)])

        self.assertFalse(result.measurement_valid)

    def test_the_verdict_carries_the_threshold_it_was_judged_against(self):
        result = judge([view("a", -45.0), view("b", 45.0)])

        self.assertEqual(
            result.as_dict()["meaningfulThresholdDegrees"], MEANINGFUL_DEGREES
        )

    def test_every_verdict_explains_itself(self):
        for views in (
            [],
            [view("a", 0.0)],
            [view("a", 0.0), view("b", 5.0)],
            [view("a", 0.0), view("b", 90.0)],
        ):
            self.assertTrue(judge(views).reason.strip(), f"{len(views)} views")


class CameraTest(unittest.TestCase):
    def test_a_camera_projects_the_athlete_into_its_frame(self):
        import numpy as np

        centre = np.array([0.0, 140.0, 0.0])
        projection = camera("front", 0.0).projection(centre)

        homogeneous = projection.astype(float) @ np.array([0.0, 140.0, 0.0, 1.0])
        pixel = homogeneous[:2] / homogeneous[2]

        # The athlete's chest sits at the centre of the frame.
        self.assertAlmostEqual(pixel[0], 1080 / 2, places=3)
        self.assertAlmostEqual(pixel[1], 1920 / 2, places=3)

    def test_the_athlete_is_in_front_of_the_camera(self):
        import numpy as np

        centre = np.array([0.0, 140.0, 0.0])
        for azimuth in (-90.0, -45.0, 0.0, 45.0, 90.0, 180.0):
            projection = camera("c", azimuth).projection(centre)
            depth = projection.astype(float) @ np.array([0.0, 140.0, 0.0, 1.0])
            self.assertGreater(depth[2], 0.0, f"azimuth {azimuth}")


if __name__ == "__main__":
    unittest.main()
