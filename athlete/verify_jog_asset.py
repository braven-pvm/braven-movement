"""Compare the two actual GLBs to guard the scope of the Jog-only rebake."""
import argparse
import hashlib
import json
from pathlib import Path
from verify_asset import read_glb,values

parser=argparse.ArgumentParser()
parser.add_argument('--before',type=Path,required=True)
parser.add_argument('--after',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args()
def read(path):
    doc,binary=read_glb(path)
    clips={}
    for action in doc['animations']:
        channels={}
        for channel in action['channels']:
            sampler=action['samplers'][channel['sampler']]
            key=(doc['nodes'][channel['target']['node']]['name'],channel['target']['path'])
            channels[key]=(sampler.get('interpolation','LINEAR'),values(doc,binary,sampler['input']),values(doc,binary,sampler['output']))
        clips[action['name']]=channels
    meshes={mesh['name']:[{name:values(doc,binary,index) for name,index in primitive['attributes'].items()} for primitive in mesh['primitives']] for mesh in doc['meshes']}
    return clips,meshes
before,mesh_before=read(args.before)
after,mesh_after=read(args.after)
assert before.keys()==after.keys()
unchanged=[]
for name in before:
    if name=='Jog':continue
    assert before[name]==after[name],name+' changed outside the Jog repair'
    unchanged.append(name)
assert mesh_before==mesh_after,'Vertex geometry or skin weights changed'
assert before['Jog']!=after['Jog'],'Jog did not change'
report={'before':hashlib.sha256(args.before.read_bytes()).hexdigest(),'after':hashlib.sha256(args.after.read_bytes()).hexdigest(),
        'unchangedAnimations':unchanged,'allMeshAttributesUnchanged':True,'changedAnimations':['Jog']}
args.report.write_text(json.dumps(report,indent=2))
print(json.dumps(report))
