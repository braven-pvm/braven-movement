"""Where the disagreement between the lift and the side view comes from.

RE-TITLED 2026-09-07. This said "the 21 degrees", and 21 was measured on two
files that are not a pair. On the real pair it is 4.4 degrees against a
projection floor of 3.2. Refer to the ladder below.

THE REPROJECTION COMPARISON THAT WAS ASKED FOR CANNOT ANSWER THIS, and the
reason is in the lift's own method note. It is not a triangulation. The front
view supplies `across`, the side view supplies `ahead`, and each view's own
pixels pass straight through to its own axis. Reprojecting the 3D back into
either camera returns the 2D it came from, to rounding, BY CONSTRUCTION. The
error would be zero and would mean nothing.

So this measures the thing a reprojection was meant to localise, directly.

WHICH READING OF `up` BUILDS THE 3D DECIDES THE ANSWER, AND THE OBVIOUS CHOICE
IS WRONG. The lift measures `up` twice, once per camera. Averaging the two is
the better ESTIMATE of where the arm was, and it is the wrong 3D for THIS test,
because the comparison is against the side view and a mean-up 3D borrows half
its `up` from that same view.

RE-MEASURED 2026-09-07 ON THE PAIR THAT IS ACTUALLY A PAIR. The table that
stood here (21.2 / 12.8 / 3.8 deg on 730 frames) was measured on
`front 0.1.mp4` against the 863-frame side file (253fa551605e), which are NOT
two views of one take; refer to the mislabel finding in
`docs/VIDEO_CAPTURE_FINDINGS.md`. Those three numbers are VOID. On
`front 0.1.mp4` + `side 0.1.mp4` (6e8f9fb2fe03, 990 frames), 763 frame pairs:

The file NAMES were corrected at source on 2026-09-07 and both readings above
are stated by hash, because the names have moved once already.

    up taken from   shares with the side view   median   projection floor
    front only      nothing                     4.4 deg        3.2 deg
    mean of both    half of the up              2.6            2.8
    side only       all of the up               2.5            2.5

THE LADDER SURVIVES AND IT IS MUCH SHORTER. The ordering still holds, and the
bottom rung still equals the projection floor exactly, which is the check that
says the arithmetic is right: with `up` from the side, the two quantities share
two of three coordinates and only the definitional difference is left. What
changed is the top rung. Nineteen of the old 21.2 degrees were the wrong
pairing, not the depth scale.

So the default here is still `front`, the view NOT being compared against.
Choosing `mean` reports a better agreement bought by asking the instrument
about itself. But read the front row against its own floor before calling any
of it error: 4.4 against 3.2 leaves about a degree, not twenty-one.

Two jobs, and one number cannot do both: a best estimate of the pose, and a
test of whether two views agree.

THE PREDICTION THE DEPTH-SCALE HYPOTHESIS MAKES. The side view's elbow angle
uses only side pixels, and both its axes share one scale, so the angle is
scale free. The lift's elbow angle mixes `across` (front scale) with `ahead`
(side scale). If the RATIO of those two scales is wrong, the arm is stretched
along one axis and the angle changes — but only in so far as the arm actually
extends along `across`. An arm lying in the side plane is unaffected.

So: if the depth scale is the cause, the disagreement must GROW with the arm's
extent along `across`, and be small when the arm is edge on to the front
camera. If the disagreement is flat against that, the scale ratio is not the
explanation and something else is.

The competing explanation is sync. The file's own `residualMetres` is the
disagreement between the two independent readings of UP, which its note says
is dominated by sync. If the elbow disagreement tracks that residual, it is
sync rather than scale.
"""

import argparse
import json
import math
import pathlib
import statistics

ARM = ("left_shoulder", "left_elbow", "left_wrist")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lift", required=True, type=pathlib.Path)
    parser.add_argument("--view", required=True, type=pathlib.Path,
                        help="the keypoint file for the view to compare against")
    parser.add_argument("--joint", nargs=3, default=list(ARM),
                        metavar=("PROXIMAL", "MIDDLE", "DISTAL"))
    # THE DEFAULT MATTERS AND IT IS NOT THE OBVIOUS ONE. Refer to the note on
    # circularity in the docstring above.
    parser.add_argument("--up", choices=("front", "mean", "side"), default="front",
                        help="which reading of UP builds the 3D. Use the view "
                             "you are NOT comparing against, or the test "
                             "borrows from the instrument it is testing.")
    return parser.parse_args()


ARGUMENTS = parse_args()


