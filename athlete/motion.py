"""Authored FK clips plus editable native IK controls; no motion-capture claim."""
import math
import bpy
from mathutils import Matrix, Quaternion, Vector


def aim(rig, name, direction):
    bone = rig.pose.bones[name]
    current = (bone.tail-bone.head).normalized()
    rotation = current.rotation_difference(Vector(direction).normalized())
    bone.matrix = Matrix.Translation(bone.head) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-bone.head) @ bone.matrix
    bpy.context.view_layer.update()


def rotate(rig, name, axis, angle):
    bone = rig.pose.bones[name]
    rotation = Quaternion(axis, angle).to_matrix().to_4x4()
    bone.matrix = Matrix.Translation(bone.head) @ rotation @ Matrix.Translation(-bone.head) @ bone.matrix
    bpy.context.view_layer.update()


def limb(rig, side, upper, lower, angle, bend, out=0):
    sign = 1 if side == 'l' else -1
    direction = (sign*math.sin(out), -math.sin(angle)*math.cos(out), -math.cos(angle)*math.cos(out))
    aim(rig, f'{upper}_{side}', direction)
    elbow = angle+bend if upper == 'upperarm' else angle-bend
    aim(rig, f'{lower}_{side}', (sign*math.sin(out), -math.sin(elbow)*math.cos(out), -math.cos(elbow)*math.cos(out)))
    if upper == 'thigh':
        aim(rig, f'foot_{side}', (0, -0.94, -0.34))
    else:
        aim(rig, f'hand_{side}', (sign*0.10, -math.sin(elbow), -math.cos(elbow)))


def jog_leg(rig, side, angle, bend, out):
    """Use a fixed sagittal bend plane, and a foot that follows its shin.

    An aim vector alone leaves bone roll underdetermined. Re-aiming a foot
    from its folded parent toward a constant forward vector can turn the shoe
    over, as well as closing the ankle almost completely during recovery.
    Build each world orientation from rest instead, with bounded ankle flex.
    """
    sign = 1 if side == 'l' else -1
    spread = Quaternion((0, 1, 0), -sign*out)
    def place(name, rotation):
        bone = rig.pose.bones[name]
        bone.matrix = Matrix.Translation(bone.head) @ rotation.to_matrix().to_4x4()
        bpy.context.view_layer.update()
    for name, swing in ((f'thigh_{side}', angle), (f'calf_{side}', angle-bend)):
        rest = rig.data.bones[name]
        neutral = (rest.tail_local-rest.head_local).normalized().rotation_difference(Vector((0,0,-1)))
        orientation = spread @ Quaternion((1,0,0), -swing) @ neutral @ rest.matrix_local.to_quaternion()
        place(name, orientation)
    # Flatten the shoe on approach to stance. During recovery let it follow the
    # shin, allowing at most 0.30 rad of dorsiflexion relative to the rest ankle.
    # This avoids a world-horizontal shoe while the shin points behind/upward.
    pitch = max(0, -(angle-bend)-.30)
    foot = f'foot_{side}'
    place(foot, Quaternion((1,0,0),pitch) @ rig.data.bones[foot].matrix_local.to_quaternion())


