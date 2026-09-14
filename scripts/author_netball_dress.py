"""Author the netball dress from the MPFB basemesh helpers and write it as a
`.mhclo` the pipeline can wear.

    blender -b --python-exit-code 9 -P scripts/author_netball_dress.py -- \\
        --kit config/kit/netball_dress.v1.json --out assets/kit

Every number is in the kit file; nothing here is modelled by hand. The steps:

1. Build the athlete of `--config` (the reference config by default, whose
   `presentation.kit` names no garment, because this script MAKES the garment).
2. Extract the `helper-tights` and `helper-skirt` vertex groups into objects.
3. Read landmarks from the rig and the mesh: the shoulder joint, the shoulder
   top at the strap, the throat and the back at the scoop heights.
4. Cut the bodysuit. Every cut is a plane that only SPLITS the mesh; then each
   face is kept or deleted by where its centroid lies against all the planes at
   once. A vertex delete on a quad mesh stair-steps at every edge, a snap to
   the plane stretches the faces, and a cut limited to a band of the mesh
   deletes centre-line vertices the other side's faces still use. Twelve
   iterations on 10 Sep 2026 found all three; split-then-classify is what was
   left standing.
5. Cut the skirt at the hem, then hang it: each vertex moves out to the widest
   body radius above it, plus an ease that blends to zero at the waist. Its
   vertex group is renamed to the skin group, so the fitting matches the skin
   and the skirt moves with the thighs in a landing.
6. Lay a planar UV map, front faces on the left half and back faces mirrored
   on the right, in the frame `uvFrame`, for the bib image.
7. Join, check with `ClothesService.mesh_is_valid_as_clothes`, match with
   `create_mhclo_from_clothes_matching`, write the `.mhclo` and `.obj`.

A sidecar `<name>.build.json` records the counts, the landmarks, the hashes of
the two inputs and the seconds each stage took, so the committed asset carries
its own provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blender_mpfb_reference_catch import (  # noqa: E402
    create_athlete,
    load_reference_catch_config,
    world_head,
)
from reference_pose_config import DEFAULT_CONFIG_PATH  # noqa: E402

from bl_ext.blender_org.mpfb.entities.meshcrossref import MeshCrossRef  # noqa: E402
from bl_ext.blender_org.mpfb.services.clothesservice import ClothesService  # noqa: E402
from bl_ext.blender_org.mpfb.services.locationservice import LocationService  # noqa: E402
from bl_ext.blender_org.mpfb.services.objectservice import ObjectService  # noqa: E402


def repository_relative(path: Path) -> str:
    """A POSIX path relative to the repository, for a provenance record.

    A RELATIVE argument on the command line is not relative to the repository
    until it is resolved, and `str()` on a Windows path writes backslashes. The
    shorts sidecar recorded `config\\kit\\netball_shorts.v1.json` the first
    time and the guard in `tests/test_kit_in_the_pipeline.py` refused it, which
    is what that guard is for. A path outside the repository is refused here,
    because a sidecar cannot describe its provenance with a path a clone has no
    way to resolve.
    """
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise SystemExit(
            f"{resolved} is outside the repository, so it cannot go in a "
            f"provenance record. Put the file under {ROOT}."
        )
    return resolved.relative_to(ROOT).as_posix()


def sha256_text(path: Path) -> str:
    """The hash of a text input with CRLF folded to LF, so the value is the
    same on a Windows checkout and on the Linux runner. The two inputs of
    this script are JSON; the receipt's own hasher stays on raw bytes, and
    `.gitattributes` keeps the OUTPUT files verbatim for that reason."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def all_geom(mesh):
    return mesh.verts[:] + mesh.edges[:] + mesh.faces[:]


