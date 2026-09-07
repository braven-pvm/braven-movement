"""Reviewer's engine-side instrument for dae979a. Written independently of
scripts/engine_clavicle.py; reads the engine's own values (the exporter's
shift formula, the solver's trunkTurnDegrees) rather than rebuilding them.

    cd spikes
    pixi run --frozen -- python -B ../scripts/engine_targets.py
    pixi run --frozen -- python -B ../scripts/consumer_residuals.py

WRITTEN BY THE INDEPENDENT REVIEW OF dae979a and committed here by the
movement lane. It is deliberately a SECOND instrument beside
`scripts/engine_clavicle.py` and was written without reference to it: it
reads the engine's own values -- the exporter's shift formula, the solver's
`trunkTurnDegrees` -- rather than rebuilding them, and the two agreeing is
worth more than either alone.

THE SPIKES PATH IS DERIVED, NOT HARDCODED, AND THAT MATTERS MORE THAN IT
LOOKS. The original pointed at the reviewer's own clone. A first attempt to
fix it here FAILED SILENTLY -- the replacement string did not match, nothing
asserted, and the pipeline then imported the engine from that other tree and
wrote its results into this one. The numbers looked right, which is the
danger. It is derived from this file's location now, and the edit that set
it asserted before it wrote.
"""
import json
import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[1] / "spikes"
sys.path.insert(0, str(SPIKES))
OUT = Path(__file__).resolve().parent

import numpy as np  # noqa: E402
from export_blender_job import joint_positions, load_character, rest_torso, to_blender  # noqa: E402
from possession_solve import solve_movement  # noqa: E402
from movement_definition import definition_files, load  # noqa: E402
from movement_engine import MOVEMENT_DIR, library  # noqa: E402


def trunk_frame(pose, index):
    up = pose[index["c_neck"]] - pose[index["root"]]
    up = up / np.linalg.norm(up)
    across = pose[index["l_upleg"]] - pose[index["r_upleg"]]
    across = across - np.dot(across, up) * up
    across = across / np.linalg.norm(across)
    return np.stack([across, up, np.cross(up, across)])


def angle(one, two):
    c = float(np.dot(one, two) / (np.linalg.norm(one) * np.linalg.norm(two)))
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def yaw_between(a, b):
    """Angle between two vectors' projections on the MHR horizontal plane (x, z)."""
    a2 = np.array([a[0], a[2]]); b2 = np.array([b[0], b[2]])
    c = float(np.dot(a2, b2) / (np.linalg.norm(a2) * np.linalg.norm(b2)))
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def basis_rotation_degrees(r_from, r_to):
    R = r_to @ r_from.T
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))))


