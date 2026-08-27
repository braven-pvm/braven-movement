"""Guard the boundary the rendering lane consumes.

`knuckleLimitsDegrees` exists because a deviation-sized number was capping
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
    from export_blender_job import DIGITS, knuckle_limits
    from movement_engine import load_character


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class KnuckleFlexionLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()
        cls.limits = knuckle_limits(cls.character)

    def test_every_digit_is_reported_including_the_thumb(self) -> None:
        """The thumb was unbounded under the first scheme, and worse than
        unbounded: the consumer's own 80 degree ceiling is above the model's
        57.3 licence, so it was over-permitted rather than merely missing."""
        self.assertEqual(set(self.limits), set(DIGITS))
        self.assertIn("thumb", self.limits)

    def test_it_licenses_a_closed_grip(self) -> None:
        """The number that matters. The old cap was 40, and a grip needs more.

        Deliberately a range rather than the exact values. Pinning 90.0 would
        make this a change detector; the question is whether the licence
        permits a hand to close, which 40 did not. The thumb is checked
        separately because its licence is genuinely tighter.
        """
        for digit, entry in self.limits.items():
            most = entry["flexion"]["max"]
            floor = 50.0 if digit == "thumb" else 60.0
            self.assertGreater(most, floor, f"{digit} cannot close a grip")
            self.assertLess(most, 120.0, f"{digit} is past a human knuckle")

    def test_flexion_and_deviation_are_separate_axes(self) -> None:
        """The whole defect was one bounding the other. They must not be equal
        by accident, and both must be present."""
        for digit, entry in self.limits.items():
            self.assertIsNotNone(entry["deviation"], f"{digit} has no deviation")
            self.assertNotEqual(
                entry["flexion"], entry["deviation"], f"{digit} conflates axes"
            )

    def test_extension_is_carried_and_the_pinky_differs(self) -> None:
        """The real per-digit reason. Flexion is 90 on all four fingers, so a
        per-digit flexion number varies for no anatomical reason; extension is
        where they actually differ."""
        self.assertLess(
            self.limits["pinky"]["flexion"]["min"],
            self.limits["index"]["flexion"]["min"],
            "the pinky extends further than the index and must say so",
        )

    def test_it_is_not_the_rest_bend_plus_the_rotation_limit(self) -> None:
        """The cautionary example in the schema note, as a test.

        The index rests at 18.5 with a rotation limit of 90, and the geometric
        bend at that limit is 90.0, not 108.5. Anyone who replaces the
        measurement with addition breaks this.
        """
        self.assertLess(
            self.limits["index"]["visibleBendAtFlexionLimit"],
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
        self.assertEqual(set(job["knuckleLimitsDegrees"]), set(DIGITS))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
