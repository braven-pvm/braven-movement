"""Measure the baked pelvis flight against gravity, including foot clearance."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = args.output
bpy.ops.wm.open_mainfile(filepath=str(out / 'netball-athlete.blend'))
rig = bpy.data.objects['Netball_Athlete']
floor = min(rig.data.bones['foot_' + s].head_local.z for s in ('l', 'r'))
metadata = json.loads((out / 'movement-library.json').read_text())
specs = {s['clip']: s for s in metadata.get('gravityCorrections', [])}
report = {'assetSha256': hashlib.sha256((out / 'netball-athlete.glb').read_bytes()).hexdigest(), 'clips': [], 'checks': []}


def check(name, value):
    assert value, name
    report['checks'].append(name)


for name in ('Jump_reach', 'netball_hooks_jump_pull_in', 'netball_double_foot_landing'):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    samples = []
    for frame in np.arange(action.frame_range[0], action.frame_range[1] + .01, .5):
        bpy.context.scene.frame_set(int(frame), subframe=float(frame % 1))
        samples.append({'time': float(frame / 60), 'height': float(rig.pose.bones['pelvis'].head.z),
                        'clearance': float(min(rig.pose.bones['foot_' + s].head.z for s in ('l', 'r')) - floor)})
    spec = specs.get(name)
    if spec:
        takeoff, touchdown = spec['takeoffSeconds'], spec['touchdownSeconds']
    else:
        airborne = [s for s in samples if s['clearance'] > .005]
        takeoff, touchdown = airborne[0]['time'], airborne[-1]['time']
    flight = [s for s in samples if takeoff + .025 < s['time'] < touchdown - .025]
    time = np.array([s['time'] - takeoff for s in flight])
    height = np.array([s['height'] for s in flight])
    fit = np.polyfit(time, height, 2)
    acceleration = float(2 * fit[0])
    residual = float(np.max(np.abs(np.polyval(fit, time) - height)))
    item = {'clip': name, 'takeoffSeconds': takeoff, 'touchdownSeconds': touchdown,
            'airtimeSeconds': touchdown - takeoff, 'verticalAccelerationMPerS2': acceleration,
            'maximumFitResidualM': residual, 'minimumAnkleClearanceM': min(s['clearance'] for s in samples),
            'peakAnkleClearanceM': max(s['clearance'] for s in samples)}
    report['clips'].append(item)
    print('FLIGHT', json.dumps(item), flush=True)
    check(name + ': pelvis follows 9.81 m/s2 downward acceleration', abs(acceleration + 9.81) < .2 and residual < .002)
    check(name + ': grounded feet do not sink below the floor', item['minimumAnkleClearanceM'] > -.002)
    check(name + ': flight is brief and has positive clearance', .2 < touchdown - takeoff < .65 and item['peakAnkleClearanceM'] > .05)
(out / 'jump-verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
