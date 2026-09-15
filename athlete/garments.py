"""Editable garment meshes sharing the athlete's deformation skeleton."""
import math
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def attach(obj, rig, role):
    obj['bravenRole'] = role
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    mod = obj.modifiers.new('Athlete deformation', 'ARMATURE')
    mod.object = rig
    for face in obj.data.polygons:
        face.use_smooth = True


def shell(human, rig, name, role, keep, offset, mats):
    obj = human.copy()
    obj.data = human.data.copy()
    obj.name = name
    bpy.context.collection.objects.link(obj)
    obj.modifiers.clear()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    reject = [f for f in bm.faces if not keep(obj.matrix_world @ f.calc_center_median())]
    bmesh.ops.delete(bm, geom=reject, context='FACES')
    bm.normal_update()
    # Smooth the outer garment so its surface is cloth rather than every body contour.
    for _ in range(4):
        bmesh.ops.smooth_vert(bm, verts=list(bm.verts), factor=0.35,
                             use_axis_x=True, use_axis_y=True, use_axis_z=False)
    boundary = [v for v in bm.verts if v.is_boundary]
    for _ in range(12):
        bmesh.ops.smooth_vert(bm, verts=boundary, factor=0.4,
                             use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.materials.clear()
    for mat in mats:
        obj.data.materials.append(mat)
    # Side colour blocking stays on the garment, independent of skin and team colours.
    for face in obj.data.polygons:
        p = obj.matrix_world @ face.center
        face.material_index = 0
    # Bake smoothing/thickness before skinning. Weights interpolate with subdivision.
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    subdiv = obj.modifiers.new('Tailored surface', 'SUBSURF')
    subdiv.levels = 1
    bpy.ops.object.modifier_apply(modifier=subdiv.name)
    thickness = obj.modifiers.new('Fabric edge', 'SOLIDIFY')
    thickness.thickness = 0.002
    bpy.ops.object.modifier_apply(modifier=thickness.name)
    obj.select_set(False)
    attach(obj, rig, role)
    return obj


def make_jersey(human, rig, primary):
    """Cut continuous garment boundaries, including connected shoulder bridges.

    Face-centre deletion leaves staircase edges and the old height cap cut the
    shoulder bridges into separate islands. Clip subdivided polygons at the
    actual boundary, then bind and smooth weights on the fitted surface.
    """
    source = human.copy()
    source.data = human.data.copy()
    bpy.context.collection.objects.link(source)
    source.modifiers.clear()
    # Cloth bridges small anatomical detail instead of embossing it.
    relaxed=bmesh.new();relaxed.from_mesh(source.data)
    for _ in range(8):
        bmesh.ops.smooth_vert(relaxed,verts=list(relaxed.verts),factor=.35,
                             use_axis_x=True,use_axis_y=True,use_axis_z=False)
    relaxed.to_mesh(source.data);relaxed.free()
    bpy.context.view_layer.objects.active = source
    source.select_set(True)
    subdivision = source.modifiers.new('Smooth tailoring source', 'SUBSURF')
    subdivision.levels = 2
    bpy.ops.object.modifier_apply(modifier=subdivision.name)
    source.select_set(False)
    points = [source.matrix_world @ v.co for v in source.data.vertices]
    def neck(p):
        back = max(0, min(1, (p.y + .055)/.10))
        back = back*back*(3-2*back)
        return 1.350 + .055*back + .082*(p.x/.078)**2 - p.z
    def armhole(p):
        # One smooth curve from the underarm to the outside of the shoulder.
        t = max(0, min(1, (p.z-1.225)/.18))
        width = .180 - .064*math.sin(t*math.pi/2)
        return width-abs(p.x)
    fields = [lambda p: p.z-.955, lambda p: 1.49-p.z, neck, armhole]
    faces = [list(f.vertices) for f in source.data.polygons]
    for field in fields:
        clipped, intersections = [], {}
        values = [field(p) for p in points]
        for face in faces:
            polygon = []
            for a,b in zip(face, face[1:]+face[:1]):
                av,bv=values[a],values[b]
                if av>=0: polygon.append(a)
                if (av>=0)!=(bv>=0):
                    edge=tuple(sorted((a,b)))
                    if edge not in intersections:
                        t=av/(av-bv)
                        intersections[edge]=len(points)
                        points.append(points[a].lerp(points[b],t))
                    polygon.append(intersections[edge])
            if len(polygon)>=3:clipped.append(polygon)
        faces=clipped
    used=sorted({i for f in faces for i in f})
    indices={old:new for new,old in enumerate(used)}
    mesh=bpy.data.meshes.new('Continuous tailored jersey')
    mesh.from_pydata([points[i] for i in used],[],[[indices[i] for i in f] for f in faces])
    mesh.update()
    obj=bpy.data.objects.new('Kit_Jersey',mesh)
    bpy.context.collection.objects.link(obj)
    bpy.data.objects.remove(source,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(mesh)
    boundary=[v for v in bm.verts if v.is_boundary]
    # Relax only along each boundary loop. Neighbours from the interior must not
    # pull an edge off its curve or split it away from the shoulder surface.
    for _ in range(10):
        changes={}
        for v in boundary:
            neighbors=[e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(neighbors)==2:
                changes[v]=v.co.lerp((neighbors[0].co+neighbors[1].co)/2,.35)
        for v,p in changes.items():v.co=p
    # Ease the fabric away from the body, tapering to a close-fitting bound edge.
    distance={v:0 for v in boundary};front=set(boundary)
    for step in range(1,9):
        following={e.other_vert(v) for v in front for e in v.link_edges}-distance.keys()
        for v in following:distance[v]=step
        front=following
    bm.normal_update()
    for v in bm.verts:
        ease=min(1,distance.get(v,9)/8)
        v.co+=v.normal*(.006+.006*ease)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    boundary_indices=[v.index for v in boundary]
    edges={v.index:[e.other_vert(v).index for e in v.link_edges if e.is_boundary] for v in boundary}
    loops=[]
    todo=set(edges)
    while todo:
        first=min(todo);loop=[first];todo.remove(first)
        while True:
            following=[i for i in edges[loop[-1]] if i in todo]
            if not following:break
            loop.append(following[0]);todo.remove(following[0])
        assert len(loop)>2 and first in edges[loop[-1]],'Garment boundary must be a closed loop'
        loops.append(loop)
    assert len(loops)==4,'Jersey must have exactly a neck, two armholes and one hem'
    bm.to_mesh(mesh);bm.free()
    # Relaxation and the cloth ease change vertex positions. Rebind to the
    # fitted location; retaining the old point's arm weight pulls the armhole
    # into a flap when the hands reach overhead.
    transfer_weights(human,obj,rig,smoothing=24)
    edge_group=obj.vertex_groups.new(name='Garment_Boundary')
    edge_group.add(boundary_indices,1,'REPLACE')
    binding=make_bindings(obj,rig,primary,loops)
    mesh.materials.append(primary)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    thickness=obj.modifiers.new('Bound fabric edges', 'SOLIDIFY')
    thickness.thickness=.0015
    thickness.offset=0
    bpy.ops.object.modifier_apply(modifier=thickness.name)
    obj.select_set(False)
    attach(obj,rig,'jersey')
    return obj,binding


def make_bindings(shirt,rig,primary,loops):
    """Continuous narrow fabric binding with uniform spacing and shared weights."""
    vertices,faces,weights=[],[],[]
    sample=surface_sampler(shirt,rig)
    for loop in loops:
        path=[shirt.data.vertices[i].co.copy() for i in loop]
        if sum(p.z for p in path)/len(path)<1.1:continue
        lengths=[(path[(i+1)%len(path)]-p).length for i,p in enumerate(path)]
        total=sum(lengths);count=max(32,round(total/.003))
        centers=[];cursor=0;start=0
        for i in range(count):
            distance=i*total/count
            while cursor<len(path)-1 and start+lengths[cursor]<distance:
                start+=lengths[cursor];cursor+=1
            t=(distance-start)/max(1e-8,lengths[cursor])
            centers.append(path[cursor].lerp(path[(cursor+1)%len(path)],t))
        for _ in range(40):
            centers=[p*.5+(centers[(i-1)%count]+centers[(i+1)%count])*.25 for i,p in enumerate(centers)]
        values=[sample(p) for p in centers]
        for _ in range(40):
            values=[{n:values[i].get(n,0)*.5+values[(i-1)%count].get(n,0)*.25+values[(i+1)%count].get(n,0)*.25
                     for n in values[i].keys()|values[(i-1)%count].keys()|values[(i+1)%count].keys()} for i in range(count)]
        # Normals on the smooth garment, sampled from its nearest polygon.
        tree=BVHTree.FromPolygons([v.co for v in shirt.data.vertices],[list(f.vertices) for f in shirt.data.polygons])
        base=len(vertices);sides=8
        for i,p in enumerate(centers):
            tangent=(centers[(i+1)%count]-centers[(i-1)%count]).normalized()
            _,normal,_,_=tree.find_nearest(p)
            across=tangent.cross(normal).normalized()
            normal=across.cross(tangent).normalized()
            for side in range(sides):
                a=math.tau*side/sides
                vertices.append(p+normal*(.001+.0012*math.cos(a))+across*(.0035*math.sin(a)))
                weights.append(values[i])
                n=base+i*sides+side;next_row=base+(i+1)%count*sides
                faces.append((n,base+i*sides+(side+1)%sides,next_row+(side+1)%sides,next_row+side))
    mesh=bpy.data.meshes.new('Continuous neck and armhole binding')
    mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(primary)
    obj=bpy.data.objects.new('Kit_Binding',mesh);bpy.context.collection.objects.link(obj)
    groups={name:obj.vertex_groups.new(name=name) for name in sorted({n for value in weights for n in value})}
    for i,value in enumerate(weights):
        for name,weight in value.items():
            if weight>1e-8:groups[name].add([i],weight,'REPLACE')
    attach(obj,rig,'jersey')
    return obj


def surface_sampler(source,rig):
    source.data.calc_loop_triangles()
    triangles=[tuple(t.vertices) for t in source.data.loop_triangles]
    points=[source.matrix_world@v.co for v in source.data.vertices]
    tree=BVHTree.FromPolygons(points,triangles,all_triangles=True)
    values=[{source.vertex_groups[g.group].name:g.weight for g in v.groups
             if source.vertex_groups[g.group].name in rig.data.bones} for v in source.data.vertices]
    def sample(vertex):
        near,_,triangle,_=tree.find_nearest(Vector(vertex))
        ids=triangles[triangle]
        a,b,c=(points[i] for i in ids)
        u,v,w=b-a,c-a,near-a
        denominator=u.dot(u)*v.dot(v)-u.dot(v)**2
        if abs(denominator)<1e-15:return dict(values[ids[0]])
        second=(v.dot(v)*w.dot(u)-u.dot(v)*w.dot(v))/denominator
        third=(u.dot(u)*w.dot(v)-u.dot(v)*w.dot(u))/denominator
        blend=[max(0,1-second-third),max(0,second),max(0,third)]
        result={}
        for index,amount in zip(ids,blend):
            for name,value in values[index].items():result[name]=result.get(name,0)+value*amount
        total=sum(result.values())
        return {name:value/total for name,value in result.items()}
    return sample


def transfer_weights(source,target,rig,smoothing=0):
    sample=surface_sampler(source,rig)
    values=[sample(target.matrix_world@v.co) for v in target.data.vertices]
    neighbors=[set() for _ in values]
    for edge in target.data.edges:
        a,b=edge.vertices;neighbors[a].add(b);neighbors[b].add(a)
    for _ in range(smoothing):
        updated=[]
        for i,current in enumerate(values):
            result={name:value*.5 for name,value in current.items()}
            if not neighbors[i]:updated.append(current);continue
            for j in neighbors[i]:
                for name,value in values[j].items():result[name]=result.get(name,0)+value*.5/len(neighbors[i])
            updated.append(result)
        values=updated
    target.vertex_groups.clear()
    groups={}
    for vertex,value in zip(target.data.vertices,values):
        for name,weight in value.items():
            if weight<1e-8:continue
            if name not in groups:groups[name]=target.vertex_groups.new(name=name)
            groups[name].add([vertex.index],weight,'REPLACE')


def skirt_outline(shorts, z):
    """Convex cross-section of the actual shorts, keeping the space between the legs."""
    points = []
    coordinates = [shorts.matrix_world @ v.co for v in shorts.data.vertices]
    for edge in shorts.data.edges:
        a, b = (coordinates[i] for i in edge.vertices)
        if (a.z <= z < b.z) or (b.z <= z < a.z):
            p = a.lerp(b, (z-a.z)/(b.z-a.z))
            points.append((p.x, p.y))
    # The hem may be below the shorts. Continue the lowest available cross-section.
    if len(points) < 3:
        band_z = min(max(z, min(p.z for p in coordinates)+.025), max(p.z for p in coordinates)-.025)
        points = [(p.x, p.y) for p in coordinates if abs(p.z-band_z) < .020]
    points = sorted(set(points))
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def half(sequence):
        result = []
        for p in sequence:
            while len(result) >= 2 and cross(result[-2], result[-1], p) <= 0:
                result.pop()
            result.append(p)
        return result
    hull = half(points)[:-1] + half(reversed(points))[:-1]
    assert len(hull) >= 3, f'No usable garment cross-section at {z}'
    return hull


def outline_radius(hull, angle, center_y):
    dx, dy = math.cos(angle), math.sin(angle)
    intersections = []
    for i, a in enumerate(hull):
        b = hull[(i+1) % len(hull)]
        ax, ay = a[0], a[1]-center_y
        ex, ey = b[0]-a[0], b[1]-a[1]
        denominator = dx*ey-dy*ex
        if abs(denominator) < 1e-10:
            continue
        radius = (ax*ey-ay*ex)/denominator
        along = (ax*dy-ay*dx)/denominator
        if radius > 0 and -.00001 <= along <= 1.00001:
            intersections.append(radius)
    assert intersections, 'Skirt cross-section must surround its center'
    return min(intersections)


def make_skirt(shorts, shirt, rig, primary, accent):
    # Sixteen independently controllable panels. No engine-specific cloth solver.
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    waist, length = 1.015, 0.275
    count, segments, original_rows = 16, 96, 14
    # A turned waistband overlaps the tucked jersey. The hem and the accepted
    # lower skirt silhouette stay at their original heights.
    heights=[1.048,1.050,1.044,1.033]+[waist-length*r/original_rows for r in range(original_rows+1)]
    rows=len(heights)-1
    for i in range(count):
        a = 2 * math.pi * i / count
        bone = rig.data.edit_bones.new(f'skirt_{i:02}')
        bone.head = (0.16 * math.cos(a), -0.015 + 0.125 * math.sin(a), waist)
        bone.tail = (0.19 * math.cos(a), -0.015 + 0.15 * math.sin(a), waist-length)
        bone.parent = rig.data.edit_bones['pelvis']
    bpy.ops.object.mode_set(mode='OBJECT')
    vertices, faces, previous = [], [], None
    center_y = -.015
    for row,z in enumerate(heights):
        t = max(0,(waist-z)/length)
        hull = skirt_outline(shorts, z)
        jersey_hull=skirt_outline(shirt,z) if z>.96 else None
        radii = []
        for i in range(segments):
            a = 2*math.pi*i/segments
            # Follow the hip instead of fitting a large ellipse around its bounding box.
            radius = outline_radius(hull, a, center_y) + .008 + .006*t
            if jersey_hull:
                jersey_radius=outline_radius(jersey_hull,a,center_y)
                if row==0:radius=jersey_radius-.0005
                elif z>=1.033:radius=jersey_radius+.0035
                else:radius=max(radius,jersey_radius+.0035)
            if previous and z<=waist:
                radius = max(radius, previous[i]+.00012)
            radii.append(radius)
            # Fabric falls almost straight after the widest hip, with shallow soft folds.
            fold = .0015*t*t*math.cos(12*a+.25)
            radius += fold
            vertices.append((radius*math.cos(a), center_y+radius*math.sin(a), z))
            if row < rows:
                n = row*segments+i
                faces.append((n, n+segments, (row+1)*segments+(i+1)%segments,
                              row*segments+(i+1)%segments))
        previous = radii
    mesh = bpy.data.meshes.new('Netball skirt mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new('Kit_Skirt', mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(primary)
    mesh.materials.append(accent)
    for face in mesh.polygons:
        # Contrasting lower hem and side panels, no texture dependency.
        face.material_index = 1 if face.index // segments == rows-1 else 0
    # A close-fitting skort must inherit the same deformation as its under-shorts.
    # A pelvis-only envelope is static at the hip while the thigh moves through it.
    sample_shorts=surface_sampler(shorts,rig)
    sample_shirt=surface_sampler(shirt,rig)
    weights = []
    for vertex in vertices:
        result=sample_shorts(vertex)
        amount=max(0,min(1,(vertex[2]-1.0)/.025))
        if amount:
            upper=sample_shirt(vertex)
            result={name:result.get(name,0)*(1-amount)+upper.get(name,0)*amount for name in result.keys()|upper.keys()}
        weights.append(result)
    # Smooth the shared region between the legs without creating a hard weight seam.
    for _ in range(3):
        smooth = []
        for row in range(rows+1):
            for i in range(segments):
                index = row*segments+i
                if heights[row]>=1.025:
                    smooth.append(weights[index])
                    continue
                neighbors = [row*segments+(i-1)%segments, row*segments+(i+1)%segments,
                             max(0, row-1)*segments+i, min(rows, row+1)*segments+i]
                result = {name: value*.6 for name, value in weights[index].items()}
                for neighbor in neighbors:
                    for name, value in weights[neighbor].items():
                        result[name] = result.get(name, 0)+value*.1
                smooth.append(result)
        weights = smooth
    body_groups = {name: obj.vertex_groups.new(name=name) for name in sorted({n for w in weights for n in w})}
    groups = [obj.vertex_groups.new(name=f'skirt_{i:02}') for i in range(count)]
    for row in range(rows+1):
        t = max(0,(waist-heights[row])/length)
        amount = .08*t*t
        for i in range(segments):
            index = row*segments+i
            panel = i/segments*count
            k, fraction = int(panel), panel % 1
            for name, weight in weights[index].items():
                body_groups[name].add([index], weight*(1-amount), 'REPLACE')
            groups[k].add([index], amount*(1-fraction), 'REPLACE')
            groups[(k+1)%count].add([index], amount*fraction, 'REPLACE')
    # Keep faces double-sided for glTF; actual edge geometry is retained in Blender.
    primary.use_backface_culling = False
    attach(obj, rig, 'skirt')
    return obj


def lettering(rig, name, text, location, size, mat):
    curve = bpy.data.curves.new(name, 'FONT')
    curve.body, curve.align_x, curve.size = text, 'CENTER', size
    curve.extrude = 0.0003
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler.x = math.pi/2
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.select_set(False)
    obj.data.materials.append(mat)
    obj.vertex_groups.new(name='spine_03').add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
    attach(obj, rig, 'lettering')
    return obj


def build_kit(human, rig, make_material):
    primary = make_material('Kit_Primary', (0.008, 0.24, 0.22))
    accent = make_material('Kit_Accent', (0.82, 0.17, 0.075))
    dark = make_material('Kit_Shorts', (0.018, 0.028, 0.033))
    white = make_material('Kit_Lettering', (0.91, 0.92, 0.85))

    shirt, binding = make_jersey(human, rig, primary)
    shorts = shell(human, rig, 'Kit_Shorts', 'shorts',
        lambda p: 0.755 < p.z < 1.016 and abs(p.x) < 0.28, 0.016, [dark, dark])
    skirt = make_skirt(shorts, shirt, rig, primary, accent)
    # The jersey front is sampled to place lettering on the fabric, not behind it.
    chest_y = min((shirt.matrix_world @ v.co).y for v in shirt.data.vertices
                  if 1.21 < (shirt.matrix_world @ v.co).z < 1.30 and abs((shirt.matrix_world @ v.co).x) < 0.07)
    text = lettering(rig, 'Position_GS', 'GS', (0, chest_y-0.005, 1.213), 0.079, white)
    logo = lettering(rig, 'Team_Braven', 'BRAVEN', (0, chest_y-0.005, 1.32), 0.019, white)
    return [shirt, binding, shorts, skirt, text, logo]
