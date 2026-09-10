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
    top_z = neck_top - vest["topBelowNeckRingM"]
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
    tests = [lambda c: c.z >= briefs, lambda c: c.z <= top_z, lambda c: abs(c.x) <= arm_x]
    split(mesh, (0, 0, briefs), (0, 0, 1))
    split(mesh, (0, 0, top_z), (0, 0, 1))
    for side in (1, -1):
        split(mesh, (side * arm_x, 0, 0), (1, 0, 0))
        split(mesh, (side * knee_x, 0, 0), (1, 0, 0))
        arm_keep = Vector((side * dz, 0, -dx))
        arm_point = Vector((side * strap_top.x, 0, strap_top.z))
        split(mesh, arm_point, arm_keep)
        knee = Vector((side * knee_x, chest_y - 0.005, scoop_front.z + 0.02))
        strap_front = Vector((side * (joint_x - vest["strapInnerInboardM"]), joint_y - 0.03, top_at_strap + 0.02))
        strap_back = Vector((side * (joint_x - vest["strapInnerInboardM"]), joint_y + 0.035, top_at_strap + 0.02))
        inner_keep = plane_keep(scoop_front, knee, front_direction)
        outer_keep = plane_keep(knee, strap_front, front_direction)
        back_keep = plane_keep(scoop_back, strap_back, back_direction)
        split(mesh, scoop_front, inner_keep)
        split(mesh, knee, outer_keep)
        split(mesh, scoop_back, back_keep)
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
    body_report = finish(body, mesh, kit["uvFrame"], "bodysuit")
    body_report["facesDeletedByClassification"] = deleted

    # ---- the skirt: cut, hang, and match the skin ------------------------
    mesh = bmesh.new()
    mesh.from_mesh(skirt.data)
    split(mesh, (0, 0, heights["skirtHem"]), (0, 0, 1))
    keep_faces(mesh, lambda c: c.z >= heights["skirtHem"])
    hang = hang_skirt(mesh, body_points, heights["skirtHem"], kit["skirt"])
    skirt_report = finish(skirt, mesh, kit["uvFrame"], "skirt")
    skirt_report.update(hang)
    skin_group = kit["helpers"]["skirtMatchesGroup"]
    if skin_group not in human.vertex_groups:
        raise SystemExit(f"the basemesh has no vertex group named {skin_group!r}")
    skirt.vertex_groups[0].name = skin_group
    stages["cutsS"] = round(time.perf_counter() - started - stages["athleteS"], 2)

    # ---- join, check, match, write ----------------------------------------
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    skirt.select_set(True)
    bpy.context.view_layer.objects.active = body
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

    sidecar = {
        "asset": target.name,
        "obj": target.with_suffix(".obj").name,
        "kitFile": args.kit.relative_to(ROOT).as_posix() if args.kit.is_relative_to(ROOT) else str(args.kit),
        "kitSha256": sha256_text(args.kit),
        "authoringConfig": args.config.relative_to(ROOT).as_posix() if args.config.is_relative_to(ROOT) else str(args.config),
        "authoringConfigSha256": sha256_text(args.config),
        "hashNote": "sha256 of the input with CRLF folded to LF",
        "landmarks": landmarks,
        "parts": [body_report, skirt_report],
        "nBodysuitVertices": body_report["vertices"],
        "nSkirtVertices": skirt_report["vertices"],
        "check": {key: value for key, value in check.items() if key != "warnings"},
        "stagesS": stages,
        "blender": bpy.app.version_string,
    }
    (args.out / f"{kit['name']}.build.json").write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    print(f"[author] wrote {target} and {target.with_suffix('.obj').name}; stages {stages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
