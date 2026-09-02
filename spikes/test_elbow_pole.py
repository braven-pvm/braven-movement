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
# Reaches oblique to BOTH `out` and `down`, which is where a basis that is not
# orthonormalised goes wrong. A reach along one axis is the case the old basis
# got right by accident, so a list of those cannot fail.
#
# ONE LIST, READ BY BOTH TESTS BELOW. The obliqueness guard used to assert over
# its own hardcoded copy of these, which made it a statement of convention
# rather than a guard: editing the circle test's directions to axis-aligned
# left everything passing, including with the orthogonalisation removed.
OBLIQUE_DIRECTIONS = (
    (0.0, 0.0, 1.0),
    (0.3, -0.9, 0.3),
    (0.6, -0.7, 0.4),
    (-0.5, -0.8, 0.3),
    (0.1, -0.99, 0.05),
    (0.7, -0.5, -0.5),
)
# What the angle actually produces on the population the manual's photographs
# describe. Marius ruled on 2026-08-30 that this is recorded and the angle is
# deferred: refer to the class docstring below.
MEASURED_CM = 36.5
# How far the one-handed drills sit ABOVE the two-handed ones at contact. This
# is a recorded fact, not a target, and its history now includes a reading that
# was never true of the athlete:
#
#   about  8 cm  before the free-hand fix
#   about 20 cm  after it
#          3.09  on ac240b2 — AN ARTEFACT, see below
#         20.96  once the locked parameters were excluded
#
# THE 3.09 WAS NOT A CONVERGENCE. `netball_hooks_outside_hand` has two solved
# poses about 33 degrees apart in ready-stance turn, and which one the solver
# reaches depends on the COMPOSITION of the enabled parameter set. The set that
# shipped as ac240b2 reached the second one, where that drill's contact elbow
# width reads 19.01 cm and drags the one-handed mean down with it. Any change to
# the set — including excluding an unrelated axis with a real range — returns it
# to 54.83, beside the other one-handed drill's 59.96.
# Refer to docs/CLAVICLE_ARTEFACT.md.
#
# So the two groups never converged. The pole question keeps its original form.
# The two-handed mean is 36.40 to 36.43 through ALL of it, which is why nothing
# caught the artefact for a day.
#
# THIS IS A PINNED FACT AND NOT A STATISTICAL CLAIM. Two drills cannot support
# the word "population" in either direction, and both this file and the coach
# bundle have made that error once each, pointing opposite ways.
ONE_HANDED_GAP_CM = 20.96


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

    def test_the_target_is_on_the_elbow_circle(self) -> None:
        """The target is exactly one upper arm from the shoulder and one
        forearm from the wrist, at every angle and every reachable span.

        THE NAME LOST A CLAUSE, and the clause is the point. This used to be
        `..._where_the_basis_is_orthogonal`, and its docstring said so: `out`
        and `down` were each projected off the reach axis but never
        orthogonalised against EACH OTHER, so on an oblique reach the target
        landed up to 12.30 cm off the circle. Every case below reached along
        +Z, where `out . down` is exactly zero and the flaw vanishes, so the
        test exercised precisely the family the defect could not reach. It was
        left that way on purpose, because widening it would have turned the
        branch red for a defect whose fix moves figures.

        The basis is orthonormal now, so the clause is gone and so are the
        axis-aligned reaches. The directions below are deliberately OBLIQUE,
        including the family where the raw `out . down` reaches -0.99.
        """
        shoulder = np.array([20.0, 140.0, 0.0])
        checked = 0
        for direction in [np.array(one) for one in OBLIQUE_DIRECTIONS]:
            direction = direction / np.linalg.norm(direction)
            for span in (15.0, 25.0, 35.0, 45.0, 50.0):
                for angle in (-20.0, 0.0, 22.4, 34.6, 60.0, 90.0):
                    wrist = shoulder + direction * span
                    found, shoulder_used = self.targets_for(wrist, angle)
                    if "target" not in found:
                        continue
                    checked += 1
                    pole = found["target"]
                    where = (f"direction {np.round(direction, 2)}, span {span}, "
                             f"angle {angle}")
                    self.assertAlmostEqual(
                        float(np.linalg.norm(pole - shoulder_used)), self.upper,
                        places=3,
                        msg=f"{where}: not one upper arm from the shoulder",
                    )
                    self.assertAlmostEqual(
                        float(np.linalg.norm(pole - wrist)), self.fore, places=3,
                        msg=f"{where}: not one forearm from the wrist",
                    )
        self.assertGreater(checked, 50, "no reachable case was checked")

    def test_the_oblique_family_is_actually_oblique(self) -> None:
        """The anti-hollow clause for the test above.

        Its directions are only worth more than the old ones if the raw basis
        they build is genuinely non-perpendicular. If a later edit made them
        axis-aligned again, the test above would pass for the reason the old
        one did.
        """
        worst = 0.0
        for direction in OBLIQUE_DIRECTIONS:
            axis = np.array(direction, dtype=np.float64)
            axis = axis / np.linalg.norm(axis)
            out = np.array([1.0, 0.0, 0.0]) - axis[0] * axis
            down = np.array([0.0, -1.0, 0.0]) + axis[1] * axis
            dot = abs(float(np.dot(out / np.linalg.norm(out),
                                   down / np.linalg.norm(down))))
            worst = max(worst, dot)
        self.assertGreater(
            worst, 0.5,
            "the reach directions above are nearly axis aligned, so the raw "
            "`out` and `down` are nearly perpendicular already and the circle "
            "test cannot see a basis that is not orthonormalised",
        )

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
class TheContactSeparationOnTheEvidencedPopulation(unittest.TestCase):
    """Solves the library, so it is the slow one here.

    THIS CLASS NO LONGER PROVES THE ANGLE WAS READ OFF THE MANUAL'S FIGURE.
    It used to, and the proof was not sound. Read this before trusting it.

    `ELBOW_POLE_ANGLE_DEGREES` is defined as the angle that puts the mean elbow
    separation at contact on the manual's 38.6 cm. That mean was taken across
    the whole library, and it agreed: 38.58 cm. But the 38.6 cm figure is read
    from photographs of a snatch AT CONTACT with the arm at 0.85 to 0.90 of
    full extension, as `docs/KNOWN_ISSUES.md` already states, and the library
    mixes two populations. Six drills put both hands on the ball at contact and
    averaged 36.57 cm. Two put one hand on it, so their other elbow is not on
    the ball at all, and they averaged 44.60. The two averaged to 38.58, which
    is 0.02 cm from the target, and no member of the population was at it.

    The agreement was an artefact of the mix. It surfaced on 2026-08-30 when
    the free-hand fix moved one population and the whole-library mean jumped to
    41.68 cm while the six two-handed drills moved by 0.03.

    So the population here is now the drills whose evidence the photographs
    actually are: both hands on the ball at the contact frame. It is taken from
    the SOLVE rather than from a field in a technique file, because what
    matters is which hands are on the ball, not what a file says the drill is.

    On that population the angle gives 36.5 cm against the manual's 38.6, a gap
    of about 2.1 cm. The gap is not new. It was there before the free-hand fix
    and moved by 0.03 cm through it.

    MARIUS RULED ON 2026-08-30: record the gap, and defer the angle.
    `ELBOW_POLE_ANGLE_DEGREES` stays at 31.3 until the coach morning provides
    the data to re-read it, because changing it moves every drill in the
    library and the library's look must not change before a second coach has
    seen it. A five-point sweep puts the angle that would close the gap at
    about 37.3 degrees; that number is evidence for the ruling, not a target.

    What this class tests now is narrower and true: the separation on the
    evidenced population is what it is measured to be, so the deferred gap
    cannot quietly grow, and the population restriction is not a no-op.
    """

    @classmethod
    def setUpClass(cls) -> None:
        character = load_character()
        index = {
            name: number
            for number, name in enumerate(character.skeleton.joint_names)
        }
        cls.two_handed: dict[str, float] = {}
        cls.one_handed: dict[str, float] = {}
        cls.not_a_catch: dict[str, float] = {}
        for movement_id in library():
            if not (has_ball(movement_id) and has_technique(movement_id)):
                continue
            if not load_technique(technique_path(movement_id)).possession_ready:
                continue
            result = solve_movement(character, movement_id)
            contact = result["possession"].contact_frame
            points = result["points"][contact]
            separation = float(
                np.linalg.norm(
                    points[index["l_lowarm"]] - points[index["r_lowarm"]]
                )
            )
            # A CATCH ONLY. This measures the elbows at the moment she TAKES
            # the ball, so a drill that begins holding it has no such moment:
            # its contact frame is frame 0 by definition, and frame 0 of a pass
            # is the ball against her chest with the elbows wide. Measured,
            # netball_chest_pass reads 53.41 cm there, against 19.01 to 40.29
            # over every drill that actually catches. Including it moved this
            # mean from 36.40 to 38.83 and closed the gap below from 3.09 to
            # 0.66 — which is this class's own stated failure, a mean over the
            # wrong population, arriving from a new direction.
            states = [frame["ballState"] for frame in result["measurements"]]
            if "flight" not in states[:contact]:
                cls.not_a_catch[movement_id] = separation
                continue
            sides = set(result["possession"].frames[contact].sides)
            where = cls.two_handed if sides == {"l", "r"} else cls.one_handed
            where[movement_id] = separation

    def test_the_population_is_not_the_whole_library(self) -> None:
        """The anti-hollow clause. A restriction that excludes nothing is a
        comment, and this file exists because a mean over the wrong population
        matched its target for months."""
        self.assertTrue(self.two_handed, "no drill puts both hands on the ball")
        self.assertTrue(
            self.one_handed,
            "no drill was excluded, so the population restriction below does "
            "nothing and this class is back to averaging the whole library",
        )

    def test_a_drill_that_never_caught_the_ball_is_excluded(self) -> None:
        """The anti-hollow clause for the catch restriction itself.

        Added when the first pass arrived. It is a separate assertion rather
        than a comment because the restriction above is invisible while the
        library is all catches: it would silently become a no-op the day the
        pass family were renamed or removed, and the mean would drift back
        without anything going red.
        """
        self.assertTrue(
            self.not_a_catch,
            "no drill was excluded as a non-catch, so the restriction in "
            "setUpClass does nothing. Either the pass family is gone, in which "
            "case delete the restriction, or a pass is being averaged into a "
            "catching population again.",
        )
        for movement_id, separation in self.not_a_catch.items():
            with self.subTest(movement=movement_id):
                self.assertNotIn(movement_id, self.two_handed)
                self.assertNotIn(movement_id, self.one_handed)

    def test_the_separation_on_the_evidenced_population(self) -> None:
        """The measurement, pinned so the deferred gap cannot grow in silence.

        Half a centimetre of slack, tighter than the whole centimetre the
        read-off claim used to carry, because this is a recorded value rather
        than a claim about agreement with a photograph.
        """
        mean = sum(self.two_handed.values()) / len(self.two_handed)
        self.assertAlmostEqual(
            mean, MEASURED_CM, delta=0.5,
            msg=f"the mean contact separation over the {len(self.two_handed)} "
            f"drills that put both hands on the ball is {mean:.2f} cm, against "
            f"the {MEASURED_CM} cm recorded when Marius deferred the angle on "
            f"2026-08-30. The manual's figure is {REFERENCE_CM} and the "
            f"documented gap to it is about 2.1 cm. If this moved because "
            "ELBOW_POLE_ANGLE_DEGREES was changed, the deferral has been "
            "overtaken and this number must be re-recorded with a ruling.",
        )

    def test_the_gap_between_the_populations_is_what_was_recorded(self) -> None:
        """WAS an assertion that the two populations stay far apart. They no
        longer are, and the fact is recorded rather than the guard relaxed.

        This asked for more than 5 cm of separation, on the reasoning that
        populations which converge no longer need splitting. It then failed on
        ac240b2 at 3.09 cm and was re-recorded as a convergence.

        THAT WAS WRONG, and this guard failing is what found it. The 3.09 was
        one drill sitting in a second solver basin; refer to the constant
        above. The two groups never converged.

        What this pins is the measured gap, so a further move cannot happen in
        silence. It is left as a pin rather than restored to a floor because a
        pin catches movement in BOTH directions, and the direction nobody
        expected is the one that cost two days.
        """
        two = sum(self.two_handed.values()) / len(self.two_handed)
        one = sum(self.one_handed.values()) / len(self.one_handed)
        self.assertAlmostEqual(
            one - two, ONE_HANDED_GAP_CM, delta=0.5,
            msg=f"the one-handed drills average {one:.2f} cm against the "
            f"two-handed {two:.2f}, a gap of {one - two:.2f} against the "
            f"{ONE_HANDED_GAP_CM} recorded when the locked parameters were "
            "excluded. The "
            "populations have moved again. Re-record this with a ruling, and "
            "re-read the pole-angle question with it: the deferral was taken "
            "when they were 20 cm apart.",
        )

    def test_the_two_populations_are_still_distinguishable(self) -> None:
        """The anti-hollow clause for the split itself.

        A pinned gap says nothing about whether the split is worth keeping. What would kill it is the populations becoming the SAME, and
        that is worth being told separately from a drift in the figure. The
        floor is the clinical five-degree threshold's length analogue: below a
        centimetre these are one population wearing two names.
        """
        two = sum(self.two_handed.values()) / len(self.two_handed)
        one = sum(self.one_handed.values()) / len(self.one_handed)
        self.assertGreater(
            one - two, 1.0,
            f"the one-handed and two-handed drills now average {one:.2f} and "
            f"{two:.2f} cm, which is the same population under two names. The "
            "split is costing complexity for nothing and the pole-angle "
            "question no longer has two answers to choose between.",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
