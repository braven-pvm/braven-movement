"""Tests for building an athlete of a given size.

Built on a fake character, so they run without the model. Whether the real
bodies come out right is measured by retarget.py, which reports rather than
asserts.
"""

from __future__ import annotations

import unittest

import numpy as np

import athlete
from athlete import HANDS, REACH, STATURE, AthleteError, _set, _solve


class FakeTransform:
    names = tuple(STATURE + REACH + HANDS + ("l_elbow_bend", "root_tx"))
    size = len(names)


class FakeCharacter:
    """A body whose height is the sum of its stature parameters, times ten."""

    def __init__(self, limits=None):
        self.parameter_transform = FakeTransform()
        self.limits = limits or {name: (-1.0, 1.0) for name in FakeTransform.names}


def fake_limits(character):
    return character.limits


class SetTest(unittest.TestCase):
    def setUp(self):
        self.real = athlete.minmax_limits if hasattr(athlete, "minmax_limits") else None
        self.character = FakeCharacter()
        self.identity = np.zeros(len(FakeTransform.names), dtype=np.float32)

    def apply(self, value, character=None):
        saved = athlete.minmax_limits
        athlete.minmax_limits = fake_limits
        try:
            return _set(character or self.character, self.identity, STATURE, value)
        finally:
            athlete.minmax_limits = saved

    def test_a_value_inside_the_range_is_set_as_asked(self):
        self.apply(0.4)
        names = list(FakeTransform.names)
        for name in STATURE:
            self.assertAlmostEqual(
                float(self.identity[names.index(name)]), 0.4, places=5
            )

    def test_a_value_outside_the_range_is_held_at_the_edge(self):
        """The foot length allows a tenth either way. Without the clamp it went
        55 units past it while the spine was still comfortable."""
        character = FakeCharacter(
            {**FakeCharacter().limits, "scale_foot_length": (-0.1, 0.1)}
        )
        self.apply(0.9, character)
        names = list(FakeTransform.names)
        self.assertAlmostEqual(
            float(self.identity[names.index("scale_foot_length")]), 0.1, places=5
        )
        self.assertAlmostEqual(
            float(self.identity[names.index("scale_spine_length")]), 0.9, places=5
        )

    def test_setting_reports_what_was_asked_not_what_was_clamped(self):
        """These are set in groups whose limits differ, so there is no single
        applied value. Reporting the clamped one poisoned the secant."""
        character = FakeCharacter(
            {**FakeCharacter().limits, "scale_foot_length": (-0.1, 0.1)}
        )
        self.assertAlmostEqual(self.apply(0.9, character), 0.9, places=6)

    def test_nothing_outside_the_named_group_is_touched(self):
        self.apply(0.5)
        names = list(FakeTransform.names)
        for name in ("l_elbow_bend", "root_tx"):
            self.assertEqual(float(self.identity[names.index(name)]), 0.0)


class SolveTest(unittest.TestCase):
    def test_it_finds_a_value_that_hits_the_target(self):
        state = {"v": 0.0}
        found = _solve(
            lambda v: (state.__setitem__("v", v), v)[1],
            lambda: 100.0 + state["v"] * 40.0,
            120.0,
            "test",
        )
        self.assertAlmostEqual(found, 0.5, places=3)

    def test_it_copes_with_a_slope_it_was_not_told(self):
        """Guessing the slope got it wrong: five stature parameters together
        are worth 28 cm per unit, not the 10 one of them is worth alone."""
        state = {"v": 0.0}
        found = _solve(
            lambda v: (state.__setitem__("v", v), v)[1],
            lambda: 172.8 + state["v"] * 27.7,
            158.0,
            "test",
        )
        self.assertAlmostEqual(172.8 + found * 27.7, 158.0, places=1)

    def test_a_target_it_cannot_reach_is_refused(self):
        state = {"v": 0.0}
        with self.assertRaises(AthleteError):
            _solve(
                lambda v: (state.__setitem__("v", v), v)[1],
                lambda: 172.8,
                158.0,
                "test",
            )

    def test_best_effort_returns_the_closest_it_managed(self):
        """A hand that cannot grow all the way is worth reporting, not
        refusing."""
        state = {"v": 0.0}
        found = _solve(
            lambda v: (state.__setitem__("v", min(0.2, v)), v)[1],
            lambda: 8.21 + min(0.2, state["v"]) * 6.0,
            9.03,
            "test",
            strict=False,
        )
        self.assertIsNotNone(found)


class SquadTest(unittest.TestCase):
    def test_a_height_of_nothing_is_not_a_person(self):
        saved = athlete.minmax_limits
        athlete.minmax_limits = fake_limits
        try:
            with self.assertRaises(AthleteError):
                athlete.build(FakeCharacter(), "nobody", 0.0)
        finally:
            athlete.minmax_limits = saved


if __name__ == "__main__":
    unittest.main()
