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
import math
import sys
import time
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from segment_measures import (  # noqa: E402
    elbow_flexion_degrees,
    shoulder_elevation_degrees,
)
from isb_angles import AAOS_LIMITS  # noqa: E402
from movement_definition import load as load_movement  # noqa: E402

DEFINITION_PATH = SPIKE_DIR / "movements" / "netball_two_hand_catch.json"


ASSET_FOLDER = SPIKE_DIR / "mhr-assets" / "assets"
LEVEL_OF_DETAIL = 3
FRAME_COUNT = 24
FRAMES_PER_SECOND = 24.0

# Pose parameters only. Shape stays locked so the athlete keeps their body.
WANTED = (
    "root",
    "spine",
    "clavicle",
    "uparm",
    "lowarm",
    "elbow",
    "wrist",
    "neck",
    "head",
)
FORBIDDEN = ("scale", "flexible")


def joint_positions(character: geometry.Character, parameters: np.ndarray) -> np.ndarray:
    state = geometry.model_parameters_to_skeleton_state(character, parameters)
    return np.asarray(state).reshape(-1, 8)[:, :3]


def catch_trajectory(rest: np.ndarray, frame: int) -> float:
    """Return the phase of the catch, from 0 at the start to 1 at the finish."""
    return frame / (FRAME_COUNT - 1)


