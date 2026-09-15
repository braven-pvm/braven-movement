"""Inspect the delivered asset, not a parallel mock of the character."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import struct


def read_glb(path):
    raw = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<4sII', raw)
    assert magic == b'glTF' and version == 2 and length == len(raw), 'Invalid GLB'
    at, doc, binary = 12, None, b''
    while at < len(raw):
        size, kind = struct.unpack_from('<II', raw, at)
        data = raw[at + 8:at + 8 + size]
        if kind == 0x4E4F534A:
            doc = json.loads(data)
        elif kind == 0x004E4942:
            binary = data
        at += 8 + size
    assert doc is not None, 'Missing JSON'
    return doc, binary


def values(doc, binary, index):
    a = doc['accessors'][index]
    view = doc['bufferViews'][a['bufferView']]
    fmt, size = {5126: ('f', 4), 5123: ('H', 2), 5121: ('B', 1), 5125: ('I', 4)}[a['componentType']]
    count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    offset = view.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = view.get('byteStride', count * size)
    return [struct.unpack_from('<' + fmt * count, binary, offset + i * stride) for i in range(a['count'])]


def verify(path, tactics):
    doc, binary = read_glb(path)
    skin = next(m for m in doc['materials'] if m.get('name') == 'Skin')
    assert skin.get('alphaMode', 'OPAQUE') == 'OPAQUE', 'Skin must write depth, not alpha blend over eyes/hair'
    eyes = next(n for n in doc['nodes'] if n.get('name') == 'Athlete_Eyes')
    eye_material = doc['materials'][doc['meshes'][eyes['mesh']]['primitives'][0]['material']]
    assert eye_material.get('alphaMode') == 'MASK', 'The transparent cornea UV island must not cover the iris'
    source = (Path(tactics) / 'src/engine/skinned.ts').read_text(encoding='utf-8')
    block = source.split('export const BONES = {', 1)[1].split('} as const', 1)[0]
    wanted = set(re.findall(r":\s*'([^']+)'", block))
    joints = {doc['nodes'][i]['name'] for skin in doc['skins'] for i in skin['joints']}
    assert not wanted - joints, f'Missing skin joints: {wanted - joints}'
    garments = {}
    vertices = 0
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        mesh = doc['meshes'][node['mesh']]
        if node.get('extras', {}).get('bravenRole') in {'jersey', 'shorts', 'skirt'}:
            garments[node['extras']['bravenRole']] = node['name']
            assert 'skin' in node, f'{node["name"]} is not skinned'
        for primitive in mesh['primitives']:
            attrs = primitive['attributes']
            vertices += doc['accessors'][attrs['POSITION']]['count']
            if 'skin' in node:
                weights = values(doc, binary, attrs['WEIGHTS_0'])
                assert all(abs(sum(row) - 1) < 0.003 for row in weights), node['name']
    assert set(garments) == {'jersey', 'shorts', 'skirt'}, garments
    clips = []
    for clip in doc.get('animations', []):
        changing = 0
        duration = 0
        for channel in clip['channels']:
            sampler = clip['samplers'][channel['sampler']]
            times = values(doc, binary, sampler['input'])
            assert all(times[i][0] < times[i + 1][0] for i in range(len(times) - 1))
            duration = max(duration, times[-1][0])
            out = values(doc, binary, sampler['output'])
            assert all(math.isfinite(x) for row in out for x in row)
            if any(max(abs(x-y) for x, y in zip(row, out[0])) > 0.002 for row in out[1:]):
                changing += 1
        assert changing >= 4 and duration > 0.5, f'Static/trivial clip {clip["name"]}'
        clips.append({'name': clip['name'], 'duration': duration, 'movingChannels': changing})
    assert len(clips) >= 3, 'At least three working clips required'
    return {'asset': str(path), 'bytes': Path(path).stat().st_size, 'joints': len(joints),
            'tacticsRequiredJoints': len(wanted), 'garments': garments, 'vertices': vertices, 'clips': clips}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset', type=Path, required=True)
    parser.add_argument('--tactics', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = verify(args.asset, args.tactics)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
