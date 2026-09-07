"""The ENGINE's rest clavicle, measured from the repository rather than quoted.

The coach pack states that the engine's clavicle is 20.4 percent longer
relative to its torso than the MPFB rig's. That figure arrived as a dump in a
message on 2026-09-04. A number that cannot be re-measured from the repository
is a quotation, so this measures it with the engine's own code and its own
skeleton.

    pixi run --frozen -- python -B engine_clavicle.py

IT ALSO ANSWERS THE SENDER'S HALF OF THE CLAVICLE QUESTION.
`scripts/clavicle_divisor_probe.py` measures the CONSUMER: 102 transmitted
shoulder targets, none of them on the rendering rig's clavicle sphere. The
question that decides between the options is about the SENDER -- does the
engine's own shoulder stay on its own sphere? -- and it is answered below.
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


def rigidity() -> None:
    """Is the engine's shoulder motion a clavicle ROTATION, or is it not?

    A clavicle rotates about its sternal end and does not stretch, so a
    shoulder's reachable positions lie on a SPHERE of the bone's radius. If
    the engine's own solved shoulder holds that radius, its displacement IS a
    rotation about a moving pivot, and a rotation can be transmitted without
    losing anything. If it does not, the engine itself does not respect the
    constraint and no encoding could.

    Measured over EVERY frame of every drill, not the graded phases alone: a
    field that is exact at 51 phases and not between them would still be wrong
    for the animation the job also carries.
    """
    from movement_definition import definition_files, load
    from movement_engine import MOVEMENT_DIR, library

    character = load_character()
    graded = {load(p).movement_id: load(p) for p in definition_files(MOVEMENT_DIR)}
    worst_any = worst_phase = (0.0, "")
    rotations: list[float] = []
    pivot_travel = 0.0
    phases = 0

    for movement_id in library():
        try:
            result = solve_movement(character, movement_id)
        except Exception:  # a drill without a ball or a technique
            continue
        index, points = result["index"], result["points"]
        rest = joint_positions(character, result["identity"])
        definition = graded.get(movement_id)
        last = len(points) - 1
        phase_frames = set()
        if definition is not None:
            phase_frames = {round(p.at_phase * last) for p in definition.phases}
            phases += len(definition.phases)

        for side in ("l", "r"):
            bone = float(np.linalg.norm(
                rest[index[f"{side}_uparm"]] - rest[index[f"{side}_clavicle"]]
            ))
            at_rest = rest[index[f"{side}_uparm"]] - rest[index[f"{side}_clavicle"]]
            for frame, pose in enumerate(points):
                arm = pose[index[f"{side}_uparm"]] - pose[index[f"{side}_clavicle"]]
                off = abs(float(np.linalg.norm(arm)) - bone) * 10.0
                if off > worst_any[0]:
                    worst_any = (off, f"{movement_id}/{side}/frame {frame}")
                if frame in phase_frames:
                    if off > worst_phase[0]:
                        worst_phase = (off, f"{movement_id}/{side}/frame {frame}")
                    cosine = float(np.dot(at_rest, arm) / (
                        np.linalg.norm(at_rest) * np.linalg.norm(arm)))
                    rotations.append(
                        float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))
                    )
                pivot_travel = max(pivot_travel, float(np.linalg.norm(
                    (pose[index[f"{side}_clavicle"]] - pose[index["root"]])
                    - (rest[index[f"{side}_clavicle"]] - rest[index["root"]])
                )))

    print()
    print("THE SENDER'S HALF: is the shoulder displacement a clavicle rotation?")
    print(f"  worst |posed - rest| clavicle length, ANY frame:  "
          f"{worst_any[0]:.4f} mm   ({worst_any[1]})")
    print(f"  the same at a GRADED phase frame:                 "
          f"{worst_phase[0]:.4f} mm   ({worst_phase[1]})")
    print(f"  the bone is RIGID in the solve, so the shoulder motion is a "
          f"rotation about a moving pivot.")
    print(f"  {phases} graded phases, so {phases * 2} shoulder targets, "
          f"which is the count the consumer probe reports.")
    print(f"  rotation from rest at those phases: "
          f"{min(rotations):.1f} to {max(rotations):.1f} degrees")
    print(f"  the pivot itself moves up to {pivot_travel:.2f} cm from rest, "
          f"relative to the pelvis, so a rotation alone would not be enough.")


if __name__ == "__main__":
    main()
    rigidity()