def pose_at(rig, kind, phase):
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
        bone.rotation_mode = 'QUATERNION'
    bpy.context.view_layer.update()
    w = math.tau*phase
    left_leg, right_leg = 0.06, 0.06
    left_knee, right_knee = 0.12, 0.12
    arms = [(.24, 1.05, .12), (.24, 1.05, .12)]
    lean, bob, out = 0.018, 0.003*math.sin(w), 0.055
    if kind == 'Jog':
        left_leg, right_leg = 0.55*math.sin(w), -0.55*math.sin(w)
        left_knee = .23 + .92*max(0, -math.sin(w))
        right_knee = .23 + .92*max(0, math.sin(w))
        arms = [(-.43*math.sin(w), 1.32, .12), (.43*math.sin(w), 1.32, .12)]
        lean, bob, out = .10, .030*abs(math.sin(w)), .035
        rotate(rig, 'spine_03', (0, 0, 1), .06*math.sin(w))
    elif kind == 'Defence':
        sway = math.sin(w)
        left_leg, right_leg = .19, .19
        left_knee = right_knee = .38
        arms = [(2.25+.12*sway, .25, .45), (2.25-.12*sway, .25, .45)]
        out, bob = .16, -.035
        rig.pose.bones['pelvis'].location.x = .035*sway
    elif kind == 'Receive_pass':
        # Loop: ready, reach, cushion, extend, recover. Sine easing is deliberate.
        reach = (1-math.cos(w))/2
        arms = [(.35+.82*reach, 1.05-.80*reach, .12), (.35+.82*reach, 1.05-.80*reach, .12)]
        left_leg, right_leg = .12, -.10
        left_knee, right_knee = .24, .15
        lean = .06*reach
    elif kind == 'Jump_reach':
        time = phase * 2
        takeoff, height, gravity = .46, .22, 9.81
        flight = 2 * math.sqrt(2 * height / gravity)
        touchdown = takeoff + flight
        smooth = lambda x: (lambda v: v*v*(3-2*v))(max(0, min(1, x)))
        if time < .22:
            crouch = smooth(time / .22)
        elif time < takeoff:
            crouch = 1 - smooth((time - .22) / (takeoff - .22))
        elif time < touchdown:
            crouch = 0
        elif time < touchdown + .13:
            crouch = smooth((time - touchdown) / .13)
        else:
            crouch = 1 - smooth((time - touchdown - .13) / .29)
        lift = smooth((time - .22) / (takeoff + flight / 2 - .22))
        if time > touchdown:
            lift *= 1 - smooth((time - touchdown) / .42)
        left_leg = right_leg = .10+.26*crouch
        left_knee = right_knee = .20+.45*crouch
        arms = [(.40+2.20*lift, .75*(1-lift)+.12, .12)]*2
        age = time - takeoff
        bob = max(0, math.sqrt(2 * gravity * height)*age - .5*gravity*age*age) if 0 < age < flight else 0
    rotate(rig, 'spine_01', (1, 0, 0), lean/2)
    rotate(rig, 'spine_02', (1, 0, 0), lean/2)
    rotate(rig, 'Head', (0, 0, 1), .035*math.sin(w))
    if kind == 'Jog':
        jog_leg(rig, 'l', left_leg, left_knee, out)
        jog_leg(rig, 'r', right_leg, right_knee, out)
    else:
        limb(rig, 'l', 'thigh', 'calf', left_leg, left_knee, out)
        limb(rig, 'r', 'thigh', 'calf', right_leg, right_knee, out)
    for side, values in zip(('l', 'r'), arms):
        limb(rig, side, 'upperarm', 'lowerarm', *values)
    # Grounded poses place the feet on the floor. Jump flight adds ballistic lift.
    feet = [rig.pose.bones[f'foot_{s}'].head.z for s in ('l', 'r')]
    reference = min(rig.data.bones[f'foot_{s}'].head_local.z for s in ('l', 'r'))
    correction = reference-min(feet)+bob
    pelvis = rig.pose.bones['pelvis']
    matrix = pelvis.matrix.copy()
    matrix.translation.z += correction
    pelvis.matrix = matrix
    bpy.context.view_layer.update()
    for i in range(16):
        a = math.tau*i/16
        leg_angle = left_leg if math.cos(a) >= 0 else right_leg
        bend = leg_angle*.72
        # Panels follow the thigh with a small authored secondary sway.
        rotate(rig, f'skirt_{i:02}', (1, 0, 0), -bend + .025*math.sin(w-a))
    # Fingers remain available as individual bones. A light relaxed curl travels in clips.
    for bone in rig.pose.bones:
        if any(bone.name.startswith(n) for n in ('index_', 'middle_', 'ring_', 'pinky_')):
            bone.rotation_quaternion = Quaternion((1, 0, 0), .10 + .02*math.sin(w))


def build_actions(rig):
    rig.animation_data_create()
    for name, frames in [('Ready', 90), ('Jog', 30), ('Defence', 90), ('Receive_pass', 90), ('Jump_reach', 60)]:
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        rig.animation_data.action = action
        for f in range(frames+1):
            bpy.context.scene.frame_set(f+1)
            pose_at(rig, name, f/frames)
            for bone in rig.pose.bones:
                bone.keyframe_insert(data_path='rotation_quaternion', frame=f+1, group=bone.name)
                if bone.name == 'pelvis':
                    bone.keyframe_insert(data_path='location', frame=f+1, group=bone.name)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def add_ik_controls(rig):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for side in ('l', 'r'):
        for end in ('hand', 'foot'):
            source = rig.data.edit_bones[f'{end}_{side}']
            target = rig.data.edit_bones.new(f'CTRL_{end}_{side}')
            target.head = source.head
            target.tail = source.head+Vector((0, 0, .10))
            target.parent = rig.data.edit_bones['root']
            target.use_deform = False
    bpy.ops.object.mode_set(mode='POSE')
    for side in ('l', 'r'):
        for end, driven in [('hand', 'lowerarm'), ('foot', 'calf')]:
            name = f'IK_{end}_{side}'
            rig[name] = 0.0
            rig.id_properties_ui(name).update(min=0, max=1, description='0: keyed FK; 1: move CTRL target in Pose Mode')
            constraint = rig.pose.bones[f'{driven}_{side}'].constraints.new('IK')
            constraint.name = f'{end.title()} IK (enable on rig custom properties)'
            constraint.target, constraint.subtarget, constraint.chain_count = rig, f'CTRL_{end}_{side}', 2
            constraint.use_stretch = False
            driver = constraint.driver_add('influence').driver
            variable = driver.variables.new()
            variable.name = 'enabled'
            variable.type = 'SINGLE_PROP'
            variable.targets[0].id = rig
            variable.targets[0].data_path = f'["{name}"]'
            driver.expression = 'enabled'
    bpy.ops.object.mode_set(mode='OBJECT')
