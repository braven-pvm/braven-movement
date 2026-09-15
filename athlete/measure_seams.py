"""Measure garment/body clearance on the evaluated, animated native meshes."""
import bpy,json,sys
from pathlib import Path
from mathutils.bvhtree import BVHTree
out=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.wm.open_mainfile(filepath=str(out/'netball-athlete.blend'))
rig=bpy.data.objects['Netball_Athlete'];body=bpy.data.objects['Athlete_Body'];shirt=bpy.data.objects['Kit_Jersey']
group=shirt.vertex_groups['Garment_Boundary'].index
ids=[v.index for v in shirt.data.vertices if v.co.z>1.15 and any(g.group==group for g in v.groups)]
report=[]
for action in bpy.data.actions:
    rig.animation_data.action=action
    for frame in [1,8,17,25,40,55]:
        if frame>action.frame_range[1]:continue
        bpy.context.scene.frame_set(frame)
        dg=bpy.context.evaluated_depsgraph_get()
        b=body.evaluated_get(dg);s=shirt.evaluated_get(dg)
        mesh=b.to_mesh();mesh.calc_loop_triangles()
        tree=BVHTree.FromPolygons([b.matrix_world@v.co for v in mesh.vertices],[t.vertices for t in mesh.loop_triangles],all_triangles=True)
        signed=[]
        for i in ids:
            p=s.matrix_world@s.data.vertices[i].co
            near,normal,face,distance=tree.find_nearest(p)
            signed.append(((p-near).dot(normal),i,list(p)))
        signed.sort()
        report.append({'action':action.name,'frame':frame,'min':signed[0],'max':signed[-1],
                       'insideCount':sum(p[0]<-.001 for p in signed),'count':len(signed)})
        b.to_mesh_clear()
(out/'seam-clearance.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
