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

IF THIS DIES WITH NO OUTPUT, TRY MKL_THREADING_LAYER=SEQUENTIAL
--------------------------------------------------------------

A reviewer running this gate on 2026-08-31 hit a hard process crash,
`0xC06D007F`, inside a numpy matrix multiply, on both `main` and the branch
under review. Setting `MKL_THREADING_LAYER=SEQUENTIAL` fixed it. The crash
kills the process rather than raising, so THIS GATE CAN DIE WITHOUT SAYING
ANYTHING, and a gate that dies silently reads like a gate that has not been
run.

    MKL_THREADING_LAYER=SEQUENTIAL pixi run python verify_tactics_clip.py

**It did not reproduce in the movement lane's worktree**, and that is recorded
rather than smoothed over, because the difference tells the next person which
situation they are in. There, with the variable unset, `numpy.__config__`
reports BLAS `blas 3.9.0` rather than MKL, and a 512 by 512 matmul and inverse
both complete. So this is an environment difference between checkouts and not a
property of the code. Check what your own numpy reports before assuming either
way.

What it gates on, and what it only reports
------------------------------------------
**It exits non-zero for one thing: a clip that no longer carries its own solve.**
Either an asserted channel has drifted past the threshold, or the comparison
could not be made at all.

**Everything about coaching bands is reported and never gated on.** Whether a
movement meets its checkpoints is a question about the movement, against bands
that are still provisional and that a coach has yet to sign off. It is not a
question about whether the clip is faithful, and the two were conjoined here
once: four drills failing a provisional band turned the gate red under the
message "a clip has left the solve it came from", which was not true and was not
what had happened. A gate that cries the wrong thing is a gate somebody switches
off, so the two answers are now separate and each says its own name.

Exit code 1 for a clip that has left its solve, so it can gate a merge.
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

    # A comparison that produced nothing is not a pass.
    #
    # `rows` only gains an entry for a measure the engine actually reported, so a
    # channel that quietly disappeared - renamed in the definition, dropped from
    # the measurement set - would leave nothing to compare and a worst gap of
    # zero. That reads as a perfect clip and is the absence of a test. This is
    # the structural half of the gate and it is separate from the numeric half
    # on purpose.
    asserted = [row for row in rows if row["asserted"]]
    structural = None
    if not asserted:
        structural = (
            "no asserted channel could be compared. Either the definition stopped "
            "reporting the measures in CHANNEL, or the clip lost the frames they "
            "are read from."
        )
    elif len(clip["frames"]) < 2:
        structural = f"the clip has {len(clip['frames'])} frames, which cannot be played."

    return {
        "clipId": clip["clipId"],
        "movementId": movement_id,
        "frames": len(clip["frames"]),
        "seconds": clip["seconds"],
        "hit": clip["hit"],
        "hitPhase": clip["hitPhase"],
        "momentGapSeconds": round((contact_at - clip["hit"]) * clip["seconds"], 3),
        "rootTravelM": clip["rootTravelM"],
        "ballAtPhases": {
            phase["name"]: clip["ball"][phase["frame"]] for phase in clip["phases"]
        },
        "rows": rows,
        # ------------------------------------------------- does the clip track the solve
        #
        # The only question this tool gates on. It asks whether the retarget kept
        # the movement, and nothing else.
        "worstAssertedGapDegrees": round(worst, 2),
        "assertedChannels": len(asserted),
        "structuralFault": structural,
        "tracks": structural is None and worst <= THRESHOLD_DEGREES,
        # ------------------------------------------------- what the coaches would say
        #
        # Reported, never gated on. Whether a movement meets a provisional
        # coaching band is a question about the movement and about bands a coach
        # has still to sign off. It is not a question about whether the clip
        # carries the movement faithfully, and a tool that conflated the two
        # would go red on a drill that is being deliberately reworked - which is
        # a gate that gets switched off rather than one that gets heeded.
        "graded": clip["graded"],
        "failingCheckpoints": len(failing),
        "failingDetail": [
            f"{phase['name']}/{checkpoint['measure']} "
            f"{checkpoint['measuredDegrees']} outside "
            f"{checkpoint['minimumDegrees']} to {checkpoint['maximumDegrees']}"
            for phase in clip["phases"]
            for checkpoint in phase["checkpoints"]
            if checkpoint["verdict"] != "within"
        ],
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
    drifted = []
    for movement_id in sorted(CLASSES):
        row = check(character, movement_id)
        report[row["clipId"]] = row
        if not row["tracks"]:
            drifted.append(row)

        mark = "ok  " if row["tracks"] else "DRIFT"
        moved = ""
        if against and row["clipId"] in against:
            was = against[row["clipId"]]["worstAssertedGapDegrees"]
            moved = f"   was {was:.2f}"
        print(
            f"{mark:5s}{row['clipId']:36s} worst gap "
            f"{row['worstAssertedGapDegrees']:5.2f} deg over "
            f"{row['assertedChannels']:2d} channels   "
            f"moment {row['hitPhase']} {row['momentGapSeconds']:+.2f} s{moved}"
        )
        if row["structuralFault"]:
            print(f"      {row['structuralFault']}")

    # What the coaching definitions make of the movements, said separately and in
    # its own words. A drill being reworked against provisional bands is expected
    # to sit outside them for a while, and that is not this tool's business.
    ungraded = [row for row in report.values() if row["failingCheckpoints"]]
    print("\nCoaching bands, for information. This is not the clip gate.")
    if not ungraded:
        print("  Every drill meets every checkpoint in its definition.")
    for row in ungraded:
        print(f"  {row['clipId']:36s} {row['failingCheckpoints']} checkpoint(s) outside band")
        for detail in row["failingDetail"]:
            print(f"      {detail}")

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

    # The gate, and it answers one question: does each clip still carry the
    # movement it was solved from. Nothing about grading reaches this line.
    if not drifted:
        print(
            f"\nGATE PASSED. Every clip carries its own solve, inside "
            f"{THRESHOLD_DEGREES:.0f} degrees."
        )
        return 0

    print("\nGATE FAILED, and here is what failed rather than a summary of it:")
    for row in drifted:
        if row["structuralFault"]:
            print(f"  {row['clipId']}: {row['structuralFault']}")
            continue
        worst = max(
            (r for r in row["rows"] if r["asserted"]),
            key=lambda r: r["gapDegrees"],
        )
        print(
            f"  {row['clipId']}: {worst['measure']} at {worst['phase']} reads "
            f"{worst['clipDegrees']} in the clip against {worst['engineDegrees']} "
            f"in the solve, {worst['gapDegrees']} degrees apart."
        )
    print(
        "\nThat is the clip disagreeing with the movement it was made from, which "
        "no viewer will show you."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
