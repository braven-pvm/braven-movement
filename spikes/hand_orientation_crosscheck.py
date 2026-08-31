"""The second instrument for hand orientation. Nothing certifies on one.

hand_orientation.py reads the solved joint centres directly, inside the build,
with an acos formulation. This script recomputes every reported row from the
coach animations export (poc-output/coach/animations.json) with an atan2
formulation, and compares.

The two fail differently, which is the point:

- Different data: the export pipeline serialises the joints through its own
  extraction and rounds to a millimetre. A joint-name mix-up, a unit slip, an
  axis swap or a stale export on either side lands here as a disagreement.
- Different arithmetic: atan2(|u x v|, u . v) against acos of a clamped
  cosine. A clamp bug or a normalisation bug on one side cannot hide.

The agreement budget is not a tuned constant. It is derived per row from the
export's own quantisation: each coordinate is rounded to 0.1 cm, so each
endpoint sits within 0.05 * sqrt(3) cm of the value the build saw, each ray's
direction within atan(2 * 0.0866 / length) of it, and an angle between two
rays within the sum of the two. The receipt's two-decimal rounding adds 0.005
degrees. Anything past that budget is a defect, not noise.

    pixi run python hand_orientation_crosscheck.py
    pixi run python hand_orientation_crosscheck.py netball_two_hand_catch_chest

Needs both artifacts on disk, from the same solve:

    pixi run python build_library.py
    pixi run python export_coach_animations.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

LIBRARY = SPIKE_DIR / "poc-output" / "library"
ANIMATIONS = SPIKE_DIR / "poc-output" / "coach" / "animations.json"

# Half of the 0.1 cm the export rounds to, along the worst diagonal.
QUANTISATION_CM = 0.05 * math.sqrt(3.0)
# The receipt rounds measured values to two decimals.
RECEIPT_ROUNDING_DEGREES = 0.005

# Deliberately restated rather than imported: this instrument must not share
# the constant under test with the instrument it checks.
UP = (0.0, 1.0, 0.0)


def _difference(start, end):
    return (
        float(end[0]) - float(start[0]),
        float(end[1]) - float(start[1]),
        float(end[2]) - float(start[2]),
    )


def _atan2_degrees(u, v) -> float:
    """The angle between two vectors, by atan2 rather than acos."""
    cross = (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )
    sine = math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)
    cosine = u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
    if sine == 0.0 and cosine == 0.0:
        raise ValueError("a zero-length vector has no direction")
    return math.degrees(math.atan2(sine, cosine))


def _length(vector) -> float:
    return math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)


def _ray_budget_degrees(length_cm: float) -> float:
    """How far quantisation alone can swing one exported ray, in degrees."""
    return math.degrees(math.atan2(2.0 * QUANTISATION_CM, length_cm))


def recompute(joints: dict, ball_centre, measure: str) -> tuple[float, float]:
    """One row's value from the export, and its quantisation budget.

    ``measure`` is the receipt row name, e.g. leftThumbUpDegrees. Returns
    (value, budget). The budget covers both rays' quantisation plus the
    receipt's own rounding.
    """
    side = {"left": "l", "right": "r"}[
        "left" if measure.startswith("left") else "right"
    ]
    if measure.endswith("ThumbUpDegrees"):
        ray = _difference(joints[f"{side}_thumb1"], joints[f"{side}_thumb3"])
        other, other_budget = UP, 0.0
    elif measure.endswith("FingerUpDegrees"):
        ray = _difference(joints[f"{side}_wrist"], joints[f"{side}_middle1"])
        other, other_budget = UP, 0.0
    elif measure.endswith("ThumbToBallDegrees"):
        ray = _difference(joints[f"{side}_thumb1"], joints[f"{side}_thumb3"])
        other = _difference(joints[f"{side}_thumb1"], ball_centre)
        other_budget = _ray_budget_degrees(_length(other))
    else:
        raise ValueError(f"unknown hand orientation measure: {measure}")
    budget = (
        _ray_budget_degrees(_length(ray)) + other_budget + RECEIPT_ROUNDING_DEGREES
    )
    return _atan2_degrees(ray, other), budget


def crosscheck(movement_id: str, receipt: dict, animation: dict) -> list[dict]:
    """Every reported row of one movement, read by both instruments."""
    section = receipt.get("handOrientation")
    if not section or section.get("status") != "report-only":
        raise ValueError(f"{movement_id}: the receipt carries no reported rows")
    anim_phase_frames = {p["name"]: p["frame"] for p in animation["phases"]}

    rows = []
    for phase_name, block in section["phases"].items():
        number = block["frame"]
        if anim_phase_frames.get(phase_name) != number:
            raise ValueError(
                f"{movement_id} [{phase_name}]: the receipt reads frame "
                f"{number} and the export says the phase is frame "
                f"{anim_phase_frames.get(phase_name)}. The two artifacts do "
                "not describe the same build."
            )
        frame = animation["frames"][number]
        for row in block["rows"]:
            value, budget = recompute(frame["j"], frame["b"], row["measure"])
            rows.append(
                {
                    "movement": movement_id,
                    "phase": phase_name,
                    "measure": row["measure"],
                    "primary": row["measured"],
                    "crosscheck": round(value, 2),
                    "gapDegrees": round(abs(value - row["measured"]), 3),
                    "budgetDegrees": round(budget, 3),
                    "agree": abs(value - row["measured"]) <= budget,
                }
            )
    return rows


def same_build(receipt_stamp: dict | None, export_stamp: dict | None) -> str | None:
    """Refuse the comparison outright when the artifacts name different builds.

    Both artifacts carry a generatedFrom stamp (PR #22 for the receipts, the
    exporter since it existed). Two clean stamps naming different commits are
    two different builds, and agreement between them would certify nothing.
    A missing or dirty stamp is not proof of a mismatch, so it does not
    refuse; the per-phase frame check below still applies either way.
    """
    if not receipt_stamp or not export_stamp:
        return None
    ours, theirs = receipt_stamp.get("commit"), export_stamp.get("commit")
    if not ours or not theirs or ours == theirs:
        return None
    return (
        f"the receipts come from {ours[:12]} and the animations export from "
        f"{theirs[:12]}: two different builds, so agreement between them "
        "would certify nothing. Rebuild both from one tree."
    )


def main(argv: list[str]) -> int:
    if not ANIMATIONS.is_file():
        print(f"missing {ANIMATIONS}: run export_coach_animations.py first")
        return 1
    payload = json.loads(ANIMATIONS.read_text(encoding="utf-8"))
    animations = payload["movements"]

    wanted = argv[1:] or sorted(animations)
    checked, disagreements = 0, []
    for movement_id in wanted:
        receipt_path = LIBRARY / f"{movement_id}.json"
        if not receipt_path.is_file():
            print(f"missing {receipt_path}: run build_library.py first")
            return 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        mismatch = same_build(
            receipt.get("generatedFrom"), payload.get("generatedFrom")
        )
        if mismatch:
            print(f"{movement_id}: {mismatch}")
            return 1
        rows = crosscheck(movement_id, receipt, animations[movement_id])
        checked += len(rows)
        worst = max(rows, key=lambda row: row["gapDegrees"])
        print(f"\n{movement_id}: {len(rows)} rows, worst gap "
              f"{worst['gapDegrees']} deg on [{worst['phase']}] "
              f"{worst['measure']} (budget {worst['budgetDegrees']})")
        for row in rows:
            flag = "   " if row["agree"] else "XX "
            print(
                f"  {flag}[{row['phase']}] {row['measure']:<28} "
                f"primary {row['primary']:>7.2f}  crosscheck "
                f"{row['crosscheck']:>7.2f}  gap {row['gapDegrees']:>6.3f}"
            )
            if not row["agree"]:
                disagreements.append(row)

    print(f"\n{checked} rows checked across {len(wanted)} movements")
    if disagreements:
        print(f"{len(disagreements)} DISAGREE beyond the quantisation budget:")
        for row in disagreements:
            print(
                f"  {row['movement']} [{row['phase']}] {row['measure']}: "
                f"{row['primary']} against {row['crosscheck']}, gap "
                f"{row['gapDegrees']} over budget {row['budgetDegrees']}"
            )
        return 1
    print("the two instruments agree on every reported row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
