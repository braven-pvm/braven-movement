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

from catch_solver import FRAME_COUNT, load_character, solve_catch  # noqa: E402
from movement_definition import load as load_movement  # noqa: E402
from render_contact_sheet import BONES  # noqa: E402

DEFINITION_PATH = SPIKE_DIR / "movements" / "netball_two_hand_catch.json"

REFERENCE_PHOTO = (
    SPIKE_DIR.parent
    / "references"
    / "202526 updated coaches manual"
    / "_page_71_Picture_13.jpeg"
)
VIEW_WIDTH = 420
VIEW_HEIGHT = 560


def main() -> int:
    character = load_character()
    result = solve_catch(character)
    index = result["index"]
    all_points = result["points"]
    measurements = result["measurements"]

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
