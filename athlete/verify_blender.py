"""Open the delivered native files, move real IK targets and reimport the GLB."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = args.output.resolve()
manifest = json.loads((out / 'manifest.json').read_text())
expected_bones = manifest.get('deformationControls', 69)
expected_actions = len(manifest['animations'])
report = {'checks': [], 'ik': []}


def check(label, condition):
    assert condition, label
    report['checks'].append(label)


bpy.ops.wm.open_mainfile(filepath=str(out / 'athlete-source.blend'))
check('Full phenotype source retains editable shape keys',
      len(bpy.data.objects['Athlete_Body'].data.shape_keys.key_blocks) > 20)
bpy.ops.wm.open_mainfile(filepath=str(out / 'netball-athlete.blend'))
rig = bpy.data.objects['Netball_Athlete']
check('Native master has four additional non-deforming IK targets',
      len([b for b in rig.data.bones if b.name.startswith('CTRL_') and not b.use_deform]) == 4)
check('All image textures are packed into the native master',
      all(i.packed_file or i.packed_files for i in bpy.data.images if i.type == 'IMAGE' and i.source == 'FILE'))
check('All editable native Actions are retained', len(bpy.data.actions) == expected_actions)
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
for end in ('hand', 'foot'):
    for side in ('l', 'r'):
        prop = f'IK_{end}_{side}'
        target = rig.pose.bones[f'CTRL_{end}_{side}']
        joint = rig.pose.bones[f'{end}_{side}']
        before = joint.head.copy()
        offset = Vector(((-.10 if side == 'l' else .10) if end == 'hand' else 0,
                         -.10, .08 if end == 'hand' else .12))
        matrix = target.matrix.copy()
        matrix.translation += offset
        target.matrix = matrix
        rig[prop] = 1.0
        rig.update_tag()
        bpy.context.view_layer.update()
        moved = (joint.head - before).length
        residual = (joint.head - target.head).length
        check(f'{prop}: target drives the actual limb', moved > .05 and residual < .025)
        report['ik'].append({'control': prop, 'jointDisplacementM': moved, 'targetResidualM': residual})
        rig[prop] = 0.0
        target.matrix_basis.identity()
        rig.update_tag()
        bpy.context.view_layer.update()

# Open-standard round trip: Blender must reconstruct skins and clips from the GLB.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(out / 'netball-athlete.glb'))
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
check('GLB reimports into Blender with every deformation bone',
      len(armatures) == 1 and len(armatures[0].data.bones) == expected_bones)
check('GLB reimports all animations', len(bpy.data.actions) == expected_actions)
for name in ['Kit_Jersey', 'Kit_Shorts', 'Kit_Skirt', 'Athlete_Body']:
    obj = bpy.data.objects[name]
    check(f'{name}: armature modifier survives GLB round trip',
          any(m.type == 'ARMATURE' and m.object == armatures[0] for m in obj.modifiers))
report['assetSha256'] = json.loads((out / 'manifest.json').read_text())['files']['netball-athlete.glb']['sha256']
(out / 'blender-verification.json').write_text(json.dumps(report, indent=2))
print('BLENDER_VERIFIED', json.dumps(report))
