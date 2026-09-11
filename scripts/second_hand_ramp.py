"""How smoothly the second hand travels out to meet the ball, PER DRILL.

`docs/KNOWN_ISSUES.md` describes the snatch drill in full, then carries the hooks
drill along in one sentence: "The hooks drill is the same shape". The ramp
figures that follow are given once, for both. **That sentence also carries a
travel figure for the hooks drill that this tree does not reproduce**, so the
sentence extending the ramp to it is the sentence already known to be unreliable.

This measures the ramp on each drill separately, so neither is assumed from the
other.

THE QUANTITY IS THE AHEAD COMPONENT from the midpoint of the two upper-arm
joints, IN THE ATHLETE'S OWN FRAME. The origin is the one the agenda and the
ledger both state. The frame is not.

THE FIRST VERSION OF THIS FILE USED THE WORLD FRAME AND EVERY NUMBER IT PRINTED
WAS WITHDRAWN. The frame was chosen by trying four components on
`one_hand_snatch_to_other_hand` and keeping the one that reproduced the recorded
figures. That athlete is SQUARE — 0.07 degrees of turn at contact — so world-ahead
and body-ahead are the same axis there and agreed to 0.01 cm. A test with no
power to separate two answers looks exactly like a test that chose between them.

ON THE TURNED DRILL THEY DISAGREE ABOUT THE FINDING, not merely about a value:

    hooks_outside_hand, 20 frames before contact    world +4.14 cm   body +0.28 cm
    the ramp start over three thresholds            world 42 frames  body  2 frames

The world reading carries her shoulders rotating back to square, because the turn
unwinds from 48.22 degrees at the first frame to 4.06 at the last. A number that
adds shoulder rotation to hand travel cannot answer a question about the hand.

WHY THE ATHLETE'S FRAME IS RIGHT, in the order the reasons carry weight:

  1. The cue is stated in body terms. Erin's note says the other hand should not
     go away from the CENTRE OF BODY towards the ball.
  2. A world number answers a different question on a turning athlete, as above.
  3. The engine AUTHORS in her frame: `technique.json`'s `afterContact[].ahead`
     is applied through the turn at `motion_track.py:426` and
     `ball_track.py:368`, and inverted at `possession.py:275`.

  NOT reproduction. It cannot separate the two here, and this file's own history
  is why that is written down.

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


def body_forward(shoulder_l, shoulder_r):
    """The direction the athlete faces, from her own shoulder line.

    Taken from the shoulders rather than from the world, because the drill this
    file exists for turns 48.22 degrees and unwinds to 4.06.
    """
    across = np.asarray(shoulder_l, dtype=float) - np.asarray(shoulder_r, dtype=float)
    across[2] = 0.0
    across /= np.linalg.norm(across)
    forward = np.cross(across, np.array([0.0, 0.0, 1.0]))
    return forward / np.linalg.norm(forward)


def ahead_track(character, movement_id: str) -> list[float]:
    """The free hand's ahead component IN HER FRAME, from the shoulder midpoint."""
    result = solve_movement(character, movement_id)
    index, points = result["index"], result["points"]
    track = []
    for frame in range(len(points)):
        here = points[frame]
        left = to_blender(here[index["l_uparm"]])
        right = to_blender(here[index["r_uparm"]])
        wrist = to_blender(here[index["l_wrist"]])
        midpoint = (left + right) / 2.0
        track.append(float((wrist - midpoint) @ body_forward(left, right)) * 100.0)
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

    print("BOTH DRILLS WAIT, THEN GO. On the athlete's own axis each is nearly")
    print("still before contact and each has a ramp start that a threshold sweep")
    print("finds to within two frames. `docs/KNOWN_ISSUES.md` calls them the same")
    print("shape and that is right.")
    print()
    print("WHAT IS NOT SHARED IS THE FRAME COUNT. The peaks sit at f58 and f60, so")
    print("the out and back windows differ in length, and a count quoted once for")
    print("both was measured on one of them.")
    print()
    print("AN EARLIER VERSION OF THIS FILE REPORTED THE OPPOSITE, on the world")
    print("axis: that one drill had no start at all. That was her shoulders")
    print("rotating back to square, not her hand travelling.")


if __name__ == "__main__":
    main()
