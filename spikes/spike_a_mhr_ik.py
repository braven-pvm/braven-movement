"""Spike A: pose an MHR athlete to an end-effector target, then measure it.

This is entry point B in one file. A coach drags a hand. The solver moves the
body. Joint limits keep the result anatomical. The measurement layer then reports
the elbow angle on ISB conventions.

Run it with the pixi environment, because it needs Meta's momentum:

    pixi run python spike_a_mhr_ik.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from isb_angles import build_segment_frame, elbow_angles  # noqa: E402


ASSET_FOLDER = Path(__file__).resolve().parent / "mhr-assets" / "assets"
LEVEL_OF_DETAIL = 3
SOLVE_REPEATS = 20


def load_character() -> geometry.Character:
    fbx_path = ASSET_FOLDER / f"lod{LEVEL_OF_DETAIL}.fbx"
    model_path = ASSET_FOLDER / "compact_v6_1.model"
    for path in (fbx_path, model_path):
        if not path.is_file():
            raise SystemExit(f"missing asset: {path}")
    return geometry.Character.load_fbx(
        str(fbx_path), str(model_path), load_blendshapes=False
    )


def joint_positions(character: geometry.Character, parameters: np.ndarray) -> np.ndarray:
    """Return the world position of every joint, one row each.

    A skeleton state row holds a translation, a quaternion, and a scale. Only
    the translation matters for landmark measurement.
    """
    state = geometry.model_parameters_to_skeleton_state(character, parameters)
    return np.asarray(state).reshape(-1, 8)[:, :3]


def exact_joint(names: list[str], wanted: str) -> int:
    """Return the index of the joint with exactly this name.

    Partial matching is unsafe here. ``l_wrist_twist`` contains ``l_wrist`` and
    appears first, so a substring search would select the twist joint.
    """
    try:
        return names.index(wanted)
    except ValueError:
        raise SystemExit(
            f"no joint named {wanted}. Upper-body names: "
            f"{[n for n in names if 'arm' in n or 'wrist' in n]}"
        ) from None


def main() -> int:
    character = load_character()
    skeleton = character.skeleton
    names = list(skeleton.joint_names)
    parameter_count = character.parameter_transform.size
    print(f"character: {skeleton.size} joints, {parameter_count} model parameters")

    rest = np.zeros(parameter_count, dtype=np.float32)
    rest_positions = joint_positions(character, rest)

    # MHR names the arm chain anatomically. The dedicated wrist twist joint is
    # where forearm pronation lives, so the wrist itself carries only bend.
    # MHR names the arm chain anatomically. The dedicated wrist twist joint is
    # where forearm pronation lives, so the name lookup must be exact.
    shoulder = exact_joint(names, "l_uparm")
    elbow = exact_joint(names, "l_lowarm")
    wrist = exact_joint(names, "l_wrist")
    print(
        f"chain: {names[shoulder]} -> {names[elbow]} -> {names[wrist]}"
    )

    # The coach drags the left hand up and forward, as if reaching for a ball.
    target = rest_positions[wrist] + np.array([0.0, 0.35, 0.30], dtype=np.float32)

    position_error = solver2.PositionErrorFunction(character, weight=1.0)
    position_error.add_constraint(
        wrist,
        target=target,
        offset=np.zeros(3, dtype=np.float32),
        weight=1.0,
        name="left_hand_target",
    )
    # Joint limits are what make the result anatomical rather than merely close.
    limit_error = solver2.LimitErrorFunction(character, weight=1.0)

    solver_function = solver2.SkeletonSolverFunction(
        character, [position_error, limit_error]
    )
    solver = solver2.GaussNewtonSolver(solver_function)

    solved = solver.solve(rest.reshape(-1, 1))
    start = time.perf_counter()
    for _ in range(SOLVE_REPEATS):
        solved = solver.solve(rest.reshape(-1, 1))
    elapsed_ms = (time.perf_counter() - start) / SOLVE_REPEATS * 1000.0

    solved = np.asarray(solved, dtype=np.float32).reshape(-1)
    positions = joint_positions(character, solved)

    reached = positions[wrist]
    residual_mm = float(np.linalg.norm(reached - target)) * 1000.0

    print(f"solve time: {elapsed_ms:.1f} ms per solve, averaged over {SOLVE_REPEATS}")
    print(f"target miss: {residual_mm:.2f} mm")

    # Measure the solved pose with the same layer that OpenSim validated.
    lateral = positions[elbow] + np.array([0.0, 0.0, -0.04], dtype=np.float32)
    styloid = positions[wrist] + np.array([0.0, 0.0, -0.03], dtype=np.float32)
    humerus = build_segment_frame(
        distal_point=tuple(float(v) for v in positions[elbow]),
        proximal_point=tuple(float(v) for v in positions[shoulder]),
        lateral_point=tuple(float(v) for v in lateral),
        name="humerus",
    )
    forearm = build_segment_frame(
        distal_point=tuple(float(v) for v in positions[wrist]),
        proximal_point=tuple(float(v) for v in positions[elbow]),
        lateral_point=tuple(float(v) for v in styloid),
        name="forearm",
    )
    angles = elbow_angles(humerus=humerus, forearm=forearm)
    print(f"ISB elbow angles: {angles.as_dict()}")

    if residual_mm > 20.0:
        print("FAIL the solver did not reach the target")
        return 1
    print("PASS the athlete reached the target under joint limits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
