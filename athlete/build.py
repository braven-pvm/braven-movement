"""Independent editable athlete authoring. Run with Blender 4.5 + MPFB.

blender -b --python-exit-code 9 -P athlete/build.py -- --output <directory>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bl_ext.blender_org.mpfb.services.humanservice import HumanService

ASSETS = Path(bpy.utils.user_resource('EXTENSIONS')) / '.user/blender_org/mpfb/data'


def material(name, colour, roughness=0.65):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*colour, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*colour, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    return mat


def freeze_mesh(obj):
    """Apply non-armature modifiers and morph mix while preserving vertex weights."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if obj.data.shape_keys:
        obj.shape_key_add(name='Baked phenotype', from_mix=True)
        while len(obj.data.shape_keys.key_blocks) > 1:
            obj.shape_key_remove(obj.data.shape_keys.key_blocks[0])
        obj.shape_key_clear()
    for mod in list(obj.modifiers):
        if mod.type != 'ARMATURE':
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except RuntimeError:
                obj.modifiers.remove(mod)
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.select_set(False)


def add_asset(human, relative, kind, name, used):
    path = ASSETS / relative
    header = path.read_text(encoding='utf-8', errors='replace')[:2000]
    if 'CC0' not in header:
        raise ValueError(f'Asset does not declare CC0: {path}')
    used.append(path)
    obj = HumanService.add_mhclo_asset(str(path), human, asset_type=kind,
                                      subdiv_levels=0, material_type='GAMEENGINE')
    obj.name = name
    obj['bravenRole'] = kind.lower()
    return obj


def portable_materials(parts):
    """Opaque skin, with cutout hair and the eye asset's transparent cornea UV island."""
    for obj in parts:
        cutout = obj.get('bravenRole') in {'hair', 'eyes', 'eyebrows', 'eyelashes'}
        for mat in obj.data.materials:
            if not mat.use_nodes:
                continue
            for node in list(mat.node_tree.nodes):
                if node.type != 'BSDF_PRINCIPLED':
                    continue
                alpha = node.inputs['Alpha']
                if cutout and alpha.is_linked:
                    source = alpha.links[0].from_socket
                    threshold = mat.node_tree.nodes.new('ShaderNodeMath')
                    threshold.operation = 'GREATER_THAN'
                    threshold.inputs[1].default_value = 0.45
                    mat.node_tree.links.new(source, threshold.inputs[0])
                    mat.node_tree.links.new(threshold.outputs[0], alpha)
                else:
                    for link in list(alpha.links):
                        mat.node_tree.links.remove(link)
                    alpha.default_value = 1
                node.inputs['Roughness'].default_value = 0.70 if cutout else 0.60
            mat.use_backface_culling = not cutout
    # Keep runtime texture memory modest. Editable MPFB source keeps its original maps.
    for image in bpy.data.images:
        if image.type == 'IMAGE' and image.size[0] > 2048:
            ratio = 2048 / image.size[0]
            image.scale(2048, round(image.size[1]*ratio))
            image.pack()


