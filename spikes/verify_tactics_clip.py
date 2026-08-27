"""Check every exported clip against the solve it came from, and record it.

Why this exists
---------------
A clip is a lossy description of a solved movement, and the only honest way to
say a retarget worked is to measure the clip against what the engine measured.

It earned its place immediately. The first retarget was checked by hand on one
drill, read 1.6 degrees at contact, and was reported as a property of all eight.
This ran in ten minutes and found that seven of the eight were outside the
threshold, the worst by 52.7 degrees, because a joint bend was being read as the
difference of two planar swings. One measurement is not a property. Refer to
`bend_of` in export_tactics_clip.py.

Two of the comparisons below are meaningful and one is not, and the difference
matters:

- **The elbow agrees, and must.** `LimbPose.lower` is the angle between the
  upper arm and the forearm, which is what elbow flexion is. A disagreement here
  is a defect in the export.
- **The knee agrees, and must**, for the same reason.
- **The shoulder does not agree, and cannot.** ISB shoulder elevation is a three
  dimensional angle from the trunk. A pose carries two axes. They part company
  by up to 15 degrees on a movement with abduction in it. Reported, never
  asserted. Refer to section 11 of docs/TACTICS_CLIP_CONTRACT.md.

It also keeps a baseline, so a later run is a comparison rather than a reading.
`clip-baseline.json` beside this file is the current solve. The movement lane's
elbow work moves elbow separation on every drill, so every engine number is
expected to move when that lands. What this answers then is whether the clip
moved *with* the solve, which is the only question a re-export has to settle.

    pixi run python verify_tactics_clip.py
    pixi run python verify_tactics_clip.py --against clip-baseline.json
    pixi run python verify_tactics_clip.py --baseline clip-baseline.json

Exit code 1 if any asserted channel has left its solve, so it can gate a merge.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
BASELINE = SPIKE_DIR / "clip-baseline.json"

from export_tactics_clip import CLASSES, build  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from movement_engine import definition_path, load_character  # noqa: E402
from possession_solve import solve_movement  # noqa: E402

# The clinical measurement threshold this project already works to. A retarget
# that clears it is worth having; one that does not is a defect rather than a
# tolerance to widen.
THRESHOLD_DEGREES = 5.0

# Which channel of a frame carries which joint. Refer to section 8 of the
# contract; the order is positional and must not be rearranged.
CHANNEL = {
    "leftKneeFlexionDegrees": 4,
    "rightKneeFlexionDegrees": 6,
    "leftElbowFlexionDegrees": 8,
    "rightElbowFlexionDegrees": 10,
}
# Measured on two axes here and on three by the engine, so it is reported and
# never asserted.
REPORTED_ONLY = {
    "leftShoulderElevationDegrees": 7,
    "rightShoulderElevationDegrees": 9,
}


def check(character, movement_id: str) -> dict:
    clip = build(character, movement_id)
    result = solve_movement(character, movement_id)
    measurements = result["measurements"]
    definition = load_definition(definition_path(movement_id))

    rows = []
    worst = 0.0
    for phase in clip["phases"]:
        frame = phase["frame"]
        pose = clip["frames"][frame]
        for measure, channel in CHANNEL.items():
            if measure not in measurements[frame]:
                continue
            engine = float(measurements[frame][measure])
            clipped = math.degrees(pose[channel])
            gap = abs(clipped - engine)
            worst = max(worst, gap)
            rows.append(
                {
                    "phase": phase["name"],
                    "measure": measure,
                    "engineDegrees": round(engine, 2),
                    "clipDegrees": round(clipped, 2),
                    "gapDegrees": round(gap, 2),
                    "asserted": True,
                }
            )
        for measure, channel in REPORTED_ONLY.items():
            if measure not in measurements[frame]:
                continue
            engine = float(measurements[frame][measure])
            clipped = math.degrees(pose[channel])
            rows.append(
                {
                    "phase": phase["name"],
                    "measure": measure,
                    "engineDegrees": round(engine, 2),
                    "clipDegrees": round(clipped, 2),
                    "gapDegrees": round(abs(clipped - engine), 2),
                    "asserted": False,
                }
            )

    failing = [
        checkpoint
        for phase in clip["phases"]
        for checkpoint in phase["checkpoints"]
        if checkpoint["verdict"] != "within"
    ]

    # The declared moment against the frame the possession model derives. They
    # agree on a catch and must not on a landing.
    contact_at = clip["contactFrame"] / max(1, len(clip["frames"]))
    return {
        "clipId": clip["clipId"],
        "movementId": movement_id,
        "frames": len(clip["frames"]),
        "seconds": clip["seconds"],
        "hit": clip["hit"],
        "hitPhase": clip["hitPhase"],
        "momentGapSeconds": round((contact_at - clip["hit"]) * clip["seconds"], 3),
        "graded": clip["graded"],
        "failingCheckpoints": len(failing),
        "rootTravelM": clip["rootTravelM"],
        "worstAssertedGapDegrees": round(worst, 2),
        "clears": worst <= THRESHOLD_DEGREES,
        "rows": rows,
        "ballAtPhases": {
            phase["name"]: clip["ball"][phase["frame"]] for phase in clip["phases"]
        },
        "assessed": bool(definition.assess(measurements).correct),
    }


def main(argv: list[str]) -> int:
    baseline = None
    against = None
    for i, value in enumerate(argv[1:], start=1):
        if value == "--baseline":
            baseline = Path(argv[i + 1]) if i + 1 < len(argv) else BASELINE
        if value == "--against":
            path = Path(argv[i + 1]) if i + 1 < len(argv) else BASELINE
            against = json.loads(path.read_text(encoding="utf-8"))

    character = load_character()
    report = {}
    ok = True
    for movement_id in sorted(CLASSES):
        row = check(character, movement_id)
        report[row["clipId"]] = row
        ok = ok and row["clears"] and row["failingCheckpoints"] == 0

        mark = "ok  " if row["clears"] else "FAIL"
        moved = ""
        if against and row["clipId"] in against:
            was = against[row["clipId"]]["worstAssertedGapDegrees"]
            moved = f"   was {was:.2f}"
        print(
            f"{mark} {row['clipId']:36s} worst gap "
            f"{row['worstAssertedGapDegrees']:5.2f} deg   "
            f"{row['failingCheckpoints']} failing   "
            f"moment {row['hitPhase']} {row['momentGapSeconds']:+.2f} s{moved}"
        )

    if against:
        print("\nWhat moved, per phase, against the baseline:")
        for clip_id, row in report.items():
            old = against.get(clip_id)
            if not old:
                print(f"  {clip_id}: new, no baseline")
                continue
            for now, then in zip(row["rows"], old["rows"]):
                shift = now["engineDegrees"] - then["engineDegrees"]
                if abs(shift) >= 0.5:
                    print(
                        f"  {clip_id:36s} {now['phase']:9s} {now['measure']:30s} "
                        f"{then['engineDegrees']:6.1f} -> {now['engineDegrees']:6.1f} "
                        f"({shift:+.1f})"
                    )

    if baseline:
        baseline.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nbaseline -> {baseline}")

    print(
        "\n"
        + (
            "Every clip carries the movement it was solved from, "
            f"inside {THRESHOLD_DEGREES:.0f} degrees."
            if ok
            else "A clip has left the solve it came from. Read the rows above."
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