def split(mesh, point, normal) -> None:
    """Split the mesh on a plane. Nothing is deleted here."""
    bmesh.ops.bisect_plane(
        mesh,
        geom=all_geom(mesh),
        dist=1e-6,
        plane_co=point,
        plane_no=Vector(normal).normalized(),
        clear_inner=False,
        clear_outer=False,
    )
    mesh.verts.ensure_lookup_table()
    mesh.edges.ensure_lookup_table()
    mesh.faces.ensure_lookup_table()


def keep_faces(mesh, keep) -> int:
    """Delete every face whose centroid fails `keep`; loose vertices go too."""
    gone = [face for face in mesh.faces if not keep(face.calc_center_median())]
    bmesh.ops.delete(mesh, geom=gone, context="FACES")
    mesh.verts.ensure_lookup_table()
    mesh.edges.ensure_lookup_table()
    mesh.faces.ensure_lookup_table()
    return len(gone)


def below(point, keep_normal):
    return lambda centre: (centre - point).dot(keep_normal) >= 0.0


def plane_keep(first, second, direction):
    """Keep-normal of the plane through two points that contains a direction:
    the side below the plane."""
    normal = (second - first).cross(direction)
    if normal.z < 0:
        normal = -normal
    return -normal


def prune_groups(mesh) -> int:
    """One vertex group per vertex, which the clothes check requires."""
    layer = mesh.verts.layers.deform.verify()
    pruned = 0
    for vertex in mesh.verts:
        weights = vertex[layer]
        if len(weights) > 1:
            pruned += 1
            best = max(weights.keys(), key=lambda key: weights[key])
            for key in list(weights.keys()):
                if key != best:
                    del weights[key]
            weights[best] = 1.0
    return pruned


def lay_planar_uvs(mesh, frame: dict) -> None:
    """Front faces on the left half, back faces mirrored on the right."""
    mesh.normal_update()
    uv_layer = mesh.loops.layers.uv.verify()
    span_x = frame["x1"] - frame["x0"]
    span_z = frame["z1"] - frame["z0"]
    for face in mesh.faces:
        front = face.normal.y < 0
        for loop in face.loops:
            co = loop.vert.co
            if front:
                u = 0.5 * (co.x - frame["x0"]) / span_x
            else:
                u = 0.5 + 0.5 * (frame["x1"] - co.x) / span_x
            loop[uv_layer].uv = (u, (co.z - frame["z0"]) / span_z)


def finish(obj, mesh, frame: dict, label: str) -> dict:
    loose = [vertex for vertex in mesh.verts if not vertex.link_faces]
    bmesh.ops.delete(mesh, geom=loose, context="VERTS")
    pruned = prune_groups(mesh)
    bmesh.ops.triangulate(mesh, faces=mesh.faces[:])
    lay_planar_uvs(mesh, frame)
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    heights = [vertex.co.z for vertex in obj.data.vertices]
    report = {
        "part": label,
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "faceSizes": sorted({len(polygon.vertices) for polygon in obj.data.polygons}),
        "zMinM": round(min(heights), 4),
        "zMaxM": round(max(heights), 4),
        "looseVerticesRemoved": len(loose),
        "verticesPrunedToOneGroup": pruned,
    }
    print(f"[author] {label}: {report}")
    return report


def extract(human, group: str):
    # THE MPFB EXTRACTOR ENTERS EDIT MODE WITH EVERYTHING STILL SELECTED and
    # deletes the inverse of the group, which wipes the object the previous
    # call made. Deselect first, every time.
    bpy.ops.object.select_all(action="DESELECT")
    before = set(bpy.data.objects.keys())
    ObjectService.extract_vertex_group_to_new_object(human, group)
    return bpy.data.objects[sorted(set(bpy.data.objects.keys()) - before)[0]]


