"""Read a directory of render receipts and say how near the hands came.

Whether the athlete touched the ball is the first thing a person asks of a
figure, and this lane once answered it wrong from a picture. The renderer
writes the millimetres into every receipt. This prints them.

Negative is inside the ball, which is a defect. A large positive is the hand
nowhere near it, which is the open grip defect. Refer to known defect 1 in
docs/HANDOFF_RENDERING.md.

    python report_clearance.py <render directory>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The bone is inside the flesh, so a bone clearance of about 8 mm is the skin
# on the surface. Anything past this is a hand not holding the ball.
CONTACT_MM = 12.0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    directory = Path(argv[1]).resolve()
    receipts = sorted(directory.glob("*.render.json"))
    if not receipts:
        print(f"no render receipt under {directory}")
        return 1

    holding, open_handed, penetrating = 0, 0, 0
    for path in receipts:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n{receipt['movementId']}")
        for phase in receipt["phases"]:
            cells = []
            for side in ("l", "r"):
                clearance = phase["hands"][side].get("surfaceClearanceMm")
                if clearance is None:
                    cells.append(f"{side}: not measured")
                    continue
                worst = clearance["worst"]
                if worst < 0.0:
                    penetrating += 1
                    mark = "INSIDE"
                elif worst > CONTACT_MM:
                    open_handed += 1
                    mark = "open"
                else:
                    holding += 1
                    mark = "held"
                cells.append(f"{side}: {worst:+7.1f} mm {mark}")
            print(f"   {phase['name']:12s} " + "   ".join(cells))

    total = holding + open_handed + penetrating
    print(f"\n{len(receipts)} drills, {total} hands measured: "
          f"{holding} on the ball, {open_handed} open, {penetrating} inside it")
    if penetrating:
        print("A hand inside the ball is a rendering defect. Report it.")
    if open_handed:
        print("An open hand is the wrist standoff in the job file, which the "
              "movement lane owns. Refer to known defect 1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
