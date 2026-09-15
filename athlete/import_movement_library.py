"""Retarget the pinned Movement jobs onto the existing editable athlete."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from garments import attach
from build import material


def add_ball(rig):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bone = rig.data.edit_bones.new('Ball_Control')
    bone.head, bone.tail = (0, -.32, 1.25), (0, -.32, 1.40)
    bone.parent = rig.data.edit_bones['root']
    bpy.ops.object.mode_set(mode='OBJECT')
    white = material('Movement_Ball', (.88, .86, .77))
    seam = material('Movement_Ball_Seams', (.015, .15, .14))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=.11, location=(0, -.32, 1.25))
    ball = bpy.context.object
    ball.name = 'Movement_Ball'
    ball.data.materials.append(white)
    pieces = [ball]
    for rotation in [(0, 0, 0), (math.pi / 2, 0, 0), (0, math.pi / 2, 0)]:
        bpy.ops.mesh.primitive_torus_add(major_radius=.1102, minor_radius=.0008,
                                       major_segments=64, minor_segments=6,
                                       location=(0, -.32, 1.25), rotation=rotation)
        part = bpy.context.object
        part.data.materials.append(seam)
        pieces.append(part)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in pieces:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = ball
    bpy.ops.object.join()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ball.vertex_groups.new(name='Ball_Control').add(list(range(len(ball.data.vertices))), 1, 'REPLACE')
    attach(ball, rig, 'movementBall')
    ball.select_set(False)
    return ball


def retarget(rig, job, ref, rest):
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
        bone.rotation_mode = 'QUATERNION'
    bpy.context.view_layer.update()
    head = lambda name: ref.world_head(rig, name)
    apply = lambda name, rotation: ref.apply_world_rotation(rig, name, head(name), rotation.to_matrix())
    # Root travel and airborne height are retained separately from the leg pose.
    ankles = {s: Vector(job['stance']['ankleFromPelvisInLegs'][s]) * rest['leg'] for s in ('l', 'r')}
    root_offset = Vector(job['rootOffsetInLegs']) * rest['leg']
    target = rest['pelvis'] + Vector((root_offset.x, root_offset.y, 0))
    target.z = rest['floor'] - min(v.z for v in ankles.values()) + job['airborneInLegs'] * rest['leg']
    ref.translate_bone_world(rig, 'pelvis', target - head('pelvis'))
    apply('pelvis', Quaternion((0, 0, 1), job['pelvisYawRadians']))
    current = ((head('upperarm_l') + head('upperarm_r')) / 2 - head('pelvis')).normalized()
    delta = current.rotation_difference(Vector(job['trunkDirection']).normalized())
    part = Quaternion().slerp(delta, 1 / 3)
    for name in ('spine_01', 'spine_02', 'spine_03'):
        apply(name, part)
    shoulder_targets = {}
    for side in ('l', 'r'):
        target = head('pelvis') + rest['shoulders'][side] + Vector(job['shoulderShiftFromRestInTorsos'][side]) * rest['torso']
        shoulder_targets[side] = target
        ref.rotate_bone_toward(rig, f'clavicle_{side}', f'upperarm_{side}', target)
        ankle = head('pelvis') + ankles[side]
        thigh, calf, foot = f'thigh_{side}', f'calf_{side}', f'foot_{side}'
        hip = head(thigh)
        knee = ref.elbow_for_target(hip, ankle, (head(calf) - hip).length,
                                   (head(foot) - head(calf)).length, Vector((0, -1, 0)))
        ref.rotate_bone_toward(rig, thigh, calf, knee)
        ref.rotate_bone_toward(rig, calf, foot, ankle)
        flat = rest['feet'][foot].copy()
        flat.translation = rig.pose.bones[foot].matrix.translation
        rig.pose.bones[foot].matrix = flat
        bpy.context.view_layer.update()
    midpoint = (head('upperarm_l') + head('upperarm_r')) / 2
    ball = midpoint + Vector(job['ball']['fromShouldersInArms']) * rest['arm']
    errors = []
    for side in ('l', 'r'):
        arm = job['arms'][side]
        grip = job.get('grip', {}).get(side)
        target = (ball + Vector(grip['outward']) * (job['ball']['radiusM'] + grip['wristFromSurfaceInArms'] * rest['arm'])) if grip else (
            head(f'upperarm_{side}') + Vector(arm['direction']) * arm['reachFraction'] * rest['arm'])
        ref.pose_arm(rig, side=side, wrist_target=target, pole=Vector(arm['pole']))
        errors.append((head(f'hand_{side}') - target).length)
        ref.orient_hand(rig, side=side, ball_centre=ball,
                        finger_direction=Vector(job['hands'][side]['fingerDirection']),
                        palm_normal=Vector(job['hands'][side]['palmNormal']), max_forearm_roll_degrees=75)
        for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            for number, direction in enumerate(job['fingerDirections'][f'{digit}_{side}'], 1):
                name = f'{digit}_{number:02}_{side}'
                bone = rig.pose.bones[name]
                current = (rig.matrix_world @ bone.tail - head(name)).normalized()
                apply(name, current.rotation_difference(Vector(direction)))
    # A bounded gaze follows the same ball without asking the neck for a full turn.
    bone = rig.pose.bones['Head']
    forward = (rig.matrix_world @ bone.matrix).to_3x3().col[2].normalized()
    delta = forward.rotation_difference((ball - head('Head')).normalized())
    if delta.angle > math.radians(50):
        delta = Quaternion().slerp(delta, math.radians(50) / delta.angle)
    apply('Head', delta)
    control = rig.pose.bones['Ball_Control']
    matrix = control.matrix.copy()
    matrix.translation = rig.matrix_world.inverted() @ ball
    control.matrix = matrix
    control.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    # The existing skirt already follows the hips/thighs; its panel bones add a
    # modest continuation of the same leg motion, not a separate invented clip.
    leg_angles = {}
    for side in ('l', 'r'):
        leg = head(f'calf_{side}') - head(f'thigh_{side}')
        leg_angles[side] = math.atan2(-leg.y, -leg.z)
    for i in range(16):
        left = (1 + math.cos(math.tau * i / 16)) / 2
        angle = left * leg_angles['l'] + (1 - left) * leg_angles['r']
        apply(f'skirt_{i:02}', Quaternion((1, 0, 0), -angle * .72))
    return {'wristTargetErrorM': max(errors), 'ball': list(ball),
            'ballAnchorErrorM': (midpoint - sum(shoulder_targets.values(), Vector()) / 2).length}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--only', nargs='*')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    library = json.loads((args.library / 'manifest.json').read_text())
    sys.path.insert(0, str(args.library / 'source'))
    import blender_mpfb_reference_catch as ref
    bpy.ops.wm.open_mainfile(filepath=str(args.input))
    rig = bpy.data.objects['Netball_Athlete']
    if 'Ball_Control' in rig.pose.bones:
        raise ValueError('Use the base athlete before Movement import (revision 3, or a fresh build.py output).')
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    original_actions = list(bpy.data.actions)
    source_fps = bpy.context.scene.render.fps
    fps = 60
    for action in original_actions:
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                for coordinate in (key.co, key.handle_left, key.handle_right):
                    coordinate.x *= fps / source_fps
    bpy.context.scene.render.fps = fps
    ball = add_ball(rig)
    head = lambda name: ref.world_head(rig, name)
    rest = {'pelvis': head('pelvis').copy(), 'floor': min(head(f'foot_{s}').z for s in ('l', 'r')),
            'shoulders': {s: head(f'upperarm_{s}') - head('pelvis') for s in ('l', 'r')},
            'feet': {f'foot_{s}': rig.pose.bones[f'foot_{s}'].matrix.copy() for s in ('l', 'r')},
            'arm': (head('lowerarm_l') - head('upperarm_l')).length + (head('hand_l') - head('lowerarm_l')).length,
            'leg': ((head('calf_l') - head('thigh_l')).length + (head('foot_l') - head('calf_l')).length)}
    rest['torso'] = ((head('upperarm_l') + head('upperarm_r')) / 2 - head('pelvis')).length
    for action in original_actions:
        rig.animation_data.action = action
        control = rig.pose.bones['Ball_Control']
        control.scale = (0, 0, 0)
        for frame in action.frame_range:
            control.keyframe_insert('scale', frame=frame, group='Ball_Control')
    report = {'sourceCommit': library['sourceCommit'], 'techniques': []}
    selected = [item for item in library['techniques'] if not args.only or item['movementId'] in args.only]
    for entry in selected:
        path = args.library / f"{entry['movementId']}.job.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['jobSha256']
        job = json.loads(path.read_text())
        action = bpy.data.actions.new(entry['clip'])
        action.use_fake_user = True
        action['sourceMovementId'] = entry['movementId']
        action['sourceCommit'] = library['sourceCommit']
        rig.animation_data.action = action
        metrics = []
        for frame in job['frames']:
            number = frame['frame'] * fps / job['framesPerSecond']
            bpy.context.scene.frame_set(int(number))
            metrics.append(retarget(rig, frame, ref, rest))
            for bone in rig.pose.bones:
                if not bone.bone.use_deform:
                    continue
                bone.keyframe_insert('rotation_quaternion', frame=number, group=bone.name)
                if bone.name in ('pelvis', 'Ball_Control'):
                    bone.keyframe_insert('location', frame=number, group=bone.name)
                if bone.name == 'Ball_Control':
                    bone.keyframe_insert('scale', frame=number, group=bone.name)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        result = dict(entry, maxWristTargetErrorM=max(m['wristTargetErrorM'] for m in metrics),
                      maxBallAnchorErrorM=max(m['ballAnchorErrorM'] for m in metrics))
        report['techniques'].append(result)
        print(f"RETARGETED {entry['movementId']}: wrist {result['maxWristTargetErrorM']*1000:.2f} mm; anchor {result['maxBallAnchorErrorM']*1000:.2f} mm", flush=True)
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj == rig or obj.get('bravenRole'):
            obj.hide_set(False)
            obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=str(args.output / 'netball-athlete.glb'), export_format='GLB',
                             use_selection=True, export_animations=True, export_animation_mode='ACTIONS',
                             export_frame_range=False, export_force_sampling=True, export_skins=True,
                             export_extras=True, export_def_bones=True, export_morph=True,
                             export_materials='EXPORT', export_image_format='AUTO', export_yup=True)
    preferred = next((entry for entry in selected if entry['movementId'] == 'netball_two_hand_snatch_pull_in'), selected[0])
    report['defaultClip'] = preferred['clip']
    rig.animation_data.action = bpy.data.actions[preferred['clip']]
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = preferred['frameCount'] - 1
    bpy.context.scene.frame_set(preferred['contactFrame'])
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / 'netball-athlete.blend'))
    report['assetSha256'] = hashlib.sha256((args.output / 'netball-athlete.glb').read_bytes()).hexdigest()
    (args.output / 'movement-library.json').write_text(json.dumps(report, indent=2))
    source_file = args.input.parent / 'athlete-source.blend'
    if source_file.resolve() != (args.output / source_file.name).resolve():
        shutil.copy2(source_file, args.output / source_file.name)
    manifest = json.loads((args.input.parent / 'manifest.json').read_text())
    manifest.update(revision=4, animations=[a.name for a in bpy.data.actions],
                    movementSourceCommit=library['sourceCommit'],
                    movementTechniques=len(selected), deformationControls=70)
    manifest['roles']['Movement_Ball'] = 'movementBall'
    manifest['files'] = {name: {'bytes': (args.output / name).stat().st_size,
                              'sha256': hashlib.sha256((args.output / name).read_bytes()).hexdigest()}
                         for name in ('netball-athlete.glb', 'netball-athlete.blend')}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
