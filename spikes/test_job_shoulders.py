"""The job transmits the girdle motion its ball position depends on.

`ball.fromShouldersInArms` is an offset from the shoulder MIDPOINT. Until
2026-09-04 the job never said where that midpoint was, so a consumer had to
guess — and the rendering lane's guess was to leave the shoulder girdle at
rest, because nothing in the job asked it to move.

The girdle moves on every drill. Midpoint travel relative to the pelvis, across
the library: `overhead_pass` 8.45 cm, `deflect_high` 5.02, `hooks_jump_pull_in`
4.09, and no drill under 1.77. An earlier note claimed every drill but three
stayed inside 1.05 cm; that was a shoulder WIDTH range, which is the wrong
statistic and the wrong axis.

THE FIELD IS A PELVIS-RELATIVE DISPLACEMENT FROM REST, and every part of that
was arrived at by a measurement that killed the previous attempt:

- NOT metres. Every position in this job is normalised and `radiusM` is the
  only absolute length, because a netball is one size on every body and a
  shoulder is not. An absolute midpoint raised the rendering rig's ball about
  6 cm on every frame, including the phases that pass today.
- NOT arm lengths. A shoulder-above-pelvis distance is a TORSO quantity. The
  rendering rig's arm is 0.9215 of this athlete's (48.547 / 52.680) and its
  REST TORSO 0.8615 (42.7689 / 49.6456), so an arm divisor is 6.5 per cent
  wrong on a torso span: this athlete's 48.8246 cm shoulder height at
  `chest_pass/ready` resolves to 45.00 on a rig whose own rest torso is
  42.7689, which is 2.23 cm out against a 1 cm rule — on the very phase the
  field exists to protect. An earlier version of these lines wrote that second
  ratio as 0.8759, WHICH IS WITHDRAWN: it is 42.7689 / 48.8246 = 0.87597,
  truncated — a rest length over a posed height, when the two rigs' rest torsos
  are what the sentence claims to compare.
- NOT a POSITION, even torso-normalised, which failed on all 48 graded phases
  by 1.1 to 5.8 cm INCLUDING the phases where both girdles are neutral and
  nothing is wrong. A divisor scales and cannot translate, and the two rigs
  carry a constant offset between where MHR puts `root` and where MPFB puts
  `pelvis` — +2.46 cm ahead here against −0.26 there.
- And the displacement is PELVIS-RELATIVE on both sides of the subtraction.
  Taken from the world it carries the root, which is never at its rest
  position: `test_the_shift_is_the_girdle_and_not_the_body` below caught 30.97
  cm on the landing drill, against a girdle that moves 1.77.

A displacement cancels every constant — landmark convention, neutral posture,
build — reads zero at rest by construction, and carries the one thing that was
actually missing: that this girdle moves and the consumer's does not.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

# The job rounds every emitted number to six decimal places of a TORSO LENGTH,
# so ONE unit in the last place is 1e-6 torso lengths — 4.96e-07 m on this
# athlete. Measured over all 1180 frames of the twelve-drill library:
#
#     the midpoint reproduces the anchor      4.9086e-07 torsos
#     each SIDE reproduces its own shoulder   4.9996e-07
#     the end-to-end ball centre              9.3398e-07
#
# THE END-TO-END CHECK GETS ITS OWN CONSTANT, because it composes TWO
# independently rounded fields — the shift and `fromShouldersInArms`. Its bound
# is derived beside that constant below, and it is 1.031 units and not two.
#
# NEITHER CONSTANT IS A TOLERANCE CHOSEN TO FIT. No wrong pair of joints —
# clavicles, the rest pose, a swapped side — lands within a micron of the right
# one. The rendering lane's own agreement guard sits at 1e-5 m, twenty times
# above.
ROUNDING_TORSOS = 1e-6
# A CEILING, NOT THE BOUND, and an earlier version of this said "twice the
# single-field bound by construction". That is imprecise: the composed check
# adds two roundings in two DIFFERENT units, the shift in torso lengths and
# `fromShouldersInArms` in arm lengths, so the exact per-coordinate maximum is
# 0.5e-6 x (1 + arm / torso) = 1.031e-6 torsos on this athlete, not 2e-6.
#
# One unit was therefore never a bound at all. THE MEASURED WORST MOVED WHEN A
# DRILL WAS ADDED: 9.2583e-07 on the eleven-drill library, 9.3398e-07 once
# `netball_one_hand_high_pass` arrived. That is the whole argument in one
# number — under a 1e-6 threshold the library was a few drills from a red suite
# with nothing wrong in it. The worst passes one unit by ALIGNMENT — the two
# errors landed on the same axis with the same sign on the landing's frame 73.
# A re-roll of the roundings puts the chance of exceeding one unit at about one
# library in nine, on a machine with no defect in it. 2e-6 is above 1.031e-6
# with room, so it fails only on a defect.
COMPOSED_TORSOS = 2e-6

FIELD = "shoulderShiftFromRestInTorsos"

# THIS SAT AT 0.75 AND WAS ABOVE ONE OF THE THREE MUTATIONS IT NAMES. The
# world-relative form reads 0.6239 torso lengths on the landing's frame 0, so
# this guard PASSED it and the swap and side guards caught it instead — a guard
# whose own docstring cites a number it cannot fail on.
#
# Measured, all four, on the twelve-drill library: the largest TRUE shift is
# 0.3932 torso lengths, on `hooks_outside_hand`, the turned drill. World-
# relative reads 0.6239, a torso-normalised POSITION about 0.98, and metres
# about 1.3 in the vertical. 0.5 is the only round value above the first and
# below the other three.
#
# The twelfth drill did not move the maximum, and it is nonetheless the
# SECOND-largest per-drill maximum of the twelve: `netball_one_hand_high_pass`
# reaches 0.1435, against 0.3932 first and 0.1366 third. (An earlier version of
# this line called it ninth-largest, which was a mis-sort.) So the margin under
# 0.5 belongs to the turned drill alone. The other eleven sit between 0.1205
# and 0.1435, a band 0.023 wide, and a new drill would have to reach 3.5 times
# the second-largest shift in the library to trouble this guard.
LOOKS_ABSOLUTE_TORSOS = 0.5

# A FLOOR ON THE COVER, NOT A TOTAL, and it replaces a total that fired on the
# first new drill. `assertEqual(checked, 1084)` was written to prove the loop
# reads the whole library rather than a sample. It did that, and it also failed
# the moment `netball_one_hand_high_pass` arrived with 96 frames — a red suite
# on a merged tree, caused by a correct new drill and by this file.
#
# So the POPULATION now comes from `library()` and each drill's frame count
# from its own clip, which is the rule a drill's author can satisfy by adding
# the drill and nothing else. This number only says the cover has not SHRUNK
# below what the field was proved on when it shipped. A new drill raises the
# cover and does not touch it. Removing a drill does fire it, which is the one
# case worth a person's attention, and then this line moves with the reason
# written beside it.
COVERED_AT_LEAST = 1084


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheJobCarriesItsOwnAnchor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from movement_engine import library, load_character

        cls.character = load_character()
        cls.library = library()

    def parts(self, movement_id):
        """The solve, its index, its rest pose and its technique."""
        from movement_engine import joint_positions
        from possession_solve import solve_movement
        from technique import load_technique, technique_path

        result = solve_movement(self.character, movement_id)
        rest_points = joint_positions(self.character, result["identity"])
        return (
            result,
            result["index"],
            rest_points,
            load_technique(technique_path(movement_id)),
        )

    def resolved(self, job, rest_points, points, index):
        """What a consumer does: apply the shift to its OWN rest girdle.

        Its own pelvis, plus its own rest shoulder measured from that pelvis,
        plus the transmitted shift scaled by its own rest torso. Here the
        consumer IS the source athlete, so this must return the positions the
        field was made from.
        """
        from export_blender_job import rest_torso, to_blender

        torso = rest_torso(rest_points, index)
        pelvis = to_blender(points[index["root"]])
        rest_pelvis = to_blender(rest_points[index["root"]])
        return {
            side: pelvis
            + (to_blender(rest_points[index[f"{side}_uparm"]]) - rest_pelvis)
            + np.array(job[FIELD][side]) * torso
            for side in ("l", "r")
        }

    def every_frame(self):
        """Every frame of every drill in the library, with its job."""
        from export_blender_job import phase_job

        for movement_id in self.library:
            result, index, rest_points, method = self.parts(movement_id)
            for frame in range(len(result["points"])):
                yield (
                    movement_id,
                    frame,
                    result,
                    index,
                    rest_points,
                    phase_job(result, index, frame, method, rest_points),
                )

    def test_the_transmitted_girdle_is_the_anchor_on_every_frame(self):
        """The whole point. Every frame of every drill, not a sample."""
        from export_blender_job import rest_torso, to_blender

        covered: dict[str, list[int]] = {}
        in_the_clip: dict[str, int] = {}
        worst = 0.0
        for movement_id, frame, result, index, rest_points, job in self.every_frame():
            points = result["points"][frame]
            back = self.resolved(job, rest_points, points, index)
            sent = np.stack([back[side] for side in ("l", "r")]).mean(axis=0)
            anchor = np.stack(
                [to_blender(points[index[f"{side}_uparm"]]) for side in ("l", "r")]
            ).mean(axis=0)
            gap = float(np.max(np.abs(sent - anchor))) / rest_torso(rest_points, index)
            worst = max(worst, gap)
            covered.setdefault(movement_id, []).append(frame)
            in_the_clip[movement_id] = len(result["points"])

        # The drills come from the library and the frames from each clip, so a
        # new drill is covered by being in the library and by nothing else.
        self.assertEqual(
            sorted(covered), sorted(self.library), "a drill went uncovered"
        )
        for movement_id, frames in covered.items():
            self.assertEqual(
                frames,
                list(range(in_the_clip[movement_id])),
                f"{movement_id} is covered with a gap, a repeat or a short tail",
            )
        self.assertGreaterEqual(
            sum(in_the_clip.values()),
            COVERED_AT_LEAST,
            "the cover has shrunk below what this field was proved on",
        )
        self.assertLess(worst, ROUNDING_TORSOS, f"worst gap {worst:.3e} torsos")

    def test_a_consumer_can_rebuild_the_ball_from_what_the_job_carries(self):
        """END TO END, which is the thing that was actually broken."""
        from export_blender_job import rest_torso, to_blender

        worst = 0.0
        for _, frame, result, index, rest_points, job in self.every_frame():
            points = result["points"][frame]
            back = self.resolved(job, rest_points, points, index)
            mid = np.stack([back[side] for side in ("l", "r")]).mean(axis=0)
            shoulder = to_blender(points[index["l_uparm"]])
            elbow = to_blender(points[index["l_lowarm"]])
            arm = float(
                np.linalg.norm(elbow - shoulder)
                + np.linalg.norm(to_blender(points[index["l_wrist"]]) - elbow)
            )
            rebuilt = mid + np.array(job["ball"]["fromShouldersInArms"]) * arm
            centre = to_blender(result["possession"].frames[frame].centre)
            worst = max(
                worst,
                float(np.max(np.abs(rebuilt - centre))) / rest_torso(rest_points, index),
            )

        self.assertLess(worst, COMPOSED_TORSOS, f"worst ball error {worst:.3e} torsos")

    def test_the_shift_is_the_girdle_and_not_the_body(self):
        """The subtraction must be pelvis-relative on BOTH sides.

        THIS GUARD ALREADY EARNED ITS PLACE. Taken from the world instead of
        from the pelvis, the field read 0.6239 torso lengths — 30.97 cm — on
        `netball_double_foot_landing` frame 0, because the solved root is 37 cm
        from its rest position at that phase. The girdle itself moves 1.77 cm
        on that drill.
        """
        worst = 0.0
        for movement_id, frame, _, _, _, job in self.every_frame():
            for side in ("l", "r"):
                worst = max(worst, float(np.max(np.abs(job[FIELD][side]))))

        self.assertLess(
            worst,
            LOOKS_ABSOLUTE_TORSOS,
            f"largest shift {worst:.4f} torsos — world-relative reads 0.6239, a "
            "position about 0.98 and metres about 1.3, so this is carrying "
            "more than a girdle",
        )

    def test_each_shift_reproduces_its_own_shoulder_exactly(self):
        """A swapped pair passes every check built on the MIDPOINT.

        The midpoint of a swapped pair is the same midpoint, so guard one is
        blind to it by construction.

        A FIRST VERSION OF THIS GUARD WAS ALSO BLIND, and its mutation proved
        it: it asked only whether each resolved shoulder was NEARER its own
        side than the other, and the rest shoulders are 0.70 torso lengths
        apart while the shifts reach 0.39, so a swap never crosses the middle.
        Swapping left and right at the point of emission passed all six tests.

        Reproducing each side EXACTLY is the guard that bites: a swap moves
        each shoulder by the difference of the two shifts, which is nonzero on
        every frame that is not perfectly still.
        """
        from export_blender_job import rest_torso, to_blender

        worst = 0.0
        for movement_id, frame, result, index, rest_points, job in self.every_frame():
            points = result["points"][frame]
            back = self.resolved(job, rest_points, points, index)
            torso = rest_torso(rest_points, index)
            for side in ("l", "r"):
                mine = to_blender(points[index[f"{side}_uparm"]])
                worst = max(
                    worst, float(np.max(np.abs(back[side] - mine))) / torso
                )

        self.assertLess(
            worst,
            ROUNDING_TORSOS,
            f"a side reproduces to {worst:.3e} torsos, so the pair is swapped or "
            "the shift is measured against the wrong shoulder",
        )

    def test_every_other_block_holds_the_value_its_own_helper_produces(self):
        """ADDITIVE, compared by VALUE and not by key.

        A first version compared the KEY SET, which a dropped `grip` or a
        changed `radiusM` both pass. This rebuilds each block from the helper
        that owns it and requires the job to carry exactly that.

        AND IT NOW REBUILDS `grip`, WHICH IT DID NOT. `grip` is the one
        conditional block in the job, so it was the one block a change could
        reach without any guard reading it. It is also the only consumer of the
        metre-valued arm divisor, which is why `blender_arm` exists: this
        rebuild calls the same function the job calls, rather than restating
        its formula and then agreeing with itself.

        AND NO GUARD REJECTED AN EXTRA KEY. Every check here was an assertion
        that some named thing is present and correct, so a job carrying a
        twelfth block nobody documented passed all six. The key set is now
        derived — from `holding` and `sides_at`, the two conditions that decide
        it — and compared whole, so an addition and a removal both fail.
        """
        from export_blender_job import (
            _arm,
            _grip,
            _hand,
            _stance,
            blender_arm,
            phase_job,
            to_blender,
        )

        for movement_id in self.library:
            result, index, rest_points, method = self.parts(movement_id)
            for frame in (0, len(result["points"]) // 2, len(result["points"]) - 1):
                points = result["points"][frame]
                job = phase_job(result, index, frame, method, rest_points)

                self.assertIn(FIELD, job)
                self.assertEqual(job["frame"], frame)
                self.assertEqual(job["stance"], _stance(points, index))
                for side in ("l", "r"):
                    self.assertEqual(job["arms"][side], _arm(points, index, side))
                    self.assertEqual(job["hands"][side], _hand(points, index, side))
                self.assertEqual(
                    job["ball"]["radiusM"], round(float(result["radiusCm"]) / 100.0, 4)
                )
                self.assertEqual(
                    job["ball"]["holding"],
                    bool(result["possession"].frames[frame].holding),
                )
                self.assertEqual(
                    sorted(job["ball"]),
                    ["fromShouldersInArms", "holding", "radiusM"],
                )

                held = result["possession"].frames[frame]
                sides = tuple(method.sides_at(held.phase)) if held.holding else ()
                if sides:
                    # Before the rebuild, or a DROPPED `grip` raises KeyError
                    # here and the guard never gets to say what is wrong.
                    self.assertIn(
                        "grip",
                        job,
                        f"{movement_id} frame {frame} holds with "
                        f"{len(sides)} hand(s) and carries no grip block",
                    )
                    self.assertEqual(
                        job["grip"],
                        _grip(
                            points,
                            index,
                            to_blender(held.centre),
                            float(result["radiusCm"]) / 100.0,
                            blender_arm(points, index),
                            sides,
                        ),
                    )
                self.assertEqual(
                    set(job),
                    {"frame", "arms", "hands", "stance", FIELD, "ball"}
                    | ({"grip"} if sides else set()),
                    f"{movement_id} frame {frame} carries an unexpected key set",
                )

    def test_the_girdle_really_moves_or_this_guards_nothing(self):
        """Guards the guard, on the MIDPOINT's travel rather than the width.

        A first version measured shoulder WIDTH, which is one axis of three and
        misses the 4.08 cm fore-and-aft travel on the overhead entirely.
        """
        from export_blender_job import phase_job, to_blender

        result, index, rest_points, method = self.parts("netball_overhead_pass")
        midpoints = []
        for frame in range(len(result["points"])):
            points = result["points"][frame]
            job = phase_job(result, index, frame, method, rest_points)
            back = self.resolved(job, rest_points, points, index)
            centre = np.stack([back[side] for side in ("l", "r")]).mean(axis=0)
            midpoints.append(centre - to_blender(points[index["root"]]))

        travel = max(
            float(np.linalg.norm(one - midpoints[0])) for one in midpoints
        )

        self.assertGreater(
            travel,
            0.04,
            f"the overhead's midpoint travels {travel * 100:.2f} cm relative to the "
            "pelvis; under 4 cm the field this file exists for carries a constant",
        )


if __name__ == "__main__":
    unittest.main()
