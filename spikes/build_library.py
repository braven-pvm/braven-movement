"""Solve, measure, grade and export every movement in the library.

This is the check that the authoring loop scales. Adding a skill should mean
adding JSON files and nothing else. If that is true, this script picks the new
skill up with no edit.

A drill that has a ball trajectory and a technique is solved by the possession
model: the ball is the reason the athlete moves and her hands are solved rather
than authored. A drill that has neither is solved the old way, from hand keys.
Both produce the same measurements, so the coaching layer cannot tell them
apart and does not need to.

    pixi run python build_library.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from build_stamp import generated_from  # noqa: E402
from isb_angles import AAOS_LIMITS  # noqa: E402
from movement_definition import (  # noqa: E402
    MINIMUM_MEANINGFUL_BAND_DEGREES,
)
from motion_track import describe, load_motion  # noqa: E402
from movement_engine import (  # noqa: E402
    SolveError,
    definition_path,
    library,
    load_character,
    motion_path,
    solve,
)
from movement_definition import (  # noqa: E402
    MovementDefinitionError,
    load as load_definition,
)
from ball_track import ball_path, has_ball, load_ball  # noqa: E402
from hand_orientation import receipt_section  # noqa: E402
from possession_solve import solve_movement, spike_report  # noqa: E402
from technique import (  # noqa: E402
    movement_carries_no_side,
    has_technique,
    load_technique,
    technique_path,
)

OUTPUT = SPIKE_DIR / "poc-output" / "library"

RANGE_KEYS = (
    ("ElbowFlexionDegrees", "elbow.flexion"),
    ("ShoulderElevationDegrees", "shoulder.elevation"),
    ("KneeFlexionDegrees", "knee.flexion"),
)


def anatomy_violations(measurements: list[dict]) -> list[str]:
    violations: list[str] = []
    for number, frame in enumerate(measurements):
        for prefix in ("left", "right"):
            for suffix, key in RANGE_KEYS:
                value = frame[f"{prefix}{suffix}"]
                limit = AAOS_LIMITS[key]
                if value < limit.minimum_degrees or value > limit.maximum_degrees:
                    violations.append(
                        f"frame {number}: {prefix} {key} is {value:.1f} degrees"
                    )
    return violations


def build_one(character, movement_id: str) -> dict:
    track = load_motion(motion_path(movement_id))
    definition = load_definition(definition_path(movement_id))
    if definition.movement_id != movement_id or track.movement_id != movement_id:
        raise MovementDefinitionError(
            f"{movement_id}: the movement id inside the files does not match the "
            "file name, so the library cannot pair them"
        )

    ball = load_ball(ball_path(movement_id)) if has_ball(movement_id) else None
    method = (
        load_technique(technique_path(movement_id))
        if has_technique(movement_id)
        else None
    )
    possession = ball is not None and method is not None and method.possession_ready
    started = time.perf_counter()
    result = (
        solve_movement(character, movement_id)
        if possession
        else solve(character, track)
    )
    solve_seconds = time.perf_counter() - started

    measurements = result["measurements"]
    assessment = definition.assess(measurements)
    separation = definition.separation(measurements)
    violations = anatomy_violations(measurements)

    series = [frame["leftElbowFlexionDegrees"] for frame in measurements]
    steps = [abs(series[i + 1] - series[i]) for i in range(len(series) - 1)]
    leans = [frame["trunkLeanDegrees"] for frame in measurements]
    possession_receipt = {}
    if possession:
        held = result["possession"]
        possession_receipt = {
            "contactFrame": held.contact_frame,
            "contactPhase": round(held.frames[held.contact_frame].phase, 4),
            "turnedByDegrees": result["turnedByDegrees"],
            "biggestBallStepCm": round(held.biggest_ball_step_cm(), 2),
            "ballStepAtHandoverCm": round(
                held.ball_step_at(held.contact_frame), 2
            ),
            "worstSpikeAgainstNeighbours": spike_report(measurements)[
                "worstNeighbourRatio"
            ],
        }
    gaps = [
        abs(frame["leftElbowFlexionDegrees"] - frame["rightElbowFlexionDegrees"])
        for frame in measurements
    ]

    OUTPUT.mkdir(parents=True, exist_ok=True)
    glb_path = OUTPUT / f"{movement_id}.glb"
    export_note = "written"
    try:
        geometry.Character.save_gltf(
            str(glb_path),
            character,
            fps=track.frames_per_second,
            motion=(list(character.parameter_transform.names), result["motion"]),
        )
    except Exception as error:  # noqa: BLE001
        export_note = f"skipped: {type(error).__name__}: {str(error)[:100]}"

    receipt = {
        "movementId": movement_id,
        "sport": definition.sport,
        "skill": definition.skill,
        "source": definition.source,
        "movement": {
            "keys": list(describe(track)),
            # Reads all THREE files, because the solve does. Until 2026-09-02
            # this published the motion file alone, which for a possession
            # drill is the one file whose hand keys the solve ignores.
            "symmetric": movement_carries_no_side(track, ball, method),
            "frames": track.frames,
            "framesPerSecond": track.frames_per_second,
            "drivenBy": "the ball" if possession else "hand keys",
            "maxHandTargetMissCm": (
                None if possession else round(max(result["misses"]), 3)
            ),
            "solveMillisecondsPerFrame": round(
                solve_seconds / track.frames * 1000, 1
            ),
        },
        "measurement": {
            "method": "frame-free joint measures from joint centres",
            "largestElbowStepBetweenFramesDegrees": round(max(steps), 2),
            "maxTrunkLeanDegrees": round(max(leans), 2),
            "maxLeftRightElbowGapDegrees": round(max(gaps), 2),
            "perFrame": measurements,
        },
        "anatomy": {
            "status": "passed" if not violations else "failed",
            "violations": violations,
        },
        "possession": possession_receipt,
        # Report-only hand orientation, the measures Erin's contact cues need
        # (docs/COACH_REVIEW_2026-08-30.md, "supports neither"). Not part of
        # coaching.phases: those rows are graded and counted, these are read.
        "handOrientation": (
            receipt_section(result, definition)
            if possession
            else {
                "status": "unavailable",
                "note": "no possession solve, so no ball to measure against",
                "phases": {},
            }
        ),
        "coaching": assessment.to_receipt(),
        # Whether each phase's own checkpoints can tell it apart from the phase
        # before it. A checkpoint that cannot fail is not a check, and it
        # inflates the score above.
        "phaseSeparation": {
            "thresholdDegrees": MINIMUM_MEANINGFUL_BAND_DEGREES,
            "phases": [
                {
                    "phase": item.phase,
                    "movedFromPrevious": None
                    if item.moved is None
                    else round(item.moved, 2),
                    "measure": item.measure,
                    "distinguishable": item.distinguishable,
                }
                for item in separation
            ],
            "indistinguishable": [
                item.phase for item in separation if not item.distinguishable
            ],
        },
        "exports": {
            "glb": {
                "note": export_note,
                "sha256": hashlib.sha256(glb_path.read_bytes()).hexdigest()
                if glb_path.is_file()
                else None,
            }
        },
        "visualQa": {"referenceCompared": False},
        "contractStatus": "pending_visual_comparison",
        "generatedFrom": generated_from(),
    }
    (OUTPUT / f"{movement_id}.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    movements = library()
    if not movements:
        print("no movements found")
        return 1

    character = load_character()
    print(f"library: {len(movements)} movements\n")

    summaries = []
    failures = 0
    for movement_id in movements:
        try:
            receipt = build_one(character, movement_id)
        except (SolveError, MovementDefinitionError) as error:
            print(f"FAIL {movement_id}: {error}")
            failures += 1
            continue

        coaching = receipt["coaching"]
        checks = sum(len(rows) for rows in coaching["phases"].values())
        met = sum(
            1
            for rows in coaching["phases"].values()
            for row in rows
            if row["verdict"] == "within"
        )
        summaries.append(
            {
                "movementId": movement_id,
                "skill": receipt["skill"],
                "symmetric": receipt["movement"]["symmetric"],
                "checksMet": met,
                "checks": checks,
                "anatomy": receipt["anatomy"]["status"],
                "msPerFrame": receipt["movement"]["solveMillisecondsPerFrame"],
                "maxTrunkLeanDegrees": receipt["measurement"]["maxTrunkLeanDegrees"],
            }
        )
        blind = receipt["phaseSeparation"]["indistinguishable"]
        flag = (
            "ok "
            if met == checks and not receipt["anatomy"]["violations"] and not blind
            else "-> "
        )
        print(
            f"{flag}{receipt['skill']:<34} {met}/{checks} checks   "
            f"{receipt['movement']['solveMillisecondsPerFrame']:>4} ms/frame   "
            f"lean {receipt['measurement']['maxTrunkLeanDegrees']:>5.2f} deg   "
            f"{receipt['movement']['drivenBy']}"
        )
        if receipt["anatomy"]["violations"]:
            print(
                f"     anatomy: {len(receipt['anatomy']['violations'])} frames "
                f"outside range, first is {receipt['anatomy']['violations'][0]}"
            )
        if blind:
            for item in receipt["phaseSeparation"]["phases"]:
                if item["distinguishable"]:
                    continue
                print(
                    f"     [{item['phase']}] cannot fail: its checkpoints move "
                    f"{item['movedFromPrevious']} from the phase before, under "
                    f"the {MINIMUM_MEANINGFUL_BAND_DEGREES:.0f} threshold"
                )
        if met != checks:
            for phase, rows in coaching["phases"].items():
                for row in rows:
                    if row["verdict"] != "within":
                        print(
                            f"     [{phase}] {row['measure']} is {row['measured']}, "
                            f"band {row['band'][0]:.0f} to {row['band'][1]:.0f}"
                        )

    (OUTPUT / "index.json").write_text(
        json.dumps(
            {"generatedFrom": generated_from(), "movements": summaries},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nindex: {OUTPUT / 'index.json'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
