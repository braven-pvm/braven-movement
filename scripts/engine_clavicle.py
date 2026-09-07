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


def geometry() -> None:
    """The sender's figures the decision paper quotes, each with its scope.

    WHAT THIS DOES NOT CLAIM. An earlier version measured the change in the
    engine's clavicle LENGTH over every frame, found 0.0001 mm, and read it as
    proof that the shoulder's motion "is" a rotation. `l_uparm`'s parent IS
    `l_clavicle` in this skeleton, so that distance is fixed by the rig's own
    topology: the reading would be the same for any bone on either rig, and the
    0.0001 mm is float32 noise. It is printed below as a check that the tree is
    what it is said to be, and it decides nothing.

    What survives is structural. Because the shoulder is the clavicle's child,
    only the DIRECTION varies -- and that is an argument about the skeleton,
    not a measurement.
    """
    from movement_definition import definition_files, load
    from movement_engine import MOVEMENT_DIR, library

    character = load_character()
    graded = {load(p).movement_id: load(p) for p in definition_files(MOVEMENT_DIR)}

    def trunk_frame(pose, index):
        """Origin `root`, up `root`->`c_neck`, across from the hip line."""
        up = pose[index["c_neck"]] - pose[index["root"]]
        up = up / np.linalg.norm(up)
        across = pose[index["l_upleg"]] - pose[index["r_upleg"]]
        across = across - np.dot(across, up) * up
        return np.stack([across / np.linalg.norm(across), up,
                         np.cross(up, across / np.linalg.norm(across))])

    def angle(one, two):
        cosine = float(np.dot(one, two)
                       / (np.linalg.norm(one) * np.linalg.norm(two)))
        return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

    print()
    print("PER DRILL. The library maximum of the pivot travel belongs to ONE")
    print("drill, and an earlier paper quoted it as the library's figure.")
    print(f"    {'drill':32s} {'world':>14s} {'trunk frame':>14s} "
          f"{'turn':>6s} {'pivot':>8s} {'frames':>7s}")

    visited = targets = 0
    failed: list[str] = []
    travel_all: list[float] = []
    at_targets: list[float] = []
    for movement_id in sorted(library()):
        try:
            result = solve_movement(character, movement_id)
        except Exception as problem:
            # REPORTED, NOT SKIPPED. A silent skip under a heading saying
            # "every frame of every drill" is a count of what happened to work.
            failed.append(f"{movement_id}: {type(problem).__name__}: {problem}")
            continue
        index, points = result["index"], result["points"]
        rows = result["measurements"]
        rest = joint_positions(character, result["identity"])
        definition = graded.get(movement_id)
        if definition is None:
            failed.append(f"{movement_id}: no graded definition")
            continue
        last = len(points) - 1
        visited += len(points)
        phase_frames = {round(p.at_phase * last) for p in definition.phases}
        rest_basis = trunk_frame(rest, index)

        world, trunk, turns, travel = [], [], [], []
        for phase in definition.phases:
            frame = round(phase.at_phase * last)
            turns.append(abs(float(rows[frame]["trunkTurnDegrees"])))
            posed_basis = trunk_frame(points[frame], index)
            for side in ("l", "r"):
                at_rest = (rest[index[f"{side}_uparm"]]
                           - rest[index[f"{side}_clavicle"]])
                arm = (points[frame][index[f"{side}_uparm"]]
                       - points[frame][index[f"{side}_clavicle"]])
                world.append(angle(at_rest, arm))
                trunk.append(angle(rest_basis @ at_rest, posed_basis @ arm))
                targets += 1
        for side in ("l", "r"):
            for number, pose in enumerate(points):
                distance = float(np.linalg.norm(
                    (pose[index[f"{side}_clavicle"]] - pose[index["root"]])
                    - (rest[index[f"{side}_clavicle"]] - rest[index["root"]])
                ))
                travel.append(distance)
                if number in phase_frames:
                    at_targets.append(distance)
        travel_all += travel
        print(f"    {movement_id.replace('netball_', ''):32s} "
              f"{min(world):5.1f} to {max(world):5.1f} "
              f"{min(trunk):5.1f} to {max(trunk):5.1f} "
              f"{max(turns):6.1f} {max(travel):7.2f} cm {len(points):6d}")

    # TWO POPULATIONS, NAMED. The consumer probe's median is over the 102
    # GRADED TARGETS; this script also sees every frame. The two are close and
    # they are not the same number, so both are printed with their scope.
    every = sorted(travel_all)
    graded_only = sorted(at_targets)
    print()
    print(f"  {visited} frames visited, {targets} graded targets")
    print(f"  pivot travel over the {len(graded_only)} GRADED TARGETS: "
          f"median {graded_only[len(graded_only) // 2]:.2f} cm, "
          f"worst {graded_only[-1]:.2f} cm")
    print(f"  pivot travel over all {len(every)} frame-sides: "
          f"median {every[len(every) // 2]:.2f} cm, worst {every[-1]:.2f} cm")
    print(f"  THE TWO FRAMES ANSWER DIFFERENT QUESTIONS. The world frame "
          f"contains the athlete's")
    print(f"  turn and lean; the trunk frame removes them and so RAISES the "
          f"other drills' maxima.")
    if failed:
        print()
        print("  DRILLS THAT DID NOT REPORT, named rather than skipped:")
        for line in failed:
            print(f"    {line}")


if __name__ == "__main__":
    main()
    geometry()
