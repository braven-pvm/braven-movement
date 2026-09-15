"""Regression checks for disconnected garment pieces and an opening waist join."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils.bvhtree import BVHTree

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = args.output.resolve()
bpy.ops.wm.open_mainfile(filepath=str(out / 'netball-athlete.blend'))
report = {'assetSha256': hashlib.sha256((out / 'netball-athlete.glb').read_bytes()).hexdigest(),
          'checks': [], 'meshes': {}, 'waist': []}


def check(label, condition):
    assert condition, label
    report['checks'].append(label)


for name, count in [('Kit_Jersey', 1), ('Kit_Binding', 3), ('Kit_Skirt', 1)]:
    obj = bpy.data.objects[name]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    remaining = set(bm.verts)
    components = []
    while remaining:
        stack = [remaining.pop()]
        size = 0
        while stack:
            v = stack.pop()
            size += 1
            for edge in v.link_edges:
                neighbor = edge.other_vert(v)
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append(size)
    boundary = sum(e.is_boundary for e in bm.edges)
    report['meshes'][name] = {'components': components, 'boundaryEdges': boundary}
    check(f'{name}: expected connected fabric pieces', len(components) == count)
    check(f'{name}: no non-manifold junctions', all(e.is_manifold or e.is_boundary for e in bm.edges))
    check(f'{name}: no zero-area faces', all(f.calc_area() > 1e-12 for f in bm.faces))
    if name != 'Kit_Skirt':
        check(f'{name}: fabric thickness and binding close every edge', boundary == 0)
    else:
        check('Skirt has only its waist and hem boundaries', boundary == 192)
    bm.free()

rig = bpy.data.objects['Netball_Athlete']
shirt = bpy.data.objects['Kit_Jersey']
skirt = bpy.data.objects['Kit_Skirt']
shorts = bpy.data.objects['Kit_Shorts']
check('Accepted skirt hem height is preserved', abs(min(v.co.z for v in skirt.data.vertices) - .740) < 1e-5)
check('Waistband covers the top of the shorts by at least 25 mm',
      max(v.co.z for v in skirt.data.vertices) - max(v.co.z for v in shorts.data.vertices) > .025)
check('Jersey has at least 80 mm of tucked overlap',
      max(v.co.z for v in skirt.data.vertices) - min(v.co.z for v in shirt.data.vertices) > .08)
# The inner turned lip is the highest boundary ring, identified geometrically.
bm = bmesh.new()
bm.from_mesh(skirt.data)
lip = [v.index for v in bm.verts if v.is_boundary and v.co.z > 1]
bm.free()
check('Waist lip is a complete ring', len(lip) == 96)
for action in bpy.data.actions:
    rig.animation_data.action = action
    worst = 0
    samples = 31
    for step in range(samples):
        frame = action.frame_range[0] + (action.frame_range[1] - action.frame_range[0]) * step / (samples - 1)
        bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
        dg = bpy.context.evaluated_depsgraph_get()
        s = shirt.evaluated_get(dg)
        k = skirt.evaluated_get(dg)
        mesh = s.to_mesh()
        tree = BVHTree.FromPolygons([s.matrix_world @ v.co for v in mesh.vertices],
                                   [list(f.vertices) for f in mesh.polygons])
        distances = [tree.find_nearest(k.matrix_world @ k.data.vertices[i].co)[3] for i in lip]
        worst = max(worst, max(distances))
        s.to_mesh_clear()
    report['waist'].append({'clip': action.name, 'samples': samples, 'maximumLipDistanceM': worst})
    check(f'{action.name}: waist join stays within 3 mm through the complete clip', worst < .003)
(out / 'seam-verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
