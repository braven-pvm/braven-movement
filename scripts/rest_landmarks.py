"""This rig's REST-POSE landmarks, in torso lengths from the pelvis.

The half of the landmark comparison that lives on this side. The pack carries a
2.507 cm fore-and-aft residual that the shoulder fix does not remove, and
nobody can yet say whether it is a landmark convention difference or a real
posture difference between the two rest poses. This rig has no `root` bone and
the movement lane has no MPFB rig, so neither side can answer it alone.

THE HYPOTHESIS THIS EXISTS TO TEST. The engine's rest shoulders sit -0.0648
torso lengths ahead of its root and this rig's sit -0.0062, a 0.0586 gap. If
the engine's ROOT simply sits further back in the body than MPFB's pelvis, then
EVERY engine landmark will be about 0.0586 more negative than its counterpart
here, and the residual is a convention with no posture in it. If only the
SHOULDERS differ, it is a real posture difference and the figures inherit it.
The HEAD and NECK rows discriminate, not the shoulders.

DO NOT PAIR THE SPINE BY NAME. `spine_03` sits at 0.4866 of the torso height
here, which is under halfway up. If the engine's `c_spine3` is a thoracic
landmark near the shoulders, the two names do not describe the same bone, and
pairing them would be the same fault as refreshing a reference-pose number from
a drill phase. The heights decide the correspondence, not the names.

Torso lengths, so the two bodies are comparable. The divisor is this rig's rest
torso MAGNITUDE, |rest shoulder midpoint - rest pelvis| = 42.7689 cm.
"""

import sys
from pathlib import Path

REPO = Path(
    "F:/Repositories/braven-movement/.claude/worktrees/zealous-tereshkova-c7f926"
)
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import blender_movement_render as R  # noqa: E402
from blender_mpfb_reference_catch import world_head, world_tail  # noqa: E402
from reference_pose_config import load_reference_catch_config  # noqa: E402

# MPFB bone, and the MHR name it is being compared against.
PAIRS = [
    ("pelvis", "root", "head"),
    ("upperarm_l", "l_uparm", "head"),
    ("upperarm_r", "r_uparm", "head"),
    ("clavicle_l", "l_clavicle (head, sternal end)", "head"),
    ("clavicle_r", "r_clavicle (head, sternal end)", "head"),
    ("clavicle_l", "l_clavicle (tail, acromial end)", "tail"),
    ("clavicle_r", "r_clavicle (tail, acromial end)", "tail"),
    ("spine_03", "c_spine3", "head"),
    ("spine_02", "c_spine2", "head"),
    ("spine_01", "c_spine1", "head"),
    ("neck_01", "c_neck", "head"),
    ("head", "c_head", "head"),
]


def main():
    studio = R.Studio(load_reference_catch_config())
    rig = studio.rig
    R.reset_pose(rig, studio.basis)
    names = {bone.name for bone in rig.pose.bones}

    pelvis = world_head(rig, "pelvis")
    mid = (world_head(rig, "upperarm_l") + world_head(rig, "upperarm_r")) / 2.0
    torso = (mid - pelvis).length
    print(f"rest torso magnitude {torso * 100:.4f} cm, the divisor")
    print(f"`root` present in this rig: {'root' in names}")
    print()
    print(f"{'MPFB bone':<18}{'MHR name':<34}{'across':>10}{'up':>10}"
          f"{'ahead':>10}")
    for bone, mhr, end in PAIRS:
        if bone not in names:
            print(f"{bone:<18}{mhr:<34}   NOT IN THIS RIG")
            continue
        point = world_head(rig, bone) if end == "head" else world_tail(rig, bone)
        span = point - pelvis
        print(f"{bone + ' ' + end:<18}{mhr:<34}{span.x / torso:>10.4f}"
              f"{span.z / torso:>10.4f}{-span.y / torso:>10.4f}")
    print()
    print("Torso lengths from the PELVIS. Axes: across, up, ahead. `ahead` is "
          "MINUS Blender y,")
    print("read from the job rather than assumed: "
          "`ball.fromShouldersInArms` has a negative y")
    print("on the chest pass and the ball is in front of her.")


if __name__ == "__main__":
    main()
