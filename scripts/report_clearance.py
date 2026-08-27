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


def is_profile(entry) -> bool:
    """Whether this digit carries a profile rather than one old number.

    Receipts written before the profile existed hold a single float per digit
    and a "worst" over the hand. That number cannot be classified, because it
    is a minimum that sits on the base knuckle and says nothing about whether
    the finger closed. Such a receipt is reported as unreadable rather than
    guessed at.
    """
    return isinstance(entry, dict) and "nearestOnBone" in entry


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
    stale, reaching, bodies = 0, 0, []
    body_measured, body_missing = 0, 0
    for path in receipts:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        print()
        print(receipt["movementId"])
        for phase in receipt["phases"]:
            body = phase.get("bodyClearanceMm")
            if body is None:
                body_missing += 1
            else:
                body_measured += 1
            if body and body["verticesInside"]:
                bodies.append(
                    f"{receipt['movementId']} {phase['name']}: "
                    f"{body['verticesInside']} vertices of the athlete inside "
                    f"the ball, {body['deepestMm']:.1f} mm deep"
                )
            for side in ("l", "r"):
                profile = phase["hands"][side].get("surfaceClearanceMm")
                if not profile:
                    print(f"   {phase['name']:12s} {side}: not measured")
                    continue
                if not any(is_profile(profile.get(d)) for d in DIGITS):
                    stale += 1
                    continue
                # A hand 1.6 m from a ball still in flight is not a defect, so
                # it is not counted as one. Older receipts have no holding
                # flag, so they are read as holding and reported as before.
                if not phase.get("holding", True):
                    reaching += 1
                    continue
                cells = []
                for digit in DIGITS:
                    entry = profile.get(digit)
                    if not is_profile(entry):
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
    if reaching:
        print(f"{reaching} hands are on a phase where she is not holding the "
              f"ball, so they are not judged against it.")
    print()
    if bodies:
        print(f"THE SECOND INSTRUMENT: {len(bodies)} phases have part of the "
              f"athlete inside the ball. The per digit table above cannot see "
              f"this, and once passed a figure with the ball through her face.")
        for line in bodies:
            print(f"   {line}")
    elif body_measured:
        print(f"The athlete is outside the ball on all {body_measured} phases "
              f"measured for it.")
    if body_missing:
        # Silence here is not a clean result. It is no result, and saying
        # otherwise is the mistake this instrument exists to prevent.
        print(f"{body_missing} phases carry NO body measurement, because they "
              f"were rendered before the field existed. Nothing above says "
              f"whether the athlete is inside the ball on those. Re-render to "
              f"find out.")
    if stale:
        print(f"{stale} hands carry the older single number per digit and cannot "
              f"be read. That number is a minimum sitting on the base knuckle "
              f"and says nothing about whether the finger closed. Re-render them.")
    if counts["inside"]:
        print("A digit inside the ball is a rendering defect. Report it.")
    if counts["away"]:
        print("A digit whose tip is further out than its knuckle is not "
              "gripping. Its knuckle is not flexing. Refer to known defect 1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
