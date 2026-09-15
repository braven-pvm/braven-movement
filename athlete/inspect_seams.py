"""Capture unposed garment geometry for seam diagnosis."""
import bpy, json, sys, bmesh
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out = Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.wm.open_mainfile(filepath=str(out/'netball-athlete.blend'))
rig=bpy.data.objects['Netball_Athlete']
rig.animation_data.action=None
for bone in rig.pose.bones: bone.matrix_basis.identity()
bpy.context.view_layer.update()
report={}
for name in ['Athlete_Body','Kit_Jersey','Kit_Shorts','Kit_Skirt']:
    obj=bpy.data.objects[name]
    bm=bmesh.new();bm.from_mesh(obj.data)
    todo=set(bm.verts); components=[]
    while todo:
        stack=[todo.pop()]; group=[]
        while stack:
            v=stack.pop();group.append(v)
            for e in v.link_edges:
                n=e.other_vert(v)
                if n in todo:todo.remove(n);stack.append(n)
        components.append(len(group))
    boundary=[v for v in bm.verts if v.is_boundary]
    report[name]={'vertices':len(bm.verts),'components':sorted(components,reverse=True),'boundaryVertices':len(boundary),
       'bounds': [[min((obj.matrix_world@v.co)[i] for v in bm.verts),max((obj.matrix_world@v.co)[i] for v in bm.verts)] for i in range(3)]}
    bm.free()
human=bpy.data.objects['Athlete_Body']
human.data.calc_loop_triangles()
tree=BVHTree.FromPolygons([human.matrix_world@v.co for v in human.data.vertices],[t.vertices for t in human.data.loop_triangles],all_triangles=True)
samples=[]
for x in [0,.04,.06,.08,.10,.12,.14,.16,.18,.20]:
    for y in [-.06,-.02,.02,.06]:
        p,n,i,d=tree.ray_cast(Vector((x,y,1.7)),Vector((0,0,-1)))
        samples.append({'x':x,'y':y,'surfaceZ':round(p.z,5) if p else None})
report['shoulderSurface']=samples
(out/'seam-inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
