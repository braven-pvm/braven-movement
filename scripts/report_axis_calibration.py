"""Read render receipts and report what the flexion-axis instrument saw.

Two calibrations in `finger_curl.py` were left open with notes instead of
numbers, and this reads the receipts that close them:

1. `FLEXION_MEASURE_FLOOR_DEGREES` is 5.0 with the note that no rig reading
   says 5 rather than 3 or 8. The below-floor population answers what actually
   sits under the floor: real small flexions with a direction, or the residue
   of digits that never flexed.

2. The thumb is recorded and not asserted, on 18 readings over 5 drills. Its
   per-drill shares here are the data that finish that calibration, one way
   or the other.

    python report_axis_calibration.py <render directory>

Reads `flexionAxis` per digit per hand per phase. A hand that is not gripping
carries an empty report, which is absence of measurement and is counted as
such, never as agreement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DIGITS = ("thumb", "index", "middle", "ring", "pinky")


def collect(directory: Path) -> tuple[list[dict], int, int]:
    """Every digit reading in every receipt, flat, plus hand coverage."""
    readings: list[dict] = []
    hands_with_report, hands_empty = 0, 0
    for path in sorted(directory.glob("*.render.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        for phase in receipt.get("phases", []):
            for side in ("l", "r"):
                report = (phase.get("hands") or {}).get(side, {}).get(
                    "flexionAxis"
                )
                if not report:
                    hands_empty += 1
                    continue
                hands_with_report += 1
                for digit, entry in report.items():
                    turned = entry["turnedDegrees"]
                    readings.append(
                        {
                            "movement": receipt["movementId"],
                            "phase": phase["name"],
                            "side": side,
                            "digit": digit,
                            "largest": max(abs(v) for v in turned),
                            "turned": turned,
                            "share": entry["namedAxisShare"],
                            "margin": entry["dominanceMarginDegrees"],
                            "measured": entry["measured"],
                        }
                    )
    return readings, hands_with_report, hands_empty


def quantiles(values: list[float]) -> str:
    if not values:
        return "none"
    ordered = sorted(values)
    mid = ordered[len(ordered) // 2]
    return (
        f"n={len(ordered)} min={ordered[0]:.3f} "
        f"median={mid:.3f} max={ordered[-1]:.3f}"
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    directory = Path(argv[1]).resolve()
    readings, covered, empty = collect(directory)
    if not readings:
        print(f"no flexionAxis reading under {directory}")
        return 1

    print(
        f"{len(readings)} digit readings from {covered} gripping hands; "
        f"{empty} hands carry no report (not gripping, which is absence of "
        f"measurement and not agreement)"
    )

    print("\n== Magnitude of what the flexion turned, per digit ==")
    for digit in DIGITS:
        mine = [r["largest"] for r in readings if r["digit"] == digit]
        print(f"  {digit:6s} {quantiles(mine)}")

    print("\n== The below-floor population (largest < 5.0) ==")
    below = [r for r in readings if r["largest"] < 5.0]
    if not below:
        print("  none: every reading in this batch cleared the floor")
    for r in below:
        print(
            f"  {r['movement']}.{r['phase']} {r['side']} {r['digit']:6s} "
            f"largest {r['largest']:.3f}  turned {r['turned']}  "
            f"share {r['share']:.4f}"
        )

    print("\n== The band a different floor would move (3.0 to 8.0) ==")
    band = [r for r in readings if 3.0 <= r["largest"] < 8.0]
    if not band:
        print("  none: no reading falls between 3 and 8 degrees")
    for r in band:
        print(
            f"  {r['movement']}.{r['phase']} {r['side']} {r['digit']:6s} "
            f"largest {r['largest']:.3f}  share {r['share']:.4f}"
        )

    print("\n== Asserted digits, measured readings: the share the name carries ==")
    for digit in ("index", "middle", "ring", "pinky"):
        shares = [
            r["share"]
            for r in readings
            if r["digit"] == digit and r["measured"]
        ]
        print(f"  {digit:6s} {quantiles(shares)}")

    print("\n== The thumb, per drill: named-Z share and the diagonal it turns on ==")
    thumbs = [r for r in readings if r["digit"] == "thumb" and r["measured"]]
    by_drill: dict[str, list[dict]] = {}
    for r in thumbs:
        by_drill.setdefault(r["movement"], []).append(r)
    for movement, mine in sorted(by_drill.items()):
        for r in mine:
            x_share = (
                abs(r["turned"][0]) / r["largest"] if r["largest"] else 0.0
            )
            print(
                f"  {movement}.{r['phase']} {r['side']}: named-Z share "
                f"{r['share']:.4f}, X carries {x_share:.4f}, margin "
                f"{r['margin']:.3f} deg"
            )
    all_z = [r["share"] for r in thumbs]
    print(f"  over this batch: named-Z share {quantiles(all_z)}")
    drills = {r["movement"] for r in readings}
    thumb_drills = {r["movement"] for r in thumbs}
    silent = sorted(drills - thumb_drills)
    if silent:
        print(f"  drills with no measured thumb: {', '.join(silent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
