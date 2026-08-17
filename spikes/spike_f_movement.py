"""Spike F: a simple movement, not just a pose.

A coach does not only pose an athlete. They show a movement. This spike drives
the two hands along a catch trajectory, solves every frame under joint limits,
keeps the frames continuous, measures every frame, and exports one animated GLB
with a receipt.

The movement is the netball two-hand catch: hands start in a ready position in
front of the chest, reach out and up to meet the ball, then draw the ball back
in to the chest. That is the "snatch pull-in" the configuration names.

    pixi run python spike_f_movement.py
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

from catch_solver import (  # noqa: E402
    FRAMES_PER_SECOND,
    LEVEL_OF_DETAIL,
    MOTION_PATH,
    load_character,
    solve_catch,
)
from isb_angles import AAOS_LIMITS  # noqa: E402
from motion_track import describe, load_motion  # noqa: E402
from movement_definition import load as load_movement  # noqa: E402

DEFINITION_PATH = SPIKE_DIR / "movements" / "netball_two_hand_catch.json"


def main() -> int:
    started = time.perf_counter()
    character = load_character()
    track = load_motion(MOTION_PATH)

    solve_started = time.perf_counter()
    result = solve_catch(character)
    solve_seconds = time.perf_counter() - solve_started

    measurements = result["measurements"]
    misses = result["misses"]
    motion = result["motion"]
    frame_count = len(measurements)

    violations: list[str] = []
    for number, frame in enumerate(measurements):
        for prefix in ("left", "right"):
            for suffix, key in (
                ("ElbowFlexionDegrees", "elbow.flexion"),
                ("ShoulderElevationDegrees", "shoulder.elevation"),
                ("KneeFlexionDegrees", "knee.flexion"),
            ):
                value = frame[f"{prefix}{suffix}"]
                limit = AAOS_LIMITS[key]
                if value < limit.minimum_degrees or value > limit.maximum_degrees:
                    violations.append(
                        f"frame {number}: {prefix} {key} is {value:.1f} degrees"
                    )

    series = [frame["leftElbowFlexionDegrees"] for frame in measurements]
    steps = [abs(series[i + 1] - series[i]) for i in range(len(series) - 1)]
    largest_step = max(steps) if steps else 0.0

    definition = load_movement(DEFINITION_PATH)
    assessment = definition.assess(measurements)

    output = SPIKE_DIR / "poc-output"
    output.mkdir(exist_ok=True)
    glb_path = output / "braven_catch_movement.glb"
    export_note = "written"
    try:
        geometry.Character.save_gltf(
            str(glb_path),
            character,
            fps=FRAMES_PER_SECOND,
            motion=(list(character.parameter_transform.names), motion),
        )
    except Exception as error:  # noqa: BLE001
        export_note = f"skipped: {type(error).__name__}: {str(error)[:120]}"

    receipt = {
        "movementId": definition.movement_id,
        "engine": {
            "athleteModel": f"MHR lod{LEVEL_OF_DETAIL}",
            "solver": "pymomentum GaussNewtonSolver, per frame",
            "enabledParameters": int(result["enabled"].sum()),
            "shapeLocked": True,
            "jointLimitsActive": True,
        },
        "movement": {
            "source": str(MOTION_PATH.name),
            "keys": list(describe(track)),
            "frames": frame_count,
            "framesPerSecond": FRAMES_PER_SECOND,
            "maxHandTargetMissCm": round(max(misses), 3),
            "solveSecondsTotal": round(solve_seconds, 3),
            "solveMillisecondsPerFrame": round(solve_seconds / frame_count * 1000, 1),
        },
        "measurement": {
            "method": "frame-free joint measures from joint centres",
            "largestElbowStepBetweenFramesDegrees": round(largest_step, 2),
            "perFrame": measurements,
        },
        "anatomy": {
            "status": "passed" if not violations else "failed",
            "violations": violations,
        },
        "coaching": assessment.to_receipt(),
        "exports": {
            "glb": {
                "path": str(glb_path),
                "note": export_note,
                "sha256": hashlib.sha256(glb_path.read_bytes()).hexdigest()
                if glb_path.is_file()
                else None,
            }
        },
        "visualQa": {"referenceCompared": False},
        "contractStatus": "pending_visual_comparison",
        "totalSeconds": round(time.perf_counter() - started, 2),
    }
    receipt_path = output / "braven_catch_movement.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print(f"movement: {MOTION_PATH.name}")
    for line in describe(track):
        print(f"  {line}")
    print(f"frames: {frame_count} at {FRAMES_PER_SECOND} fps")
    print(
        f"solve: {receipt['movement']['solveMillisecondsPerFrame']} ms per frame"
    )
    print(f"max hand target miss: {max(misses):.2f} cm")
    print(f"largest elbow step between frames: {largest_step:.2f} degrees")
    for label, number in (
        ("start", 0),
        ("contact", round(0.55 * (frame_count - 1))),
        ("finish", frame_count - 1),
    ):
        sample = measurements[number]
        print(
            f"  {label:8s} left elbow {sample['leftElbowFlexionDegrees']:6.1f}  "
            f"left shoulder {sample['leftShoulderElevationDegrees']:6.1f}"
        )
    print(f"anatomy: {receipt['anatomy']['status']}")
    for violation in violations[:5]:
        print(f"  {violation}")
    print(
        f"coaching ({definition.skill}): "
        f"{'all checkpoints met' if assessment.correct else 'corrections needed'}"
    )
    for note in assessment.coaching_notes():
        print(f"  {note}")
    print(f"glb: {export_note}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