def hang_skirt(mesh, body_points, hem: float, skirt: dict) -> dict:
    """Hang each skirt vertex from the widest body point above it."""
    bins = int(skirt["angularBins"])
    waist = max(vertex.co.z for vertex in mesh.verts)
    ring = [vertex.co for vertex in mesh.verts if vertex.co.z > waist - 0.02]
    centre_x = sum(co.x for co in ring) / len(ring)
    centre_y = sum(co.y for co in ring) / len(ring)
    by_bin: dict[int, list[tuple[float, float]]] = {}
    for point in body_points:
        if not (hem - 0.01 <= point.z <= waist + 0.01) or abs(point.x) >= 0.20:
            continue
        angle = math.atan2(point.x - centre_x, -(point.y - centre_y))
        radius = math.hypot(point.x - centre_x, point.y - centre_y)
        by_bin.setdefault(int((angle + math.pi) / (2 * math.pi) * bins) % bins, []).append(
            (radius, point.z)
        )

    def bin_radius(index: int, z: float) -> float:
        best = 0.0
        for neighbour in (index - 1, index, index + 1):
            for radius, height in by_bin.get(neighbour % bins, []):
                if height >= z - 0.005:
                    best = max(best, radius)
        return best

    def widest_above(angle: float, z: float) -> float:
        position = (angle + math.pi) / (2 * math.pi) * bins - 0.5
        index = int(math.floor(position))
        fraction = position - index
        return (1 - fraction) * bin_radius(index % bins, z) + fraction * bin_radius(
            (index + 1) % bins, z
        )

    moved = 0
    for vertex in mesh.verts:
        if vertex.co.z > waist - 0.005:
            continue
        angle = math.atan2(vertex.co.x - centre_x, -(vertex.co.y - centre_y))
        ease = skirt["easeM"] * min(1.0, (waist - vertex.co.z) / skirt["easeBlendM"])
        radius = widest_above(angle, vertex.co.z) + ease
        vertex.co.x = centre_x + radius * math.sin(angle)
        vertex.co.y = centre_y - radius * math.cos(angle)
        moved += 1
    return {"verticesHung": moved, "axisXY": [round(centre_x, 4), round(centre_y, 4)], "waistRingZ": round(waist, 4)}


def measure_boundary(mesh, planes: list[tuple], label: str,
                     only_below: float | None = None) -> dict:
    """Every cut edge lies on a plane this script registered.

    THIS IS NOT A TORN-EDGE DETECTOR, and it is worth saying so because it was
    written as one and disproved. `docs/A_NETBALL_DRESS_FROM_THE_HELPERS.md`
    says "the clearance number catches the thigh, and nothing yet catches a
    torn edge", a torn hem reached Marius on 11 Sep, and TWO candidate
    measurements were tried against the two hems and neither separates them:

    distance to the nearest cutting plane, which is what this function
        measures: 0.00 mm on the torn flat hem AND on the clean rising hem.
        `bisect_plane` puts the new edge ON the plane by construction, so a
        tear is the boundary wandering WITHIN the plane and this quantity
        cannot see it.
    the turning angle along the boundary loop: WORSE on the clean hem, 67.6
        degrees against 38.3, because the four intended corners where a
        tilted hem meets the inner-thigh apex turn more sharply than a
        stair-step does.

    So that sentence in the document stands, and it now stands on evidence.

    What this function does catch is DRIFT between the `split` calls and the
    plane list beside them: a cut whose plane nobody registered leaves a
    boundary that no plane explains, and the worst distance goes positive. It
    also caught its own first reference, a skirt waist ring modelled as a
    plane when it is an original open edge following the hip line, 25.07 mm
    away from any plane and no fault of the cut.

    It measures straight after the classification and before any shaping,
    because a deliberate offset moves the boundary too.
    """
    boundary = [vertex for vertex in mesh.verts
                if any(len(edge.link_faces) < 2 for edge in vertex.link_edges)]
    # AN ORIGINAL OPEN EDGE IS NOT A CUT. The skirt helper arrives with its
    # waist ring already open, and that ring follows the hip line rather
    # than any plane: measured against the highest point of it, 32 of its
    # vertices sit up to 25.07 mm away, which says nothing about the cut.
    # `only_below` keeps the measurement on the cut edge.
    if only_below is not None:
        boundary = [vertex for vertex in boundary if vertex.co.z < only_below]
    worst = 0.0
    off = 0
    for vertex in boundary:
        nearest = min(abs((vertex.co - point).dot(normal.normalized()))
                      for point, normal in planes)
        worst = max(worst, nearest)
        if nearest > 0.001:
            off += 1
    report = {
        "boundaryVertices": len(boundary),
        "cuttingPlanes": len(planes),
        "originalEdgeExcludedAboveZ": only_below,
        "offEveryPlaneOver1mm": off,
        "worstDistanceToACutMm": round(worst * 1000, 2),
    }
    print(f"[author] {label} edge {report}")
    return report


