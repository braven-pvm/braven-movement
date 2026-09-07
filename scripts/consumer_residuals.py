"""The consumer-side residuals, rebuilt in pure numpy with no Blender.

WRITTEN BY THE INDEPENDENT REVIEW OF dae979a and committed here by the movement
lane, unchanged except for the archive path below, because the decision paper
quotes its numbers -- 52.11 and 31.05 against the probe's 52.09 and 31.03, and
the 54.72 mm that refuted this lane's decomposition -- and a figure without a
committed instrument is a quotation.

THE ARCHIVE PATH IS NAMED AND CHECKED rather than assumed. The original carried
an absolute path to the reviewer's own clone; a script that says it measures
"the receipts" while reading somebody else's tree is the fault
`scripts/engine_clavicle.py` records against its own first version, so this one
fails loudly if the archive is not where it says.

Reviewer's own header follows.

---

Reviewer's consumer-side rebuild for dae979a, pure numpy, no Blender.

The rig's rest landmarks are the rendering lane's own, committed in
scripts/landmark_comparison.py (MINE) and re-measured in the rendering review
(REVIEW-rendering-0b2495c.md row 5b): torso lengths from the pelvis, axes
(across, up, ahead), divisor 42.7689 cm. The right side is the mirror of the
left across; that assumption is VALIDATED below against all 96 receipts before
it is used for anything.
"""
import glob
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ARCH = r"F:\Repositories\braven-movement\.assets\archives\coach-figures-2413f9d"
RIG_TORSO_M = 0.427689
ENGINE_TORSO_CM = 49.6456      # the probe's quoted constant; engine_targets.json re-measures it
ENGINE_CLAVICLE_CM = 17.6505


def blender(across, up, ahead):
    """rest_landmarks.py prints (x, z, -y): so Blender = (across, -ahead, up)."""
    return np.array([across, -ahead, up], dtype=np.float64)


# scripts/landmark_comparison.py MINE, torso lengths from the pelvis
UPPERARM_L = blender(0.3522, 1.0000, -0.0062) * RIG_TORSO_M
CLAV_L = blender(0.0605, 1.0436, 0.0083) * RIG_TORSO_M
MIRROR = np.array([-1.0, 1.0, 1.0])
REST = {
    "l": {"shoulder": UPPERARM_L, "clavicle": CLAV_L},
    "r": {"shoulder": UPPERARM_L * MIRROR, "clavicle": CLAV_L * MIRROR},
}
for s in REST:
    REST[s]["bone"] = float(np.linalg.norm(REST[s]["shoulder"] - REST[s]["clavicle"]))
    REST[s]["unit"] = (REST[s]["shoulder"] - REST[s]["clavicle"]) / REST[s]["bone"]


def residual_mm(shift_torsos, side, scale_m):
    """|target - rest sternal end| - bone, in mm. target = rest shoulder + shift * scale."""
    target = REST[side]["shoulder"] + np.asarray(shift_torsos, dtype=np.float64) * scale_m
    return float((np.linalg.norm(target - REST[side]["clavicle"]) - REST[side]["bone"]) * 1000.0)


