"""Export the athlete as a skinned body, not a stick figure.

Every viewer so far drew seven lines. MHR carries a real mesh, and the solver
already produces the skeleton state that poses it, so the body was there the
whole time and only the presentation was missing.

The mesh is taken at level of detail 5, which is 971 vertices and 1938 faces.
That is small enough to inline in a page with no external files, and still reads
as a person. Skinning happens here rather than in a shader, so the viewer only
has to draw triangles.

    pixi run python export_mesh_viewer.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pymomentum.geometry as geometry

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from motion_track import load_motion  # noqa: E402
from movement_definition import load as load_definition  # noqa: E402
from render_contact_sheet import BONES  # noqa: E402
from movement_engine import (  # noqa: E402
    ASSET_FOLDER,
    definition_path,
    library,
    motion_path,
    solve,
)

# Low enough to inline, high enough to read as a person.
VIEWER_LOD = 5
# A size 5 netball is 690 to 710 mm around, so about 22 cm across.
BALL_RADIUS_CM = 11.0
OUTPUT = SPIKE_DIR / "poc-output" / "library"


def load_mesh_character() -> geometry.Character:
    return geometry.Character.load_fbx(
        str(ASSET_FOLDER / f"lod{VIEWER_LOD}.fbx"),
        str(ASSET_FOLDER / "compact_v6_1.model"),
        load_blendshapes=False,
    )


def export(character: geometry.Character, movement_id: str) -> Path:
    track = load_motion(motion_path(movement_id))
    definition = load_definition(definition_path(movement_id))
    result = solve(character, track)

    faces = np.asarray(character.mesh.faces, dtype=np.int32)
    names = list(character.skeleton.joint_names)
    index = {name: number for number, name in enumerate(names)}
    bones = [pair for pair in BONES if all(n in index for n in pair)]

    frames = []
    skeletons = []
    hand_centres = []
    for parameters in result["motion"]:
        state = geometry.model_parameters_to_skeleton_state(
            character, np.asarray(parameters, dtype=np.float32)
        )
        joints = np.asarray(state).reshape(-1, 8)[:, :3]
        # Only the joints the skeleton overlay draws, so the page stays small.
        segment = []
        for first, second in bones:
            for joint in (first, second):
                segment.extend(
                    round(float(value), 1) for value in joints[index[joint]]
                )
        skeletons.append(segment)
        joint_rows = np.asarray(state).reshape(-1, 8)[:, :3]
        hand_centres.append(
            (joint_rows[index["l_wrist"]] + joint_rows[index["r_wrist"]]) / 2.0
        )
        skinned = np.asarray(character.skin_points(state), dtype=np.float64)
        # Only the vertices travel. Normals are recomputed from the faces in the
        # viewer, which costs nothing at this size and halves the page.
        frames.append([round(float(value), 1) for value in skinned.reshape(-1)])

    # The ball. It flies in, meets the hands at contact, then travels with them.
    # Without it a catch is a person grasping at nothing.
    contact = round(track.contact_phase() * (len(frames) - 1))
    meet = hand_centres[contact]
    approach = meet + np.array([0.0, 26.0, 78.0])
    balls = []
    for number, centre_now in enumerate(hand_centres):
        if number < contact:
            travel = number / max(contact, 1)
            eased = travel * travel
            ball = approach + (meet - approach) * eased
        else:
            ball = centre_now
        balls.append([round(float(value), 1) for value in ball])

    # One shared frame of reference, so the athlete does not drift or resize
    # between movements.
    everything = np.concatenate(
        [np.asarray(frame).reshape(-1, 3) for frame in frames], axis=0
    )
    payload = {
        "movementId": movement_id,
        "skill": definition.skill,
        "sport": definition.sport,
        "source": definition.source,
        "vertexCount": int(faces.max()) + 1,
        "faces": [int(value) for value in faces.reshape(-1)],
        "frames": frames,
        "skeletons": skeletons,
        "balls": balls,
        "ballRadius": BALL_RADIUS_CM,
        "boneCount": len(bones),
        "framesPerSecond": track.frames_per_second,
        "bounds": {
            "min": [round(float(value), 1) for value in everything.min(axis=0)],
            "max": [round(float(value), 1) for value in everything.max(axis=0)],
        },
        "measurements": result["measurements"],
        "phaseAnchors": {
            phase.name: phase.at_phase for phase in definition.phases
        },
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"{movement_id}.mesh.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def main() -> int:
    character = load_mesh_character()
    faces = np.asarray(character.mesh.faces)
    print(f"mesh: lod{VIEWER_LOD}, {int(faces.max()) + 1} vertices, {len(faces)} faces")

    total = 0
    for movement_id in library():
        path = export(character, movement_id)
        size = path.stat().st_size / 1024
        total += size
        print(f"  {movement_id:<42} {size:7.0f} KB")
    print(f"total {total / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
