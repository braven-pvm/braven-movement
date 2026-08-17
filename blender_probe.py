from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from movement_contract import max_rgba_alpha  # noqa: E402


OUTPUT_DIR = Path(tempfile.gettempdir()) / "braven_blender_glb_mvp_probe"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def point_at(item, target: Vector) -> None:
    item.rotation_euler = (target - item.location).to_track_quat("-Z", "Y").to_euler()


def set_up() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.resolution_x = 240
    scene.render.resolution_y = 300
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.875))
    subject = bpy.context.active_object
    subject.scale = (0.3, 0.2, 0.875)

    material = bpy.data.materials.new("PROBE_Material")
    material.diffuse_color = (0.05, 0.55, 0.5, 1.0)
    subject.data.materials.append(material)

    camera_data = bpy.data.cameras.new("PROBE_Camera")
    camera = bpy.data.objects.new("PROBE_Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (2.8, -5.0, 2.1)
    point_at(camera, Vector((0.0, 0.0, 0.8)))
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.5
    scene.camera = camera

    light_data = bpy.data.lights.new("PROBE_Key", "AREA")
    light_data.energy = 700.0
    light_data.size = 4.0
    light = bpy.data.objects.new("PROBE_Key", light_data)
    light.location = (-2.6, -4.2, 3.4)
    point_at(light, Vector((0.0, 0.0, 0.8)))
    scene.collection.objects.link(light)


def render_engine(engine: str) -> bool:
    scene = bpy.context.scene
    path = OUTPUT_DIR / f"probe_{engine.lower()}.png"
    if path.exists():
        path.unlink()
    try:
        scene.render.engine = engine
    except (TypeError, ValueError) as error:
        print(f"[probe] {engine} UNAVAILABLE {error}")
        return False
    if engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = 16
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if not path.is_file() or path.stat().st_size == 0:
        print(f"[probe] {engine} FAIL no non-empty PNG")
        return False
    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        maximum_alpha = max_rgba_alpha(image.pixels)
        dimensions = tuple(image.size)
    finally:
        bpy.data.images.remove(image)
    passed = maximum_alpha > 0
    print(
        f"[probe] {engine} {'PASS' if passed else 'FAIL'} "
        f"bytes={path.stat().st_size} dimensions={dimensions} max_alpha={maximum_alpha:.3f} path={path}"
    )
    return passed


set_up()
cycles = render_engine("CYCLES")
eevee = render_engine("BLENDER_EEVEE_NEXT")
print(
    f"[probe] SUMMARY blender={bpy.app.version_string} "
    f"cycles={'PASS' if cycles else 'FAIL'} eevee={'PASS' if eevee else 'FAIL'}"
)
if not cycles or not eevee:
    raise SystemExit(2)
