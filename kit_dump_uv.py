"""Dump the athlete's body mesh, so a kit can be painted without Blender.

Writes one .npz: rest-pose coordinates, the UV of every loop, the polygons,
and the weight of the bone groups a garment boundary is cut from. Painting
then runs in plain Python in seconds, and Blender is paid for once.

    blender -b --python-exit-code 9 -P kit_dump_uv.py -- --output out/kit/body.npz
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy
import numpy as np

REPO = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from reference_pose_config import load_reference_catch_config  # noqa: E402
from blender_mpfb_reference_catch import create_athlete  # noqa: E402

GROUPS = (
    "body",
    "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head",
    "clavicle_l", "clavicle_r",
    "upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r", "hand_l", "hand_r",
    "thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l", "foot_r",
) + tuple(
    # THE FINGERS ARE THEIR OWN BONES. A garment rule that excludes the hand
    # by `hand_l` alone leaves every finger vertex outside the hand group, and
    # the first painted kit put the dress colour on her fingers.
    f"{name}_{number:02d}_{side}"
    for name in ("index", "middle", "pinky", "ring", "thumb")
    for number in (1, 2, 3)
    for side in ("l", "r")
)

argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
output = Path(argv[argv.index("--output") + 1]).resolve()
output.parent.mkdir(parents=True, exist_ok=True)

config = load_reference_catch_config(None)
human, rig, assets, source_assets = create_athlete(config.athlete, config.presentation)

# THE MASKS COME OFF FIRST. They delete the helper vertices and the body under
# the clothes, and the body under the clothes is exactly the surface a painted
# kit is painted on. Evaluate with them on and the garment region is missing.
for modifier in human.modifiers:
    if modifier.type == "MASK":
        modifier.show_viewport = False
depsgraph = bpy.context.evaluated_depsgraph_get()
depsgraph.update()
evaluated = human.evaluated_get(depsgraph)
mesh = evaluated.to_mesh()

vertex_count = len(mesh.vertices)
if vertex_count != len(human.data.vertices):
    raise SystemExit(
        f"[kit-dump] the evaluated mesh has {vertex_count} vertices and the "
        f"original has {len(human.data.vertices)}. The group weights below are "
        f"read off the original and would not line up."
    )

co = np.empty(vertex_count * 3, dtype=np.float32)
mesh.vertices.foreach_get("co", co)
co = co.reshape(vertex_count, 3)

loop_count = len(mesh.loops)
loop_vert = np.empty(loop_count, dtype=np.int32)
mesh.loops.foreach_get("vertex_index", loop_vert)
uv_layer = mesh.uv_layers.active
if uv_layer is None:
    raise SystemExit("[kit-dump] the body mesh has no active UV layer")
uv = np.empty(loop_count * 2, dtype=np.float32)
uv_layer.data.foreach_get("uv", uv)
uv = uv.reshape(loop_count, 2)

polygon_count = len(mesh.polygons)
loop_start = np.empty(polygon_count, dtype=np.int32)
mesh.polygons.foreach_get("loop_start", loop_start)
loop_total = np.empty(polygon_count, dtype=np.int32)
mesh.polygons.foreach_get("loop_total", loop_total)

# Weights off the ORIGINAL object: a vertex carries its groups there, and the
# evaluated copy is only shape.
indices = {}
for name in GROUPS:
    group = human.vertex_groups.get(name)
    if group is None:
        print(f"[kit-dump] no vertex group named {name!r}", flush=True)
        continue
    indices[name] = group.index
weights = {name: np.zeros(vertex_count, dtype=np.float32) for name in indices}
for vertex in human.data.vertices:
    for element in vertex.groups:
        for name, index in indices.items():
            if element.group == index:
                weights[name][vertex.index] = element.weight

payload = {
    "co": co,
    "uv": uv,
    "loop_vert": loop_vert,
    "loop_start": loop_start,
    "loop_total": loop_total,
}
for name, array in weights.items():
    payload[f"w_{name}"] = array
np.savez_compressed(output, **payload)

low = co.min(axis=0)
high = co.max(axis=0)
print(f"[kit-dump] vertices {vertex_count} loops {loop_count} polygons {polygon_count}")
print(f"[kit-dump] bounds min {low.tolist()} max {high.tolist()}")
print(f"[kit-dump] groups dumped: {', '.join(sorted(weights))}")
print(f"[kit-dump] wrote {output} ({output.stat().st_size} bytes)")
print("KIT DUMP OK", flush=True)
