"""Bake gravity-based jump trajectories into the editable master and GLB.

The pelvis is an animation proxy for body mass, not a biomechanical COM solve.
Original poses and ball-relative contact are retained at remapped source frames.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion import pose_at


def remap_frame(frame, anchors):
    for (old_a, new_a), (old_b, new_b) in zip(anchors, anchors[1:]):
        if frame <= old_b:
            return new_a + (frame - old_a) / (old_b - old_a) * (new_b - new_a)
    return anchors[-1][1] + frame - anchors[-1][0]


def key_pose(rig, frame):
    for bone in rig.pose.bones:
        if not bone.bone.use_deform:
            continue
        bone.keyframe_insert('rotation_quaternion', frame=frame, group=bone.name)
        if bone.name in ('pelvis', 'Ball_Control'):
            bone.keyframe_insert('location', frame=frame, group=bone.name)
        if bone.name == 'Ball_Control':
            bone.keyframe_insert('scale', frame=frame, group=bone.name)


def new_action(rig, name):
    old = bpy.data.actions[name]
    properties = dict(old.items())
    rig.animation_data.action = None
    bpy.data.actions.remove(old)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    for key, value in properties.items():
        action[key] = value
    rig.animation_data.action = action
    return action


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.input.parent
    metadata = json.loads((source / 'movement-library.json').read_text())
    if metadata.get('gravityCorrections'):
        raise ValueError('Use the archived revision 4 master before gravity correction.')
    bpy.ops.wm.open_mainfile(filepath=str(args.input))
    rig = bpy.data.objects['Netball_Athlete']
    fps, gravity = 60, 9.81
    bpy.context.scene.render.fps = fps
    floor = min(rig.data.bones['foot_' + s].head_local.z for s in ('l', 'r'))
    corrections = []

    action = new_action(rig, 'Jump_reach')
    for frame in range(121):
        bpy.context.scene.frame_set(frame)
        pose_at(rig, 'Jump_reach', frame / 120)
        rig.pose.bones['Ball_Control'].scale = (0, 0, 0)
        key_pose(rig, frame)
    takeoff, height = .46, .22
    flight = 2 * math.sqrt(2 * height / gravity)
    corrections.append({'clip': 'Jump_reach', 'model': 'ballistic-pelvis-proxy', 'gravityMPerS2': gravity,
                        'takeoffSeconds': takeoff, 'touchdownSeconds': takeoff + flight,
                        'peakLiftM': height, 'flightSeconds': flight})
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'

    recipes = {'netball_hooks_jump_pull_in': (45, 62, 96),
               'netball_double_foot_landing': (38, 55, 89)}
    for name, (takeoff_frame, apex_frame, landing_frame) in recipes.items():
        action = bpy.data.actions[name]
        rig.animation_data.action = action
        samples = []
        for frame in range(round(action.frame_range[1]) + 1):
            bpy.context.scene.frame_set(frame)
            samples.append({'basis': {b.name: b.matrix_basis.copy() for b in rig.pose.bones},
                            'pelvis': rig.pose.bones['pelvis'].head.copy(),
                            'clearance': min(rig.pose.bones['foot_' + s].head.z for s in ('l', 'r')) - floor})
        start = samples[takeoff_frame]['pelvis'].copy()
        end = samples[landing_frame]['pelvis'].copy()
        start.z -= samples[takeoff_frame]['clearance']
        end.z -= samples[landing_frame]['clearance']
        desired_peak = max(max(s['pelvis'].z for s in samples),
                           max(start.z, end.z) + max(s['clearance'] for s in samples))
        natural_duration = math.sqrt(2 * (desired_peak - start.z) / gravity) + math.sqrt(2 * (desired_peak - end.z) / gravity)
        flight_frames = round(natural_duration * fps)
        duration = flight_frames / fps
        velocity = (end.z - start.z + .5 * gravity * duration**2) / duration
        apex_age = velocity / gravity
        anchors = [[0, 0], [takeoff_frame, takeoff_frame],
                   [apex_frame, takeoff_frame + apex_age * fps],
                   [landing_frame, takeoff_frame + flight_frames],
                   [len(samples) - 1, takeoff_frame + flight_frames + len(samples) - 1 - landing_frame]]
        action = new_action(rig, name)
        action['gravityMPerS2'] = gravity
        for frame, sample in enumerate(samples):
            target_frame = remap_frame(frame, anchors)
            bpy.context.scene.frame_set(int(target_frame), subframe=target_frame % 1)
            for bone in rig.pose.bones:
                bone.matrix_basis = sample['basis'][bone.name]
            bpy.context.view_layer.update()
            if takeoff_frame <= frame <= landing_frame:
                age = (target_frame - takeoff_frame) / fps
                target = start.lerp(end, age / duration)
                target.z = start.z + velocity * age - .5 * gravity * age**2
                delta = target - sample['pelvis']
            else:
                delta = Vector((0, 0, -sample['clearance']))
            # The ball has a root-level control; translate it with the athlete
            # to preserve the original hand/ball contact throughout retiming.
            for bone_name in ('pelvis', 'Ball_Control'):
                bone = rig.pose.bones[bone_name]
                matrix = bone.matrix.copy()
                matrix.translation += delta
                bone.matrix = matrix
                bpy.context.view_layer.update()
            key_pose(rig, target_frame)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        entry = next(t for t in metadata['techniques'] if t['clip'] == name)
        entry['sourceTiming'] = {k: copy.deepcopy(entry[k]) for k in ('fps', 'frameCount', 'seconds', 'contactFrame', 'releaseFrame', 'phases')}
        entry['sourceFrameMap'] = anchors
        entry['frameCount'] = round(anchors[-1][1]) + 1
        entry['seconds'] = anchors[-1][1] / fps
        for key in ('contactFrame', 'releaseFrame'):
            if entry[key] is not None:
                entry[key] = remap_frame(entry[key], anchors)
        for phase in entry['phases']:
            phase['frame'] = remap_frame(phase['frame'], anchors)
            phase['time'] = phase['frame'] / fps
        correction = {'clip': name, 'model': 'ballistic-pelvis-proxy', 'gravityMPerS2': gravity,
                      'takeoffSeconds': takeoff_frame / fps, 'touchdownSeconds': (takeoff_frame + flight_frames) / fps,
                      'flightSeconds': duration, 'initialVerticalVelocityMPerS': velocity,
                      'takeoffPelvisHeightM': start.z, 'landingPelvisHeightM': end.z,
                      'apexPelvisHeightM': start.z + velocity**2 / (2 * gravity), 'sourceFrameMap': anchors}
        entry['gravityCorrection'] = correction
        corrections.append(correction)
        print('CORRECTED_JUMP', json.dumps(correction), flush=True)

    metadata['gravityCorrections'] = corrections
    metadata['defaultClip'] = 'Jump_reach'
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
    rig.animation_data.action = bpy.data.actions['Jump_reach']
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, 120
    bpy.context.scene.frame_set(round((takeoff + flight / 2) * fps))
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / 'netball-athlete.blend'))
    metadata['assetSha256'] = hashlib.sha256((args.output / 'netball-athlete.glb').read_bytes()).hexdigest()
    (args.output / 'movement-library.json').write_text(json.dumps(metadata, indent=2))
    shutil.copy2(source / 'athlete-source.blend', args.output / 'athlete-source.blend')
    manifest = json.loads((source / 'manifest.json').read_text())
    manifest.update(revision=6, gravityCorrections=corrections)
    manifest['files'] = {name: {'bytes': (args.output / name).stat().st_size,
                              'sha256': hashlib.sha256((args.output / name).read_bytes()).hexdigest()}
                         for name in ('netball-athlete.glb', 'netball-athlete.blend')}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
