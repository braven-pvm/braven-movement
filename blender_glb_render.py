from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from movement_contract import (  # noqa: E402
    ContractError,
    max_rgba_alpha,
    normalization_transform,
    read_job_manifest,
)


TARGET_HEIGHT = 1.75
RESOLUTION = (1080, 1350)
ENGINE = "BLENDER_EEVEE_NEXT"


def arguments() -> argparse.Namespace:
    cli = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Render one still from a Braven movement GLB job")
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frame", type=int)
    return parser.parse_args(cli)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def world_bounds(meshes: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    points: list[Vector] = []
    for source in meshes:
        evaluated = source.evaluated_get(depsgraph)
        points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    if not points:
        raise ContractError("imported GLB contains no mesh bounds")
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
    )


def normalise_imported(objects: list[bpy.types.Object], meshes: list[bpy.types.Object]) -> dict:
    minimum, maximum = world_bounds(meshes)
    transform = normalization_transform(
        minimum=tuple(minimum),
        maximum=tuple(maximum),
        target_height=TARGET_HEIGHT,
    )
    root = bpy.data.objects.new("BRAVEN_FigureRoot", None)
    bpy.context.scene.collection.objects.link(root)
    for item in objects:
        if item.parent is None and item is not root:
            matrix = item.matrix_world.copy()
            item.parent = root
            item.matrix_world = matrix
    root.scale = (transform.scale,) * 3
    root.location = (transform.offset_x, transform.offset_y, transform.offset_z)
    bpy.context.view_layer.update()
    return {
        "sourceMinimum": [round(value, 6) for value in minimum],
        "sourceMaximum": [round(value, 6) for value in maximum],
        "sourceHeight": round(maximum.z - minimum.z, 6),
        "targetHeight": TARGET_HEIGHT,
        "scale": transform.scale,
    }


def material_for_figure() -> bpy.types.Material:
    material = bpy.data.materials.new("BRAVEN_Teal")
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.035, 0.36, 0.34, 1.0)
    shader.inputs["Roughness"].default_value = 0.58
    shader.inputs["Metallic"].default_value = 0.0
    return material


def apply_look(meshes: list[bpy.types.Object]) -> None:
    material = material_for_figure()
    for item in meshes:
        item.data.materials.clear()
        item.data.materials.append(material)


def point_at(item: bpy.types.Object, target: Vector) -> None:
    item.rotation_euler = (target - item.location).to_track_quat("-Z", "Y").to_euler()


def add_camera_and_lights() -> None:
    camera_data = bpy.data.cameras.new("BRAVEN_Camera")
    camera = bpy.data.objects.new("BRAVEN_Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (3.4, -6.2, 2.35)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.35
    point_at(camera, Vector((0.0, 0.0, 0.92)))
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("BRAVEN_Key", (-3.2, -4.5, 5.2), 900.0, 4.0),
        ("BRAVEN_Fill", (4.5, -1.5, 3.0), 500.0, 3.0),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        point_at(light, Vector((0.0, 0.0, 0.9)))
        bpy.context.scene.collection.objects.link(light)


def configure_render(job, output: Path) -> None:
    scene = bpy.context.scene
    scene.render.engine = ENGINE
    scene.render.fps = int(round(job.fps))
    scene.render.fps_base = scene.render.fps / job.fps
    scene.frame_start = job.frame_start
    scene.frame_end = job.frame_end
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(output)


def inspect_render(path: Path) -> float:
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        return max_rgba_alpha(image.pixels)
    finally:
        bpy.data.images.remove(image)


def render() -> None:
    options = arguments()
    job = read_job_manifest(options.job.resolve())
    frame = job.frame_start if options.frame is None else options.frame
    if frame < job.frame_start or frame > job.frame_end:
        raise ContractError(f"frame {frame} outside {job.frame_start}..{job.frame_end}")

    output = options.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    clear_scene()
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(job.asset_path))
    imported = [item for item in bpy.context.scene.objects if item not in before]
    meshes = [item for item in imported if item.type == "MESH"]
    if not meshes:
        raise ContractError("GLB import produced no mesh objects")

    scene = bpy.context.scene
    scene.frame_set(frame)
    normalization = normalise_imported(imported, meshes)
    apply_look(meshes)
    add_camera_and_lights()
    configure_render(job, output)
    bpy.ops.render.render(write_still=True)

    if not output.is_file() or output.stat().st_size == 0:
        raise ContractError("Blender did not write a non-empty PNG")
    maximum_alpha = inspect_render(output)
    if maximum_alpha <= 0:
        raise ContractError("rendered PNG has no visible pixels")

    output_sha256 = hashlib.sha256(output.read_bytes()).hexdigest()
    receipt = {
        "renderVersion": 1,
        "movementId": job.movement_id,
        "publishable": job.publishable,
        "sourceAsset": job.asset_path.name,
        "sourceSha256": job.asset_sha256,
        "output": output.name,
        "outputSha256": output_sha256,
        "outputBytes": output.stat().st_size,
        "resolution": list(RESOLUTION),
        "frame": frame,
        "fps": job.fps,
        "engine": ENGINE,
        "blender": bpy.app.version_string,
        "meshCount": len(meshes),
        "maxAlpha": maximum_alpha,
        "normalization": normalization,
    }
    receipt_path = output.with_suffix(".render.json")
    temporary = receipt_path.with_suffix(receipt_path.suffix + ".tmp")
    temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temporary.replace(receipt_path)
    print(
        f"[render] PASS output={output} bytes={output.stat().st_size} "
        f"max_alpha={maximum_alpha:.3f} receipt={receipt_path}"
    )


if __name__ == "__main__":
    render()
