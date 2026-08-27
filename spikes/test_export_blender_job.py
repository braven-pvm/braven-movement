"""Guard the boundary the rendering lane consumes.

`fingerBaseFlexionDegrees` exists because a deviation-sized number was capping
a flexion axis and the fingers stopped short of the ball. If this derivation
drifts, nothing else in the suite notices: the athlete still solves, still
grades, and the hand quietly stops gripping again on the far side of a
boundary this lane cannot see.

These run only where the solver is installed, which is the pixi environment.
A green system-python run says nothing about any of them.
"""

from __future__ import annotations

import unittest

# Only a genuinely absent solver may skip. Catching every exception here would
# swallow a break in the code under test and skip the guard in silence.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    from export_blender_job import FINGERS, knuckle_flexion_limits
    from movement_engine import load_character


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class KnuckleFlexionLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()
        cls.limits = knuckle_flexion_limits(cls.character)

    def test_every_finger_is_reported(self) -> None:
        self.assertEqual(set(self.limits), set(FINGERS))

    def test_it_licenses_a_closed_grip(self) -> None:
        """The number that matters. The old cap was 40, and a grip needs more.

        Deliberately a range rather than the exact values. Pinning 90.0 would
        make this a change detector; the question is whether the licence
        permits a hand to close, which 40 did not.
        """
        for finger, degrees in self.limits.items():
            self.assertGreater(degrees, 60.0, f"{finger} cannot close a grip")
            self.assertLess(degrees, 120.0, f"{finger} is past a human knuckle")

    def test_it_is_derived_and_not_the_deviation_limit(self) -> None:
        """40 was the deviation-shaped number. None of these may be near it."""
        for finger, degrees in self.limits.items():
            self.assertGreater(
                degrees,
                50.0,
                f"{finger} looks like the deviation limit that caused this",
            )

    def test_it_is_not_the_rest_bend_plus_the_rotation_limit(self) -> None:
        """The cautionary example in the schema note, as a test.

        The index rests at 18.5 with a rotation limit of 90, and the geometric
        bend at that limit is 90.0, not 108.5. Anyone who replaces the
        measurement with addition breaks this.
        """
        self.assertLess(
            self.limits["index"],
            100.0,
            "the index limit looks like rest bend added to rotation limit",
        )

    def test_the_job_carries_it_without_disturbing_the_old_block(self) -> None:
        """Additive. A reader that does not know the new field keeps working."""
        from export_blender_job import ANATOMY_LIMITS, build

        job = build(self.character, "netball_two_hand_snatch_pull_in")
        self.assertEqual(job["anatomyLimitsDegrees"], dict(ANATOMY_LIMITS))
        self.assertEqual(
            job["anatomyLimitsDegrees"]["fingerBaseDeviation"],
            40.0,
            "deviation still means deviation and must not be repurposed",
        )
        self.assertEqual(set(job["fingerBaseFlexionDegrees"]), set(FINGERS))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
