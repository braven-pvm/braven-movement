"""Export the solved movement as data a viewer can draw.

Produces one JSON file holding every frame's 2D skeleton, every frame's measured
angles, the coaching assessment, and the manual photograph as a data URI. The
viewer needs nothing else.

    pixi run python export_viewer_data.py
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry
import pymomentum.solver2 as solver2

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from movement_definition import load as load_movement  # noqa: E402
from render_contact_sheet import BONES  # noqa: E402
from segment_measures import (  # noqa: E402
    elbow_flexion_degrees,
    shoulder_elevation_degrees,
)
from spike_f_movement import (  # noqa: E402
    ASSET_FOLDER,
    DEFINITION_PATH,
    FORBIDDEN,
    FRAME_COUNT,
    LEVEL_OF_DETAIL,
    WANTED,
    catch_trajectory,
    hand_targets,
    joint_positions,
)

REFERENCE_PHOTO = (
    SPIKE_DIR.parent
    / "references"
    / "202526 updated coaches manual"
    / "_page_71_Picture_13.jpeg"
)
VIEW_WIDTH = 420
VIEW_HEIGHT = 560


def main() -> int:
    character = geometry.Character.load_fbx(
        str(ASSET_FOLDER / f"lod{LEVEL_OF_DETAIL}.fbx"),
        str(ASSET_FOLDER / "compact_v6_1.model"),
        load_blendshapes=False,
    )
    names = list(character.skeleton.joint_names)
    index = {name: position for position, name in enumerate(names)}
    parameter_names = list(character.parameter_transform.names)
    count = character.parameter_transform.size
    enabled = np.array(
        [
            any(key in name for key in WANTED)
            and not any(key in name for key in FORBIDDEN)
            for name in parameter_names
        ],
        dtype=bool,
    )
    options = solver2.GaussNewtonSolverOptions()
    options.do_line_search = True
    options.max_iterations = 30
    options.min_iterations = 4

    rest = np.zeros(count, dtype=np.float32)
    rest_positions = joint_positions(character, rest)
    rest_left = rest_positions[index["l_wrist"]].copy()
    rest_right = rest_positions[index["r_wrist"]].copy()
    rest_chest = rest_positions[index["c_spine3"]].copy()

    all_points: list[np.ndarray] = []
    measurements: list[dict[str, float]] = []
    previous = rest.copy()
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
        continuity = solver2.ModelParametersErrorFunction(character)
        continuity.weight = 0.02
        function = solver2.SkeletonSolverFunction(
            character,
            [
                position_error,
                solver2.LimitErrorFunction(character, weight=5.0),
                continuity,
            ],
        )
        solver = solver2.GaussNewtonSolver(function, options)
        solver.set_enabled_parameters(enabled)
        solved = np.asarray(
            solver.solve(previous.reshape(-1, 1)), dtype=np.float32
        ).reshape(-1)
        previous = solved
        points = joint_positions(character, solved)
        all_points.append(points)

        def point(name: str) -> tuple[float, float, float]:
            return tuple(float(v) for v in points[index[name]])  # type: ignore[return-value]

        entry = {"phase": round(phase, 4)}
        for side, prefix in (("l", "left"), ("r", "right")):
            entry[f"{prefix}ElbowFlexionDegrees"] = round(
                elbow_flexion_degrees(
                    shoulder=point(f"{side}_uparm"),
                    elbow=point(f"{side}_lowarm"),
                    wrist=point(f"{side}_wrist"),
                ),
                1,
            )
            entry[f"{prefix}ShoulderElevationDegrees"] = round(
                shoulder_elevation_degrees(
                    pelvis=point("root"),
                    neck=point("c_neck"),
                    shoulder=point(f"{side}_uparm"),
                    elbow=point(f"{side}_lowarm"),
                ),
                1,
            )
        measurements.append(entry)

    # A shared scale across all frames, so the athlete does not drift or resize.
    stacked = np.concatenate(all_points, axis=0)
    minimum = stacked.min(axis=0)
    maximum = stacked.max(axis=0)
    span = float(max(maximum[0] - minimum[0], maximum[1] - minimum[1])) or 1.0
    scale = (VIEW_HEIGHT - 90) / span
    # Cast out of numpy, or the JSON encoder rejects float32 later.
    centre_x = float(minimum[0] + maximum[0]) / 2.0
    floor = float(minimum[1])

    drawn = sorted({name for bone in BONES for name in bone if name in index})
    frames = []
    for points in all_points:
        screen = {}
        for name in drawn:
            position = points[index[name]]
            screen[name] = [
                round(VIEW_WIDTH / 2 + (float(position[0]) - centre_x) * scale, 1),
                round(VIEW_HEIGHT - 45 - (float(position[1]) - floor) * scale, 1),
            ]
        frames.append(screen)

    definition = load_movement(DEFINITION_PATH)
    assessment = definition.assess(measurements)

    photo_uri = ""
    if REFERENCE_PHOTO.is_file():
        encoded = base64.b64encode(REFERENCE_PHOTO.read_bytes()).decode("ascii")
        photo_uri = f"data:image/jpeg;base64,{encoded}"

    payload = {
        "skill": definition.skill,
        "sport": definition.sport,
        "source": definition.source,
        "view": {"width": VIEW_WIDTH, "height": VIEW_HEIGHT},
        "bones": [list(bone) for bone in BONES if all(n in index for n in bone)],
        "frames": frames,
        "measurements": measurements,
        "coaching": assessment.to_receipt(),
        "referencePhoto": photo_uri,
    }
    output = SPIKE_DIR / "poc-output" / "viewer_data.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(payload), encoding="utf-8")
    print(f"viewer data: {output}")
    print(f"frames: {len(frames)}  bones: {len(payload['bones'])}")
    print(f"photo embedded: {'yes' if photo_uri else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