def scene_setup(rig):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new('Athlete studio world')
    scene.world.color = (0.35, 0.35, 0.35)
    scene.view_settings.view_transform = 'AgX'
    for name, position, power, size in [
        ('Key', (3, -4, 5), 700, 4), ('Fill', (-3, -1, 3), 500, 3),
        ('Rim', (1, 3, 4), 850, 3)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = power, 'DISK', size
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = position
        light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200)
    ground = bpy.context.object
    ground.name = 'Studio floor'
    ground.location.z = -0.012
    ground.data.materials.append(material('Studio', (0.28, 0.31, 0.31)))
    data = bpy.data.cameras.new('Athlete camera')
    camera = bpy.data.objects.new('Athlete camera', data)
    scene.collection.objects.link(camera)
    camera.location = (2.9, -5.4, 2.35)
    camera.rotation_euler = (Vector((0, 0, 0.92)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type, data.ortho_scale = 'ORTHO', 2.28
    scene.camera = camera
    rig.show_in_front = True
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
                area.spaces.active.shading.type = 'MATERIAL'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--base-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    phenotype = dict(age=0.28, gender=0, height=0.78, muscle=0.8, weight=0.30,
                     proportions=0.55, cupsize=0.25, firmness=0.8,
                     race={'african': 0.0, 'asian': 0.0, 'caucasian': 1.0})
    human = HumanService.create_human(mask_helpers=True, detailed_helpers=True,
        extra_vertex_groups=True, feet_on_ground=True, scale=0.1, macro_detail_dict=phenotype)
    human.name = 'Athlete_Body'
    human['bravenRole'] = 'body'
    rig = HumanService.add_builtin_rig(human, 'game_engine', import_weights=True)
    rig.name = 'Netball_Athlete'
    # Canonical runtime-facing names, including case. Native controls are separate.
    rig.data.bones['Root'].name = 'root'
    rig.data.bones['head'].name = 'Head'
    used = []
    skin = ASSETS / 'skins/young_caucasian_female/young_caucasian_female.mhmat'
    assert 'CC0' in skin.read_text(encoding='utf-8')[:2000]
    used.append(skin)
    HumanService.set_character_skin(str(skin), human, skin_type='GAMEENGINE', material_instances=False)
    parts = [human]
    for relative, kind, name in [
        ('hair/ponytail01/ponytail01.mhclo', 'Hair', 'Athlete_Hair'),
        ('eyes/high-poly/high-poly.mhclo', 'Eyes', 'Athlete_Eyes'),
        ('eyebrows/eyebrow006/eyebrow006.mhclo', 'Eyebrows', 'Athlete_Brows'),
        ('eyelashes/eyelashes01/eyelashes01.mhclo', 'Eyelashes', 'Athlete_Lashes'),
        ('clothes/shoes05/shoes05.mhclo', 'Clothes', 'Athlete_Shoes')]:
        parts.append(add_asset(human, relative, kind, name, used))
    # The full MakeHuman source is preserved for changing phenotype and rebuilding.
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'athlete-source.blend'))
    for obj in parts:
        freeze_mesh(obj)
    portable_materials(parts)
    human.data.materials[0].name = 'Skin'
    # Keep body topology including the covered body in the editable source.
    # The helper mask has already been applied by freeze_mesh.
    rig['bravenAthlete'] = 1
    rig['forwardAxis'] = '+Z in glTF / -Y in Blender'
    rig['description'] = 'Editable netball athlete. Actions are demonstrations; not coach-validated.'
    bpy.context.scene.render.fps = 30
    bones = {b.name: {'head': list(rig.matrix_world @ b.head_local),
                      'tail': list(rig.matrix_world @ b.tail_local)} for b in rig.data.bones}
    (output / 'base-inspection.json').write_text(json.dumps({
        'bones': bones, 'meshes': {o.name: {'vertices': len(o.data.vertices),
            'bounds': [[min((o.matrix_world @ v.co)[i] for v in o.data.vertices),
                        max((o.matrix_world @ v.co)[i] for v in o.data.vertices)] for i in range(3)]}
            for o in parts}}, indent=2))
    if args.base_only:
        bpy.ops.wm.save_as_mainfile(filepath=str(output / 'athlete-base.blend'))
        return
    from garments import build_kit
    from motion import build_actions, add_ik_controls
    parts.extend(build_kit(human, rig, material))
    build_actions(rig)
    add_ik_controls(rig)
    scene_setup(rig)
    # All garment alternatives travel in one model. Viewer selects visibility by role.
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [rig, *parts]:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.scene.frame_set(0)
    bpy.ops.export_scene.gltf(filepath=str(output / 'netball-athlete.glb'),
        export_format='GLB', use_selection=True, export_animations=True,
        export_animation_mode='ACTIONS', export_frame_range=False,
        export_force_sampling=True, export_skins=True, export_extras=True,
        export_def_bones=True, export_morph=True, export_materials='EXPORT',
        export_image_format='AUTO', export_yup=True)
    # Default Blender view: kit is dressed, relaxed ready animation is selected.
    rig.animation_data.action = bpy.data.actions['Ready']
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 91
    bpy.context.scene.frame_set(12)
    bpy.data.objects['Kit_Skirt'].hide_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'netball-athlete.blend'))
    if args.render:
        bpy.context.scene.render.filepath = str(output / 'athlete-preview.png')
        bpy.ops.render.render(write_still=True)
    manifest = {'schemaVersion': 1, 'name': 'Braven netball athlete', 'revision': 3, 'phenotype': phenotype,
        'kitFit': {'skirtBodyLengthM': 0.275, 'waistbandHeightM': 0.035, 'hemHeightM': 0.740,
                   'profile': 'Fitted hip contour with straight soft hem'},
        'seams': {'jersey': 'Connected shoulder bridges; continuous bound neckline and armholes',
                  'waist': 'Turned waistband with shared jersey weights and tucked overlap'},
        'generator': 'Independent Blender/MPFB authoring', 'blender': bpy.app.version_string,
        'animations': [a.name for a in bpy.data.actions],
        'roles': {o.name: o.get('bravenRole') for o in parts},
        'sources': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                     'licence': 'CC0 declared in source header'} for p in used],
        'files': {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in [output / 'netball-athlete.glb', output / 'netball-athlete.blend']}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('ATHLETE_COMPLETE', json.dumps(manifest['files']))


if __name__ == '__main__':
    main()
