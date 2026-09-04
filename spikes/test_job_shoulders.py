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
- NOT arm lengths. A shoulder-above-pelvis distance is a TORSO quantity: that
  rig's arm is 0.9215 of this athlete's but its shoulder-above-pelvis is
  0.8759, so an arm divisor put its neutral phase 2.23 cm out against a 1 cm
  rule — on the very phase the field exists to protect.
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
# athlete. Measured over all 1084 frames:
#
#     the midpoint reproduces the anchor      4.9086e-07 torsos
#     each SIDE reproduces its own shoulder   4.9996e-07
#     the end-to-end ball centre              9.2583e-07
#
# THE END-TO-END CHECK GETS TWO UNITS, AND NOT BECAUSE IT NEEDED THEM TO PASS.
# It composes TWO independently rounded fields — the shift and
# `fromShouldersInArms` — so its bound is twice the single-field bound by
# construction. Holding it to one unit passed with 8 per cent to spare, which
# is a threshold waiting to fail on another machine for a reason that would
# not be a defect.
#
# NEITHER IS A TOLERANCE CHOSEN TO FIT. No wrong pair of joints — clavicles,
# the rest pose, a swapped side — lands within a micron of the right one. The
# rendering lane's own agreement guard sits at 1e-5 m, twenty times above.
ROUNDING_TORSOS = 1e-6
COMPOSED_TORSOS = 2e-6

FIELD = "shoulderShiftFromRestInTorsos"

# A metre-valued shoulder reads about 1.3 in the vertical on this athlete and a
# torso-normalised POSITION about 0.98. The largest true shift measured across
# the library is 0.3932 torso lengths, on the turned drill. This sits between
# them.
LOOKS_ABSOLUTE_TORSOS = 0.75


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
        """Every frame of every drill, with its job. 1084 frames."""
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

        checked = 0
        worst = 0.0
        for _, frame, result, index, rest_points, job in self.every_frame():
            points = result["points"][frame]
            back = self.resolved(job, rest_points, points, index)
            sent = np.stack([back[side] for side in ("l", "r")]).mean(axis=0)
            anchor = np.stack(
                [to_blender(points[index[f"{side}_uparm"]]) for side in ("l", "r")]
            ).mean(axis=0)
            gap = float(np.max(np.abs(sent - anchor))) / rest_torso(rest_points, index)
            worst = max(worst, gap)
            checked += 1

        self.assertEqual(checked, 1084, "the whole library must be covered")
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
            f"largest shift {worst:.4f} torsos — a position reads about 0.98 and "
            "metres about 1.3, so this is carrying more than a girdle",
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
        """
        from export_blender_job import _arm, _hand, _stance, phase_job

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
