"""Tests for the technique file and for closing the fingers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from finger_wrap import (
    FINGERS,
    curl_parameters,
    enable_curl,
    wrap_joints,
    wrap_report,
)
from technique import (
    MAXIMUM_SPREAD_DEGREES,
    MINIMUM_SPREAD_DEGREES,
    TechniqueError,
    load_technique,
    technique_path,
)

SNATCH = "netball_two_hand_snatch_pull_in"

VALID = {
    "movementId": "test_movement",
    "hands": "both",
    "grip": {"spreadDegrees": 90, "faceBall": True},
    "afterContact": [
        {"atPhase": 0.8, "name": "absorb", "across": 0.0, "up": 0.3, "ahead": 0.5},
        {"atPhase": 1.0, "name": "pull_in", "across": 0.0, "up": 0.04, "ahead": 0.36},
    ],
}


def write(data: dict) -> Path:
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".technique.json", delete=False, encoding="utf-8"
    )
    json.dump(data, handle)
    handle.close()
    return Path(handle.name)


def variant(**changes) -> dict:
    data = json.loads(json.dumps(VALID))
    data.update(changes)
    return data


class LoadTest(unittest.TestCase):
    def test_loads_a_valid_technique(self):
        method = load_technique(write(VALID))
        self.assertEqual(method.hands, "both")
        self.assertEqual(method.sides, ("l", "r"))
        self.assertAlmostEqual(method.spread_degrees, 90.0)
        self.assertTrue(method.drives_the_ball())

    def test_one_hand_takes_only_its_own_side(self):
        self.assertEqual(load_technique(write(variant(hands="left"))).sides, ("l",))
        self.assertEqual(load_technique(write(variant(hands="right"))).sides, ("r",))

    def test_rejects_a_hand_that_is_not_a_hand(self):
        with self.assertRaises(TechniqueError):
            load_technique(write(variant(hands="either")))

    def test_rejects_a_grip_with_no_spread(self):
        with self.assertRaises(TechniqueError):
            load_technique(write(variant(grip={"faceBall": True})))

    def test_rejects_a_spread_no_person_can_hold(self):
        for spread in (MINIMUM_SPREAD_DEGREES - 1, MAXIMUM_SPREAD_DEGREES + 1):
            with self.assertRaises(TechniqueError):
                load_technique(write(variant(grip={"spreadDegrees": spread})))

    def test_rejects_unordered_after_contact_keys(self):
        data = variant()
        data["afterContact"] = list(reversed(data["afterContact"]))
        with self.assertRaises(TechniqueError):
            load_technique(write(data))

    def test_a_drill_that_drives_the_ball_must_say_where_it_ends(self):
        data = variant()
        data["afterContact"][-1]["atPhase"] = 0.9
        with self.assertRaises(TechniqueError):
            load_technique(write(data))

    def test_a_drill_may_drive_nothing(self):
        data = variant()
        del data["afterContact"]
        method = load_technique(write(data))
        self.assertFalse(method.drives_the_ball())


class SnatchTechniqueTest(unittest.TestCase):
    def setUp(self):
        self.method = load_technique(technique_path(SNATCH))

    def test_it_is_the_snatch(self):
        self.assertEqual(self.method.movement_id, SNATCH)
        self.assertEqual(self.method.hands, "both")

    def test_the_grip_is_one_this_athlete_can_make(self):
        """Measured, not assumed.

        Sweeping the spread and solving each one, the athlete produces what is
        asked from 80 degrees upward. Below that her forearm reaches its
        supination limit and the palms stay wider than requested.
        """
        self.assertGreaterEqual(self.method.spread_degrees, 80.0)

    def test_the_ball_finishes_at_the_chest(self):
        last = self.method.after_contact[-1]
        self.assertAlmostEqual(last.at_phase, 1.0)
        self.assertLess(last.offset.ahead, 0.5)
        self.assertLess(last.offset.up, 0.2)


class CurlTest(unittest.TestCase):
    class FakeTransform:
        names = tuple(
            [f"{side}_{finger}{segment}_rz"
             for side in ("l", "r") for finger in FINGERS for segment in (1, 2, 3)]
            + [f"{side}_{finger}{segment}_ry"
               for side in ("l", "r") for finger in FINGERS for segment in (1,)]
            + [f"{side}_thumb{n}_rz" for side in ("l", "r") for n in (1, 2, 3)]
            + ["l_elbow_bend", "r_elbow_bend", "root_tx"]
        )

    class FakeCharacter:
        def __init__(self, transform):
            self.parameter_transform = transform

    def setUp(self):
        self.character = self.FakeCharacter(self.FakeTransform())

    def test_only_the_curl_of_the_named_hands_is_freed(self):
        freed = curl_parameters(self.character, ("l",))
        self.assertTrue(all(name.startswith("l_") for name in freed))
        self.assertTrue(all(name.endswith("_rz") for name in freed))
        self.assertEqual(len(freed), len(FINGERS) * 3 + 3)

    def test_the_spread_across_the_hand_stays_frozen(self):
        """Freeing the spread let the little finger swing across the palm."""
        freed = curl_parameters(self.character, ("l", "r"))
        self.assertFalse(any(name.endswith("_ry") for name in freed))

    def test_nothing_above_the_wrist_is_freed(self):
        names = list(self.character.parameter_transform.names)
        enabled = np.zeros(len(names), dtype=bool)
        freed = enable_curl(self.character, enabled, ("l", "r"))
        for name in ("l_elbow_bend", "r_elbow_bend", "root_tx"):
            self.assertFalse(freed[names.index(name)], name)

    def test_enabling_never_switches_anything_off(self):
        names = list(self.character.parameter_transform.names)
        enabled = np.ones(len(names), dtype=bool)
        freed = enable_curl(self.character, enabled, ("l",))
        self.assertTrue(freed.all())

    def test_every_digit_is_asked_to_reach_the_ball(self):
        joints = wrap_joints(("l",))
        for finger in FINGERS:
            self.assertIn(f"l_{finger}3", joints)
        self.assertIn("l_thumb3", joints)


class WrapReportTest(unittest.TestCase):
    def test_a_finger_inside_the_ball_is_reported_as_inside(self):
        centre = np.array([0.0, 0.0, 0.0])
        names = [f"l_{finger}3" for finger in FINGERS] + ["l_thumb3"]
        index = {name: number for number, name in enumerate(names)}
        # Every tip on the surface except the little finger, 2 cm inside it.
        points = np.array(
            [[0.0, 0.0, 11.8]] * 3 + [[0.0, 0.0, 9.8]] + [[0.0, 0.0, 11.8]]
        )
        report = wrap_report(points, index, centre, 11.0, ("l",))
        self.assertAlmostEqual(report["deepestFingerInsideBallCm"], 2.0, places=6)
        self.assertAlmostEqual(report["worstFingertipGapCm"], 2.0, places=6)

    def test_every_tip_on_the_surface_reports_no_gap(self):
        centre = np.zeros(3)
        names = [f"l_{finger}3" for finger in FINGERS] + ["l_thumb3"]
        index = {name: number for number, name in enumerate(names)}
        points = np.array([[0.0, 0.0, 11.8]] * 5)
        report = wrap_report(points, index, centre, 11.0, ("l",))
        self.assertAlmostEqual(report["worstFingertipGapCm"], 0.0, places=6)
        self.assertAlmostEqual(report["deepestFingerInsideBallCm"], 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
