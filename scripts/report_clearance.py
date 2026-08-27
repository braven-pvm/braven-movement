"""Read a directory of render receipts and say how each hand met the ball.

Whether the athlete grips the ball is the first thing a person asks of a
figure, and this lane answered it wrong twice from summary numbers. So this
reads the shape of each finger, never one number for the hand.

A grip runs high at the knuckle and low at the tip, about 40 mm down to 7 on
the solved athlete. A finger whose tip is further out than its knuckle is not
gripping at all: it points away from the ball, and the knuckle is not flexing.

    python report_clearance.py <render directory>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DIGITS = ("thumb", "index", "middle", "ring", "pinky")

# The bone sits inside the flesh, so a tip clearance of about 8 mm is the skin
# on the surface. Past this and the finger is not touching.
CONTACT_MM = 12.0


def classify(entry: dict) -> str:
    if entry["nearestOnBone"] < 0.0:
        return "inside"
    if entry["knuckleToTip"] < 0.0:
        return "away"
    if entry["tip"] > CONTACT_MM:
        return "short"
    return "held"


MARKS = {"inside": "IN", "away": "away", "short": "short", "held": "held"}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    directory = Path(argv[1]).resolve()
    receipts = sorted(directory.glob("*.render.json"))
    if not receipts:
        print(f"no render receipt under {directory}")
        return 1

    counts = {"held": 0, "short": 0, "away": 0, "inside": 0}
    for path in receipts:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        print()
        print(receipt["movementId"])
        for phase in receipt["phases"]:
            for side in ("l", "r"):
                profile = phase["hands"][side].get("surfaceClearanceMm")
                if not profile:
                    print(f"   {phase['name']:12s} {side}: not measured")
                    continue
                cells = []
                for digit in DIGITS:
                    entry = profile.get(digit)
                    if not entry:
                        continue
                    verdict = classify(entry)
                    counts[verdict] += 1
                    cells.append(
                        f"{digit[:3]} {entry['knuckle']:+5.0f}>{entry['tip']:+5.0f} "
                        f"{MARKS[verdict]}"
                    )
                print(f"   {phase['name']:12s} {side}: " + "  ".join(cells))

    total = sum(counts.values())
    print()
    print(f"{len(receipts)} drills, {total} digits measured: "
          f"{counts['held']} on the ball, {counts['short']} short of it, "
          f"{counts['away']} pointing away, {counts['inside']} inside it")
    print("Each digit reads knuckle > tip. A grip falls; a pointing finger climbs.")
    if counts["inside"]:
        print("A digit inside the ball is a rendering defect. Report it.")
    if counts["away"]:
        print("A digit whose tip is further out than its knuckle is not "
              "gripping. Its knuckle is not flexing. Refer to known defect 1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
