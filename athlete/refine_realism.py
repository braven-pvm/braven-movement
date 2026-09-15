"""Bake a reversible realism candidate from revision 6; preserve editable source.

Free ball motion is solved in world metres, not in the athlete's moving shoulder
frame. Jump time remapping applies to the body only. A documented, small catch
response moves the pelvis and hands while solving feet back to their source
positions. This is an authored presentation improvement, not a mass/COM solve.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from correct_jumps import new_action, key_pose


def smooth(value):
    u = min(1, max(0, value))
    return u * u * (3 - 2 * u)


def absorb(age, spec):
    if age < 0 or age >= spec['endSeconds']:
        return 0
    peak = spec['peakSeconds']
    return smooth(age / peak) if age <= peak else 1 - smooth((age - peak) / (spec['endSeconds'] - peak))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--recipe', type=Path, default=HERE / 'realism.v1.json')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, out = args.input.parent.resolve(), args.output.resolve()
    if source == out:
        raise ValueError('Write a separate candidate; never replace the accepted source.')
    metadata = json.loads((source / 'movement-library.json').read_text())
    if metadata.get('realismCorrections'):
        raise ValueError('Start with the revision 6 baseline, not an already corrected candidate.')
    spec = json.loads(args.recipe.read_text())
    sys.path.insert(0, str(args.library / 'source'))
    import blender_mpfb_reference_catch as ref
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.input))
    rig = bpy.data.objects['Netball_Athlete']
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(p) for obj in bpy.data.objects
               if obj.type == 'MESH' and obj.get('bravenRole') for p in obj.bound_box]
    floor = min(p.z for p in corners)
    native_height = max(p.z for p in corners)-floor
    metres = native_height/spec['referenceHeightM']
    fps, gravity = 60, spec['gravityMPerS2']*metres
    bpy.context.scene.render.fps = fps
    head = lambda name: ref.world_head(rig, name)
    sample = lambda t: bpy.context.scene.frame_set(int(t * fps), subframe=t * fps % 1)
    world_matrix = lambda name: (rig.matrix_world @ rig.pose.bones[name].matrix).copy()
    def place(name, matrix):
        rig.pose.bones[name].matrix = rig.matrix_world.inverted() @ matrix
        bpy.context.view_layer.update()
    def translate(name, delta):
        m = world_matrix(name); m.translation += delta; place(name, m)
    corrections = []
    for entry in metadata['techniques']:
        name = entry['clip']
        old = bpy.data.actions[name]
        rig.animation_data.action = old
        duration = float(old.frame_range[1]) / fps
        contact = entry['contactFrame'] / fps
        release = entry['releaseFrame'] / fps if entry['releaseFrame'] is not None else None
        original = entry.get('sourceTiming', entry)
        definition = json.loads((args.library / 'source/spikes/movements' / (name + '.ball.json')).read_text())
        launch_phase = definition.get('release', {}).get('atPhase', 0)
        sample(0); initial_ball = head('Ball_Control').copy()
        sample(contact); contact_ball = head('Ball_Control').copy()
        incoming = None
        if launch_phase > 0:
            # Preserve the original flight duration even when the body's jump
            # has since been compressed. The end remains its new hand contact.
            flight = original['contactFrame'] / original['fps'] - launch_phase * original['seconds']
            incoming = max(0, contact - flight)
            flight = contact - incoming
            incoming_velocity = (contact_ball - initial_ball) / flight
            incoming_velocity.z += gravity * flight / 2
        outgoing = None
        if release is not None and release > contact:
            sample(release); released_ball = head('Ball_Control').copy()
            dt = min(.04, (duration-release)/2)
            sample(release+dt)
            launch_velocity = (head('Ball_Control')-released_ball)/dt
            launch_velocity.z += gravity*dt/2
            if name in spec['throwSpeedsMPerS']:
                speed = spec['throwSpeedsMPerS'][name]*metres
                direction = Vector((launch_velocity.x, launch_velocity.y, 0)).normalized()
                launch_velocity = direction * speed
                travel = spec['previewDistanceM']*metres/speed
                launch_velocity.z = gravity*travel/2  # level receiver, true gravity
            outgoing = {'start': release, 'position': list(released_ball), 'velocity': list(launch_velocity)}
            if name == 'netball_bounce_pass':
                # Centre touches one ball radius above the actual court plane.
                radius = .11
                to_floor = spec['previewDistanceM']*metres*spec['bounceAt']/speed
                launch_velocity.z = (floor+radius-released_ball.z)/to_floor + gravity*to_floor/2
                outgoing.update(velocity=list(launch_velocity), bounceSeconds=release+to_floor,
                                radiusM=radius, floorHeightM=floor, horizontalRetention=spec['bounceHorizontalRetention'],
                                verticalRetention=spec['bounceVerticalRetention'])
                duration = max(duration, release + to_floor + .24)
        frame_count = math.ceil(duration*fps)
        # Capture original transforms before replacing the Action. This leaves
        # unmodified keys/poses in other Actions and the accepted file intact.
        frames = []
        for number in range(frame_count+1):
            t = number/fps; sample(min(t, float(old.frame_range[1])/fps))
            frames.append({b.name:b.matrix_basis.copy() for b in rig.pose.bones})
        source_job = json.loads((args.library / (name+'.job.json')).read_text())
        action = new_action(rig, name)
        action['realismRecipe'] = 'realism.v1.json'
        max_foot_error, max_hand_error = 0., 0.
        for number, basis in enumerate(frames):
            t = number/fps; sample(t)
            for bone in rig.pose.bones:
                bone.matrix_basis = basis[bone.name]
                bone.rotation_mode = 'QUATERNION'
            bpy.context.view_layer.update()
            strength = absorb(t-contact, spec['catchAbsorption']) if name in spec['catchAbsorption']['clips'] else 0
            if strength:
                feet = {s:world_matrix('foot_'+s) for s in ('l','r')}
                hands = {s:world_matrix('hand_'+s) for s in ('l','r')}
                knees = {s:head('calf_'+s)-head('thigh_'+s) for s in ('l','r')}
                elbows = {s:head('lowerarm_'+s)-head('upperarm_'+s) for s in ('l','r')}
                down = Vector((0,0,-spec['catchAbsorption']['pelvisDropM']*metres*strength))
                give = Vector((contact_ball.x-initial_ball.x,contact_ball.y-initial_ball.y,0)).normalized()
                give *= spec['catchAbsorption']['handGiveM']*metres*strength
                translate('pelvis',down); translate('Ball_Control',down+give)
                for side in ('l','r'):
                    upper,lower,end = 'thigh_'+side,'calf_'+side,'foot_'+side
                    target = feet[side].translation
                    knee = ref.elbow_for_target(head(upper),target,(head(lower)-head(upper)).length,
                                               (head(end)-head(lower)).length,knees[side])
                    ref.rotate_bone_toward(rig,upper,lower,knee)
                    ref.rotate_bone_toward(rig,lower,end,target)
                    # Restore orientation only: do not hide an IK miss by
                    # translating the ankle outside its fixed-length chain.
                    m = feet[side].copy(); m.translation = head(end); place(end,m)
                    max_foot_error = max(max_foot_error,(head(end)-target).length)
                job = source_job['frames'][min(len(source_job['frames'])-1,round(t*source_job['framesPerSecond']))]
                for side in job.get('grip',{}):
                    target = hands[side].translation+down+give
                    ref.pose_arm(rig,side=side,wrist_target=target,pole=elbows[side])
                    m = hands[side].copy(); m.translation = head('hand_'+side); place('hand_'+side,m)
                    max_hand_error = max(max_hand_error,(head('hand_'+side)-target).length)
            visible = incoming is None or t >= incoming
            if incoming is not None and t < contact:
                age = max(0,t-incoming)
                position = initial_ball+incoming_velocity*age+Vector((0,0,-gravity*age*age/2))
                m = world_matrix('Ball_Control'); m.translation = position; place('Ball_Control',m)
            if outgoing and t > release:
                age = t-release
                position = released_ball+launch_velocity*age+Vector((0,0,-gravity*age*age/2))
                if 'bounceSeconds' in outgoing and t >= outgoing['bounceSeconds']:
                    before = outgoing['bounceSeconds']-release; after = t-outgoing['bounceSeconds']
                    hit = released_ball+launch_velocity*before+Vector((0,0,-gravity*before*before/2))
                    rebound = Vector((launch_velocity.x*spec['bounceHorizontalRetention'],
                                      launch_velocity.y*spec['bounceHorizontalRetention'],
                                      -(launch_velocity.z-gravity*before)*spec['bounceVerticalRetention']))
                    position = hit+rebound*after+Vector((0,0,-gravity*after*after/2))
                m = world_matrix('Ball_Control'); m.translation = position; place('Ball_Control',m)
            rig.pose.bones['Ball_Control'].scale = (1,1,1) if visible else (0,0,0)
            key_pose(rig,number)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'CONSTANT' if curve.data_path.endswith('.scale') else 'LINEAR'
        entry['preRealismTiming'] = {k:copy.deepcopy(entry[k]) for k in ('seconds','frameCount','phases')}
        entry['seconds'],entry['frameCount'] = frame_count/fps,frame_count+1
        if outgoing and 'bounceSeconds' in outgoing:
            for label,time in [('floor_contact',outgoing['bounceSeconds']),('rebound',outgoing['bounceSeconds']+.12)]:
                entry['phases'].append({'name':label,'time':time,'frame':time*fps,'source':'integration-realism-v1'})
            entry['phases'].sort(key=lambda phase:phase['time'])
        dynamics = {'gravityMPerS2':spec['gravityMPerS2'],'nativeGravityMPerS2':gravity,
                    'referenceHeightM':spec['referenceHeightM'],'nativeHeightM':native_height,
                    'incomingStartSeconds':incoming,'contactSeconds':contact,
                    'incomingPositionM':list(initial_ball) if incoming is not None else None,
                    'contactPositionM':list(contact_ball),'outgoing':outgoing,
                    'catchAbsorption':spec['catchAbsorption'] if name in spec['catchAbsorption']['clips'] else None,
                    'maxFootTargetErrorM':max_foot_error,'maxWristTargetErrorM':max_hand_error}
        entry['ballDynamics'] = dynamics
        assert max_foot_error < .002 and max_hand_error < .002, (name,max_foot_error,max_hand_error)
        corrections.append({'clip':name,**dynamics})
        print('REALISM_BAKED',name,'foot',max_foot_error,'wrist',max_hand_error,flush=True)
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj == rig or obj.get('bravenRole'):
            obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=str(out/'netball-athlete.glb'),export_format='GLB',use_selection=True,
        export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,
        export_skins=True,export_extras=True,export_def_bones=True,export_morph=True,export_materials='EXPORT',
        export_image_format='AUTO',export_yup=True)
    rig.animation_data.action = bpy.data.actions['netball_two_hand_snatch_pull_in']
    bpy.context.scene.frame_start,bpy.context.scene.frame_end = 0,97
    bpy.context.scene.frame_set(58)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'netball-athlete.blend'))
    shutil.copy2(source/'athlete-source.blend',out/'athlete-source.blend')
    metadata['realismCorrections'] = corrections
    metadata['realismRecipe'] = spec
    metadata['assetSha256'] = hashlib.sha256((out/'netball-athlete.glb').read_bytes()).hexdigest()
    (out/'movement-library.json').write_text(json.dumps(metadata,indent=2))
    manifest = json.loads((source/'manifest.json').read_text())
    manifest.update(revision=7,parentAssetSha256=manifest['files']['netball-athlete.glb']['sha256'],
                    realismRecipeSha256=hashlib.sha256(args.recipe.read_bytes()).hexdigest())
    manifest['files'] = {n:{'bytes':(out/n).stat().st_size,'sha256':hashlib.sha256((out/n).read_bytes()).hexdigest()}
                         for n in ('netball-athlete.glb','netball-athlete.blend')}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    shutil.copy2(args.recipe,out/'realism.v1.json')
    print('REALISM_CANDIDATE',metadata['assetSha256'],flush=True)


if __name__ == '__main__':
    main()
