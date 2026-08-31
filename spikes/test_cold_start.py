"""The opening frames do not settle into place while the targets stand still.

Frame zero used to be the only frame solved without a neighbour to start from.
Every other frame is seeded with the previous frame's answer, so a joint the
constraints do not determine carries on from where it already was. Frame zero
had nothing to carry on from, so such a joint resolved however the rest pose
left it, and the drill then stepped into line.

On `netball_hooks_outside_hand` the right knee opened at 34.1 degrees against
the 47 the drill settles at, held that for six frames and stepped 9.6 into
line. Both feet read 0.00 cm off the floor throughout and the pelvis stayed
inside 0.02 cm, so nothing was broken in the pose: a planted foot and a fixed
pelvis do not determine a knee, and nothing pulled it back.

WHAT THIS FILE MEASURES, AND WHY IT IS NOT A STEP COUNT

A step count cannot see this fault. The opening drifted 34.1 to 37.6 over six
frames in steps of half a degree each, which is smaller than the drill's
ordinary motion, and then crossed the remaining gap at once. The signature is
the DRIFT, not the step: the pose moving while nothing asks it to.

So the comparison is drift against target movement, which is the same pairing
the cold start's own docstring used when it described the fault in the arm:
"the elbow moved 33 degrees over the first few frames while the target barely
moved". A window in which the hand target does not move is a window in which
the pose has no business moving either.

Each drill is compared against ITSELF. The opening window is measured, then
every later window of the same length whose target moved no further is taken as
a control. A drill whose opening genuinely moves is not tested, and says so.
"""

from __future__ import annotations

import unittest

import numpy as np

# Only a genuinely absent solver may skip. Catching every exception here would
# swallow a break in the code under test and skip the guard in silence.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    from ball_track import has_ball
    from movement_engine import library, load_character
    from possession_solve import solve_movement
    from technique import has_technique, load_technique, technique_path

# The angles a solver chooses. `trunkTurnDegrees` is excluded on purpose: it is
# read from the authored track rather than solved, so a drill that turns would
# fail a rule about the solver for a reason that has nothing to do with it.
SOLVED = (
    "leftElbowFlexionDegrees",
    "rightElbowFlexionDegrees",
    "leftShoulderElevationDegrees",
    "rightShoulderElevationDegrees",
    "leftKneeFlexionDegrees",
    "rightKneeFlexionDegrees",
    "trunkLeanDegrees",
)
# Long enough to hold the settle. The recorded fault took six frames to drift
# and a seventh to step, so a shorter window would end inside it and measure
# half the drift as if it were the whole.
WINDOW = 12
# What counts as a target standing still, over that window. A hand that has
# moved less than a centimetre in twelve frames is not asking the arm for
# anything, and every drill except the two that genuinely move in their opening
# sits at 0.00 to 0.72 cm here.
STILL_CM = 1.0
# The clinical measurement threshold this project already works to, borrowed
# rather than invented: `verify_tactics_clip.py` gates the whole clip contract
# on it. It is the floor for the bound below, so the rule fires on a pose in
# the wrong place and not on a fraction of a degree of solver repeatability.
THRESHOLD_DEGREES = 5.0


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheOpeningDoesNotSettleIntoPlace(unittest.TestCase):
    """Solves the library, so it is one of the slow ones."""

    @classmethod
    def setUpClass(cls) -> None:
        character = load_character()
        cls.drills: dict[str, dict] = {}
        for movement_id in sorted(library()):
            if not (has_ball(movement_id) and has_technique(movement_id)):
                continue
            if not load_technique(technique_path(movement_id)).possession_ready:
                continue
            result = solve_movement(character, movement_id)
            entries = result["measurements"]
            frames = result["possession"].frames
            if len(entries) <= WINDOW + WINDOW:
                continue
            targets = [np.asarray(f.presented, dtype=np.float64) for f in frames]

            def moved(start: int) -> float:
                return float(
                    np.linalg.norm(targets[start + WINDOW] - targets[start])
                )

            per_angle = {}
            for angle in SOLVED:
                values = [e[angle] for e in entries]

                def drift(start: int) -> float:
                    return abs(values[start + WINDOW] - values[start])

                per_angle[angle] = {
                    "opening": drift(0),
                    # Controls start at WINDOW, so none of them overlaps the
                    # opening. An overlapping window contains the very drift
                    # being tested and would licence it.
                    "controls": [
                        drift(start)
                        for start in range(WINDOW, len(values) - WINDOW)
                        if moved(start) < STILL_CM
                    ],
                }
            cls.drills[movement_id] = {
                "openingTargetCm": moved(0),
                "angles": per_angle,
            }

    def _tested(self) -> list[str]:
        return [
            movement_id
            for movement_id, found in self.drills.items()
            if found["openingTargetCm"] < STILL_CM
            and any(a["controls"] for a in found["angles"].values())
        ]

    def test_the_library_gives_this_rule_something_to_test(self) -> None:
        """Guards the guard.

        Two conditions exclude a drill, and between them they could exclude
        every drill and leave the rule below asserting nothing at all.
        """
        self.assertTrue(self.drills, "no drill was solved")
        tested = self._tested()
        self.assertGreaterEqual(
            len(tested),
            3,
            "fewer than three drills have both a still opening and a still "
            f"window later to compare it against, so this file is nearly "
            f"empty. Tested: {tested}",
        )

    def test_a_drill_that_genuinely_moves_is_excluded_and_not_failed(self) -> None:
        """The other half of the guard.

        `netball_double_foot_landing` drifts 26 degrees at the knee over its
        opening, which is the landing and not a fault. A rule that failed it
        would be measuring the drill rather than the solver, and would be
        switched off the first time somebody read it.
        """
        moving = [
            movement_id
            for movement_id, found in self.drills.items()
            if found["openingTargetCm"] >= STILL_CM
        ]
        self.assertTrue(
            moving,
            "no drill in the library moves during its opening, so the "
            "exclusion below is untested and may be excluding nothing",
        )

    def test_the_opening_does_not_drift_while_its_target_stands_still(self) -> None:
        """The rule.

        The bound is the drill's own worst still window, or the clinical
        threshold, whichever is larger. Neither is chosen here: the first is
        measured from the same drill and the second is the figure the clip
        contract already gates on.
        """
        for movement_id in self._tested():
            found = self.drills[movement_id]
            for angle, measured in sorted(found["angles"].items()):
                if not measured["controls"]:
                    continue
                worst_control = max(measured["controls"])
                bound = max(worst_control, THRESHOLD_DEGREES)
                with self.subTest(movement=movement_id, angle=angle):
                    self.assertLessEqual(
                        measured["opening"],
                        bound,
                        f"{movement_id}: {angle} drifts "
                        f"{measured['opening']:.2f} degrees over the first "
                        f"{WINDOW} frames while the hand target moves "
                        f"{found['openingTargetCm']:.2f} cm. The worst later "
                        f"window with a target as still as that drifts "
                        f"{worst_control:.2f}. The pose is settling into place "
                        "rather than following anything.",
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
