"""The ENGINE's rest clavicle, measured from the repository rather than quoted.

The coach pack states that the engine's clavicle is 20.4 percent longer
relative to its torso than the MPFB rig's. That figure arrived as a dump in a
message on 2026-09-04. A number that cannot be re-measured from the repository
is a quotation, so this measures it with the engine's own code and its own
skeleton.

    pixi run --frozen python engine_clavicle.py
"""

import sys
from pathlib import Path

# THE REPOSITORY THIS FILE IS IN. It was hard-coded to one worktree, so
# the script that says it measures "from the repository" measured a
# different tree.
SPIKES = Path(__file__).resolve().parents[1] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

import numpy as np  # noqa: E402
from export_blender_job import (  # noqa: E402
    joint_positions,
    load_character,
    rest_torso,
    to_blender,
)
from possession_solve import solve_movement  # noqa: E402


def main() -> None:
    character = load_character()
    index = {n: i for i, n in enumerate(character.skeleton.joint_names)}
    shoulder_like = sorted(
        n for n in index
        if any(k in n for k in ("clav", "uparm", "scap", "shoulder", "root"))
    )
    print("joints that could be a girdle landmark:", shoulder_like)

    # The SAME rest the exporter uses: the solved athlete's identity with
    # no pose, not a default body. The clavicle-to-torso ratio depends on
    # the identity, so a default body would answer a different question.
    result = solve_movement(character, "netball_chest_pass")
    rest = joint_positions(character, result["identity"])
    index = result["index"]
    torso = rest_torso(rest, index)
    print(f"rest torso (engine, metres): {torso:.6f}   "
          f"{torso * 100:.4f} cm")

    for side in ("l", "r"):
        clav_name = f"{side}_clavicle"
        if clav_name not in index:
            print(f"  {clav_name} NOT in the skeleton")
            continue
        clav = to_blender(rest[index[clav_name]])
        uparm = to_blender(rest[index[f"{side}_uparm"]])
        root = to_blender(rest[index["root"]])
        length = float(np.linalg.norm(np.asarray(uparm) - np.asarray(clav)))
        print(f"  {side}: clavicle {length * 100:.4f} cm = "
              f"{length / torso:.5f} torso lengths")
        print(f"     {clav_name} from root, torso lengths: "
              f"{[round(float(v) / torso, 4) for v in (np.asarray(clav) - np.asarray(root))]}")
        print(f"     {side}_uparm  from root, torso lengths: "
              f"{[round(float(v) / torso, 4) for v in (np.asarray(uparm) - np.asarray(root))]}")


if __name__ == "__main__":
    main()
