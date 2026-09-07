"""What a CLAVICLE divisor would have produced, measured rather than proposed.

The job normalises each shoulder's displacement by the body's TORSO length. A
shoulder's reachable displacement is governed by its CLAVICLE, because the bone
rotates about its sternal end and does not stretch. The two rigs' clavicles
differ by 20.4 percent relative to their torsos, so a torso-normalised
displacement asks the shorter bone to reach further than it can.

THIS PROPOSES NOTHING. The divisor is the movement lane's field and it is ruled.
This exists because the pack quotes a figure — a clavicle divisor cuts the worst
residual from 52.09 mm to 31.03 mm and does not remove it — and a figure without
an instrument is a quotation. The first version of this script lived in a
scratchpad that a worktree recycle destroyed, which is the reason it is
committed now.

    blender -b --python-exit-code 9 -P scripts/clavicle_divisor_probe.py --
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import blender_movement_render as R  # noqa: E402
from blender_mpfb_reference_catch import world_head  # noqa: E402
from reference_pose_config import load_reference_catch_config  # noqa: E402

JOBS = sorted((REPO / "spikes" / "poc-output").glob("*.job.json"))

# The engine's rest geometry, measured by `scripts/engine_clavicle.py` from the
# repository: rest torso 49.6456 cm, clavicle 17.6505 cm, left and right
# identical to four decimals.
ENGINE_TORSO_CM = 49.6456
ENGINE_CLAVICLE_CM = 17.6505


def main() -> None:
    studio = R.Studio(load_reference_catch_config())
    R.reset_pose(studio.rig, studio.basis)
    rest = R.rest_girdle(studio.rig)
    here = rest["clavicle"]["l"] * 100.0

    torso_scale = rest["torso"] * 100.0 / ENGINE_TORSO_CM
    clavicle_scale = here / ENGINE_CLAVICLE_CM
    print(f"clavicle here {here:.4f} cm = {here / (rest['torso'] * 100):.5f} "
          f"torso lengths")
    print(f"clavicle engine {ENGINE_CLAVICLE_CM:.4f} cm = "
          f"{ENGINE_CLAVICLE_CM / ENGINE_TORSO_CM:.5f} torso lengths")
    print(f"a displacement scales by {torso_scale:.5f} under the ruled TORSO "
          f"divisor")
    print(f"and by {clavicle_scale:.5f} under a CLAVICLE divisor")
    print()

    ruled_worst = other_worst = 0.0
    ruled_row = other_row = ""
    outside = inside = 0
    for path in JOBS:
        job = json.loads(path.read_text(encoding="utf-8"))
        drill = job["movementId"].replace("netball_", "")
        for phase in job["phases"]:
            shift = phase.get(R.GIRDLE_FIELD)
            if shift is None:
                continue
            R.reset_pose(studio.rig, studio.basis)
            rest = R.rest_girdle(studio.rig)
            rest_shoulder = {s: world_head(studio.rig, f"upperarm_{s}")
                             for s in ("l", "r")}
            rest_clavicle = {s: world_head(studio.rig, f"clavicle_{s}")
                             for s in ("l", "r")}
            R.pose_stance(studio.rig, phase["stance"], studio.foot_baseline)
            travel = world_head(studio.rig, "pelvis") - rest["pelvis"]
            for side in ("l", "r"):
                bone = (rest_shoulder[side] - rest_clavicle[side]).length
                pivot = rest_clavicle[side] + travel
                base = rest["pelvis"] + travel + rest["offset"][side]
                step = R.Vector(shift[side])
                ruled = base + step * rest["torso"]
                other = base + step * (ENGINE_TORSO_CM / 100.0) * clavicle_scale
                signed = (ruled - pivot).length - bone
                outside += 1 if signed > 0 else 0
                inside += 1 if signed <= 0 else 0
                if abs(signed) * 1000 > ruled_worst:
                    ruled_worst = abs(signed) * 1000
                    ruled_row = f"{drill}/{phase['name']} {side}"
                alt = abs((other - pivot).length - bone) * 1000
                if alt > other_worst:
                    other_worst, other_row = alt, f"{drill}/{phase['name']} {side}"
    print(f"{outside + inside} shoulder targets: {outside} outside this rig's "
          f"sphere, {inside} inside it. None lies on it.")
    print(f"worst residual, ruled TORSO divisor:  {ruled_worst:.2f} mm  "
          f"({ruled_row})")
    print(f"worst residual, a CLAVICLE divisor:   {other_worst:.2f} mm  "
          f"({other_row})")
    print()
    print("A clavicle divisor reduces the worst residual and does NOT remove "
          "it, because the")
    print("two clavicles differ in rest ORIENTATION as well as in length. "
          "Neither divisor is")
    print("the whole answer, and this lane proposes neither.")


if __name__ == "__main__":
    main()
