"""What axis each knuckle actually turns about, across the shipped library.

`netball_one_hand_high_pass/ready` cannot be posed: the right index knuckle
turns 42.2 degrees about z while `FLEXION_AXIS` names x, so the named axis
carries 0.44 of the turn and the guard refuses the frame.

THE GUARD IS RIGHT TO REFUSE. If the named axis is wrong, real flexion is
measured against the DEVIATION licence and stopped early, or deviation gets the
flexion licence and runs past the joint. The question this answers is not
whether to keep the guard. It is whose assumption the axis is, and how close the
eleven drills that DO pose came to the same refusal.

It reads the archived receipts and adds nothing: every figure below was recorded
by the render that drew the library. It PROPOSES NOTHING.

    python scripts/flexion_axis_survey.py [--archive coach-figures-2413f9d]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# The renderer's own table, quoted rather than imported: importing it needs bpy.
# `blender_mpfb_reference_catch.py:437`.
NAMED_AXIS = {"index": 0, "middle": 0, "ring": 0, "pinky": 0, "thumb": 2}
# `finger_curl.MIN_AXIS_SHARE`. Below this the guard refuses the frame.
MIN_AXIS_SHARE = 0.5
AXIS = ("x", "y", "z")


def archives() -> Path:
    for base in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        candidate = base / ".assets" / "archives"
        if candidate.is_dir():
            return candidate
    raise SystemExit(
        "no .assets/archives found from this file. The archives are not in the "
        "repository; they sit beside the main checkout."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", default="coach-figures-2413f9d")
    arguments = parser.parse_args()

    directory = archives() / arguments.archive
    rows = []
    for path in sorted(directory.glob("*.render.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        drill = receipt["movementId"].replace("netball_", "")
        for phase in receipt["phases"]:
            for side, hand in phase["hands"].items():
                for digit, entry in (hand.get("flexionAxis") or {}).items():
                    if not entry.get("asserted"):
                        continue
                    rows.append({
                        "where": f"{drill}/{phase['name']} {side}",
                        "digit": digit,
                        "share": entry["namedAxisShare"],
                        "named": entry["namedAxis"],
                        "dominant": entry["dominantAxis"],
                        "turned": entry["turnedDegrees"],
                        "margin": entry["dominanceMarginDegrees"],
                    })
    if not rows:
        raise SystemExit(f"no asserted knuckles in {directory}")

    print(f"{len(rows)} asserted knuckle readings in {directory.name}")
    print(f"The guard refuses below a named-axis share of {MIN_AXIS_SHARE}.")
    print()

    print("SHARE OF THE TURN CARRIED BY THE NAMED AXIS, per digit")
    print(f"{'digit':<9}{'named':>6}{'count':>7}{'lowest':>9}{'highest':>9}"
          f"{'under 0.6':>11}{'under 0.7':>11}")
    for digit in sorted({row["digit"] for row in rows}):
        here = [row for row in rows if row["digit"] == digit]
        shares = [row["share"] for row in here]
        print(f"{digit:<9}{AXIS[NAMED_AXIS[digit]]:>6}{len(here):>7}"
              f"{min(shares):>9.4f}{max(shares):>9.4f}"
              f"{sum(1 for s in shares if s < 0.6):>11}"
              f"{sum(1 for s in shares if s < 0.7):>11}")

    print()
    print("DOES THE NAMED AXIS EVER DISAGREE WITH THE ONE THAT TURNED MOST?")
    disagree = [row for row in rows if row["named"] != row["dominant"]]
    print(f"  {len(disagree)} of {len(rows)} readings, "
          f"{len(disagree) / len(rows):.1%}")
    for row in sorted(disagree, key=lambda r: r["share"])[:8]:
        print(f"    {row['where']:<40}{row['digit']:<8}"
              f"share {row['share']:.4f}  named {AXIS[row['named']]}  "
              f"turned most about {AXIS[row['dominant']]}  "
              f"margin {row['margin']:.2f} deg")

    print()
    print("THE CLOSEST THE SHIPPED LIBRARY CAME TO THE SAME REFUSAL")
    for row in sorted(rows, key=lambda r: r["share"])[:8]:
        turned = ", ".join(f"{AXIS[i]}={v:+.1f}" for i, v in
                           enumerate(row["turned"]))
        print(f"  {row['where']:<40}{row['digit']:<8}share {row['share']:.4f}"
              f"   {turned}")

    print()
    worst = min(rows, key=lambda r: r["share"])
    print(f"lowest share in the whole library: {worst['share']:.4f} at "
          f"{worst['where']} {worst['digit']}")
    print(f"the refused frame's share: 0.44 "
          f"(one_hand_high_pass/ready r index, x=18.5 y=-7.2 z=42.2)")
    print()
    print("THE JOB CARRIES NO AXIS. `knuckleLimitsDegrees` names a flexion "
          "range and a")
    print("deviation range and never says WHICH component is flexion. "
          "`FLEXION_AXIS` is a")
    print("constant in blender_mpfb_reference_catch.py:437, and its own "
          "comment at :645")
    print("says it is an assumption about the rig that nothing checked.")


if __name__ == "__main__":
    main()
