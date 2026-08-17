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

from catch_solver import (  # noqa: E402
    CONTACT_PHASE,
    FRAME_COUNT,
    load_character,
    solve_catch,
)
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

    # Two views, because the reach and the pull-in happen in depth. A front
    # view alone shows the arms swinging sideways and hides the whole skill.
    # Front looks along Z. Side looks along X, with the athlete facing right.
    stacked = np.concatenate(all_points, axis=0)
    minimum = stacked.min(axis=0)
    maximum = stacked.max(axis=0)
    floor = float(minimum[1])
    top = float(maximum[1])
    # One vertical scale for both views, so the athlete is the same height in each.
    scale = (VIEW_HEIGHT - 110) / max(top - floor, 1.0)
    centre_x = float(minimum[0] + maximum[0]) / 2.0
    centre_z = float(minimum[2] + maximum[2]) / 2.0

    def to_screen(position, view):
        across = float(position[0]) - centre_x if view == "front" else float(position[2]) - centre_z
        return [
            round(VIEW_WIDTH / 2 + across * scale, 1),
            round(VIEW_HEIGHT - 60 - (float(position[1]) - floor) * scale, 1),
        ]

    drawn = sorted({name for bone in BONES for name in bone if name in index})
    contact_frame = round(CONTACT_PHASE * (len(all_points) - 1))

    # The ball. It arrives from in front, meets the hands at contact, then
    # travels with them into the chest. Without it there is no catch to see.
    contact_points = all_points[contact_frame]
    meet = (
        contact_points[index["l_wrist"]] + contact_points[index["r_wrist"]]
    ) / 2.0
    # Close enough that the ball is inside the frame from the very first frame.
    # At 68 cm it started off the right edge of the side view.
    approach = meet + np.array([0.0, 20.0, 40.0])

    frames = []
    for number, points in enumerate(all_points):
        hands = (points[index["l_wrist"]] + points[index["r_wrist"]]) / 2.0
        if number < contact_frame:
            travel = number / max(contact_frame, 1)
            eased = travel * travel
            ball = approach + (meet - approach) * eased
        else:
            ball = hands
        entry = {"ball": {}}
        for view in ("front", "side"):
            screen = {}
            for name in drawn:
                screen[name] = to_screen(points[index[name]], view)
            entry[view] = screen
            entry["ball"][view] = to_screen(ball, view)
        frames.append(entry)

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
        "contactFrame": contact_frame,
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