def angle(a, b, c):
    """The angle at b, in degrees, for points of any dimension."""
    first = [x - y for x, y in zip(a, b)]
    second = [x - y for x, y in zip(c, b)]
    na = math.sqrt(sum(v * v for v in first))
    nb = math.sqrt(sum(v * v for v in second))
    if na < 1e-9 or nb < 1e-9:
        return None
    dot = sum(x * y for x, y in zip(first, second)) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def correlation(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    top = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    bottom = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return top / bottom if bottom else 0.0


ARM = tuple(ARGUMENTS.joint)


def up_of(row: dict) -> float:
    if ARGUMENTS.up == "front":
        return row["upFrontMetres"]
    if ARGUMENTS.up == "side":
        return row["upSideMetres"]
    return 0.5 * (row["upFrontMetres"] + row["upSideMetres"])
lift = json.loads(ARGUMENTS.lift.read_text(encoding="utf-8"))
side = json.loads(ARGUMENTS.view.read_text(encoding="utf-8"))

# THIS SCRIPT USED TO READ `offsetSecondsToReference` AND CRASHED ON EVERY
# ARTEFACT THE LIFT NOW WRITES. That field was removed on 2026-09-07, because
# the two cameras' frame periods differ by 11 microseconds and an offset in
# seconds therefore drifts across the clip: two such offsets had already been
# withdrawn from this material. The measurement is a FRAME COUNT. The field was
# removed from the writer and this reader was not found, because nothing ran
# it. `git grep` finds it in two seconds and nobody ran that either.
applied = lift["syncApplied"]
if "offsetSecondsToReference" in applied:
    raise SystemExit(
        "this lift artefact carries the withdrawn `offsetSecondsToReference`. "
        "Re-run video_lift_3d.py --pair to write a current one.")
frame_offset = int(applied["frameOffsetToReference"])

# THE MAPPING IS BY FRAME INDEX, EXACTLY. The lift row carries the front frame
# index and the side frame index it was paired with, so no nearest-time match
# with a tolerance is needed here; a tolerance is what let a frame be paired
# with its neighbour when a time landed between two.
by_index = {}
for row in lift["rows"]:
    by_index.setdefault(row["frameIndex"], {})[row["name"]] = row

side_by_index = {
    frame["frameIndex"]: {mark["name"]: mark
                          for mark in frame.get("landmarks", [])}
    for frame in side["frames"] if frame.get("detected")
}


def side_frame_of(front_index: int):
    """The side frame the lift paired with this front frame, by index."""
    return side_by_index.get(front_index + frame_offset)


rows = []
for front_index in sorted(by_index):
    marks = by_index[front_index]
    when = marks[next(iter(marks))]["ptsSeconds"]
    if not all(name in marks for name in ARM):
        continue
    # 3D from the lift. `up` is measured twice; take the mean, and keep the
    # gap, because the file's note says that gap is dominated by sync.
    def point(name):
        r = marks[name]
        return (r["acrossMetres"], r["aheadMetres"], up_of(r)), r

    (ps, rs), (pe, re), (pw, rw) = point("left_shoulder"), point("left_elbow"), point("left_wrist")
    lifted = angle(ps, pe, pw)
    if lifted is None:
        continue

    seen = side_frame_of(front_index)
    if seen is None or not all(name in seen for name in ARM):
        continue
    flat = angle(
        (seen["left_shoulder"]["xPixel"], seen["left_shoulder"]["yPixel"]),
        (seen["left_elbow"]["xPixel"], seen["left_elbow"]["yPixel"]),
        (seen["left_wrist"]["xPixel"], seen["left_wrist"]["yPixel"]),
    )
    if flat is None:
        continue

    # How much of the arm lies along ACROSS, the axis the front camera sets and
    # the side camera cannot see. This is the quantity the depth-scale
    # hypothesis says the disagreement must follow.
    across_extent = max(abs(ps[0] - pe[0]), abs(pe[0] - pw[0]))
    ahead_extent = max(abs(ps[1] - pe[1]), abs(pe[1] - pw[1]))
    span = math.sqrt(across_extent ** 2 + ahead_extent ** 2)
    across_share = across_extent / span if span > 1e-9 else 0.0

    rows.append({
        "t": when,
        "lifted": lifted,
        "flat": flat,
        "gap": lifted - flat,
        "acrossExtent": across_extent,
        "acrossShare": across_share,
        "upResidual": max(rs["residualMetres"], re["residualMetres"], rw["residualMetres"]),
        "visibility": min(seen[n].get("visibility", 1.0) for n in ARM),
    })

print(f"{len(rows)} frame pairs, up taken from the {ARGUMENTS.up.upper()} view")
gaps = [abs(r["gap"]) for r in rows]
print(f"disagreement: median {statistics.median(gaps):.1f} deg, "
      f"mean {statistics.mean(gaps):.1f}, p90 {sorted(gaps)[int(0.9*len(gaps))]:.1f}, "
      f"worst {max(gaps):.1f}")
signed = [r["gap"] for r in rows]
print(f"signed: median {statistics.median(signed):+.1f} deg  "
      f"-> {'the lift reads WIDER' if statistics.median(signed) > 0 else 'the lift reads TIGHTER'}")
print()

print("THE DEPTH-SCALE PREDICTION: disagreement must grow with the arm's extent")
print("along ACROSS, the axis only the front camera sees.")
for label, key in (("acrossExtent (m)", "acrossExtent"), ("acrossShare (0-1)", "acrossShare")):
    r = correlation([x[key] for x in rows], gaps)
    print(f"  correlation of |gap| with {label:<18} {r:+.3f}")
print()
print("THE SYNC EXPLANATION: disagreement must track the file's own up-residual.")
print(f"  correlation of |gap| with upResidual (m)   "
      f"{correlation([x['upResidual'] for x in rows], gaps):+.3f}")
print()

# Banded, because a correlation near zero can hide a threshold.
print("BANDED BY ACROSS EXTENT, which a single correlation would hide:")
ordered = sorted(rows, key=lambda r: r["acrossExtent"])
size = max(1, len(ordered) // 5)
for index in range(0, len(ordered), size):
    band = ordered[index:index + size]
    if len(band) < 5:
        continue
    band_gaps = [abs(b["gap"]) for b in band]
    print(f"  across {band[0]['acrossExtent']:.3f} to {band[-1]['acrossExtent']:.3f} m  "
          f"n={len(band):3d}  median |gap| {statistics.median(band_gaps):5.1f} deg")
print()
print("BANDED BY UP-RESIDUAL:")
ordered = sorted(rows, key=lambda r: r["upResidual"])
for index in range(0, len(ordered), size):
    band = ordered[index:index + size]
    if len(band) < 5:
        continue
    band_gaps = [abs(b["gap"]) for b in band]
    print(f"  residual {band[0]['upResidual']:.3f} to {band[-1]['upResidual']:.3f} m  "
          f"n={len(band):3d}  median |gap| {statistics.median(band_gaps):5.1f} deg")


# THE PROJECTION FLOOR, from the lift's own 3D and nothing else. The same arm
# measured in 3D, then measured again with `across` dropped, which is exactly
# what a flawless view from that side would read. Any comparison of a 3D angle
# against a 2D angle from one camera carries this much disagreement as
# GEOMETRY, before any error is involved.
floor = []
floor_shares = []
for front_index in sorted(by_index):
    marks = by_index[front_index]
    if not all(name in marks for name in ARM):
        continue
    def whole(name):
        r = marks[name]
        return (r["acrossMetres"], r["aheadMetres"],
                up_of(r))
    ps, pe, pw = whole(ARM[0]), whole(ARM[1]), whole(ARM[2])
    full = angle(ps, pe, pw)
    flat = angle((ps[1], ps[2]), (pe[1], pe[2]), (pw[1], pw[2]))
    if full is None or flat is None:
        continue
    across = max(abs(ps[0] - pe[0]), abs(pe[0] - pw[0]))
    ahead = max(abs(ps[1] - pe[1]), abs(pe[1] - pw[1]))
    span = math.hypot(across, ahead)
    floor_shares.append(across / span if span > 1e-9 else 0.0)
    floor.append(abs(full - flat))

print()
print("THE PROJECTION FLOOR: the same 3D arm, measured with `across` dropped.")
print(f"  n {len(floor)}  median {statistics.median(floor):.1f} deg  "
      f"p90 {sorted(floor)[int(0.9 * len(floor))]:.1f}  worst {max(floor):.1f}")
print("  banded by the arm's across share, which this MUST grow with:")
order = sorted(zip(floor_shares, floor))
size = max(1, len(order) // 5)
for index in range(0, len(order), size):
    band = order[index:index + size]
    if len(band) < 5:
        continue
    print(f"    share {band[0][0]:.2f} to {band[-1][0]:.2f}  n={len(band):3d}  "
          f"median {statistics.median([value for _, value in band]):5.1f} deg")
