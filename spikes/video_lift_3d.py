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

THE 150 ms SYNC THIS PARAGRAPH ASSUMED IS WITHDRAWN (2026-09-07). The file
names are wrong: `front 0.1.mp4` pairs with `side 0.2.mp4` at a constant FRAME
offset of -5, and the remaining two files have no established partner. A lift
runs only for a pair whose sync block carries a frame offset.

AND THE RESIDUAL IS NOT DOMINATED BY THE SYNC, which this paragraph also used to
say. Sweeping the offset from -5.0 to +3.0 s moves the median residual only 14.8
to 16.0 mm, so it never measured sync quality and cannot bound it. What it does
measure is not established.

    pixi run python video_lift_3d.py --pair "front 0.1 + side 0.2"

Every --set refuses: no set's two same-named files are a pair.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from video_keypoints import (PAIRS, frame_offset_of, load_keypoints,
                             pair_slug, refuse_by_set)

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
    return load_keypoints(f"{view} {set_id}.mp4")


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
    # --set IS KEPT SO THE REFUSAL IS REACHABLE. No set's two same-named files
    # are a pair, so every --set now refuses and names the real pairing; the
    # argument exists to tell a caller that rather than to fail obscurely.
    parser.add_argument("--set", dest="set_id", default=None)
    parser.add_argument("--pair", dest="pair_key", default=None,
                        help="a key from PAIRS in video_keypoints.py, "
                             "for example 'front 0.1 + side 0.2'")
    arguments = parser.parse_args(argv[1:])

    if arguments.pair_key:
        pair = PAIRS.get(arguments.pair_key)
        if pair is None:
            raise SystemExit(
                f"no pair named {arguments.pair_key!r}. Known: "
                + ", ".join(repr(k) for k in PAIRS))
        label = arguments.pair_key
        front = load_keypoints(pair["referenceFile"])
        side = load_keypoints(pair["otherFile"])
    elif arguments.set_id:
        label = f"set {arguments.set_id}"
        front = load("front", arguments.set_id)
        side = load("side", arguments.set_id)
    else:
        raise SystemExit("give --pair (preferred) or --set")
    # THE GUARD IS "ARE THESE TWO FILES THE PAIR", NOT "IS ONE OF THEM
    # MEASURED". A first version of this check asked only whether the side file
    # had a sync, and `side 0.2.mp4` HAS one — it is half of the real pair, with
    # `front 0.1.mp4`. So asking for set 0.2 loaded front 0.2 against side 0.2,
    # passed, and wrote a plausible lift from two files that are not a pair.
    # That is the same fault as the offsets this pack withdraws, one level up.
    if side["sync"].get("pairedWith") != front["source"]["videoFile"]:
        raise SystemExit(refuse_by_set(arguments.set_id or arguments.pair_key))

    # THE MAPPING IS BY FRAME INDEX. `offsetSecondsToReference` is gone: the two
    # cameras' frame periods differ by 11 microseconds, so any offset in seconds
    # drifts across the clip and two such offsets have already been withdrawn
    # from this material. The index arithmetic cannot drift.
    # THE CHECK THE SCHEMA TELLS EVERY CONSUMER TO RUN, on integers, and it
    # lives with the writer so that one mutation can fail both consumers.
    frame_offset = frame_offset_of(side["sync"], side["frames"])

    front_limit = front["source"].get("usableToSeconds")
    side_limit = side["source"].get("usableToSeconds")

    # ---- scale, measured on settled frames only -------------------------
    widths, torso_front, torso_side = [], [], []
    pairs = []
    for record in front["frames"]:
        if not usable(record, front_limit):
            continue
        # EXACT, not nearest. With a frame offset the mate is a subscript,
        # so no frame is paired with a neighbour because a time landed between
        # two of them.
        index = record["frameIndex"] + frame_offset
        mate = (side["frames"][index]
                if 0 <= index < len(side["frames"]) else None)
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

    print(f"{label}: {len(pairs)} usable frame pairs\n")
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
                # THE FRAME INDEX, so a consumer can re-do the pairing exactly.
                # Without it a reader has only a time, and a time forces a
                # nearest-match with a tolerance, which is what the frame
                # mapping exists to remove. `scripts/compare_lift_against_view.py`
                # reads this and the sync's frame offset, and subscripts.
                "frameIndex": record["frameIndex"],
                "sideFrameIndex": mate["frameIndex"],
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
    where = OUTPUT / f"lift-3d-{pair_slug(label)}.json"
    where.write_text(json.dumps({
        "pair": label,
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
            "frameOffsetToReference": frame_offset,
            "pairedWith": side["sync"]["pairedWith"],
            "uncertaintySeconds": side["sync"]["offsetUncertaintySeconds"],
            "note": ("THE RESIDUAL BELOW IS NOT DOMINATED BY THE SYNC, which an "
                     "earlier version of this line claimed. Sweeping the offset "
                     "across eight seconds moved the MEDIAN by 1.2 mm. What the "
                     "sync moves is the TAIL: on the mislabelled pairing the "
                     "mean was 49.8 mm and the worst 535.7; on the real pair "
                     "they are 29.4 and 209.2. The median rose, from 15.0 to "
                     "20.0, because it was never measuring the pairing."),
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
