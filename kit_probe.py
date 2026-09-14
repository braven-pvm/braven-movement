"""Inventory the athlete the pipeline builds, before anything is painted.

Prints what a painted kit would have to touch: the body's image nodes, the
mask modifiers the clothes add to the body, the UV layers and the vertex
groups. Renders nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from reference_pose_config import load_reference_catch_config  # noqa: E402
from blender_mpfb_reference_catch import create_athlete  # noqa: E402

config = load_reference_catch_config(None)
human, rig, assets, source_assets = create_athlete(config.athlete, config.presentation)

print("=== ASSETS ===", flush=True)
for item in assets:
    print(f"  object {item.name!r} type={item.type}")

print("=== SOURCE ASSETS ===", flush=True)
for item in source_assets[:12]:
    print(f"  {item}")

print("=== HUMAN MATERIALS AND IMAGE NODES ===", flush=True)
for material in human.data.materials:
    if material is None:
        print("  <empty slot>")
        continue
    print(f"  material {material.name!r} use_nodes={material.use_nodes}")
    if not material.use_nodes:
        continue
    for node in material.node_tree.nodes:
        if node.type != "TEX_IMAGE":
            continue
        image = node.image
        print(
            f"    node {node.name!r} image="
            f"{None if image is None else image.name!r} "
            f"filepath={'' if image is None else image.filepath} "
            f"packed={None if image is None else bool(image.packed_file)} "
            f"colorspace={None if image is None else image.colorspace_settings.name}"
        )

print("=== HUMAN MODIFIERS ===", flush=True)
for modifier in human.modifiers:
    group = getattr(modifier, "vertex_group", None)
    print(f"  {modifier.name!r} type={modifier.type} vertex_group={group!r}")

print("=== HUMAN UV LAYERS ===", flush=True)
for layer in human.data.uv_layers:
    print(f"  {layer.name!r} active={layer.active}")

groups = [g.name for g in human.vertex_groups]
print(f"=== HUMAN VERTEX GROUPS ({len(groups)}) ===", flush=True)
for name in groups:
    print(f"  {name}")

print(f"=== HUMAN MESH: {len(human.data.vertices)} verts, "
      f"{len(human.data.polygons)} faces ===", flush=True)
print("PROBE OK", flush=True)

print("=== BODY MATERIAL NODE GRAPH ===", flush=True)
material = human.data.materials.get("BRAVEN_Athlete.body")
if material is None:
    print("  no BRAVEN_Athlete.body material")
else:
    for node in material.node_tree.nodes:
        print(f"  node {node.name!r} type={node.type} label={node.label!r}")
    print("  --- links ---")
    for link in material.node_tree.links:
        print(
            f"  {link.from_node.name!r}.{link.from_socket.name}"
            f"  ->  {link.to_node.name!r}.{link.to_socket.name}"
        )
print("PROBE GRAPH OK", flush=True)
