"""Inspect baked Movement actions, contact targets, ball paths and provenance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from correct_jumps import remap_frame

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--library', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
metadata = json.loads((args.output / 'movement-library.json').read_text())
library = json.loads((args.library / 'manifest.json').read_text())
report = {'assetSha256': hashlib.sha256((args.output / 'netball-athlete.glb').read_bytes()).hexdigest(),
          'sourceCommit': library['sourceCommit'], 'checks': [], 'clips': []}


def check(label, value):
    assert value, label
    report['checks'].append(label)


check('Metadata matches the actual GLB', report['assetSha256'] == metadata['assetSha256'])
bpy.ops.wm.open_mainfile(filepath=str(args.output / 'netball-athlete.blend'))
rig = bpy.data.objects['Netball_Athlete']
head = lambda name: rig.matrix_world @ rig.pose.bones[name].head
arm = sum((rig.data.bones[n].tail_local - rig.data.bones[n].head_local).length
          for n in ('upperarm_l', 'lowerarm_l'))
check('Ball has its own editable deform bone', rig.data.bones['Ball_Control'].use_deform)
check('One skinned ball shares the athlete armature', any(
    m.type == 'ARMATURE' and m.object == rig for m in bpy.data.objects['Movement_Ball'].modifiers))
for entry in metadata['techniques']:
    job_path = args.library / (entry['movementId'] + '.job.json')
    check(entry['clip'] + ': source job hash preserved',
          hashlib.sha256(job_path.read_bytes()).hexdigest() == entry['jobSha256'])
    job = json.loads(job_path.read_text())
    action = bpy.data.actions[entry['clip']]
    rig.animation_data.action = action
    check(entry['clip'] + ': duration and provenance retained',
          abs((action.frame_range[1] - action.frame_range[0]) / 60 - entry['seconds']) < 1e-5
          and action['sourceCommit'] == library['sourceCommit'])
    balls, contact_errors, finger_errors = [], [], []
    for frame in job['frames']:
        target_frame = remap_frame(frame['frame'], entry['sourceFrameMap']) if entry.get('sourceFrameMap') else frame['frame']
        bpy.context.scene.frame_set(int(target_frame), subframe=target_frame % 1)
        centre = head('Ball_Control')
        balls.append(list(centre))
        for side, grip in frame.get('grip', {}).items():
            target = centre + Vector(grip['outward']) * (frame['ball']['radiusM'] + grip['wristFromSurfaceInArms'] * arm)
            contact_errors.append((head('hand_' + side) - target).length)
        for digit in ('index', 'middle', 'thumb'):
            for side in ('l', 'r'):
                for number, direction in enumerate(frame['fingerDirections'][digit + '_' + side], 1):
                    bone = rig.pose.bones[f'{digit}_{number:02}_{side}']
                    actual = (rig.matrix_world @ bone.tail - head(bone.name)).normalized()
                    finger_errors.append(actual.angle(Vector(direction)))
    minimum_ball_height = min(p[2] for p in balls)
    maximum_contact_error = max(contact_errors, default=0)
    check(entry['clip'] + ': baked ball path is finite and animated',
          all(math.isfinite(v) for p in balls for v in p) and
          max((Vector(p) - Vector(balls[0])).length for p in balls) > .015)
    check(entry['clip'] + ': keyed holding wrists retain solved targets within 2 mm', maximum_contact_error < .002)
    check(entry['clip'] + ': baked finger segments retain source directions within one degree',
          max(finger_errors) < math.radians(1))
    check(entry['clip'] + ': ball remains above the floor', minimum_ball_height >= .095)
    report['clips'].append({'clip': entry['clip'], 'framesChecked': len(balls),
                            'minimumBallCentreHeightM': minimum_ball_height,
                            'maxHoldingWristErrorM': maximum_contact_error,
                            'maxFingerDirectionErrorDegrees': math.degrees(max(finger_errors)),
                            'sourceChecksPassed': entry['sourceChecksPassed']})
(args.output / 'movement-native-verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
