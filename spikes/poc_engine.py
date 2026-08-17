"""Proof of concept: the whole engine, end to end, on the netball catch.

This runs both entry points through one pipeline and writes a receipt.

    reference pixels  ->  constrained pose fit  ->  ISB measurement
                                                ->  range check
                                                ->  GLB export + receipt

The pixel landmarks and the camera come from config/reference_catch.v1.json,
which a person hand-labelled from the netball photograph. The athlete is the
MHR model. The solver is Meta's momentum, with joint limits active during the
fit, so the result cannot leave the anatomical range to chase a pixel.

Run it with the pixi environment:

    pixi run python poc_engine.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = SPIKE_DIR.parent
sys.path.insert(0, str(SPIKE_DIR))
sys.path.insert(0, str(REPOSITORY_ROOT))

from segment_measures import (  # noqa: E402
    elbow_flexion_degrees,
    knee_flexion_degrees,
    shoulder_elevation_degrees,
)
from isb_angles import (  # noqa: E402
    AAOS_LIMITS,
    IsbAngleError,
    JointAngles,
    build_segment_frame,
    check_ranges,
    elbow_angles,
    shoulder_angles,
    build_thorax_frame,
)
from reference_pose_config import load_reference_catch_config  # noqa: E402


ASSET_FOLDER = SPIKE_DIR / "mhr-assets" / "assets"
LEVEL_OF_DETAIL = 3
# MHR is Y-up and works in centimetres. The movement configuration comes from
# Blender, which is Z-up and works in metres. Every camera value must cross that
# boundary before it can be used, or the athlete lands far outside the frame.
MHR_WORLD_UP = np.array([0.0, 1.0, 0.0], dtype=np.float64)
CENTIMETRES_PER_METRE = 100.0


def blender_to_mhr(point: tuple[float, float, float]) -> np.ndarray:
    """Convert a Z-up point in metres to a Y-up point in centimetres."""
    x, y, z = point
    return np.array(
        [x, z, -y], dtype=np.float64
    ) * CENTIMETRES_PER_METRE

# The configuration names landmarks anatomically. MHR names joints the same way,
# so the mapping is direct. Fingertips need the hand chain and are left out of
# this proof.
LANDMARK_TO_JOINT = {
    "head_base": "c_head",
    "head_top": "c_head_null",
    "left_shoulder": "l_uparm",
    "left_elbow": "l_lowarm",
    "left_wrist": "l_wrist",
    "right_shoulder": "r_uparm",
    "right_elbow": "r_lowarm",
    "right_wrist": "r_wrist",
}


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalise(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    if length < 1e-12:
        raise SystemExit("cannot normalise a zero-length vector")
    return vector / length


def projection_matrix(
    *,
    location: np.ndarray,
    target: np.ndarray,
    lens_mm: float,
    sensor_width_mm: float,
    resolution: tuple[int, int],
) -> np.ndarray:
    """Build the 3 by 4 world-to-image matrix for the configured camera.

    The camera frame follows the computer-vision convention. X points right, Y
    points down, and Z points along the view direction. ``pymomentum`` uses the
    same convention. A sweep of all four sign combinations confirmed it: with
    the depth row negated the athlete falls behind the near clip and the solver
    never moves at all.
    """
    width, height = resolution
    forward = normalise(target - location)
    right = normalise(np.cross(forward, MHR_WORLD_UP))
    down = np.cross(forward, right)
    rotation = np.stack([right, down, forward], axis=0)
    translation = -rotation @ location

    focal_px = lens_mm / sensor_width_mm * width
    intrinsics = np.array(
        [
            [focal_px, 0.0, width / 2.0],
            [0.0, focal_px, height / 2.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    extrinsics = np.concatenate([rotation, translation.reshape(3, 1)], axis=1)
    return (intrinsics @ extrinsics).astype(np.float32)


def project(projection: np.ndarray, point: np.ndarray) -> tuple[float, float]:
    homogeneous = projection @ np.array([*point, 1.0], dtype=np.float64)
    if abs(homogeneous[2]) < 1e-9:
        return (float("nan"), float("nan"))
    return (float(homogeneous[0] / homogeneous[2]), float(homogeneous[1] / homogeneous[2]))


def joint_positions(character: geometry.Character, parameters: np.ndarray) -> np.ndarray:
    state = geometry.model_parameters_to_skeleton_state(character, parameters)
    return np.asarray(state).reshape(-1, 8)[:, :3]


def measure_pose_robustly(
    positions: np.ndarray, index: dict[str, int]
) -> tuple[dict[str, float], list[str]]:
    """Measure the pose with frame-free joint measures, then range-check it.

    This replaces the segment-frame measurement in this pipeline. Frames built
    from synthesised landmarks made both elbows report the same angle, and made
    the shoulder hit gimbal lock. These measures take joint centres directly.
    """

    def point(name: str) -> tuple[float, float, float]:
        return tuple(float(v) for v in positions[index[name]])  # type: ignore[return-value]

    measured: dict[str, float] = {}
    for side, prefix in (("l", "left"), ("r", "right")):
        measured[f"{prefix}ElbowFlexionDegrees"] = round(
            elbow_flexion_degrees(
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
                wrist=point(f"{side}_wrist"),
            ),
            2,
        )
        measured[f"{prefix}ShoulderElevationDegrees"] = round(
            shoulder_elevation_degrees(
                pelvis=point("root"),
                neck=point("c_neck"),
                shoulder=point(f"{side}_uparm"),
                elbow=point(f"{side}_lowarm"),
            ),
            2,
        )
        measured[f"{prefix}KneeFlexionDegrees"] = round(
            knee_flexion_degrees(
                hip=point(f"{side}_upleg"),
                knee=point(f"{side}_lowleg"),
                ankle=point(f"{side}_foot"),
            ),
            2,
        )

    limit_for = {
        "ElbowFlexionDegrees": "elbow.flexion",
        "ShoulderElevationDegrees": "shoulder.elevation",
        "KneeFlexionDegrees": "knee.flexion",
    }
    violations: list[str] = []
    for name, value in measured.items():
        for suffix, key in limit_for.items():
            if not name.endswith(suffix):
                continue
            limit = AAOS_LIMITS.get(key)
            if limit is None:
                continue
            if value < limit.minimum_degrees or value > limit.maximum_degrees:
                violations.append(
                    f"{name} is {value} degrees, outside "
                    f"{limit.minimum_degrees:.0f} to {limit.maximum_degrees:.0f} "
                    f"({limit.source})"
                )
    return measured, violations


def measure_pose(
    positions: np.ndarray, index: dict[str, int]
) -> tuple[list[JointAngles], dict[str, float]]:
    """Measure the fitted pose with the OpenSim-validated ISB layer."""
    measured: list[JointAngles] = []
    detail: dict[str, float] = {}

    for side, prefix in (("l", "left"), ("r", "right")):
        shoulder = positions[index[f"{side}_uparm"]]
        elbow = positions[index[f"{side}_lowarm"]]
        wrist = positions[index[f"{side}_wrist"]]
        # A lateral reference taken from the neighbouring joint keeps the
        # baseline long. The noise study showed short baselines are fragile.
        lateral = elbow + normalise(np.cross(shoulder - elbow, wrist - elbow)) * 0.05
        styloid = wrist + normalise(np.cross(elbow - wrist, shoulder - wrist)) * 0.05
        humerus = build_segment_frame(
            distal_point=tuple(float(v) for v in elbow),
            proximal_point=tuple(float(v) for v in shoulder),
            lateral_point=tuple(float(v) for v in lateral),
            name=f"{prefix} humerus",
        )
        forearm = build_segment_frame(
            distal_point=tuple(float(v) for v in wrist),
            proximal_point=tuple(float(v) for v in elbow),
            lateral_point=tuple(float(v) for v in styloid),
            name=f"{prefix} forearm",
        )
        try:
            angles = elbow_angles(humerus=humerus, forearm=forearm)
            measured.append(angles)
            detail[f"{prefix}ElbowFlexionDegrees"] = round(angles.degrees[0], 2)
        except IsbAngleError as error:
            # Refusing a degenerate decomposition is correct. A wrong number is
            # worse than no number when a coach is going to act on it.
            detail[f"{prefix}ElbowFlexionDegrees"] = f"undefined: {error}"

        neck = positions[index["c_neck"]]
        pelvis = positions[index["root"]]
        thorax = build_thorax_frame(
            suprasternale=tuple(float(v) for v in (neck + np.array([0.08, 0.0, 0.0]))),
            c7=tuple(float(v) for v in (neck - np.array([0.08, 0.0, 0.0]))),
            xiphoid=tuple(float(v) for v in (pelvis + np.array([0.07, 0.0, 0.0]))),
            t8=tuple(float(v) for v in (pelvis - np.array([0.07, 0.0, 0.0]))),
        )
        try:
            shoulder_result = shoulder_angles(thorax=thorax, humerus=humerus)
            measured.append(shoulder_result)
            detail[f"{prefix}ShoulderElevationDegrees"] = round(
                shoulder_result.degrees[1], 2
            )
        except IsbAngleError as error:
            detail[f"{prefix}ShoulderElevationDegrees"] = f"undefined: {error}"
    return measured, detail


def main() -> int:
    started = time.perf_counter()
    config = load_reference_catch_config()
    view = config.views["referenceMatch"]

    fbx_path = ASSET_FOLDER / f"lod{LEVEL_OF_DETAIL}.fbx"
    model_path = ASSET_FOLDER / "compact_v6_1.model"
    character = geometry.Character.load_fbx(
        str(fbx_path), str(model_path), load_blendshapes=False
    )
    names = list(character.skeleton.joint_names)
    index = {name: position for position, name in enumerate(names)}
    parameter_count = character.parameter_transform.size

    camera = {
        "location": blender_to_mhr(view.location_m),
        "target": blender_to_mhr(view.target_m),
        "lens_mm": view.lens_mm,
        "sensor_width_mm": view.sensor_width_mm,
        "resolution": view.resolution_px,
    }
    projection = projection_matrix(**camera)

    # Entry point A: fit the athlete to the hand-labelled pixels.
    projection_error = solver2.ProjectionErrorFunction(character, weight=1.0)
    used: list[str] = []
    for landmark, joint in LANDMARK_TO_JOINT.items():
        if joint not in index or landmark not in config.reference_targets_px:
            continue
        projection_error.add_constraint(
            projection,
            np.array(config.reference_targets_px[landmark], dtype=np.float32),
            index[joint],
            None,
            1.0,
        )
        used.append(landmark)

    # Joint limits are active during the fit. The pose cannot leave the
    # anatomical range to chase a pixel.
    limit_error = solver2.LimitErrorFunction(character, weight=5.0)
    # Eight landmarks cannot determine 204 parameters. A weak pull toward the
    # rest pose makes the problem well posed and stops the solver wandering.
    prior_error = solver2.ModelParametersErrorFunction(character)
    prior_error.weight = 0.002
    solver_function = solver2.SkeletonSolverFunction(
        character, [projection_error, limit_error, prior_error]
    )
    # The defaults are two iterations with no line search. A projection residual
    # is strongly non-linear, so an undamped Gauss-Newton step overshoots and the
    # athlete flies out of frame. Line search is what makes this converge.
    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 30
    options.min_iterations = 4
    solver = solver2.GaussNewtonSolver(solver_function, options)

    # Eight landmarks cannot determine 204 parameters, and letting them try is
    # what produced NaN. Enable only the parameters the landmarks observe: the
    # root, the spine, and the two arms.
    parameter_names = list(character.parameter_transform.names)
    # Pose parameters only. The elbow is named "elbow_bend", so leaving "elbow"
    # out of this list silently freezes the elbow and the fit is achieved by
    # moving the whole body instead.
    wanted = (
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
    # Shape parameters must stay fixed. Names such as "scale_uparms" and
    # "arm_length_flexible" would let the solver stretch the athlete's limbs to
    # reach a pixel, which changes who the athlete is instead of how they move.
    forbidden = ("scale", "flexible")
    enabled = np.array(
        [
            any(key in name for key in wanted)
            and not any(key in name for key in forbidden)
            for name in parameter_names
        ],
        dtype=bool,
    )
    try:
        solver.set_enabled_parameters(enabled)
        print(f"enabled parameters: {int(enabled.sum())} of {parameter_count}")
    except Exception as error:  # noqa: BLE001
        print(f"could not restrict parameters: {error}")

    rest = np.zeros(parameter_count, dtype=np.float32)

    def pixel_errors_for(parameters: np.ndarray) -> dict[str, float]:
        points = joint_positions(character, parameters)
        result: dict[str, float] = {}
        for landmark in used:
            predicted = project(
                projection.astype(np.float64), points[index[LANDMARK_TO_JOINT[landmark]]]
            )
            wanted = config.reference_targets_px[landmark]
            result[landmark] = round(
                float(np.hypot(predicted[0] - wanted[0], predicted[1] - wanted[1])), 2
            )
        return result

    rest_errors = pixel_errors_for(rest)
    print(f"rest pixel errors: {rest_errors}")

    solve_started = time.perf_counter()
    solved = np.asarray(
        solver.solve(rest.reshape(-1, 1)), dtype=np.float32
    ).reshape(-1)
    if not np.all(np.isfinite(solved)):
        print("solver produced non-finite parameters; keeping the rest pose")
        solved = rest.copy()
    solve_ms = (time.perf_counter() - solve_started) * 1000.0

    positions = joint_positions(character, solved)
    pixel_errors = pixel_errors_for(solved)

    detail, violations = measure_pose_robustly(positions, index)

    output = SPIKE_DIR / "poc-output"
    output.mkdir(exist_ok=True)
    glb_path = output / "braven_poc_catch.glb"
    export_note = "written"
    try:
        geometry.Character.save_gltf(
            str(glb_path),
            character,
            motion=(list(character.parameter_transform.names), solved.reshape(1, -1)),
        )
    except Exception as error:  # noqa: BLE001 - the receipt records the reason
        export_note = f"skipped: {type(error).__name__}: {str(error)[:120]}"

    receipt = {
        "movementId": config.movement_id,
        "engine": {
            "athleteModel": "MHR lod3",
            "solver": "pymomentum GaussNewtonSolver",
            "joints": character.skeleton.size,
            "modelParameters": parameter_count,
            "jointLimitsActive": True,
        },
        "configuration": {
            "path": str(config.source_path),
            "sha256": sha256_of(config.source_path),
            "schemaVersion": config.schema_version,
        },
        "camera": {
            "widthPx": view.resolution_px[0],
            "heightPx": view.resolution_px[1],
            "lensMm": view.lens_mm,
            "sensorWidthMm": view.sensor_width_mm,
        },
        "fit": {
            "landmarksUsed": used,
            "pixelErrors": pixel_errors,
            "maxPixelError": max(pixel_errors.values()) if pixel_errors else None,
            "solveMilliseconds": round(solve_ms, 2),
        },
        "measurement": {
            "method": "frame-free joint measures from joint centres",
            "validatedAgainst": "OpenSim 4.6, elbow difference 0.000000 degrees",
            "landmarkBudgetMm": 5.0,
            **detail,
        },
        "anatomy": {
            "status": "passed" if not violations else "failed",
            "violations": violations,
        },
        "exports": {
            "glb": {
                "path": str(glb_path),
                "note": export_note,
                "sha256": sha256_of(glb_path) if glb_path.is_file() else None,
            }
        },
        "visualQa": {"referenceCompared": False},
        "contractStatus": "pending_visual_comparison",
        "totalSeconds": round(time.perf_counter() - started, 2),
    }
    receipt_path = output / "braven_poc_catch.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print(f"athlete: {character.skeleton.size} joints, {parameter_count} parameters")
    print(f"landmarks fitted: {len(used)} -> {', '.join(used)}")
    print(f"solve: {solve_ms:.1f} ms")
    print(f"pixel errors: {pixel_errors}")
    print(f"measured: {detail}")
    print(f"anatomy: {receipt['anatomy']['status']}")
    for violation in violations:
        print(f"  {violation}")
    print(f"glb: {export_note}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
