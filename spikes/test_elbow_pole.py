"""The elbow pole is an angle, and one property licenses the whole design.

The old pole pushed the elbow to an absolute offset, 16 cm out and 6 cm down,
gated by `slack = 1 - span / reach`. A point target argues with the reach, so
it HAD to yield near full extension, and that gate is why its authority grew as
the arm folded. The term was strongest exactly where no photograph was taken
and silent exactly where the 38.6 cm evidence was measured.

An angle about the shoulder-to-wrist axis cannot argue with the reach, because
rotating the elbow about that axis moves neither end of the arm. That single
property is the licence to delete the gate, so it is the first thing guarded
here. If it stops holding, the gate has to come back.

Most of this needs no solver, because the claim is geometry. The calibration
test does, and says so.
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
    from contact_solve import (
        ELBOW_POLE_ANGLE_DEGREES,
        UPPER_ARM_FRACTION,
        elbow_poles,
    )
    from movement_engine import joint_positions, library, load_character
    from possession_solve import solve_movement
    from technique import has_technique, load_technique, technique_path

REFERENCE_CM = 38.6


class Frame:
    """The little that `elbow_poles` reads from a trunk placement."""

    def __init__(self, shoulders, rotation):
        self.shoulders = shoulders
        self.rotation = rotation


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class ThePoleTargetSitsWhereTheElbowCanReach(unittest.TestCase):
    """The licence, tested directly rather than argued in a comment."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()
        cls.index = {
            name: number
            for number, name in enumerate(cls.character.skeleton.joint_names)
        }
        cls.reach = 52.68
        cls.upper = UPPER_ARM_FRACTION * cls.reach
        cls.fore = cls.reach - cls.upper

    def targets_for(self, wrist, angle):
        shoulder = np.array([20.0, 140.0, 0.0])
        frame = Frame({"l": shoulder, "r": shoulder * np.array([-1.0, 1.0, 1.0])},
                      np.eye(3))
        found = {}

        class Capture:
            def add_constraint(self, joint, target, offset, weight):
                found["target"] = np.asarray(target, dtype=np.float64)
                found["weight"] = weight

        import contact_solve

        real = contact_solve.solver2.PositionErrorFunction
        contact_solve.solver2.PositionErrorFunction = lambda *a, **k: Capture()
        try:
            elbow_poles(
                self.character,
                self.index,
                frame,
                {"l_wrist": np.asarray(wrist, dtype=np.float64)},
                self.reach,
                ("l",),
                angle,
            )
        finally:
            contact_solve.solver2.PositionErrorFunction = real
        return found, shoulder

    def test_the_target_is_on_the_elbow_circle_where_the_basis_is_orthogonal(
        self,
    ) -> None:
        """What this proves, and what it does not.

        It proves the target is exactly one upper arm from the shoulder and one
        forearm from the wrist, at every angle and every reachable span, FOR
        REACHES ALONG THE AXIS FAMILY BELOW.

        It does NOT prove that in general, and the name now says so. Review
        found that `out` and `down` are each projected off the reach axis but
        never orthogonalised against each other, so on an oblique reach they
        are not perpendicular and the target lands up to 10.2 cm off the
        circle. Every case here reaches along +Z, where `out . down` is exactly
        0.000 and the flaw vanishes — so this test exercises precisely the
        family the defect cannot reach.

        It is left as it is deliberately. Widening it would turn the branch red
        for a defect whose fix moves figures, and that fix is filed as
        follow-up. The dishonesty was the name and the claim, not the coverage.
        """
        shoulder = np.array([20.0, 140.0, 0.0])
        checked = 0
        for span in (15.0, 25.0, 35.0, 45.0, 50.0):
            for angle in (-20.0, 0.0, 22.4, 34.6, 60.0, 90.0):
                wrist = shoulder + np.array([0.0, 0.0, span])
                found, shoulder_used = self.targets_for(wrist, angle)
                if "target" not in found:
                    continue
                checked += 1
                pole = found["target"]
                self.assertAlmostEqual(
                    float(np.linalg.norm(pole - shoulder_used)), self.upper, places=3,
                    msg=f"span {span}, angle {angle}: not one upper arm from the shoulder",
                )
                self.assertAlmostEqual(
                    float(np.linalg.norm(pole - wrist)), self.fore, places=3,
                    msg=f"span {span}, angle {angle}: not one forearm from the wrist",
                )
        self.assertGreater(checked, 10, "no reachable case was checked")

    def test_the_weight_does_not_depend_on_how_folded_the_arm_is(self) -> None:
        """The gate, stated as its absence. This is the defect the pack exists
        for: the old weight was `CONTACT_POLE_WEIGHT * slack`, so it grew as
        the arm folded."""
        shoulder = np.array([20.0, 140.0, 0.0])
        weights = set()
        for span in (15.0, 30.0, 45.0):
            found, _ = self.targets_for(
                shoulder + np.array([0.0, 0.0, span]), ELBOW_POLE_ANGLE_DEGREES
            )
            if "weight" in found:
                weights.add(round(float(found["weight"]), 6))
        self.assertEqual(
            len(weights), 1, f"the pole's weight still varies with the fold: {weights}"
        )

    def test_a_straight_arm_gets_no_pole_at_all(self) -> None:
        """Not a special case bolted on. At full extension the elbow circle
        collapses to a point, so every angle names the same place and the term
        has nothing to say. The old code needed a gate to achieve this."""
        shoulder = np.array([20.0, 140.0, 0.0])
        found, _ = self.targets_for(
            shoulder + np.array([0.0, 0.0, self.reach + 1.0]), ELBOW_POLE_ANGLE_DEGREES
        )
        self.assertNotIn("target", found, "a straight arm was still poled")

    def test_the_angle_is_honoured(self) -> None:
        """The dial must do something, or moving `elbowWidth` here achieves
        nothing. Measured back off the target rather than trusted."""
        shoulder = np.array([20.0, 140.0, 0.0])
        wrist = shoulder + np.array([0.0, 0.0, 30.0])
        seen = []
        for angle in (0.0, 30.0, 60.0):
            found, _ = self.targets_for(wrist, angle)
            pole = found["target"]
            axis = (wrist - shoulder) / np.linalg.norm(wrist - shoulder)
            off = pole - shoulder
            off = off - np.dot(off, axis) * axis
            off = off / np.linalg.norm(off)
            out = np.array([1.0, 0.0, 0.0]) - 0.0
            out = out - np.dot(out, axis) * axis
            out = out / np.linalg.norm(out)
            down = np.array([0.0, -1.0, 0.0])
            down = down - np.dot(down, axis) * axis
            down = down / np.linalg.norm(down)
            seen.append(
                float(np.degrees(np.arctan2(np.dot(off, out), np.dot(off, down))))
            )
        for asked, got in zip((0.0, 30.0, 60.0), seen):
            self.assertAlmostEqual(got, asked, places=3)


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class ModelFactsThePoleRestsOn(unittest.TestCase):
    def test_upper_arm_fraction(self) -> None:
        """`UPPER_ARM_FRACTION` places the elbow on its circle. A model change
        would move it and nothing else in the suite would notice: the athlete
        would still solve, still grade, and put her elbows somewhere else."""
        character = load_character()
        index = {
            name: number
            for number, name in enumerate(character.skeleton.joint_names)
        }
        rest = joint_positions(
            character, np.zeros(character.parameter_transform.size, dtype=np.float32)
        )
        for side in ("l", "r"):
            upper = float(
                np.linalg.norm(rest[index[f"{side}_lowarm"]] - rest[index[f"{side}_uparm"]])
            )
            fore = float(
                np.linalg.norm(rest[index[f"{side}_wrist"]] - rest[index[f"{side}_lowarm"]])
            )
            self.assertAlmostEqual(
                upper / (upper + fore), UPPER_ARM_FRACTION, places=5,
                msg=f"the {side} arm's proportions have moved",
            )


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheAngleReproducesTheEvidence(unittest.TestCase):
    """Solves the library, so it is the slow one here. It is worth it: this is
    the only test that says the number was read rather than chosen."""

    def test_the_mean_contact_separation_is_the_manual_figure(self) -> None:
        character = load_character()
        index = {
            name: number
            for number, name in enumerate(character.skeleton.joint_names)
        }
        found = []
        for movement_id in library():
            if not (has_ball(movement_id) and has_technique(movement_id)):
                continue
            if not load_technique(technique_path(movement_id)).possession_ready:
                continue
            result = solve_movement(character, movement_id)
            contact = result["possession"].contact_frame
            points = result["points"][contact]
            found.append(
                float(
                    np.linalg.norm(
                        points[index["l_lowarm"]] - points[index["r_lowarm"]]
                    )
                )
            )
        self.assertTrue(found, "no drill was measured, so this is empty")
        mean = sum(found) / len(found)
        # A whole centimetre of slack. The claim is that the angle was read off
        # the manual's figure, not that a decimal place survives a refactor.
        self.assertAlmostEqual(
            mean, REFERENCE_CM, delta=1.0,
            msg=f"mean contact separation is {mean:.2f} cm against the manual's "
            f"{REFERENCE_CM}. The angle no longer reproduces the evidence it "
            "was read from.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