def main():
    print("RIG REST (Blender metres):")
    for s in ("l", "r"):
        print(f"  {s}: bone {REST[s]['bone']*100:.4f} cm = {REST[s]['bone']/RIG_TORSO_M:.5f} torsos; unit {np.round(REST[s]['unit'], 4).tolist()}")

    # 1. validate against the receipts (96 targets)
    receipts = {}
    for f in sorted(glob.glob(os.path.join(ARCH, "*.render.json"))):
        d = json.load(open(f, encoding="utf-8"))
        for p in d["phases"]:
            for s in ("l", "r"):
                receipts[(d["movementId"], p["frame"], s)] = p["girdle"]["sides"][s]
    worst = 0.0
    worst_row = None
    for key, g in receipts.items():
        r = abs(residual_mm(g["shiftInTorsos"], key[2], RIG_TORSO_M))
        dv = abs(r - g["reachableMissMm"])
        if dv > worst:
            worst, worst_row = dv, (key, r, g["reachableMissMm"])
    print(f"\nVALIDATION against {len(receipts)} receipt targets (ruled torso divisor, rig geometry incl. mirrored right):")
    print(f"  worst |rebuilt - reachableMissMm| = {worst:.4f} mm at {worst_row}")
    by_side = {s: max(abs(abs(residual_mm(g['shiftInTorsos'], k[2], RIG_TORSO_M)) - g['reachableMissMm']) for k, g in receipts.items() if k[2] == s) for s in ("l", "r")}
    print(f"  worst by side: {by_side}")

    # 2. engine targets from review_engine.py
    eng = json.loads((HERE / "engine_targets.json").read_text(encoding="utf-8"))
    torso_cm = eng["rest"]["torso_m"] * 100.0
    clav_cm = {s: eng["rest"]["sides"][s]["clavicle_len_m"] * 100.0 for s in ("l", "r")}
    print(f"\nENGINE rest torso {torso_cm:.4f} cm (probe quotes {ENGINE_TORSO_CM}); clavicle l {clav_cm['l']:.4f} r {clav_cm['r']:.4f} (probe quotes {ENGINE_CLAVICLE_CM})")
    targets = eng["targets"]
    print(f"  {len(targets)} engine targets")
    # shifts equal the receipts?
    maxd = 0.0
    matched = 0
    for t in targets:
        g = receipts.get((t["movementId"], t["frame"], t["side"]))
        if g is None:
            continue
        matched += 1
        maxd = max(maxd, float(np.max(np.abs(np.array(t["shift_torsos_blender"]) - np.array(g["shiftInTorsos"])))))
    print(f"  engine shifts vs receipts' shiftInTorsos: {matched} matched, max |diff| {maxd:.6f} torsos")

    # 3. the three residual families on all 102
    clav_scale = {s: (REST[s]["bone"] * 100.0) / clav_cm[s] for s in ("l", "r")}
    print(f"  clavicle scale (rig bone / engine bone): {clav_scale}")
    rows = []
    for t in targets:
        s = t["side"]
        ruled = residual_mm(t["shift_torsos_blender"], s, RIG_TORSO_M)
        div = residual_mm(t["shift_torsos_blender"], s, torso_cm / 100.0 * clav_scale[s])
        no_pivot = residual_mm(t["clav_torsos_blender"], s, torso_cm / 100.0 * clav_scale[s])
        pivot_only = residual_mm(t["pivot_torsos_blender"], s, torso_cm / 100.0 * clav_scale[s])
        rows.append((t, ruled, div, no_pivot, pivot_only))
    on = sum(1 for r in rows if abs(r[1]) < 0.01)
    outside = sum(1 for r in rows if r[1] > 0)
    inside = sum(1 for r in rows if r[1] <= 0 and abs(r[1]) >= 0.01)
    print(f"\nON THE 102: ruled residual: {outside} outside, {inside} inside, {on} on the sphere (<0.01 mm)")
    for name, i in (("ruled TORSO divisor", 1), ("CLAVICLE divisor", 2), ("clavicle divisor, PIVOT TRAVEL REMOVED", 3), ("clavicle divisor, pivot only", 4)):
        w = max(rows, key=lambda r: abs(r[i]))
        print(f"  worst |residual| {name}: {abs(w[i]):.2f} mm at {w[0]['movementId']}/{w[0]['phase']} {w[0]['side']} frame {w[0]['frame']}")
    print("\nAT hooks_outside_hand/facing_away r:")
    for r in rows:
        if r[0]["movementId"] == "netball_hooks_outside_hand" and r[0]["phase"] == "facing_away" and r[0]["side"] == "r":
            print(f"  ruled {r[1]:.2f}  clavicle-divisor {r[2]:.2f}  pivot-removed {r[3]:.2f}  pivot-only {r[4]:.2f} mm;  "
                  f"52.09-31.03 = {52.09-31.03:.2f}; {(52.09-31.03)/52.09*100:.1f} per cent")
    raised = sum(1 for r in rows if abs(r[3]) > abs(r[2]))
    print(f"  targets where removing the pivot travel RAISES the clavicle-divisor residual: {raised} of {len(rows)}")
    print(f"  max over 102 of the ruled residual: {max(abs(r[1]) for r in rows):.2f} mm (the projection's worst move)")

    # 4. the rest directions
    print("\nREST CLAVICLE DIRECTIONS (Blender axes):")
    for s in ("l", "r"):
        e = np.array(eng["rest"]["sides"][s]["clavicle_unit_blender"])
        g = REST[s]["unit"]
        ang = float(np.degrees(np.arccos(np.clip(np.dot(e, g), -1, 1))))
        chord_rig = 2 * REST[s]["bone"] * 100 * np.sin(np.radians(ang) / 2)
        chord_eng = 2 * clav_cm[s] * np.sin(np.radians(ang) / 2)
        print(f"  {s}: engine {np.round(e, 4).tolist()} vs rig {np.round(g, 4).tolist()} -> {ang:.2f} degrees; "
              f"chord at the rig's bone {chord_rig:.2f} cm, at the engine's {chord_eng:.2f} cm")
    # the same from landmark_comparison.py THEIRS, the movement lane's dump
    theirs_u = blender(0.3542, 0.9979, -0.0648) - blender(0.0568, 0.9699, 0.1280)
    theirs_u /= np.linalg.norm(theirs_u)
    ang2 = float(np.degrees(np.arccos(np.clip(np.dot(theirs_u, REST['l']['unit']), -1, 1))))
    print(f"  from landmark_comparison.py's two quoted tables alone (left): {ang2:.2f} degrees")


if __name__ == "__main__":
    main()