def main():
    motion_frames = {}
    for p in sorted((SPIKES / "movements").glob("*.motion.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        motion_frames[d["movementId"]] = int(d["frames"])

    character = load_character()
    # THE TOPOLOGY CLAIM: is l_uparm a child of l_clavicle?
    names = list(character.skeleton.joint_names)
    parents = None
    for attr in ("joint_parents", "parents", "joint_parent"):
        if hasattr(character.skeleton, attr):
            parents = list(getattr(character.skeleton, attr))
            break
    if parents is None:
        print("skeleton parent table: attribute not found; dir:", [a for a in dir(character.skeleton) if not a.startswith("_")])
    else:
        for j in ("l_uparm", "r_uparm", "l_clavicle", "r_clavicle"):
            p = parents[names.index(j)]
            print(f"  parent of {j}: {names[p] if p >= 0 else None}")
    graded = {load(p).movement_id: load(p) for p in definition_files(MOVEMENT_DIR)}
    drills = sorted(library())
    print(f"library: {len(drills)} drills; motion files: {len(motion_frames)}; "
          f"definitions: {len(graded)}")

    rest_geometry = None
    targets = []
    per_drill = {}
    all_travel = []
    failed = []
    visited = 0
    for mid in drills:
        try:
            result = solve_movement(character, mid)
        except Exception as problem:  # noqa: BLE001
            failed.append(f"{mid}: {type(problem).__name__}: {problem}")
            continue
        index, points, rows = result["index"], result["points"], result["measurements"]
        rest = joint_positions(character, result["identity"])
        torso = rest_torso(rest, index)
        definition = graded[mid]
        last = len(points) - 1
        assert len(points) == motion_frames[mid], (mid, len(points), motion_frames[mid])
        visited += len(points)
        if rest_geometry is None:
            rest_geometry = {"torso_m": float(torso), "sides": {}}
            for s in ("l", "r"):
                clav = to_blender(rest[index[f"{s}_clavicle"]]); up = to_blender(rest[index[f"{s}_uparm"]])
                root = to_blender(rest[index["root"]])
                v = up - clav
                rest_geometry["sides"][s] = {
                    "clavicle_vec_blender_m": v.tolist(),
                    "clavicle_len_m": float(np.linalg.norm(v)),
                    "clavicle_unit_blender": (v / np.linalg.norm(v)).tolist(),
                    "clavicle_from_root_torsos_blender": ((clav - root) / torso).tolist(),
                    "uparm_from_root_torsos_blender": ((up - root) / torso).tolist(),
                }
        rest_basis = trunk_frame(rest, index)
        rest_hip = rest[index["l_upleg"]] - rest[index["r_upleg"]]
        rest_shl = rest[index["l_uparm"]] - rest[index["r_uparm"]]

        travel_drill = []
        for s in ("l", "r"):
            for n, pose in enumerate(points):
                d = float(np.linalg.norm((pose[index[f"{s}_clavicle"]] - pose[index["root"]])
                                         - (rest[index[f"{s}_clavicle"]] - rest[index["root"]])))
                travel_drill.append(d)
        all_travel += travel_drill
        per_drill[mid] = {"frames": len(points), "pivot_max_cm": max(travel_drill),
                          "world": [], "trunk": [], "turns": [], "hip_yaw": [], "shoulder_yaw": []}

        for phase in definition.phases:
            frame = round(phase.at_phase * last)
            pose = points[frame]
            posed_basis = trunk_frame(pose, index)
            turn = float(rows[frame]["trunkTurnDegrees"])
            lean = rows[frame].get("trunkLeanDegrees")
            hip_yaw = yaw_between(rest_hip, pose[index["l_upleg"]] - pose[index["r_upleg"]])
            shl_yaw = yaw_between(rest_shl, pose[index["l_uparm"]] - pose[index["r_uparm"]])
            basis_rot = basis_rotation_degrees(rest_basis, posed_basis)
            per_drill[mid]["turns"].append(abs(turn)); per_drill[mid]["hip_yaw"].append(hip_yaw)
            per_drill[mid]["shoulder_yaw"].append(shl_yaw)
            for s in ("l", "r"):
                at_rest = rest[index[f"{s}_uparm"]] - rest[index[f"{s}_clavicle"]]
                arm = pose[index[f"{s}_uparm"]] - pose[index[f"{s}_clavicle"]]
                w = angle(at_rest, arm)
                t = angle(rest_basis @ at_rest, posed_basis @ arm)
                # THE EXPORTER'S OWN FORMULA (export_blender_job.py:403-416)
                shift = ((to_blender(pose[index[f"{s}_uparm"]]) - to_blender(pose[index["root"]]))
                         - (to_blender(rest[index[f"{s}_uparm"]]) - to_blender(rest[index["root"]]))) / torso
                pivot = ((to_blender(pose[index[f"{s}_clavicle"]]) - to_blender(pose[index["root"]]))
                         - (to_blender(rest[index[f"{s}_clavicle"]]) - to_blender(rest[index["root"]]))) / torso
                clav = ((to_blender(pose[index[f"{s}_uparm"]]) - to_blender(pose[index[f"{s}_clavicle"]]))
                        - (to_blender(rest[index[f"{s}_uparm"]]) - to_blender(rest[index[f"{s}_clavicle"]]))) / torso
                assert np.allclose(shift, pivot + clav, atol=1e-12)
                pivot_cm = float(np.linalg.norm(pivot) * torso * 100.0)
                per_drill[mid]["world"].append(w); per_drill[mid]["trunk"].append(t)
                targets.append({
                    "movementId": mid, "phase": phase.name, "frame": frame, "side": s,
                    "world_deg": w, "trunk_deg": t, "trunkTurnDegrees": turn,
                    "trunkLeanDegrees": lean, "hip_yaw_deg": hip_yaw, "shoulder_yaw_deg": shl_yaw,
                    "trunk_basis_rotation_deg": basis_rot,
                    "shift_torsos_blender": [round(float(v), 6) for v in shift],
                    "pivot_torsos_blender": pivot.tolist(), "clav_torsos_blender": clav.tolist(),
                    "pivot_travel_cm": pivot_cm,
                    "clav_len_change_mm": float(abs(np.linalg.norm(arm) - np.linalg.norm(at_rest)) * 10.0),
                })

    print(f"\nframes visited {visited}  (motion files sum {sum(motion_frames.values())})  "
          f"graded targets {len(targets)}  frame-sides {len(all_travel)}")
    if failed:
        print("FAILED:", *failed, sep="\n  ")

    print("\nREST GEOMETRY (engine, Blender axes)")
    print(f"  rest torso {rest_geometry['torso_m']*100:.4f} cm")
    for s, g in rest_geometry["sides"].items():
        print(f"  {s}: clavicle {g['clavicle_len_m']*100:.4f} cm = {g['clavicle_len_m']/rest_geometry['torso_m']:.5f} torsos; "
              f"unit {np.round(g['clavicle_unit_blender'], 4).tolist()}; "
              f"clav from root {np.round(g['clavicle_from_root_torsos_blender'], 4).tolist()}; "
              f"uparm from root {np.round(g['uparm_from_root_torsos_blender'], 4).tolist()}")

    print("\nPER DRILL")
    print(f"  {'drill':40s} {'frames':>6s} {'world':>14s} {'trunk':>14s} {'turn':>6s} {'hipyaw':>7s} {'shlyaw':>7s} {'pivot':>6s}")
    for mid, d in per_drill.items():
        print(f"  {mid:40s} {d['frames']:6d} {min(d['world']):5.1f} to {max(d['world']):5.1f} "
              f"{min(d['trunk']):5.1f} to {max(d['trunk']):5.1f} {max(d['turns']):6.1f} "
              f"{max(d['hip_yaw']):7.1f} {max(d['shoulder_yaw']):7.1f} {d['pivot_max_cm']:6.2f}")
    others = [t for t in targets if t["movementId"] != "netball_hooks_outside_hand"]
    hooks = [t for t in targets if t["movementId"] == "netball_hooks_outside_hand"]
    print(f"\n  hooks_outside_hand: world {min(t['world_deg'] for t in hooks):.1f} to {max(t['world_deg'] for t in hooks):.1f}; "
          f"trunk {min(t['trunk_deg'] for t in hooks):.1f} to {max(t['trunk_deg'] for t in hooks):.1f}")
    print(f"  every other drill:  world {min(t['world_deg'] for t in others):.1f} to {max(t['world_deg'] for t in others):.1f}; "
          f"trunk {min(t['trunk_deg'] for t in others):.1f} to {max(t['trunk_deg'] for t in others):.1f}")
    print(f"  library: world max {max(t['world_deg'] for t in targets):.1f}; trunk max {max(t['trunk_deg'] for t in targets):.1f}")
    print(f"  trunkTurnDegrees on every non-hooks target: {sorted({t['trunkTurnDegrees'] for t in others})}")
    print(f"  trunkTurnDegrees on hooks targets by phase: {[(t['phase'], t['trunkTurnDegrees']) for t in hooks if t['side']=='l']}")

    print("\nTHE TARGET hooks_outside_hand/facing_away r frame 0")
    for t in targets:
        if t["movementId"] == "netball_hooks_outside_hand" and t["phase"] == "facing_away":
            print(f"  side {t['side']}: world {t['world_deg']:.2f}, trunk {t['trunk_deg']:.2f}, turn {t['trunkTurnDegrees']}, "
                  f"hip yaw {t['hip_yaw_deg']:.2f}, shoulder yaw {t['shoulder_yaw_deg']:.2f}, basis rot {t['trunk_basis_rotation_deg']:.2f}, "
                  f"pivot {t['pivot_travel_cm']:.2f} cm, shift {t['shift_torsos_blender']}")

    print("\nHOOKS per phase (l side): hip yaw / shoulder yaw / authored turn / basis rotation")
    for t in hooks:
        if t["side"] == "l":
            print(f"  {t['phase']:12s} frame {t['frame']:3d}: hip {t['hip_yaw_deg']:5.1f}  shoulders {t['shoulder_yaw_deg']:5.1f}  "
                  f"turn {t['trunkTurnDegrees']:5.1f}  basis {t['trunk_basis_rotation_deg']:5.1f}")

    worst_t = max(targets, key=lambda t: t["trunk_deg"])
    worst_w = max(targets, key=lambda t: t["world_deg"])
    print("\nWORST TRUNK-FRAME TARGET:", worst_t["movementId"], worst_t["phase"], worst_t["side"], f"frame {worst_t['frame']}")
    print(f"  trunk {worst_t['trunk_deg']:.2f}  world {worst_t['world_deg']:.2f}  basis rotation {worst_t['trunk_basis_rotation_deg']:.2f}  "
          f"lean {worst_t['trunkLeanDegrees']}  turn {worst_t['trunkTurnDegrees']}  hip yaw {worst_t['hip_yaw_deg']:.2f}")
    print("WORST WORLD-FRAME TARGET:", worst_w["movementId"], worst_w["phase"], worst_w["side"], f"frame {worst_w['frame']}",
          f"world {worst_w['world_deg']:.2f} trunk {worst_w['trunk_deg']:.2f}")
    # the mechanism claim: trunk-frame > world-frame where the trunk itself rotates
    raised = [t for t in others if t["trunk_deg"] > t["world_deg"]]
    print(f"  non-hooks targets where trunk-frame angle > world-frame angle: {len(raised)} of {len(others)}")

    grd = sorted(t["pivot_travel_cm"] for t in targets)
    every = sorted(all_travel)
    print("\nPIVOT TRAVEL")
    print(f"  over the {len(grd)} graded targets: median(index n//2) {grd[len(grd)//2]:.2f} cm, "
          f"np.median {np.median(grd):.2f}, 90th pct {np.percentile(grd, 90):.2f}, worst {grd[-1]:.2f}; "
          f">2.5 cm: {sum(1 for v in grd if v > 2.5)} "
          f"({sorted({t['movementId'] for t in targets if t['pivot_travel_cm'] > 2.5})})")
    print(f"  over all {len(every)} frame-sides: median(index n//2) {every[len(every)//2]:.2f} cm, np.median {np.median(every):.2f}, worst {every[-1]:.2f}")
    print(f"  worst clavicle length change at a graded target: {max(t['clav_len_change_mm'] for t in targets):.4f} mm")

    (OUT / "engine_targets.json").write_text(json.dumps({"rest": rest_geometry, "targets": targets, "per_drill_pivot_max_cm": {k: v["pivot_max_cm"] for k, v in per_drill.items()}}, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT / 'engine_targets.json'}")


if __name__ == "__main__":
    main()
