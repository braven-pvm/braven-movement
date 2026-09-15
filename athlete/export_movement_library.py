"""Snapshot and export Braven Movement's own solved techniques, without its mesh.

Run through an existing activated Movement pixi environment. All outputs go to
the explicit destination; the source checkout and the runtime stay untouched.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--snapshot-only', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    snapshot = out / 'source'
    snapshot.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip()
    if args.snapshot_only:
        previous = json.loads((out / 'manifest.json').read_text())
        assert previous['sourceCommit'] == commit, 'Do not replace a library snapshot with a different source commit'
    archive = subprocess.check_output(['git', '-C', str(args.source), 'archive', '--format=zip', commit])
    hashes = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        for name in zipped.namelist():
            wanted = (name.endswith('.py') and (name.count('/') == 0 or
                      (name.startswith('spikes/') and name.count('/') == 1))) or (
                      name.startswith('spikes/movements/') and name.endswith('.json')) or (
                      name.startswith(('config/', 'assets/kit/')) and name.endswith('.json')) or (
                      name in ('spikes/pixi.toml', 'spikes/pixi.lock'))
            if not wanted:
                continue
            data = zipped.read(name)
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            hashes[name] = hashlib.sha256(data).hexdigest()
    if args.snapshot_only:
        manifest_path = out / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        assert manifest['sourceCommit'] == commit, 'Do not replace a library snapshot with a different source commit'
        manifest['sourceFiles'] = hashes
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return
    sys.path[:0] = [str(snapshot / 'spikes'), str(snapshot)]
    import numpy as np
    import movement_engine as engine
    import export_blender_job as exporter
    from possession_solve import solve_movement
    from movement_definition import load as load_definition
    from technique import has_technique, load_technique, technique_path
    from ball_track import has_ball

    engine.ASSET_FOLDER = args.assets.resolve()
    character = engine.load_character()
    wanted = args.only or [name for name in engine.library() if has_ball(name) and
                          has_technique(name) and load_technique(technique_path(name)).possession_ready]
    manifest = {'schemaVersion': 1, 'sourceCommit': commit, 'sourceFiles': hashes,
                'description': 'Braven Movement authored solver output, retargeted separately; no source character mesh.',
                'techniques': [], 'failures': []}
    for movement_id in wanted:
        try:
            result = solve_movement(character, movement_id)
            # Reuse the exact job exporter and the already-computed result.
            exporter.solve_movement = lambda *a, **k: result
            job = exporter.build(character, movement_id, every=1)
            points, index = result['points'], result['index']
            origin = exporter.to_blender(points[0][index['root']])
            first = points[0]
            leg = float(np.mean([np.linalg.norm(first[index[f'{s}_upleg']] - first[index[f'{s}_lowleg']]) +
                           np.linalg.norm(first[index[f'{s}_lowleg']] - first[index[f'{s}_foot']])
                           for s in ('l', 'r')]) / 100)
            floor = min(float(p[index[f'{s}_foot']][1]) / 100 for p in points for s in ('l', 'r'))
            for frame in job['frames']:
                p = points[frame['frame']]
                root = exporter.to_blender(p[index['root']])
                shoulders = np.mean([exporter.to_blender(p[index[f'{s}_uparm']]) for s in ('l', 'r')], axis=0)
                hips = exporter.to_blender(p[index['l_upleg']] - p[index['r_upleg']])
                frame['rootOffsetInLegs'] = ((root - origin) / leg).tolist()
                frame['airborneInLegs'] = max(0, (min(float(p[index[f'{s}_foot']][1]) / 100 for s in ('l', 'r')) - floor) / leg)
                frame['trunkDirection'] = exporter.unit(shoulders - root).tolist()
                frame['pelvisYawRadians'] = float(np.arctan2(hips[1], hips[0]))
                fingers = {}
                for side in ('l', 'r'):
                    for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                        names = [f'{side}_{digit}{i}' for i in (1, 2, 3)]
                        segments = [exporter.unit(exporter.to_blender(p[index[b]] - p[index[a]])).tolist()
                                    for a, b in zip(names, names[1:])]
                        tip = next((n for n in (f'{side}_{digit}_tip', f'{side}_{digit}4') if n in index), None)
                        segments.append(exporter.unit(exporter.to_blender(p[index[tip]] - p[index[names[-1]]])).tolist()
                                        if tip else segments[-1])
                        fingers[f'{digit}_{side}'] = segments
                frame['fingerDirections'] = fingers
            definition = load_definition(engine.definition_path(movement_id))
            assessment = definition.assess(result['measurements'])
            states = result['possession'].frames
            release = next((f.number for f in states if f.state == 'released'), None)
            entry = {'movementId': movement_id, 'clip': movement_id, 'label': job['skill'],
                     'sourceCommit': commit, 'fps': job['framesPerSecond'], 'frameCount': len(job['frames']),
                     'seconds': (len(job['frames']) - 1) / job['framesPerSecond'],
                     'contactFrame': int(result['possession'].contact_frame), 'releaseFrame': release,
                     'sourceChecksPassed': bool(assessment.correct), 'coachApproved': False,
                     'phases': [{'name': p['name'], 'frame': p['frame'], 'time': p['frame'] / job['framesPerSecond']}
                                for p in job['phases']]}
            job['source'] = entry
            file = out / f'{movement_id}.job.json'
            file.write_text(json.dumps(job, separators=(',', ':')), encoding='utf-8')
            entry['jobSha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
            manifest['techniques'].append(entry)
            print(f"EXPORTED {movement_id}: {len(job['frames'])} frames; source checkpoints={assessment.correct}", flush=True)
        except Exception as exc:
            manifest['failures'].append({'movementId': movement_id, 'error': str(exc)})
            print(f'FAILED {movement_id}: {exc}', flush=True)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if manifest['failures']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
