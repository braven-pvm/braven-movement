"""Lift two camera views into 3D, and measure how far the assumptions hold.

There is no calibration board in this material, so this is NOT triangulation.
It is an assumption stated plainly and then tested:

    the two cameras are 90 degrees apart and roughly level, so the front view
    reads ACROSS and UP, and the side view reads AHEAD and UP.

Which means UP is measured TWICE, once by each camera, and the two answers are
independent. Their disagreement is the residual, and it is the whole point of
this file. A lift with no way to be wrong tells you nothing.

Scale, from the athlete's own measurements rather than a guess
--------------------------------------------------------------

Marius supplied height 1.77 m, wingspan 1.82 m and one-arm reach 0.77 m. Those
cross-check: 2 x 0.77 leaves 0.28 m across the shoulders inside the 1.82
wingspan, which is ordinary. So SHOULDER WIDTH 0.28 m is a measured quantity,
not an anthropometric table, and it is visible in the front view every frame.

The side view sees her in profile, where shoulder width is nearly zero and
useless. Its scale comes instead from requiring that the TORSO — shoulder
midpoint to hip midpoint — is the same length in metres in both views. That
needs no anthropometry at all: it is one length, seen twice.

What this cannot do
-------------------

The sync is good to about 150 ms, so a hand moving at 2 m/s is displaced about
30 cm between the views. The lift therefore certifies that the pipeline runs.
It yields usable numbers only where the athlete is nearly still, and in fast
phases it is illustrative and never a measurement. The residual reported here
is dominated by that, not by the camera geometry.

    pixi run python video_lift_3d.py --set 0.1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
OUTPUT = SPIKE_DIR / "poc-output" / "video"

# Derived from Marius's own numbers: wingspan - 2 x one-arm reach.
SHOULDER_WIDTH_METRES = 1.82 - 2.0 * 0.77
# Landmarks whose UP reading both cameras can see. The residual is measured on
# these, because a landmark only one camera can see cannot disagree with itself.
CHECKED = (
    "left_shoulder", "right_shoulder", "left_hip", "right_hip",
    "left_elbow", "right_elbow", "left_wrist", "right_wrist",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)
# Below this, a landmark is a guess rather than a reading.
VISIBLE_ENOUGH = 0.5


def load(view: str, set_id: str) -> dict:
    path = OUTPUT / f"keypoints-{view}-{set_id}.json"
    if not path.exists():
        raise SystemExit(f"{path} is missing; run video_keypoints.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def by_name(record: dict) -> dict:
    return {p["name"]: p for p in record.get("landmarks", [])}


def usable(record: dict, limit: float | None) -> bool:
    if not record["detected"] or record["degraded"]:
        return False
    return limit is None or record["ptsSeconds"] <= limit


def nearest(records: list[dict], when: float) -> dict | None:
    """The record closest in time. Never an index arithmetic shortcut."""
    best, gap = None, 1e9
    for record in records:
        difference = abs(record["ptsSeconds"] - when)
        if difference < gap:
            best, gap = record, difference
    # Half a frame at 30 fps. Further than that is not the same moment.
    return best if gap <= 0.017 else None


def span(points: dict, first: str, second: str, axis: str) -> float | None:
    a, b = points.get(first), points.get(second)
    if not a or not b:
        return None
    if min(a["visibility"], b["visibility"]) < VISIBLE_ENOUGH:
        return None
    return abs(a[axis] - b[axis])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", dest="set_id", default="0.1")
    arguments = parser.parse_args(argv[1:])

    front = load("front", arguments.set_id)
    side = load("side", arguments.set_id)
    if not side["sync"].get("measured"):
        raise SystemExit(
            f"set {arguments.set_id} has no measured sync offset, so its two "
            "views cannot be placed on one clock. Refer to the sync block."
        )
    offset = float(side["sync"]["offsetSecondsToReference"])
    # The assertion the schema tells every consumer to run.
    worked = side["sync"]["worked"]
    assert abs(worked["thisViewSeconds"] + offset - worked["referenceViewSeconds"]) < 1e-6, (
        "the sync block's own worked example does not hold; the sign is wrong"
    )

    front_limit = front["source"].get("usableToSeconds")
    side_limit = side["source"].get("usableToSeconds")

    # ---- scale, measured on settled frames only -------------------------
    widths, torso_front, torso_side = [], [], []
    pairs = []
    for record in front["frames"]:
        if not usable(record, front_limit):
            continue
        mate = nearest(side["frames"], record["ptsSeconds"] - offset)
        if mate is None or not usable(mate, side_limit):
            continue
        pairs.append((record, mate))
        f, s = by_name(record), by_name(mate)
        width = span(f, "left_shoulder", "right_shoulder", "xPixel")
        if width:
            widths.append(width)
        for points, into in ((f, torso_front), (s, torso_side)):
            top = [points.get(n) for n in ("left_shoulder", "right_shoulder")]
            low = [points.get(n) for n in ("left_hip", "right_hip")]
            if all(top) and all(low) and min(p["visibility"] for p in top + low) >= VISIBLE_ENOUGH:
                into.append(
                    abs(np.mean([p["yPixel"] for p in top])
                        - np.mean([p["yPixel"] for p in low]))
                )

    if not widths or not torso_front or not torso_side:
        raise SystemExit("not enough visible frames to fix a scale")

    front_metres_per_pixel = SHOULDER_WIDTH_METRES / float(np.median(widths))
    torso_metres = float(np.median(torso_front)) * front_metres_per_pixel
    side_metres_per_pixel = torso_metres / float(np.median(torso_side))

    print(f"set {arguments.set_id}: {len(pairs)} usable frame pairs\n")
    print("SCALE, from the athlete's own measurements")
    print(f"  shoulder width      {SHOULDER_WIDTH_METRES:.3f} m "
          f"(wingspan 1.82 minus twice the 0.77 reach)")
    print(f"  front               {front_metres_per_pixel*1000:.4f} mm per pixel "
          f"(median shoulder span {np.median(widths):.1f} px)")
    print(f"  torso, shoulder to hip  {torso_metres:.3f} m — one length, seen twice")
    print(f"  side                {side_metres_per_pixel*1000:.4f} mm per pixel "
          f"(median torso {np.median(torso_side):.1f} px)")

    # ---- the residual: UP, measured twice --------------------------------
    rows = []
    for record, mate in pairs:
        f, s = by_name(record), by_name(mate)
        # Each view's own vertical origin is its hip midpoint, so the residual
        # measures SHAPE disagreement rather than an unknown camera height.
        f_hip = [f.get(n) for n in ("left_hip", "right_hip")]
        s_hip = [s.get(n) for n in ("left_hip", "right_hip")]
        if not (all(f_hip) and all(s_hip)):
            continue
        f_zero = float(np.mean([p["yPixel"] for p in f_hip]))
        s_zero = float(np.mean([p["yPixel"] for p in s_hip]))
        for name in CHECKED:
            a, b = f.get(name), s.get(name)
            if not a or not b:
                continue
            if min(a["visibility"], b["visibility"]) < VISIBLE_ENOUGH:
                continue
            up_front = -(a["yPixel"] - f_zero) * front_metres_per_pixel
            up_side = -(b["yPixel"] - s_zero) * side_metres_per_pixel
            rows.append({
                "ptsSeconds": record["ptsSeconds"],
                "name": name,
                "upFrontMetres": round(up_front, 4),
                "upSideMetres": round(up_side, 4),
                "residualMetres": round(up_front - up_side, 4),
                "acrossMetres": round((a["xPixel"] - float(np.mean([p["xPixel"] for p in f_hip])))
                                      * front_metres_per_pixel, 4),
                "aheadMetres": round((b["xPixel"] - float(np.mean([p["xPixel"] for p in s_hip])))
                                     * side_metres_per_pixel, 4),
            })

    residual = np.array([abs(r["residualMetres"]) for r in rows])
    print(f"\nRESIDUAL: UP measured by the front camera against UP measured by the side")
    print(f"  {len(rows)} landmark readings on {len(pairs)} frame pairs")
    print(f"  median {np.median(residual)*1000:6.1f} mm")
    print(f"  mean   {residual.mean()*1000:6.1f} mm")
    print(f"  90th   {np.percentile(residual, 90)*1000:6.1f} mm")
    print(f"  worst  {residual.max()*1000:6.1f} mm")

    print(f"\n{'landmark':16s} {'readings':>8s} {'median mm':>10s} {'90th mm':>9s}")
    for name in CHECKED:
        mine = np.array([abs(r["residualMetres"]) for r in rows if r["name"] == name])
        if len(mine):
            note = "  <- the vertical origin, so nearly circular" if name.endswith("_hip") else ""
            print(f"{name:16s} {len(mine):8d} {np.median(mine)*1000:10.1f} "
                  f"{np.percentile(mine, 90)*1000:9.1f}{note}")
    print("\n  The hips are the vertical origin of BOTH views, so their residual is")
    print("  nearly circular and is NOT a measure of accuracy. Read the shoulders")
    print("  and the knees for that. Refer to VIDEO_SPIKE_NOTES.md for the speed")
    print("  banding, which tests whether this residual is sync-dominated.")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    where = OUTPUT / f"lift-3d-{arguments.set_id}.json"
    where.write_text(json.dumps({
        "set": arguments.set_id,
        "method": (
            "NOT triangulation. The two cameras are assumed 90 degrees apart "
            "and roughly level, so the front view reads across and up and the "
            "side view reads ahead and up. Up is therefore measured twice and "
            "the two answers are independent; their disagreement is the "
            "residual below."
        ),
        "scale": {
            "shoulderWidthMetres": SHOULDER_WIDTH_METRES,
            "shoulderWidthSource": "wingspan 1.82 minus twice the one-arm reach 0.77, both supplied by Marius 2026-08-28",
            "frontMetresPerPixel": front_metres_per_pixel,
            "sideMetresPerPixel": side_metres_per_pixel,
            "torsoMetres": torso_metres,
            "torsoNote": "shoulder midpoint to hip midpoint; one length seen by both cameras, which is what ties the side view's scale to the front's without anthropometry",
        },
        "syncApplied": {
            "offsetSecondsToReference": offset,
            "uncertaintySeconds": side["sync"]["offsetUncertaintySeconds"],
            "note": "The residual below is dominated by this, not by camera geometry.",
        },
        "residualMetres": {
            "readings": len(rows),
            "framePairs": len(pairs),
            "median": float(np.median(residual)),
            "mean": float(residual.mean()),
            "p90": float(np.percentile(residual, 90)),
            "worst": float(residual.max()),
        },
        "rows": rows,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
