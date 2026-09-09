"""How smoothly the second hand travels out to meet the ball, PER DRILL.

`docs/KNOWN_ISSUES.md` describes the snatch drill in full, then carries the hooks
drill along in one sentence: "The hooks drill is the same shape". The ramp
figures that follow are given once, for both. **That sentence also carries a
travel figure for the hooks drill that this tree does not reproduce**, so the
sentence extending the ramp to it is the sentence already known to be unreliable.

This measures the ramp on each drill separately, so neither is assumed from the
other.

THE QUANTITY IS THE AHEAD COMPONENT from the midpoint of the two upper-arm
joints, which is the origin the agenda and the ledger both state, and the
component that reproduces their numbers. A 3D distance from the same origin
disagrees by more than 5 cm, and that difference is in the component and not in
the origin.

WHERE THE MOVEMENT STARTS IS A THRESHOLD, SO THE THRESHOLD IS SWEPT. A single
value would make the frame count an artefact of a choice nobody stated. Three are
reported, and the count is only quoted when it is stable across them.

THE SECOND HAND'S ARRIVAL PHASE IS NOT NAMED THE SAME ON BOTH DRILLS. The snatch
has `join`; the hooks drill has `gather`. `docs/KNOWN_ISSUES.md` names both keys.
Each drill's step is reported at its own phase, named, rather than one substituted
silently for the other.

    pixi run --frozen python ../scripts/second_hand_ramp.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import numpy as np  # noqa: E402
from export_blender_job import load_character, to_blender  # noqa: E402
from possession_solve import solve_movement  # noqa: E402

ARCHIVE = "coach-figures-2413f9d"

# The two drills where one hand takes the ball and the other joins.
DRILLS = ("netball_one_hand_snatch_to_other_hand", "netball_hooks_outside_hand")

# The phase at which the second hand arrives, per drill, by that drill's own name.
ARRIVAL = {"netball_one_hand_snatch_to_other_hand": "join",
           "netball_hooks_outside_hand": "gather"}

# Centimetres per frame below which the hand is called still. Swept, never single.
THRESHOLDS = (0.05, 0.10, 0.20)


def archives() -> Path:
    for base in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        candidate = base / ".assets" / "archives"
        if candidate.is_dir():
            return candidate
    raise SystemExit("no .assets/archives found from this file")


def ahead_track(character, movement_id: str) -> list[float]:
    """The free hand's ahead component, from the shoulder midpoint, every frame."""
    result = solve_movement(character, movement_id)
    index, points = result["index"], result["points"]
    track = []
    for frame in range(len(points)):
        here = points[frame]
        left = to_blender(here[index["l_uparm"]])
        right = to_blender(here[index["r_uparm"]])
        wrist = to_blender(here[index["l_wrist"]])
        midpoint = (left + right) / 2.0
        track.append(float(midpoint[1] - wrist[1]) * 100.0)
    return track


def first_moving(track: list[float], floor: int, peak: int,
                 threshold: float) -> int:
    """Where the ramp begins: walk back from the peak while the hand is moving.

    THE FLOOR MUST NOT BE THE CONTACT FRAME. A first version of this clamped the
    search at contact, so it could never report a start before it, and then
    called the answer stable across three thresholds. It was stable because it
    could not move. `docs/KNOWN_ISSUES.md` puts the start at about frame 45 and
    contact is 48, so the clamp hid exactly the frames the question is about.
    """
    start = peak
    for frame in range(peak - 1, floor - 1, -1):
        if abs(track[frame + 1] - track[frame]) < threshold:
            break
        start = frame
    return start


def main() -> None:
    directory = archives() / ARCHIVE
    receipts = {}
    for path in sorted(directory.glob("*.render.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipts[receipt["movementId"]] = receipt

    character = load_character()
    for movement_id in DRILLS:
        receipt = receipts[movement_id]
        frames = {phase["name"]: phase["frame"] for phase in receipt["phases"]}
        contact = frames["contact"]
        arrival_name = ARRIVAL[movement_id]
        arrival = frames[arrival_name]
        track = ahead_track(character, movement_id)
        peak = contact + int(np.argmax(track[contact:]))
        last = len(track) - 1

        print(f"--- {movement_id.replace('netball_', '')}")
        print(f"    contact f{contact}  {track[contact]:6.2f} cm")
        print(f"    the frames either side of contact, ahead in cm:")
        window = range(max(0, contact - 6), min(len(track), contact + 4))
        print("      " + "  ".join(f"f{f}:{track[f]:.2f}" for f in window))
        print(f"    furthest f{peak}  {track[peak]:6.2f} cm")
        print(f"    back to  f{last}  {track[last]:6.2f} cm")
        print(f"    TRAVEL, contact to furthest: {track[peak] - track[contact]:.2f} cm")
        print()
        print(f"    {'threshold':<12}{'starts':>8}{'out frames':>12}"
              f"{'cm per frame out':>20}")
        # The floor is the START OF THE MOVEMENT, not the contact frame, so a
        # ramp that begins before contact can be found. It is what the ledger
        # reports for this drill.
        starts = set()
        for threshold in THRESHOLDS:
            start = first_moving(track, 0, peak, threshold)
            starts.add(start)
            steps = [track[f + 1] - track[f] for f in range(start, peak)]
            span = f"{min(steps):.2f} to {max(steps):.2f}" if steps else "none"
            print(f"    {threshold:<12.2f}{'f' + str(start):>8}{peak - start:>12}"
                  f"{span:>20}")
        spread = max(starts) - min(starts)
        if spread == 0:
            verdict = "STABLE across the three thresholds"
        elif spread <= 2:
            verdict = f"stable to within {spread} frame(s) across the three thresholds"
        else:
            verdict = (f"NOT STABLE: {spread} frames apart, so this drill has no "
                       "distinct start and no frame count can be quoted for it")
        print(f"    the start is {verdict}")

        # HOW STILL IS THE HAND BEFORE CONTACT? This is what decides whether a
        # ramp start exists at all. A hand already moving has no start to find,
        # and a threshold sweep on it returns whatever the threshold was.
        before = [abs(track[f + 1] - track[f]) for f in range(max(0, contact - 20), contact)]
        print(f"    over the 20 frames before contact it moves "
              f"{min(before):.2f} to {max(before):.2f} cm per frame, "
              f"{track[contact] - track[max(0, contact - 20)]:+.2f} cm in total")

        back = [track[f + 1] - track[f] for f in range(peak, last)]
        print()
        print(f"    on the way back: {last - peak} frames, "
              f"{min(back):.2f} to {max(back):.2f} cm per frame")
        print(f"    (falling, so these are negative; the ledger quotes their size)")
        print(f"    by size: {min(abs(v) for v in back):.2f} to "
              f"{max(abs(v) for v in back):.2f} cm per frame")

        step = track[arrival] - track[arrival - 1]
        print()
        print(f"    the step at this drill's own arrival phase, `{arrival_name}` "
              f"f{arrival}: {step:+.2f} cm")
        biggest = max(range(len(track) - 1), key=lambda f: abs(track[f + 1] - track[f]))
        print(f"    the biggest single step anywhere: f{biggest} to f{biggest + 1}, "
              f"{track[biggest + 1] - track[biggest]:+.2f} cm")
        print()

    print("THE TWO DRILLS DO NOT SHARE A RAMP. Their peaks are at different")
    print("frames, so the out and back windows differ in length, and any figure")
    print("quoted once for both was measured on one of them.")


if __name__ == "__main__":
    main()
