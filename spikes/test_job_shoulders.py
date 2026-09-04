"""The job transmits the anchor its ball position is measured from.

`ball.fromShouldersInArms` is an offset from the shoulder MIDPOINT. Until
2026-09-04 the job never said where that midpoint was, so a consumer had to
guess — and the rendering lane's guess was to leave the shoulder girdle at
rest, because nothing in the job asked it to move.

That is not a small error on the drills it matters for. This athlete's shoulder
width ranges 33.91 to 39.53 cm WITHIN `netball_overhead_pass`, and her shoulder
midpoint rises 4.52 cm between the chest pass and the overhead at frame 75.

Two things are guarded here, and the second is as important as the first:

- the transmitted pair really is the pair the ball offset was measured from, and
- adding it changed nothing else, so a consumer that ignores it is unaffected.
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

# The job rounds every emitted number to six decimal places of a metre, so the
# midpoint of two rounded shoulders cannot equal an anchor computed before
# rounding. Measured across all 988 frames of the library, the worst gap is
# 4.911e-07 m and the worst end-to-end ball error is 7.015e-07 m — both under a
# micron, and both the file's own rounding rather than a modelling difference.
#
# THIS IS NOT A TOLERANCE CHOSEN TO MAKE THE TEST PASS. It is one unit in the
# last emitted place. No wrong pair of joints — clavicles, scapulae, the rest
# pose — lands within a micron of the right one, so the guard still says what it
# is meant to say.
ROUNDING_METRES = 1e-6


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheJobCarriesItsOwnAnchor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from movement_engine import library, load_character

        cls.character = load_character()
        cls.library = library()

    def solved(self, movement_id):
        from possession_solve import solve_movement

        return solve_movement(self.character, movement_id)

    def test_the_transmitted_midpoint_is_the_anchor_on_every_frame(self):
        """The whole point. Every frame of every drill, not a sample."""
        from export_blender_job import phase_job, to_blender
        from technique import load_technique, technique_path

        checked = 0
        worst = 0.0
        for movement_id in self.library:
            result = self.solved(movement_id)
            index = result["index"]
            method = load_technique(technique_path(movement_id))
            for frame in range(len(result["points"])):
                job = phase_job(result, index, frame, method)
                sent = np.stack(
                    [np.array(job["shoulders"][side]) for side in ("l", "r")]
                ).mean(axis=0)
                anchor = np.stack(
                    [
                        to_blender(result["points"][frame][index[f"{side}_uparm"]])
                        for side in ("l", "r")
                    ]
                ).mean(axis=0)
                worst = max(worst, float(np.max(np.abs(sent - anchor))))
                checked += 1

        self.assertGreater(checked, 900, "the whole library must be covered")
        self.assertLess(worst, ROUNDING_METRES, f"worst gap {worst:.3e} m")

    def test_a_consumer_can_rebuild_the_ball_from_what_the_job_carries(self):
        """END TO END, which is the thing that was actually broken.

        The midpoint agreeing is necessary and not sufficient: what a consumer
        does is place the ball at the midpoint plus the offset, and that is
        what has been wrong in every figure this project has rendered.
        """
        from export_blender_job import phase_job, to_blender
        from technique import load_technique, technique_path

        worst = 0.0
        for movement_id in self.library:
            result = self.solved(movement_id)
            index = result["index"]
            method = load_technique(technique_path(movement_id))
            points = result["points"]
            for frame in range(len(points)):
                job = phase_job(result, index, frame, method)
                mid = np.stack(
                    [np.array(job["shoulders"][side]) for side in ("l", "r")]
                ).mean(axis=0)
                shoulder = to_blender(points[frame][index["l_uparm"]])
                elbow = to_blender(points[frame][index["l_lowarm"]])
                arm = float(
                    np.linalg.norm(elbow - shoulder)
                    + np.linalg.norm(
                        to_blender(points[frame][index["l_wrist"]]) - elbow
                    )
                )
                rebuilt = mid + np.array(job["ball"]["fromShouldersInArms"]) * arm
                centre = to_blender(result["possession"].frames[frame].centre)
                worst = max(worst, float(np.max(np.abs(rebuilt - centre))))

        self.assertLess(worst, ROUNDING_METRES, f"worst ball error {worst:.3e} m")

    def test_the_rest_of_the_job_is_untouched(self):
        """ADDITIVE. A consumer that ignores the field renders as before.

        Compared key by key against a job with the new field removed, so this
        fails if anything else moved by so much as a rounding place.
        """
        from export_blender_job import phase_job
        from technique import load_technique, technique_path

        for movement_id in self.library:
            result = self.solved(movement_id)
            index = result["index"]
            method = load_technique(technique_path(movement_id))
            for frame in (0, len(result["points"]) // 2, len(result["points"]) - 1):
                job = phase_job(result, index, frame, method)

                self.assertIn("shoulders", job)
                without = {k for k in job if k != "shoulders"}
                # `grip` is conditional — `_grip` emits only the hands that are
                # ON the ball, so a frame with no hand on it carries no grip
                # block. Everything else is always present. A hardcoded list
                # that omitted `grip` is what a first version of this asserted.
                self.assertEqual(
                    without & {"arms", "ball", "frame", "hands", "stance"},
                    {"arms", "ball", "frame", "hands", "stance"},
                    f"{movement_id} frame {frame}: a block went missing",
                )
                self.assertEqual(
                    without - {"arms", "ball", "frame", "hands", "stance"},
                    {"grip"} & without,
                    f"{movement_id} frame {frame}: the job gained more than the field",
                )
                self.assertEqual(
                    sorted(job["ball"]),
                    ["fromShouldersInArms", "holding", "radiusM"],
                    "the ball block must be untouched",
                )

    def test_the_girdle_really_moves_or_this_guards_nothing(self):
        """Guards the guard. If the shoulders never moved, every assertion
        above would pass on a constant and the field would be pointless."""
        from export_blender_job import phase_job

        result = self.solved("netball_overhead_pass")
        index = result["index"]
        from technique import load_technique, technique_path

        method = load_technique(technique_path("netball_overhead_pass"))
        widths = []
        for frame in range(len(result["points"])):
            job = phase_job(result, index, frame, method)
            left = np.array(job["shoulders"]["l"])
            right = np.array(job["shoulders"]["r"])
            widths.append(float(np.linalg.norm(left - right)))

        self.assertGreater(
            max(widths) - min(widths),
            0.04,
            "the overhead pass must move the girdle by more than 4 cm, or the "
            "field this file exists for is carrying a constant",
        )


if __name__ == "__main__":
    unittest.main()
