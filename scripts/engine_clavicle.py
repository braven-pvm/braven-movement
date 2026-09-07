"""The ENGINE's rest clavicle, measured from the repository rather than quoted.

The coach pack states that the engine's clavicle is 20.4 percent longer
relative to its torso than the MPFB rig's. That figure arrived as a dump in a
message on 2026-09-04. A number that cannot be re-measured from the repository
is a quotation, so this measures it with the engine's own code and its own
skeleton.

    pixi run --frozen -- python -B engine_clavicle.py

IT ALSO PRINTS THE SENDER'S FIGURES THE DECISION PAPER QUOTES.
`scripts/clavicle_divisor_probe.py` measures the CONSUMER: 102 transmitted
shoulder targets, none of them on the rendering rig's clavicle sphere.

AN EARLIER VERSION OF THIS DOCSTRING PROMISED MORE THAN THE CODE DELIVERS. It
said the question was whether the engine's own shoulder stays on its own sphere,
"and it is answered below". It is not a question: `l_uparm`'s parent IS
`l_clavicle`, so the distance is fixed by the rig's topology and would read the
same for any bone on either rig. `geometry()` says so and this docstring no
longer promises otherwise.
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
    print("  THE TWO FRAMES ANSWER DIFFERENT QUESTIONS, and the trunk column "
          "is NOT the lean.")
    print("  It is pinned to the HIP LINE, and the solver yaws the pelvis on "
          "every drill, so the")
    print("  column is the world angle PLUS OR MINUS that yaw. Refer to the "
          "pelvis yaw below.")
    print(f"  90th percentile over the graded targets: "
          f"{graded_only[int(0.9 * len(graded_only))]:.2f} cm; "
          f"{sum(1 for d in graded_only if d > 2.5)} targets exceed 2.5 cm")

    # THE FRAME COUNT AGAINST ITS SOURCE. Printing what was visited says
    # nothing about what was there to visit; a drill that failed to solve would
    # lower both numbers together if only one were printed.
    import json as _json
    expected = 0
    for path in sorted(Path(MOVEMENT_DIR).glob("*.motion.json")):
        expected += int(_json.loads(path.read_text(encoding="utf-8"))["frames"])
    files = len(list(Path(MOVEMENT_DIR).glob("*.motion.json")))
    print(f"  frames visited {visited}; the motion files declare {expected} "
          f"across {files} drills"
          + ("" if visited == expected else "  <-- THEY DISAGREE"))

    if failed:
        print()
        print("  DRILLS THAT DID NOT REPORT, named rather than skipped:")
        for line in failed:
            print(f"    {line}")


def pelvis_yaw() -> None:
    """Is the solved pelvis facing where the drill says?

    FOUND TWICE INDEPENDENTLY on 2026-09-07: by this lane while rebuilding the
    clavicle paper, and by that paper's independent review, which named it as
    the reason a hip-pinned frame moved the numbers. Its `review_hips.py` is
    the review's instrument; this is the movement lane's, and it prints the raw
    joints so nothing is inferred.

    THE MEASURE THIS ENGINE ALREADY HAS IS NOT THIS ONE. `trunkTurnDegrees` is
    `track.turn_at(phase)`, the AUTHORED value, so it reads 0.0 on drills whose
    solved pelvis is yawed about 15 degrees. Nothing else reads the difference.
    """
    from movement_engine import library

    character = load_character()

    def flat_hip_line(pose, index):
        line = pose[index["l_upleg"]] - pose[index["r_upleg"]]
        flat = np.array([line[0], 0.0, line[2]])
        return flat / np.linalg.norm(flat)

    print()
    print("THE SOLVED PELVIS YAW, against the AUTHORED turn beside it.")
    print(f"    {'drill':32s} {'pelvis yaw':>18s} {'authored':>9s}")
    for movement_id in sorted(library()):
        try:
            result = solve_movement(character, movement_id)
        except Exception as problem:
            print(f"    {movement_id:32s} DID NOT SOLVE: "
                  f"{type(problem).__name__}")
            continue
        index, points = result["index"], result["points"]
        rest = joint_positions(character, result["identity"])
        at_rest = flat_hip_line(rest, index)
        yaws = []
        for pose in points:
            here = flat_hip_line(pose, index)
            yaws.append(float(np.degrees(np.arctan2(
                float(np.cross(at_rest, here)[1]), float(np.dot(at_rest, here))
            ))))
        authored = max(
            abs(float(row["trunkTurnDegrees"])) for row in result["measurements"]
        )
        print(f"    {movement_id.replace('netball_', ''):32s} "
              f"{min(yaws):8.2f} to {max(yaws):6.2f} {authored:9.1f}")

    # THE RAW JOINTS ON ONE SQUARE DRILL, so the yaw is read and not inferred.
    result = solve_movement(character, "netball_chest_pass")
    index, points = result["index"], result["points"]
    rest = joint_positions(character, result["identity"])
    root = points[0][index["root"]]
    print()
    print("    netball_chest_pass frame 0, from the root, in centimetres:")
    for label, pose, origin in (
        ("rest ", rest, rest[index["root"]]), ("posed", points[0], root)
    ):
        left = pose[index["l_upleg"]] - origin
        right = pose[index["r_upleg"]] - origin
        print(f"      {label} l_upleg {np.round(left, 3)}  "
              f"r_upleg {np.round(right, 3)}")
    for side in ("l", "r"):
        foot = points[0][index[f"{side}_foot"]] - root
        arm = points[0][index[f"{side}_uparm"]] - root
        print(f"      {side}_foot {np.round(foot, 2)}   "
              f"{side}_uparm {np.round(arm, 2)}")
    print("    The feet and the shoulders are symmetric; the hip line is not.")


if __name__ == "__main__":
    main()
    geometry()
    pelvis_yaw()
