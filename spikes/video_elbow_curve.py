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

    pixi run python video_elbow_curve.py --pair "front 0.1 + side 0.2"

Every --set refuses: no set's two same-named files are a pair.
Run video_lift_3d.py on the same pair first; this reads its artefact.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from reference_curves import curve_values
from video_keypoints import (PAIRS, frame_offset_of, load_keypoints,
                             pair_slug, refuse_by_set)

SPIKE_DIR = Path(__file__).resolve().parent
OUTPUT = SPIKE_DIR / "poc-output" / "video"
# The library drill closest in ARM SHAPE: a two-hand catch brought in to the
# body. Its ball does something entirely different, which is the whole caveat.
NEAREST_DRILL = "netball_two_hand_snatch_pull_in"


def angle_at(middle, first, second) -> float:
    """Elbow FLEXION at `middle`, in degrees, in THE ENGINE'S convention.

    Returns NaN on a degenerate triangle. A NaN reaching the summary poisons
    the median and the correlation silently, so a caller that cannot tolerate
    one must filter before aggregating. Nothing in this material produces one.

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
    # --set IS KEPT SO ITS REFUSAL IS REACHABLE, and it has NO DEFAULT. It used
    # to default to "0.1", so a call with no argument silently analysed one
    # particular pairing — and that pairing is now known to be wrong.
    parser.add_argument("--set", dest="set_id", default=None)
    parser.add_argument("--pair", dest="pair_key", default=None,
                        help="a key from PAIRS in video_keypoints.py, "
                             "for example 'front 0.1 + side 0.2'")
    arguments = parser.parse_args(argv[1:])

    # THE REACHABLE PASS. Without --pair this script had no working path at
    # all: every set refuses, so the only thing it could do was exit 1, and a
    # consumer that can only refuse proves nothing a syntax error would not.
    if arguments.pair_key:
        pair = PAIRS.get(arguments.pair_key)
        if pair is None:
            raise SystemExit(
                f"no pair named {arguments.pair_key!r}. Known: "
                + ", ".join(repr(k) for k in PAIRS))
        label = arguments.pair_key
        front_name, side_name = pair["referenceFile"], pair["otherFile"]
    elif arguments.set_id:
        label = f"set {arguments.set_id}"
        front_name = f"front {arguments.set_id}.mp4"
        side_name = f"side {arguments.set_id}.mp4"
    else:
        raise SystemExit("give --pair (preferred) or --set")

    # THE SYNC IS CHECKED FIRST, before any file that only exists for a synced
    # set. Loading the lift first made an unsynced set fail with a
    # FileNotFoundError about a derived artifact, which names the symptom and
    # hides the cause: the set has no measured offset, so no lift was ever made.
    # BOTH KEYPOINT FILES ARE LOADED BEFORE THE GUARD, because the guard reads
    # both of them. An earlier arrangement loaded only the side file here and
    # then compared it against `front`, which was loaded two lines LOWER: every
    # call raised UnboundLocalError. It went unseen because the test asserted
    # only that the exit code was not zero, and a crash is not zero either. A
    # refusal test must read the refusal, not merely the failure.
    side = load_keypoints(side_name)
    front = load_keypoints(front_name)
    # THE GUARD IS "ARE THESE TWO FILES THE PAIR", NOT "IS ONE OF THEM
    # MEASURED". A first version of this check asked only whether the side file
    # had a sync, and `side 0.2.mp4` HAS one — it is half of the real pair, with
    # `front 0.1.mp4`. So asking for set 0.2 loaded front 0.2 against side 0.2,
    # passed, and wrote a plausible lift from two files that are not a pair.
    # That is the same fault as the offsets this pack withdraws, one level up.
    if side["sync"].get("pairedWith") != front["source"]["videoFile"]:
        raise SystemExit(refuse_by_set(arguments.set_id or arguments.pair_key))
    # The lift is loaded only after the pairing holds: it exists only for a
    # pair, so a FileNotFoundError here would name the symptom and hide it.
    lift = json.loads(
        (OUTPUT / f"lift-3d-{pair_slug(label)}.json").read_text(encoding="utf-8"))
    reference = json.loads((OUTPUT / "reference-curves.json").read_text(encoding="utf-8"))

    across = lift["scale"]["frontMetresPerPixel"]
    ahead = lift["scale"]["sideMetresPerPixel"]
    # THE MAPPING IS BY FRAME INDEX. `offsetSecondsToReference` is gone: the
    # cameras' frame periods differ by 11 microseconds, so any offset in
    # seconds drifts across the clip, and two such offsets have already been
    # withdrawn from this material.
    # THE CHECK THE SCHEMA TELLS EVERY CONSUMER TO RUN, on integers, and it
    # lives with the writer so that one mutation can fail both consumers.
    frame_offset = frame_offset_of(side["sync"], side["frames"])


    limit = front["source"].get("usableToSeconds")
    side_limit = side["source"].get("usableToSeconds")
    rows = []
    for record in front["frames"]:
        if not record["detected"] or record["degraded"]:
            continue
        if limit is not None and record["ptsSeconds"] > limit:
            continue
        # EXACT, not nearest: with a frame offset the mate is a subscript.
        index = record["frameIndex"] + frame_offset
        mate = (side["frames"][index]
                if 0 <= index < len(side["frames"]) else None)
        if mate is None or not mate["detected"] or mate["degraded"]:
            continue
        if side_limit is not None and mate["ptsSeconds"] > side_limit:
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

        # Lifted: across and up from the FRONT, ahead from the side.
        #
        # UP COMES FROM THE FRONT CAMERA ONLY, AND THAT IS THE POINT. Averaging
        # the two cameras' up looks like an improvement and is not: it folds
        # half the side view's own reading into the 3D, and then this compares
        # that 3D against the side view. Measured, the disagreement falls from
        # 21.2 degrees to 12.8 with the mean and to 3.8 with side-only up — a
        # ladder that tracks how much is shared, and at the bottom rung the
        # remainder is exactly the projection floor. Front-only shares NOTHING
        # with the instrument it is tested against, which is what an
        # independence test requires.
        #
        # If you change this to average, you will halve the reported
        # disagreement and will not have improved anything.
        #
        # Both front pixels are scaled by `across`, the FRONT's metres per
        # pixel, because across and up are both read off the front image. Only
        # `ahead` uses the side's scale. That is correct and it reads like a
        # copy-paste error, so it is written down.
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

    print(f"{label}, LEFT elbow, {len(rows)} frames\n")
    print("THE TWO VIDEO CURVES, and they are two instruments not one")
    print(f"  from the 3D lift    {lifted_curve.min():6.1f} to {lifted_curve.max():6.1f} deg,"
          f" median {np.median(lifted_curve):6.1f}")
    print(f"  from the side view  {flat_curve.min():6.1f} to {flat_curve.max():6.1f} deg,"
          f" median {np.median(flat_curve):6.1f}")
    print(f"  they differ by      median {np.median(gap):5.1f} deg, "
          f"90th {np.percentile(gap, 90):5.1f}, worst {gap.max():5.1f}")
    print(f"  correlation between them {np.corrcoef(lifted_curve, flat_curve)[0, 1]:+.3f}")

    drill = reference["movements"][NEAREST_DRILL]
    engine = curve_values(reference, drill,
                          "leftElbowFlexionDegrees", "degrees")
    print(f"\nTHE ENGINE, {NEAREST_DRILL[8:]}, for shape only")
    print(f"  {engine.min():6.1f} to {engine.max():6.1f} deg over {len(engine)} frames,"
          f" contact at phase {drill['landmarks']['contactPhase']}")
    print(f"  range {engine.max()-engine.min():.1f} deg against the video's "
          f"{lifted_curve.max()-lifted_curve.min():.1f} from the lift")

    print("\nTHE COMPARISON IS SHAPE ONLY. The filmed drill is a SELF-FED toss and")
    print("every library drill is fed by a passer, so the ball does something")
    print("entirely different. Same joint, similar shape, never the same drill.")

    where = OUTPUT / f"elbow-curve-{pair_slug(label)}.json"
    where.write_text(json.dumps({
        "pair": label,
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
