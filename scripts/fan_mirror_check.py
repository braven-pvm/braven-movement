"""Left and right hand fan per phase, and whether a moving ball disturbs it.

The fan is index tip to pinky tip on one hand. `docs/HAND_MIRROR_EVIDENCE.md`
reports 14.37 cm on the left against 1.75 cm on the right before PR #46: a
right hand that was closed instead of opened.

READ THE GRIP, NOT THE DRILL NAME. Two phases show a fan gap above 2 cm:
`hooks_outside_hand/contact` at 2.372 and
`one_hand_snatch_to_other_hand/contact` at 2.248. Neither is a defect. The job
carries `grip` for the RIGHT SIDE ONLY on both, so one hand is closed on the
ball near 6.9 cm and the other is open near 9.3 cm. The mirror claim applies to
phases where BOTH sides appear in `grip`, and across all of those the worst gap
is 0.095 cm at `deflect_high/contact`.

THE FAN IS NOT INVARIANT TO THE BALL'S POSITION, so these figures cannot be
built before the shoulder-anchor fix lands. Posing every phase a second time
with the ball raised by the overhead pass's own girdle travel of 7.40 cm moves
the fan by up to 0.273 cm, at `chest_pass/release`. The fingers flex until they
reach the ball surface, so moving the ball changes the flexion and the fan with
it. That drift is nearly three times the 0.095 cm mirror gap the figures would
report, so the pending fix can change the headline number by more than the
number itself. Measure the fan AFTER the fix.

    blender -b --python-exit-code 9 -P scripts/fan_mirror_check.py -- --all
"""

import json
import sys
from pathlib import Path

REPO = Path(
    "F:/Repositories/braven-movement/.claude/worktrees/zealous-tereshkova-c7f926"
)
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import blender_movement_render as R  # noqa: E402
from blender_mpfb_reference_catch import world_tail  # noqa: E402
from reference_pose_config import load_reference_catch_config  # noqa: E402

GIRDLE_TRAVEL_M = 0.0740  # the overhead pass's own, engine side
JOBS = sorted((REPO / "spikes" / "poc-output").glob("*.job.json"))


def fan(rig, side: str) -> float:
    """Index tip to pinky tip, cm. A distance on ONE rigid hand."""
    return (world_tail(rig, f"index_03_{side}")
            - world_tail(rig, f"pinky_03_{side}")).length * 100.0


def measure(studio, phase) -> tuple[float, float]:
    R.pose_phase(
        studio.rig, phase, studio.config.anatomy_limits_degrees, studio.basis,
        studio.foot_baseline, studio.config.finger_curl_degrees, None,
        studio.human,
    )
    return fan(studio.rig, "l"), fan(studio.rig, "r")


def displaced(phase: dict, arm_m: float) -> dict:
    """The same phase with the ball raised by the girdle's travel."""
    moved = json.loads(json.dumps(phase))
    offset = moved["ball"]["fromShouldersInArms"]
    offset[2] = offset[2] + GIRDLE_TRAVEL_M / arm_m
    return moved


def main():
    studio = R.Studio(load_reference_catch_config())
    arm = R.bone_chain_length(studio.rig, "upperarm_l", "lowerarm_l", "hand_l")
    print(f"arm {arm * 100:.3f} cm, ball raised {GIRDLE_TRAVEL_M * 100:.2f} cm "
          f"for the second reading")
    print(f"{'drill / phase':<44}{'left':>8}{'right':>8}{'|L-R|':>8}"
          f"{'moved L':>9}{'moved R':>9}{'fan drift':>11}")
    worst_mirror = worst_drift = 0.0
    for path in JOBS:
        job = json.loads(path.read_text(encoding="utf-8"))
        drill = job["movementId"].replace("netball_", "")
        for phase in job["phases"]:
            left, right = measure(studio, phase)
            moved_l, moved_r = measure(studio, displaced(phase, arm))
            mirror = abs(left - right)
            drift = max(abs(left - moved_l), abs(right - moved_r))
            worst_mirror = max(worst_mirror, mirror)
            worst_drift = max(worst_drift, drift)
            label = f"{drill}/{phase.get('id', phase.get('name', '?'))}"
            print(f"{label:<44}{left:>8.3f}{right:>8.3f}{mirror:>8.3f}"
                  f"{moved_l:>9.3f}{moved_r:>9.3f}{drift:>11.4f}")
    print()
    print(f"worst mirror gap |left - right|: {worst_mirror:.4f} cm")
    print(f"worst fan drift when the ball moves 7.40 cm: {worst_drift:.4f} cm")


if __name__ == "__main__":
    main()
