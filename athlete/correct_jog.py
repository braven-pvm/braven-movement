"""Rebake only Jog into a separate editable candidate; preserve all other Actions."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from motion import pose_at
from correct_jumps import key_pose,new_action

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source,out=args.input.parent.resolve(),args.output.resolve()
    if source==out or (out/'netball-athlete.blend').exists():
        raise ValueError('Write a fresh candidate; retain the preceding editable master.')
    out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.input))
    rig=bpy.data.objects['Netball_Athlete']
    def fingerprint(action):
        return [(c.data_path,c.array_index,[(tuple(k.co),k.interpolation) for k in c.keyframe_points]) for c in action.fcurves]
    untouched={a.name:fingerprint(a) for a in bpy.data.actions if a.name!='Jog'}
    frames=round(bpy.data.actions['Jog'].frame_range[1])
    action=new_action(rig,'Jog')
    action['correction']='jog-ankle-v1: stable bend plane and shin-relative ankle'
    for frame in range(frames+1):
        bpy.context.scene.frame_set(frame)
        pose_at(rig,'Jog',frame/frames)
        rig.pose.bones['Ball_Control'].scale=(0,0,0)
        key_pose(rig,frame)
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation='LINEAR'
    assert untouched=={a.name:fingerprint(a) for a in bpy.data.actions if a.name!='Jog'}
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    bpy.context.scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj==rig or obj.get('bravenRole'):
            obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(out/'netball-athlete.glb'),export_format='GLB',use_selection=True,
        export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,
        export_skins=True,export_extras=True,export_def_bones=True,export_morph=True,export_materials='EXPORT',
        export_image_format='AUTO',export_yup=True)
    rig.animation_data.action=action
    bpy.context.scene.frame_start,bpy.context.scene.frame_end=0,frames
    bpy.context.scene.frame_set(round(frames*.25))
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'netball-athlete.blend'))
    shutil.copy2(source/'athlete-source.blend',out/'athlete-source.blend')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    metadata=json.loads((source/'movement-library.json').read_text())
    correction={'clip':'Jog','recipe':'correct_jog.py + motion.py','fps':bpy.context.scene.render.fps,
        'seconds':frames/bpy.context.scene.render.fps,'unchangedActions':list(untouched),
        'maxRecoveryDorsiflexionRad':.30,'parentAssetSha256':metadata['assetSha256']}
    metadata.update(assetSha256=digest(out/'netball-athlete.glb'),jogCorrection=correction)
    (out/'movement-library.json').write_text(json.dumps(metadata,indent=2))
    manifest=json.loads((source/'manifest.json').read_text())
    manifest.update(revision=8,parentAssetSha256=manifest['files']['netball-athlete.glb']['sha256'],jogCorrection=correction)
    manifest['files']={n:{'bytes':(out/n).stat().st_size,'sha256':digest(out/n)} for n in ('netball-athlete.glb','netball-athlete.blend')}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    for name in ('correct_jog.py','motion.py','correct_jumps.py','realism.v1.json'):shutil.copy2(HERE/name,out/name)
    print('JOG_CANDIDATE',metadata['assetSha256'],flush=True)

if __name__=='__main__':main()