def hand_targets(
    rest_left: np.ndarray, rest_right: np.ndarray, phase: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return where both hands should be at this phase of the catch.

    The reach rises and extends, peaks at contact, then draws back toward the
    chest. A raised cosine keeps the speed smooth at both ends, which is what a
    coached movement looks like.
    """
    # Reach peaks at contact, which sits at 55 percent of the movement.
    contact = 0.55
    if phase <= contact:
        reach = 0.5 - 0.5 * math.cos(math.pi * phase / contact)
    else:
        reach = 0.5 + 0.5 * math.cos(math.pi * (phase - contact) / (1.0 - contact))
    pull_in = max(0.0, (phase - contact) / (1.0 - contact))

    # Centimetres, because MHR works in centimetres.
    forward = 26.0 * reach - 14.0 * pull_in
    rise = 22.0 * reach
    together = 9.0 * reach

    left = rest_left + np.array([-together, rise, forward], dtype=np.float32)
    right = rest_right + np.array([together, rise, forward], dtype=np.float32)
    return left, right


def main() -> int:
    started = time.perf_counter()
    character = geometry.Character.load_fbx(
        str(ASSET_FOLDER / f"lod{LEVEL_OF_DETAIL}.fbx"),
        str(ASSET_FOLDER / "compact_v6_1.model"),
        load_blendshapes=False,
    )
    names = list(character.skeleton.joint_names)
    index = {name: position for position, name in enumerate(names)}
    parameter_names = list(character.parameter_transform.names)
    parameter_count = character.parameter_transform.size

    enabled = np.array(
        [
            any(key in name for key in WANTED)
            and not any(key in name for key in FORBIDDEN)
            for name in parameter_names
        ],
        dtype=bool,
    )

    rest = np.zeros(parameter_count, dtype=np.float32)
    rest_positions = joint_positions(character, rest)
    rest_left = rest_positions[index["l_wrist"]].copy()
    rest_right = rest_positions[index["r_wrist"]].copy()

    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 30
    options.min_iterations = 4

    motion = np.zeros((FRAME_COUNT, parameter_count), dtype=np.float32)
    measurements: list[dict[str, float]] = []
    violations: list[str] = []
    misses: list[float] = []

    previous = rest.copy()
    solve_started = time.perf_counter()
    for frame in range(FRAME_COUNT):
        phase = catch_trajectory(rest, frame)
        left_target, right_target = hand_targets(rest_left, rest_right, phase)

        position_error = solver2.PositionErrorFunction(character, weight=1.0)
        for joint, target in (("l_wrist", left_target), ("r_wrist", right_target)):
            position_error.add_constraint(
                index[joint],
                target=np.asarray(target, dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=1.0,
            )
        limit_error = solver2.LimitErrorFunction(character, weight=5.0)
        # Continuity: pull toward the previous frame so the movement does not
        # jump between two equally valid solutions of the same target.
        continuity = solver2.ModelParametersErrorFunction(character)
        continuity.weight = 0.02

        solver_function = solver2.SkeletonSolverFunction(
            character, [position_error, limit_error, continuity]
        )
        solver = solver2.GaussNewtonSolver(solver_function, options)
        solver.set_enabled_parameters(enabled)

        solved = np.asarray(
            solver.solve(previous.reshape(-1, 1)), dtype=np.float32
        ).reshape(-1)
        if not np.all(np.isfinite(solved)):
            print(f"frame {frame}: solver produced non-finite values")
            solved = previous.copy()
        motion[frame] = solved
        previous = solved

        positions = joint_positions(character, solved)
        misses.append(
            float(np.linalg.norm(positions[index["l_wrist"]] - left_target))
        )

        def point(name: str) -> tuple[float, float, float]:
            return tuple(float(v) for v in positions[index[name]])  # type: ignore[return-value]

        frame_measure = {"phase": round(phase, 3)}
        for side, prefix in (("l", "left"), ("r", "right")):
            elbow = elbow_flexion_degrees(
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
                wrist=point(f"{side}_wrist"),
            )
            elevation = shoulder_elevation_degrees(
                pelvis=point("root"),
                neck=point("c_neck"),
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
            )
            frame_measure[f"{prefix}ElbowFlexionDegrees"] = round(elbow, 2)
            frame_measure[f"{prefix}ShoulderElevationDegrees"] = round(elevation, 2)
            for value, key in (
                (elbow, "elbow.flexion"),
                (elevation, "shoulder.elevation"),
            ):
                limit = AAOS_LIMITS[key]
                if value < limit.minimum_degrees or value > limit.maximum_degrees:
                    violations.append(
                        f"frame {frame}: {prefix} {key} is {value:.1f} degrees"
                    )
        measurements.append(frame_measure)
    solve_seconds = time.perf_counter() - solve_started

    # Continuity check: a coached movement has no jumps.
    elbow_series = [m["leftElbowFlexionDegrees"] for m in measurements]
    steps = [
        abs(elbow_series[i + 1] - elbow_series[i]) for i in range(len(elbow_series) - 1)
    ]
    largest_step = max(steps) if steps else 0.0

    output = SPIKE_DIR / "poc-output"
    output.mkdir(exist_ok=True)
    glb_path = output / "braven_catch_movement.glb"
    export_note = "written"
    try:
        geometry.Character.save_gltf(
            str(glb_path), character, fps=FRAMES_PER_SECOND,
            motion=(parameter_names, motion),
        )
    except Exception as error:  # noqa: BLE001
        export_note = f"skipped: {type(error).__name__}: {str(error)[:120]}"

    # The sport layer turns measured angles into what a coach would say.
    definition = load_movement(DEFINITION_PATH)
    assessment = definition.assess(measurements)

    receipt = {
        "movementId": definition.movement_id,
        "engine": {
            "athleteModel": f"MHR lod{LEVEL_OF_DETAIL}",
            "solver": "pymomentum GaussNewtonSolver, per frame",
            "enabledParameters": int(enabled.sum()),
            "totalParameters": parameter_count,
            "shapeLocked": True,
            "jointLimitsActive": True,
        },
        "movement": {
            "frames": FRAME_COUNT,
            "framesPerSecond": FRAMES_PER_SECOND,
            "contactPhase": 0.55,
            "maxHandTargetMissCm": round(max(misses), 3),
            "solveSecondsTotal": round(solve_seconds, 3),
            "solveMillisecondsPerFrame": round(solve_seconds / FRAME_COUNT * 1000, 1),
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

    print(f"frames: {FRAME_COUNT} at {FRAMES_PER_SECOND} fps")
    print(
        f"solve: {receipt['movement']['solveMillisecondsPerFrame']} ms per frame, "
        f"{receipt['movement']['solveSecondsTotal']} s total"
    )
    print(f"max hand target miss: {max(misses):.2f} cm")
    print(f"largest elbow step between frames: {largest_step:.2f} degrees")
    start = measurements[0]
    contact = measurements[int(0.55 * (FRAME_COUNT - 1))]
    finish = measurements[-1]
    for label, sample in (("start", start), ("contact", contact), ("finish", finish)):
        print(
            f"  {label:8s} left elbow {sample['leftElbowFlexionDegrees']:6.1f}  "
            f"left shoulder {sample['leftShoulderElevationDegrees']:6.1f}"
        )
    print(f"anatomy: {receipt['anatomy']['status']}")
    for violation in violations[:5]:
        print(f"  {violation}")
    print(f"coaching ({definition.skill}): "
          f"{'all checkpoints met' if assessment.correct else 'corrections needed'}")
    for note in assessment.coaching_notes():
        print(f"  {note}")
    print(f"glb: {export_note}")
    print(f"receipt: {receipt_path}")
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
