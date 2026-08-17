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
    knee_flexion_degrees,
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
# The legs are included because the manual coaches this drill from a wide base
# power position, which the knees have to produce.
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
    "upleg",
    "lowleg",
    "knee",
    "foot",
    "ankle",
)
# Shape parameters must never move, or the solver stretches the athlete.
FORBIDDEN = ("scale", "flexible")

# The manual keeps the feet static: "Worker is static with feet, in power
# position ready to move but use hands & arms to pull in ball." That is enforced
# by pinning the feet, not by locking the root. Pinning the feet and lowering the
# hips is what produces a power position; locking the root instead leaves the
# athlete standing straight-legged and lets the torso lean to reach the ball.
POWER_POSITION_DROP_CM = 9.0
FOOT_WEIGHT = 12.0


def joint_positions(character: geometry.Character, parameters: np.ndarray) -> np.ndarray:
    state = geometry.model_parameters_to_skeleton_state(character, parameters)
    return np.asarray(state).reshape(-1, 8)[:, :3]


def catch_trajectory(rest: np.ndarray, frame: int) -> float:
    """Return the phase of the catch, from 0 at the start to 1 at the finish."""
    return frame / (FRAME_COUNT - 1)


def hand_targets(
    rest_left: np.ndarray,
    rest_right: np.ndarray,
    phase: float,
    chest: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return where both hands should be at this phase of the catch.

    The shape of this trajectory comes from the coaches manual, not from
    guesswork. The manual coaches the two-hand snatch and pull-in as: react to
    the front, in front of the shoulder, take the ball with the arms almost
    straight, then pull the ball in to the chest.

    That means the arms extend to nearly full reach at contact, and only then
    fold. An earlier version of this function bent the elbows at contact and
    straightened them at the finish, which is the opposite of the coached
    technique.
    """
    contact = 0.55
    if phase <= contact:
        # Rise smoothly to full extension at contact.
        reach = 0.5 - 0.5 * math.cos(math.pi * phase / contact)
        pull_in = 0.0
    else:
        reach = 1.0
        # After contact the hands travel in to the chest.
        pull_in = 0.5 - 0.5 * math.cos(math.pi * (phase - contact) / (1.0 - contact))

    # Centimetres, because MHR works in centimetres.
    # Full extension in front. The reach must approach the arm length, roughly
    # 50 cm on this athlete, or the elbows never straighten.
    extension = np.array([0.0, 30.0, 52.0], dtype=np.float32)
    left = rest_left + extension * reach
    right = rest_right + extension * reach
    # The hands come together in front rather than staying out to the side.
    left[0] -= 22.0 * reach
    right[0] += 22.0 * reach

    if chest is not None and pull_in > 0.0:
        # Pull the ball in to the chest. This is what folds the elbows.
        chest_left = chest + np.array([-11.0, -6.0, 9.0], dtype=np.float32)
        chest_right = chest + np.array([11.0, -6.0, 9.0], dtype=np.float32)
        left = left + (chest_left - left) * pull_in
        right = right + (chest_right - right) * pull_in
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
    rest_chest = rest_positions[index["c_spine3"]].copy()
    rest_root = rest_positions[index["root"]].copy()

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
        left_target, right_target = hand_targets(
            rest_left, rest_right, phase, chest=rest_chest
        )

        position_error = solver2.PositionErrorFunction(character, weight=1.0)
        for joint, target in (("l_wrist", left_target), ("r_wrist", right_target)):
            position_error.add_constraint(
                index[joint],
                target=np.asarray(target, dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=1.0,
            )
        # Feet stay where they started, and the hips sit lower than standing.
        # Together these two facts are the power position.
        for foot in ("l_foot", "r_foot"):
            position_error.add_constraint(
                index[foot],
                target=np.asarray(rest_positions[index[foot]], dtype=np.float32),
                offset=np.zeros(3, dtype=np.float32),
                weight=FOOT_WEIGHT,
            )
        position_error.add_constraint(
            index["root"],
            target=np.asarray(
                rest_root - np.array([0.0, POWER_POSITION_DROP_CM, 0.0]),
                dtype=np.float32,
            ),
            offset=np.zeros(3, dtype=np.float32),
            weight=3.0,
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
            knee = knee_flexion_degrees(
                hip=point(f"{side}_upleg"),
                knee=point(f"{side}_lowleg"),
                ankle=point(f"{side}_foot"),
            )
            frame_measure[f"{prefix}ElbowFlexionDegrees"] = round(elbow, 2)
            frame_measure[f"{prefix}ShoulderElevationDegrees"] = round(elevation, 2)
            frame_measure[f"{prefix}KneeFlexionDegrees"] = round(knee, 2)
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
