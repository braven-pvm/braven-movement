"""Tests for the technique file and for closing the fingers."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

from finger_wrap import (
    FINGERS,
    curl_parameters,
    enable_curl,
    wrap_joints,
    wrap_report,
)
from ball_track import MOVEMENT_DIR, ball_path, load_ball
from motion_track import load_motion
from technique import (
    movement_carries_no_side,
    MAXIMUM_SPREAD_DEGREES,
    MINIMUM_SPREAD_DEGREES,
    TechniqueError,
    load_technique,
    read_elbow_angle_degrees,
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


class CarriesNoSideTest(unittest.TestCase):
    """The population of the left-right knee guard is read from three files.

    Each clause below is planted, because a clause nothing exercises is a
    clause that can be deleted while the suite stays green.
    """

    EVEN = "netball_two_hand_catch_chest"

    def parts(self, movement_id):
        # MOVEMENT_DIR rather than movement_engine.motion_path: this file
        # must stay runnable without the solver installed.
        return (
            load_motion(MOVEMENT_DIR / f"{movement_id}.motion.json"),
            load_ball(ball_path(movement_id)),
            load_technique(technique_path(movement_id)),
        )

    def test_an_even_drill_reads_even_in_all_three_files(self):
        track, ball, method = self.parts(self.EVEN)

        self.assertTrue(track.keys_carry_no_side())
        self.assertTrue(ball.carries_no_side())
        self.assertTrue(method.carries_no_side())
        self.assertTrue(movement_carries_no_side(track, ball, method))

    def test_a_ball_arriving_to_one_side_leaves_the_population(self):
        """THE FAULT THIS FIXED. The motion file stays even and says nothing.

        A possession solve reads no hand keys, so a ball off the midline is
        an asymmetric demand that the motion file cannot show.
        """
        track, ball, method = self.parts(self.EVEN)
        keys = list(ball.keys)
        keys[-1] = replace(
            keys[-1], offset=replace(keys[-1].offset, across=0.05)
        )
        moved = replace(ball, keys=tuple(keys))

        self.assertTrue(track.keys_carry_no_side(), "the motion file is blind to this")
        self.assertFalse(moved.carries_no_side())
        self.assertFalse(movement_carries_no_side(track, moved, method))

    def test_a_technique_carrying_the_ball_across_leaves_the_population(self):
        track, ball, method = self.parts(self.EVEN)
        keys = list(method.after_contact)
        keys[-1] = replace(
            keys[-1], offset=replace(keys[-1].offset, across=0.2)
        )
        carried = replace(method, after_contact=tuple(keys))

        self.assertFalse(carried.carries_no_side())
        self.assertFalse(movement_carries_no_side(track, ball, carried))

    def test_a_one_handed_technique_leaves_the_population(self):
        track, ball, method = self.parts(self.EVEN)

        self.assertFalse(replace(method, hands="right").carries_no_side())

    def test_the_deflecting_drill_is_out_on_two_counts(self):
        """Named because it is the drill the old one-file test admitted."""
        track, ball, method = self.parts("netball_deflect_high")

        self.assertTrue(track.keys_carry_no_side(), "its motion file IS even")
        self.assertFalse(ball.carries_no_side(), "its ball arrives to her left")
        self.assertFalse(method.carries_no_side(), "its technique carries across")
        self.assertFalse(movement_carries_no_side(track, ball, method))

    def test_a_missing_file_is_not_evidence_of_evenness(self):
        track, ball, method = self.parts(self.EVEN)

        self.assertFalse(movement_carries_no_side(track, None, method))
        self.assertFalse(movement_carries_no_side(track, ball, None))


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
        """Near the chest, not out at arm's length.

        The bound is 0.7 rather than 0.5 because the chest key is measured from
        c_spine3, which is a spine joint at the back of the torso. 0.55 of an
        arm length from there puts the ball a few centimetres off the sternum.
        Closer than that folds the elbow past what AAOS allows.
        """
        last = self.method.after_contact[-1]
        self.assertAlmostEqual(last.at_phase, 1.0)
        self.assertLess(last.offset.ahead, 0.7)
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


class ElbowAngleDegrees(unittest.TestCase):
    """`elbowAngleDegrees` is a technique property, so a chest catch can differ.

    It replaces `elbowWidth`, a dimensionless multiplier on the upper arm aim
    term. That dial was named for the folded case and attached to a term which
    a weight sweep from 2.0 down to 0.0 showed moves folded elbow separation by
    0.2 cm, so it could not have honoured a coach's number whatever they said.
    It now sets the pole angle, which does control separation, and it is in
    degrees rather than in multiples of nothing.

    Absent means the engine's own angle, which is read from the manual's
    38.6 cm rather than typed. A drill states one only to differ from it.
    """

    def test_a_grip_without_it_leaves_the_engine_its_own(self):
        self.assertIsNone(read_elbow_angle_degrees({}))

    def test_a_stated_angle_is_read(self):
        self.assertEqual(read_elbow_angle_degrees({"elbowAngleDegrees": 10.0}), 10.0)
        self.assertEqual(read_elbow_angle_degrees({"elbowAngleDegrees": 0}), 0.0)

    def test_an_angle_outside_the_range_is_refused(self):
        for value in (-20.1, 90.1, 400.0):
            with self.assertRaises(TechniqueError):
                read_elbow_angle_degrees({"elbowAngleDegrees": value})

    def test_the_range_boundaries_are_allowed(self):
        """The old range check was never probed at its edges, which the ball
        pack's review flagged as a place an off-by-strictness would survive."""
        self.assertEqual(read_elbow_angle_degrees({"elbowAngleDegrees": -20.0}), -20.0)
        self.assertEqual(read_elbow_angle_degrees({"elbowAngleDegrees": 90.0}), 90.0)

    def test_an_angle_that_is_not_a_number_is_refused(self):
        with self.assertRaises(TechniqueError):
            read_elbow_angle_degrees({"elbowAngleDegrees": "wide"})


if __name__ == "__main__":
    unittest.main()