def skin_surface_modifiers(human) -> list[str]:
    """Switch off what stands between the evaluated mesh and the SKIN, and say
    which. Returns the names, for `restore_modifiers`.

    Three things are in the way, and each was found by measuring rather than
    by reading:

    `SUBSURF`   a subdivided copy is the same surface at more cost.
    `Delete.*`  MPFB gives every fitted garment a mask that DELETES the body
                under it. With `female_casualsuit02` on the athlete, a third
                of the body faces between z 0.69 and 1.02 are gone -- 3290
                against 4960 -- which is exactly where a short sits. A
                distance measured against that mesh is a distance to the
                nearest SURVIVING skin, so it is overstated wherever it
                matters, and a vertex in the hole cannot register as inside
                the body at all.

    The helper mask STAYS ON. The helpers are offset surfaces standing outside
    the skin, so leaving them in the BVH is the opposite error.
    """
    off = []
    for modifier in human.modifiers:
        if modifier.type == "SUBSURF" or modifier.name.startswith("Delete."):
            if modifier.show_viewport:
                modifier.show_viewport = False
                off.append(modifier.name)
    return off


def restore_modifiers(human, names: list[str]) -> None:
    for modifier in human.modifiers:
        if modifier.name in names:
            modifier.show_viewport = True


def shape_shorts(mesh, human, shorts: dict) -> dict:
    """Stand the shorts off the body, and span the cleft instead of following it.

    THE CUT ALONE IS SKIN-TIGHT. `helper-tights` is a skin offset, so a piece
    cut out of it follows every contour of the body underneath, including the
    cleft at the front of the crotch. Marius, 11 Sep: "pls can we get rid of
    the cameltoe, and make it look more like shorts". The skirt hid this,
    because it hung in front of it; take the skirt away and it is what a
    viewer looks at.

    A CAMELTOE IS A CONCAVITY IN THE HORIZONTAL CROSS-SECTION, so an offset
    alone does not remove it: the offset surface of a cleft is still a cleft.
    Two operations, in this order:

    1. Every vertex moves to the nearest point on the SKIN plus `easeM` along
       the skin's normal. The clearance is then the parameter itself, and it
       is the same quantity `scripts/kit_studio_sheet.py` measures.
    2. Across the front of the crotch the vertices move forward onto ONE
       depth per height, the most forward point the skin reaches within
       `frontSpanM` of the centre line, plus the same ease. That is a flat
       panel spanning the cleft, which is what fabric does. The move is
       weighted to zero at the edge of the span, so the hips are untouched
       and no crease is left where the panel ends.

    The depth is read by casting a ray at the skin rather than by binning the
    mesh's own vertices: a slab thin enough to be one height is thinner than
    the spacing between vertex rows, so binning measures the rows.
    """
    from mathutils.bvhtree import BVHTree

    # THE EVALUATED HUMAN IS THE SKIN. `human.data.vertices` is not: MPFB sets
    # its macro details as shape keys, 47 of them non-zero on this athlete, so
    # the base mesh is the undeformed basemesh and stands up to 2.7 cm away
    # from the body the render draws. Offsetting from it put 43 vertices INSIDE
    # the real skin and the clearance read -9.5 mm. Two MASK modifiers have
    # already removed the helper geometry by this point, so every face of the
    # evaluated mesh is skin and no vertex-group filter is needed.
    off = skin_surface_modifiers(human)
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = human.evaluated_get(graph)
    points = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
    faces = [list(polygon.vertices) for polygon in evaluated.data.polygons]
    tree = BVHTree.FromPolygons(points, faces)
    print(f"[author] skin surface {len(points)} verts, {len(faces)} faces, "
          f"modifiers switched off for it: {off}")
    restore_modifiers(human, off)

    ease = float(shorts["easeM"])
    span = float(shorts["frontSpanM"])
    crotch_top = float(shorts["crotchTopZ"])
    limit = float(shorts["maxForwardM"])
    ladder = [span * k / 6.0 for k in range(-6, 7)]

    def front_depth(z: float) -> float | None:
        """The most forward the skin reaches within the span, at this height."""
        best = None
        for x in ladder:
            location, _, _, _ = tree.ray_cast(Vector((x, -0.6, z)), Vector((0.0, 1.0, 0.0)))
            if location is not None and (best is None or location.y < best):
                best = location.y
        return best

    offset = 0
    for vertex in mesh.verts:
        location, normal, _, _ = tree.find_nearest(vertex.co)
        if location is None:
            continue
        vertex.co = location + normal * ease
        offset += 1

    flattened = 0
    moved = []
    for vertex in mesh.verts:
        if vertex.co.y >= 0.0 or vertex.co.z > crotch_top or abs(vertex.co.x) > span:
            continue
        depth = front_depth(vertex.co.z)
        if depth is None:
            continue
        # 1 at the centre line, 0 at the edge of the span, smooth between
        weight = 1.0 - (abs(vertex.co.x) / span) ** 2
        target = depth - ease
        shift = (target - vertex.co.y) * weight
        # A CAP, BECAUSE THE UNCAPPED MOVE IS NOT FABRIC. Without it the
        # deepest vertices between the legs travel to the front of the pubic
        # bone, 8.9 cm on this body, and the panel reads as a bulge rather
        # than as a short. The cap is the distance a real inseam can bridge.
        shift = max(shift, -limit)
        if shift < 0.0:
            vertex.co.y += shift
            moved.append(-shift * 1000)
            flattened += 1

    report = {
        "easeM": ease,
        "frontSpanM": span,
        "crotchTopZ": crotch_top,
        "maxForwardM": limit,
        "verticesStoodOff": offset,
        "verticesInTheFrontPanel": flattened,
        "largestForwardMoveMm": round(max(moved), 1) if moved else 0.0,
        "meanForwardMoveMm": round(sum(moved) / len(moved), 1) if moved else 0.0,
    }
    print(f"[author] shorts {report}")
    return report


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="author the netball dress")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--kit", type=Path, default=ROOT / "config" / "kit" / "netball_dress.v1.json")
    parser.add_argument("--out", type=Path, default=ROOT / "assets" / "kit")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    stages: dict[str, float] = {}
    kit = json.loads(args.kit.read_text(encoding="utf-8"))
    config = load_reference_catch_config(args.config)
    if config.presentation.kit.garment:
        raise SystemExit(
            "the authoring config must not wear a garment: this script makes one"
        )
    human, rig, assets, _ = create_athlete(config.athlete, config.presentation)
    stages["athleteS"] = round(time.perf_counter() - started, 2)

    body = extract(human, kit["helpers"]["bodysuit"])
    skirt = extract(human, kit["helpers"]["skirt"])
    body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]

    # ---- landmarks, measured and recorded --------------------------------
    vest = kit["vest"]
    left, right = world_head(rig, "upperarm_l"), world_head(rig, "upperarm_r")
    joint_x = (abs(left.x) + abs(right.x)) / 2
    joint_y = (left.y + right.y) / 2
    joint_z = (left.z + right.z) / 2
    strap_x = joint_x - vest["strapOuterInboardM"]
    top_at_strap = max(
        p.z for p in body_points if abs(abs(p.x) - strap_x) < 0.012 and abs(p.y - joint_y) < 0.04
    )
    neck_top = max(p.z for p in body_points if abs(p.x) < 0.02)
    scoop_front_z = joint_z + vest["scoopFrontAboveJointM"]
    scoop_back_z = joint_z + vest["scoopBackAboveJointM"]
    chest_y = min(p.y for p in body_points if abs(p.x) < 0.02 and abs(p.z - scoop_front_z) < 0.012)
    back_y = max(p.y for p in body_points if abs(p.x) < 0.02 and abs(p.z - scoop_back_z) < 0.012)
    # A SHORTS-ONLY KIT IS CUT AT A WAISTBAND INSTEAD OF AT THE NECK. The
    # painted-kit lane keeps the torso, so the two pieces meet on one line and
    # that line is a number both lanes hold in metres on this body.
    top_z = (float(kit["heightsM"]["waistband"]) if "waistband" in kit["heightsM"]
             else neck_top - vest["topBelowNeckRingM"])
    landmarks = {
        "shoulderJointM": [round(joint_x, 4), round(joint_y, 4), round(joint_z, 4)],
        "strapEdgeX": round(strap_x, 4),
        "shoulderTopAtStrapZ": round(top_at_strap, 4),
        "neckRingTopZ": round(neck_top, 4),
        "chestFrontYAtScoop": round(chest_y, 4),
        "backYAtScoop": round(back_y, 4),
        "topCutZ": round(top_z, 4),
    }
    print(f"[author] landmarks {landmarks}")

    # ---- the bodysuit: split on every plane, then classify ----------------
    heights = kit["heightsM"]
    briefs, arm_x, knee_x = heights["briefsHem"], kit["armCutX"], vest["scoopKneeX"]
    tilt = vest["necklineTilt"]
    mesh = bmesh.new()
    mesh.from_mesh(body.data)
    strap_top = Vector((strap_x, 0, top_at_strap + 0.01))
    armpit = Vector((joint_x + vest["armholeOutboardM"], 0, joint_z - vest["armholeDropM"]))
    dx, dz = armpit.x - strap_top.x, armpit.z - strap_top.z
    front_direction = Vector((0, 1, tilt))
    back_direction = Vector((0, -1, tilt))
    scoop_front = Vector((0, chest_y - 0.005, scoop_front_z))
    scoop_back = Vector((0, back_y + 0.005, scoop_back_z))
    tests = [lambda c: c.z <= top_z, lambda c: abs(c.x) <= arm_x]
    # EVERY CUTTING PLANE, BESIDE ITS SPLIT, so the edge can be measured
    # against the surfaces that made it. A plane that only helps the
    # bisector subdivide, and bounds nothing, is not in this list.
    planes = [(Vector((0, 0, top_z)), Vector((0, 0, 1)))]
    # THE HEM. A world-z plane grazes the inner thigh, where the surface is
    # nearly horizontal, and `bisect_plane` cannot cut a face that lies in the
    # plane. The centroid test then keeps or drops whole faces and the edge
    # wanders across the triangles: it read as torn paper on the inner thigh
    # of each leg, and clean on the outer thigh where the plane meets the leg
    # squarely. A hem that RISES inboard meets both sides at a decent angle,
    # and it is also the shape a real short has.
    rise = float(heights.get("hemRiseM", 0.0))
    hem_span = float(heights.get("hemSpanX", arm_x))
    if rise > 0.0:
        for side in (1, -1):
            hem_point = Vector((side * hem_span, 0.0, briefs))
            hem_keep = Vector((side * rise, 0.0, hem_span))
            split(mesh, hem_point, hem_keep)
            planes.append((hem_point, hem_keep))
            hem_test = below(hem_point, hem_keep)

            def hem_side(c, side=side, hem_test=hem_test):
                return True if side * c.x < 0 else hem_test(c)

            tests.append(hem_side)
    else:
        tests.append(lambda c: c.z >= briefs)
        split(mesh, (0, 0, briefs), (0, 0, 1))
        planes.append((Vector((0, 0, briefs)), Vector((0, 0, 1))))
    split(mesh, (0, 0, top_z), (0, 0, 1))
    for side in (1, -1):
        split(mesh, (side * arm_x, 0, 0), (1, 0, 0))
        planes.append((Vector((side * arm_x, 0, 0)), Vector((1, 0, 0))))
        split(mesh, (side * knee_x, 0, 0), (1, 0, 0))
        arm_keep = Vector((side * dz, 0, -dx))
        arm_point = Vector((side * strap_top.x, 0, strap_top.z))
        split(mesh, arm_point, arm_keep)
        planes.append((arm_point, arm_keep))
        knee = Vector((side * knee_x, chest_y - 0.005, scoop_front.z + 0.02))
        strap_front = Vector((side * (joint_x - vest["strapInnerInboardM"]), joint_y - 0.03, top_at_strap + 0.02))
        strap_back = Vector((side * (joint_x - vest["strapInnerInboardM"]), joint_y + 0.035, top_at_strap + 0.02))
        inner_keep = plane_keep(scoop_front, knee, front_direction)
        outer_keep = plane_keep(knee, strap_front, front_direction)
        back_keep = plane_keep(scoop_back, strap_back, back_direction)
        split(mesh, scoop_front, inner_keep)
        split(mesh, knee, outer_keep)
        split(mesh, scoop_back, back_keep)
        planes.extend(((scoop_front, inner_keep), (knee, outer_keep),
                       (scoop_back, back_keep)))
        arm_test = below(arm_point, arm_keep)
        inner_test, outer_test = below(scoop_front, inner_keep), below(knee, outer_keep)
        back_test = below(scoop_back, back_keep)

        def side_test(c, side=side, arm_test=arm_test, inner_test=inner_test,
                      outer_test=outer_test, back_test=back_test):
            if side * c.x < 0:
                return True  # the other side judges this face
            return arm_test(c) and back_test(c) and (inner_test(c) if abs(c.x) < knee_x else outer_test(c))

        tests.append(side_test)
    split(mesh, (0, 0, 0), (1, 0, 0))
    deleted = keep_faces(mesh, lambda c: all(test(c) for test in tests))
    edge_report = measure_boundary(mesh, planes, "bodysuit")
    shorts_report = shape_shorts(mesh, human, kit["shorts"]) if kit.get("shorts") else None
    body_report = finish(body, mesh, kit["uvFrame"], "bodysuit")
    body_report["edge"] = edge_report
    body_report["facesDeletedByClassification"] = deleted
    if shorts_report is not None:
        body_report["shorts"] = shorts_report

    skirt_report = None
    if "skirt" not in kit.get("parts", ["bodysuit", "skirt"]):
        bpy.data.objects.remove(skirt, do_unlink=True)
        skirt = None

    # ---- the skirt: cut, hang, and match the skin ------------------------
    if skirt is not None:
        mesh = bmesh.new()
        mesh.from_mesh(skirt.data)
        split(mesh, (0, 0, heights["skirtHem"]), (0, 0, 1))
        keep_faces(mesh, lambda c: c.z >= heights["skirtHem"])
        skirt_edge = measure_boundary(
            mesh,
            [(Vector((0, 0, heights["skirtHem"])), Vector((0, 0, 1)))],
            "skirt", only_below=heights["skirtHem"] + 0.05)
        hang = hang_skirt(mesh, body_points, heights["skirtHem"], kit["skirt"])
        skirt_report = finish(skirt, mesh, kit["uvFrame"], "skirt")
        skirt_report.update(hang)
        skirt_report["edge"] = skirt_edge
        skin_group = kit["helpers"]["skirtMatchesGroup"]
        if skin_group not in human.vertex_groups:
            raise SystemExit(f"the basemesh has no vertex group named {skin_group!r}")
        skirt.vertex_groups[0].name = skin_group
    stages["cutsS"] = round(time.perf_counter() - started - stages["athleteS"], 2)

    # ---- join, check, match, write ----------------------------------------
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    if skirt is not None:
        skirt.select_set(True)
    bpy.context.view_layer.objects.active = body
    if skirt is not None:
        bpy.ops.object.join()
    body.name = f"BRAVEN_{kit['name']}"

    check = ClothesService.mesh_is_valid_as_clothes(body, human)
    failed = [key for key, value in check.items() if value is False]
    print(f"[author] check all_ok={check.get('all_checks_ok')} failed={failed} warnings={check.get('warnings')}")
    if not check.get("all_checks_ok"):
        raise SystemExit(f"the clothes check refused the dress: {failed} {check.get('warnings')}")

    # The matching needs the basemesh cross-reference cache; build it once.
    cache = Path(LocationService.get_user_cache("basemesh_xref"))
    if not cache.is_dir() or not any(cache.iterdir()):
        cache.mkdir(parents=True, exist_ok=True)
        cache_started = time.perf_counter()
        MeshCrossRef(human, after_modifiers=False, build_faces_by_group_reference=True,
                     cache_dir=str(cache), write_cache=True, read_cache=False)
        stages["xrefCacheS"] = round(time.perf_counter() - cache_started, 2)

    properties = {
        "author": kit["author"],
        "name": kit["name"],
        "description": kit["description"],
        "homepage": "",
        "license": kit["licence"],
    }
    mhclo = ClothesService.create_mhclo_from_clothes_matching(
        human, body, properties_dict=properties, delete_group=None, allow_exact=True
    )
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"{kit['name']}.mhclo"
    mhclo.write_mhclo(str(target))
    # LF ON EVERY PLATFORM. MPFB writes with the platform newline, and a file
    # that is hashed into receipts must not change bytes with the machine that
    # authored it. `.gitattributes` keeps these files verbatim from here on.
    for written in (target, target.with_suffix(".obj")):
        written.write_bytes(written.read_bytes().replace(b"\r\n", b"\n"))
    stages["checkMatchWriteS"] = round(time.perf_counter() - started - stages["athleteS"] - stages["cutsS"], 2)
    stages["totalS"] = round(time.perf_counter() - started, 2)

    # THE PROVENANCE CLAIM, under the same key the painted-kit sidecar uses:
    # this script reads no texture and no third-party mesh file. The dress is
    # cut from the MakeHuman hm08 basemesh helpers, which are CC0, and from
    # nothing else, so the claim is one boolean and one sentence.
    sidecar = {
        "instrument": Path(__file__).name,
        "output": target.name,
        "outputSha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "obj": target.with_suffix(".obj").name,
        "objSha256": hashlib.sha256(target.with_suffix(".obj").read_bytes()).hexdigest(),
        "readsNoSkin": True,
        "derivedFrom": "MakeHuman hm08 basemesh helper-tights and helper-skirt (CC0), and nothing else",
        "asset": target.name,
        "kitFile": repository_relative(args.kit),
        "kitSha256": sha256_text(args.kit),
        "authoringConfig": repository_relative(args.config),
        "authoringConfigSha256": sha256_text(args.config),
        "hashNote": "sha256 of the input with CRLF folded to LF",
        "landmarks": landmarks,
        "parts": [report for report in (body_report, skirt_report) if report is not None],
        "nBodysuitVertices": body_report["vertices"],
        "nSkirtVertices": skirt_report["vertices"] if skirt_report is not None else 0,
        "check": {key: value for key, value in check.items() if key != "warnings"},
        "stagesS": stages,
        "blender": bpy.app.version_string,
    }
    (args.out / f"{kit['name']}.build.json").write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    print(f"[author] wrote {target} and {target.with_suffix('.obj').name}; stages {stages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
