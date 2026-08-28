"""Elbow flexion against time, from the lift, checked against the side view.

Deliverable (d). Three curves, and the point is the disagreements between them.

1. **From the 3D lift.** Across from the front camera, up from the front, ahead
   from the side. The angle at the elbow between the upper arm and the forearm.
2. **From the side view alone, in 2D.** The same joint, measured in one image
   plane with no lift at all. It fails differently: it is blind to any motion
   toward or away from that camera, and it needs no sync whatsoever.
3. **The engine's own curve**, from `reference-curves.json`, phase-indexed.

The LEFT arm only. The side camera sees the athlete in profile, so her right
limbs are occluded: the right wrist has 28 usable readings against the left
wrist's 731. A comparison drawn on 28 readings would be a drawing, not a
measurement.

WHAT THE ENGINE COMPARISON IS AND IS NOT. The filmed drill is a SELF-FED toss:
she throws the ball up and catches her own toss. Every library drill is fed by
a passer, so the ball arrives with a speed and direction she must answer. This
is the same JOINT doing a SIMILAR SHAPE. It is never the same drill, and no
number here grades anything.

    pixi run python video_elbow_curve.py --set 0.1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
OUTPUT = SPIKE_DIR / "poc-output" / "video"
# The library drill closest in ARM SHAPE: a two-hand catch brought in to the
# body. Its ball does something entirely different, which is the whole caveat.
NEAREST_DRILL = "netball_two_hand_snatch_pull_in"


def angle_at(middle, first, second) -> float:
    """Elbow FLEXION at `middle`, in degrees, in THE ENGINE'S convention.

    A straight arm is ZERO, which is `180 - included angle`. This is
    `segment_measures.elbow_flexion_degrees` and it is not a choice: a video
    curve carrying the included angle would be the opposite convention, and
    laying it beside the engine's would compare two different quantities that
    both read in degrees. That is the units-across-a-boundary fault this
    project has removed five times, and the first version of this file had it.
    """
    a = np.asarray(first) - np.asarray(middle)
    b = np.asarray(second) - np.asarray(middle)
    scale = np.linalg.norm(a) * np.linalg.norm(b)
    if scale < 1e-9:
        return float("nan")
    included = float(np.degrees(np.arccos(np.clip(np.dot(a, b) / scale, -1.0, 1.0))))
    return 180.0 - included


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", dest="set_id", default="0.1")
    arguments = parser.parse_args(argv[1:])

    lift = json.loads((OUTPUT / f"lift-3d-{arguments.set_id}.json").read_text(encoding="utf-8"))
    front = json.loads((OUTPUT / f"keypoints-front-{arguments.set_id}.json").read_text(encoding="utf-8"))
    side = json.loads((OUTPUT / f"keypoints-side-{arguments.set_id}.json").read_text(encoding="utf-8"))
    reference = json.loads((OUTPUT / "reference-curves.json").read_text(encoding="utf-8"))

    across = lift["scale"]["frontMetresPerPixel"]
    ahead = lift["scale"]["sideMetresPerPixel"]
    offset = float(side["sync"]["offsetSecondsToReference"])

    side_by_time = {round(f["ptsSeconds"], 6): f for f in side["frames"]}
    side_times = np.array(sorted(side_by_time))

    def side_near(when: float):
        if not len(side_times):
            return None
        found = side_times[np.argmin(np.abs(side_times - when))]
        return side_by_time[found] if abs(found - when) <= 0.017 else None

    limit = front["source"].get("usableToSeconds")
    rows = []
    for record in front["frames"]:
        if not record["detected"] or record["degraded"]:
            continue
        if limit is not None and record["ptsSeconds"] > limit:
            continue
        mate = side_near(record["ptsSeconds"] - offset)
        if mate is None or not mate["detected"] or mate["degraded"]:
            continue
        f = {p["name"]: p for p in record["landmarks"]}
        s = {p["name"]: p for p in mate["landmarks"]}
        joints = ("left_shoulder", "left_elbow", "left_wrist")
        if not all(n in f and n in s for n in joints):
            continue
        if min(f[n]["visibility"] for n in joints) < 0.5:
            continue
        if min(s[n]["visibility"] for n in joints) < 0.5:
            continue

        # Lifted: across and up from the front, ahead from the side.
        lifted = {
            n: (
                f[n]["xPixel"] * across,
                -f[n]["yPixel"] * across,
                s[n]["xPixel"] * ahead,
            )
            for n in joints
        }
        # Side only, in its own image plane. No lift, no sync, blind to depth.
        flat = {n: (s[n]["xPixel"], -s[n]["yPixel"]) for n in joints}

        rows.append({
            "ptsSeconds": round(record["ptsSeconds"], 4),
            "fromLiftDegrees": round(angle_at(*[lifted[n] for n in ("left_elbow", "left_shoulder", "left_wrist")]), 2),
            "fromSideViewDegrees": round(angle_at(*[flat[n] for n in ("left_elbow", "left_shoulder", "left_wrist")]), 2),
        })

    lifted_curve = np.array([r["fromLiftDegrees"] for r in rows])
    flat_curve = np.array([r["fromSideViewDegrees"] for r in rows])
    gap = np.abs(lifted_curve - flat_curve)

    print(f"set {arguments.set_id}, LEFT elbow, {len(rows)} frames\n")
    print("THE TWO VIDEO CURVES, and they are two instruments not one")
    print(f"  from the 3D lift    {lifted_curve.min():6.1f} to {lifted_curve.max():6.1f} deg,"
          f" median {np.median(lifted_curve):6.1f}")
    print(f"  from the side view  {flat_curve.min():6.1f} to {flat_curve.max():6.1f} deg,"
          f" median {np.median(flat_curve):6.1f}")
    print(f"  they differ by      median {np.median(gap):5.1f} deg, "
          f"90th {np.percentile(gap, 90):5.1f}, worst {gap.max():5.1f}")
    print(f"  correlation between them {np.corrcoef(lifted_curve, flat_curve)[0, 1]:+.3f}")

    drill = reference["movements"][NEAREST_DRILL]
    engine = np.array([v for v in drill["curves"]["leftElbowFlexionDegrees"] if v is not None])
    print(f"\nTHE ENGINE, {NEAREST_DRILL[8:]}, for shape only")
    print(f"  {engine.min():6.1f} to {engine.max():6.1f} deg over {len(engine)} frames,"
          f" contact at phase {drill['landmarks']['contactPhase']}")
    print(f"  range {engine.max()-engine.min():.1f} deg against the video's "
          f"{lifted_curve.max()-lifted_curve.min():.1f} from the lift")

    print("\nTHE COMPARISON IS SHAPE ONLY. The filmed drill is a SELF-FED toss and")
    print("every library drill is fed by a passer, so the ball does something")
    print("entirely different. Same joint, similar shape, never the same drill.")

    where = OUTPUT / f"elbow-curve-{arguments.set_id}.json"
    where.write_text(json.dumps({
        "set": arguments.set_id,
        "arm": "left",
        "armNote": (
            "Left only. The side camera sees her in profile so the right limbs "
            "are occluded: 28 usable right-wrist readings against 731 left. A "
            "comparison drawn on 28 readings would be a drawing."
        ),
        "instruments": {
            "fromLift": "across and up from the front camera, ahead from the side; needs the sync",
            "fromSideView": "one image plane, no lift, no sync; blind to motion toward that camera",
        },
        "agreementDegrees": {
            "median": float(np.median(gap)),
            "p90": float(np.percentile(gap, 90)),
            "worst": float(gap.max()),
            "correlation": float(np.corrcoef(lifted_curve, flat_curve)[0, 1]),
        },
        "engineReference": {
            "movement": NEAREST_DRILL,
            "minDegrees": float(engine.min()),
            "maxDegrees": float(engine.max()),
            "contactPhase": drill["landmarks"]["contactPhase"],
            "caveat": (
                "Shape only. The filmed drill is self-fed; every library drill "
                "is fed by a passer. Same joint, similar shape, never the same "
                "drill. Nothing here grades anything."
            ),
        },
        "rows": rows,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
