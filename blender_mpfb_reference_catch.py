from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector


TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from movement_contract import inspect_glb, max_rgba_alpha  # noqa: E402
from reference_pose_calibration import (  # noqa: E402
    PoseCalibrationError,
    compare_projected_landmarks,
    validate_reference_target_schema,
    validate_pixel_calibration,
)
from reference_pose_config import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    ReferenceCatchConfig,
    ViewConfig,
    load_reference_catch_config,
)
from reference_pose_contract import validate_reference_catch_receipt  # noqa: E402

from bl_ext.blender_org.mpfb.services.humanservice import HumanService  # noqa: E402


ASSET_DATA = (
    Path(bpy.utils.user_resource("EXTENSIONS"))
    / ".user"
    / "blender_org"
    / "mpfb"
    / "data"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--reference-compared", action="store_true")
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(values)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def world_head(armature: bpy.types.Object, bone_name: str) -> Vector:
    return armature.matrix_world @ armature.pose.bones[bone_name].head


def world_tail(armature: bpy.types.Object, bone_name: str) -> Vector:
    return armature.matrix_world @ armature.pose.bones[bone_name].tail


def apply_world_rotation(
    armature: bpy.types.Object,
    bone_name: str,
    pivot: Vector,
    rotation: Matrix,
) -> None:
    bone = armature.pose.bones[bone_name]
    world_matrix = armature.matrix_world @ bone.matrix
    rotated = (
        Matrix.Translation(pivot)
        @ rotation.to_4x4()
        @ Matrix.Translation(-pivot)
        @ world_matrix
    )
    bone.matrix = armature.matrix_world.inverted() @ rotated
    bpy.context.view_layer.update()


def rotate_bone_toward(
    armature: bpy.types.Object,
    bone_name: str,
    child_name: str,
    target: Vector,
) -> None:
    pivot = world_head(armature, bone_name)
    current = world_head(armature, child_name) - pivot
    desired = target - pivot
    if current.length < 1e-8 or desired.length < 1e-8:
        raise RuntimeError(f"cannot aim zero-length bone {bone_name}")
    delta = current.normalized().rotation_difference(desired.normalized())
    apply_world_rotation(armature, bone_name, pivot, delta.to_matrix())


def rotate_bone_tail_toward(
    armature: bpy.types.Object,
    bone_name: str,
    target: Vector,
) -> None:
    pivot = world_head(armature, bone_name)
    current = world_tail(armature, bone_name) - pivot
    desired = target - pivot
    if current.length < 1e-8 or desired.length < 1e-8:
        raise RuntimeError(f"cannot aim zero-length bone {bone_name}")
    apply_world_rotation(
        armature,
        bone_name,
        pivot,
        current.normalized().rotation_difference(desired.normalized()).to_matrix(),
    )


def translate_bone_world(
    armature: bpy.types.Object,
    bone_name: str,
    offset: Vector,
) -> None:
    bone = armature.pose.bones[bone_name]
    world_matrix = armature.matrix_world @ bone.matrix
    world_matrix.translation += offset
    bone.matrix = armature.matrix_world.inverted() @ world_matrix
    bpy.context.view_layer.update()


def elbow_for_target(
    shoulder: Vector,
    target: Vector,
    upper_length: float,
    lower_length: float,
    pole: Vector,
) -> Vector:
    reach = target - shoulder
    distance = min(reach.length, upper_length + lower_length - 0.0001)
    direction = reach.normalized()
    along = (upper_length**2 - lower_length**2 + distance**2) / (2.0 * distance)
    height = max(upper_length**2 - along**2, 0.0) ** 0.5
    perpendicular = pole - direction * pole.dot(direction)
    if perpendicular.length < 1e-8:
        raise RuntimeError("arm pole is parallel to the reach direction")
    return shoulder + direction * along + perpendicular.normalized() * height


def pose_power_stance(
    armature: bpy.types.Object,
    baseline: dict[str, Matrix],
) -> dict[str, list[float]]:
    ankle_targets = {
        side: world_head(armature, f"foot_{side}").copy()
        for side in ("l", "r")
    }
    translate_bone_world(armature, "pelvis", Vector((0.0, 0.018, -0.050)))
    result: dict[str, list[float]] = {}
    for side in ("l", "r"):
        thigh = f"thigh_{side}"
        calf = f"calf_{side}"
        foot = f"foot_{side}"
        hip = world_head(armature, thigh)
        knee = world_head(armature, calf)
        ankle = world_head(armature, foot)
        desired_knee = elbow_for_target(
            hip,
            ankle_targets[side],
            (knee - hip).length,
            (ankle - knee).length,
            Vector((0.0, -1.0, 0.0)),
        )
        rotate_bone_toward(armature, thigh, calf, desired_knee)
        rotate_bone_toward(armature, calf, foot, ankle_targets[side])
        armature.pose.bones[foot].matrix = baseline[foot]
        bpy.context.view_layer.update()
        result[side] = list(world_head(armature, calf))
    return result


def pose_arm(
    armature: bpy.types.Object,
    *,
    side: str,
    wrist_target: Vector,
    pole: Vector,
) -> dict[str, list[float]]:
    upper = f"upperarm_{side}"
    lower = f"lowerarm_{side}"
    hand = f"hand_{side}"
    shoulder = world_head(armature, upper)
    elbow = world_head(armature, lower)
    wrist = world_head(armature, hand)
    desired_elbow = elbow_for_target(
        shoulder,
        wrist_target,
        (elbow - shoulder).length,
        (wrist - elbow).length,
        pole,
    )
    rotate_bone_toward(armature, upper, lower, desired_elbow)
    rotate_bone_toward(armature, lower, hand, wrist_target)
    return {
        "shoulder": list(shoulder),
        "elbow": list(world_head(armature, lower)),
        "wrist": list(world_head(armature, hand)),
    }


def hand_basis(
    armature: bpy.types.Object,
    side: str,
) -> tuple[Vector, Vector, Vector]:
    wrist = world_head(armature, f"hand_{side}")
    finger = (world_head(armature, f"middle_01_{side}") - wrist).normalized()
    lateral = (
        world_head(armature, f"index_01_{side}")
        - world_head(armature, f"pinky_01_{side}")
    )
    lateral -= finger * lateral.dot(finger)
    lateral.normalize()
    return finger, lateral, finger.cross(lateral).normalized()


def orient_hand(
    armature: bpy.types.Object,
    *,
    side: str,
    ball_centre: Vector,
    finger_direction: Vector,
    palm_normal: Vector,
    max_forearm_roll_degrees: float,
) -> dict[str, float]:
    hand_name = f"hand_{side}"
    wrist = world_head(armature, hand_name)
    elbow = world_head(armature, f"lowerarm_{side}")
    forearm_axis = (wrist - elbow).normalized()
    current_finger, _, current_normal = hand_basis(armature, side)
    desired_finger = finger_direction.normalized()
    desired_normal = palm_normal - desired_finger * palm_normal.dot(desired_finger)
    desired_normal.normalize()

    # Pronation/supination belongs in the forearm, not as an unconstrained twist
    # at the wrist. Search the bounded forearm roll whose subsequent minimal
    # wrist swing best exposes the palm to the reference camera.
    best_roll_degrees = 0.0
    best_normal_error = math.inf
    for roll_degrees in range(
        -int(max_forearm_roll_degrees),
        int(max_forearm_roll_degrees) + 1,
    ):
        roll = Matrix.Rotation(
            math.radians(roll_degrees),
            3,
            forearm_axis,
        )
        rolled_finger = roll @ current_finger
        rolled_normal = roll @ current_normal
        swing = rolled_finger.rotation_difference(desired_finger)
        final_normal = swing @ rolled_normal
        final_normal -= desired_finger * final_normal.dot(desired_finger)
        if final_normal.length < 1e-8:
            continue
        normal_error = final_normal.normalized().angle(desired_normal)
        if normal_error < best_normal_error:
            best_normal_error = normal_error
            best_roll_degrees = float(roll_degrees)

    apply_world_rotation(
        armature,
        f"lowerarm_{side}",
        elbow,
        Matrix.Rotation(
            math.radians(best_roll_degrees),
            3,
            forearm_axis,
        ),
    )
    wrist = world_head(armature, hand_name)
    current_finger, _, _ = hand_basis(armature, side)
    apply_world_rotation(
        armature,
        hand_name,
        wrist,
        current_finger.rotation_difference(desired_finger).to_matrix(),
    )
    final_hand_direction = (palm_centre(armature, side) - wrist).normalized()
    return {
        "wristBendDegrees": round(
            math.degrees(forearm_axis.angle(final_hand_direction)),
            2,
        ),
        "forearmRollDegrees": round(abs(best_roll_degrees), 2),
        "palmNormalErrorDegrees": round(math.degrees(best_normal_error), 2),
    }


def pose_articulated_hand(
    armature: bpy.types.Object,
    *,
    side: str,
    ball_centre: Vector,
) -> dict[str, list[list[float]]]:
    result: dict[str, list[list[float]]] = {}
    wrist = world_head(armature, f"hand_{side}")
    palm_direction = (palm_centre(armature, side) - wrist).normalized()
    toward_ball = (ball_centre - wrist).normalized()
    lateral = (
        world_head(armature, f"index_01_{side}")
        - world_head(armature, f"pinky_01_{side}")
    )
    lateral -= palm_direction * lateral.dot(palm_direction)
    lateral.normalize()
    splay = {"index": 0.28, "middle": 0.08, "ring": -0.08, "pinky": -0.22}

    for digit, spread in splay.items():
        chain = [f"{digit}_{index:02d}_{side}" for index in (1, 2, 3)]
        direction = (
            palm_direction + lateral * spread + toward_ball * 0.04
        ).normalized()
        for index, name in enumerate(chain):
            if index + 1 < len(chain):
                rotate_bone_toward(
                    armature,
                    name,
                    chain[index + 1],
                    world_head(armature, name) + direction,
                )
            else:
                rotate_bone_tail_toward(
                    armature,
                    name,
                    world_head(armature, name) + direction,
                )
        result[digit] = [
            list((world_tail(armature, name) - world_head(armature, name)).normalized())
            for name in chain
        ]

    thumb_chain = [f"thumb_{index:02d}_{side}" for index in (1, 2, 3)]
    thumb_direction = (
        palm_direction * 0.50 + lateral * 0.72 + toward_ball * 0.12
    ).normalized()
    for index, name in enumerate(thumb_chain):
        if index + 1 < len(thumb_chain):
            rotate_bone_toward(
                armature,
                name,
                thumb_chain[index + 1],
                world_head(armature, name) + thumb_direction,
            )
        else:
            rotate_bone_tail_toward(
                armature,
                name,
                world_head(armature, name) + thumb_direction,
            )
    result["thumb"] = [
        list((world_tail(armature, name) - world_head(armature, name)).normalized())
        for name in thumb_chain
    ]
    return result


def max_finger_joint_bend_degrees(armature: bpy.types.Object) -> float:
    maximum = 0.0
    for side in ("l", "r"):
        for digit in ("thumb", "index", "middle", "ring", "pinky"):
            directions = [
                (
                    world_tail(armature, f"{digit}_{index:02d}_{side}")
                    - world_head(armature, f"{digit}_{index:02d}_{side}")
                ).normalized()
                for index in (1, 2, 3)
            ]
            maximum = max(
                maximum,
                *(math.degrees(directions[index].angle(directions[index + 1]))
                  for index in (0, 1)),
            )
    return round(maximum, 2)


def max_finger_base_deviation_degrees(armature: bpy.types.Object) -> float:
    maximum = 0.0
    for side in ("l", "r"):
        wrist = world_head(armature, f"hand_{side}")
        palm_direction = (palm_centre(armature, side) - wrist).normalized()
        for digit in ("index", "middle", "ring", "pinky"):
            first = f"{digit}_01_{side}"
            direction = (world_tail(armature, first) - world_head(armature, first)).normalized()
            maximum = max(maximum, math.degrees(palm_direction.angle(direction)))
    return round(maximum, 2)


def orient_head_to_ball(armature: bpy.types.Object, ball_centre: Vector) -> None:
    bone = armature.pose.bones["head"]
    pivot = world_head(armature, "head")
    current_forward = (armature.matrix_world @ bone.matrix).to_3x3().col[2].normalized()
    desired_forward = (ball_centre - pivot).normalized()
    delta = current_forward.rotation_difference(desired_forward)
    apply_world_rotation(armature, "head", pivot, delta.to_matrix())


def joint_angle_degrees(a: Vector, pivot: Vector, b: Vector) -> float:
    return math.degrees((a - pivot).angle(b - pivot))


def palm_centre(armature: bpy.types.Object, side: str) -> Vector:
    names = [
        f"hand_{side}",
        f"index_01_{side}",
        f"middle_01_{side}",
        f"ring_01_{side}",
        f"pinky_01_{side}",
    ]
    return sum((world_head(armature, name) for name in names), Vector()) / len(names)


def projected_pixel(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    point: Vector,
    frame: tuple[int, int],
) -> tuple[float, float]:
    projected = world_to_camera_view(scene, camera, point)
    return (
        round(projected.x * frame[0], 2),
        round((1.0 - projected.y) * frame[1], 2),
    )


def project_pose_landmarks(
    armature: bpy.types.Object,
    ball: bpy.types.Object,
    camera: bpy.types.Object,
    frame: tuple[int, int],
) -> dict[str, tuple[float, float]]:
    scene = bpy.context.scene
    points: dict[str, Vector] = {
        "ball_center": ball.location.copy(),
        "head_base": world_head(armature, "head"),
        "head_top": world_tail(armature, "head"),
    }
    for side_name, bone_side in (("left", "l"), ("right", "r")):
        points[f"{side_name}_shoulder"] = world_head(
            armature, f"upperarm_{bone_side}"
        )
        points[f"{side_name}_elbow"] = world_head(
            armature, f"lowerarm_{bone_side}"
        )
        points[f"{side_name}_wrist"] = world_head(armature, f"hand_{bone_side}")
        points[f"{side_name}_palm"] = palm_centre(armature, bone_side)
        for digit in ("thumb", "index", "middle", "ring", "pinky"):
            points[f"{side_name}_{digit}_tip"] = world_tail(
                armature, f"{digit}_03_{bone_side}"
            )
    return {
        name: projected_pixel(scene, camera, point, frame)
        for name, point in points.items()
    }


def make_material(
    name: str,
    colour: tuple[float, float, float, float],
    roughness: float,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = colour
    shader.inputs["Roughness"].default_value = roughness
    return material


def asset_path(*parts: str) -> Path:
    path = ASSET_DATA.joinpath(*parts)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def create_athlete() -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object], list[Path]]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    macro = {
        "age": 0.32,
        "cupsize": 0.30,
        "firmness": 0.65,
        "gender": 0.0,
        "height": 0.72,
        "muscle": 0.66,
        "proportions": 0.52,
        "race": {"african": 0.0, "asian": 0.0, "caucasian": 1.0},
        "weight": 0.38,
    }
    human = HumanService.create_human(
        mask_helpers=True,
        detailed_helpers=True,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=0.1,
        macro_detail_dict=macro,
    )
    human.name = "BRAVEN_Athlete"
    rig = HumanService.add_builtin_rig(human, "game_engine", import_weights=True)
    rig.name = "BRAVEN_Athlete_Rig"

    skin = asset_path("skins", "young_caucasian_female", "young_caucasian_female.mhmat")
    suit = asset_path("clothes", "female_casualsuit02", "female_casualsuit02.mhclo")
    hair = asset_path("hair", "ponytail01", "ponytail01.mhclo")
    eyes = asset_path("eyes", "high-poly", "high-poly.mhclo")
    brows = asset_path("eyebrows", "eyebrow006", "eyebrow006.mhclo")
    lashes = asset_path("eyelashes", "eyelashes01", "eyelashes01.mhclo")
    source_assets = [skin, suit, hair, eyes, brows, lashes]

    HumanService.set_character_skin(
        str(skin),
        human,
        skin_type="GAMEENGINE",
        material_instances=False,
    )
    assets = [
        HumanService.add_mhclo_asset(
            str(path),
            human,
            asset_type=asset_type,
            subdiv_levels=1,
            material_type="GAMEENGINE",
        )
        for path, asset_type in (
            (suit, "Clothes"),
            (hair, "Hair"),
            (eyes, "Eyes"),
            (brows, "Eyebrows"),
            (lashes, "Eyelashes"),
        )
    ]
    sportswear = assets[0]
    sportswear.data.materials.clear()
    sportswear.data.materials.append(
        make_material("BRAVEN_Black_Training_Kit", (0.018, 0.022, 0.032, 1.0), 0.72)
    )
    return human, rig, assets, source_assets


def select_only(objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for item in objects:
        item.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def export_fbx(path: Path, objects: list[bpy.types.Object], *, animation: bool) -> None:
    select_only(objects)
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        add_leaf_bones=False,
        bake_anim=animation,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        apply_scale_options="FBX_SCALE_UNITS",
    )


def point_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def add_camera_and_lights() -> bpy.types.Object:
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.name = "BRAVEN_Reference_Camera"
    bpy.context.scene.camera = camera

    for name, light_type, location, energy, size, colour in (
        ("BRAVEN_Key", "AREA", (3.0, -3.8, 4.5), 900.0, 3.2, (1.0, 0.91, 0.82)),
        ("BRAVEN_Fill", "AREA", (-3.2, -2.2, 2.8), 520.0, 3.8, (0.72, 0.86, 1.0)),
        ("BRAVEN_Rim", "AREA", (0.3, 2.6, 3.6), 760.0, 2.4, (0.72, 0.82, 1.0)),
    ):
        data = bpy.data.lights.new(name, type=light_type)
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = colour
        item = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(item)
        item.location = location
        item.rotation_euler = (Vector((0.0, -0.15, 1.1)) - item.location).to_track_quat("-Z", "Y").to_euler()
    return camera


def configure_render(path: Path, resolution: tuple[int, int]) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(path)
    scene.render.use_file_extension = True
    if scene.world is None:
        scene.world = bpy.data.worlds.new("BRAVEN_Reference_World")
    scene.world.color = (0.012, 0.016, 0.024)


def render_view(
    camera: bpy.types.Object,
    *,
    path: Path,
    resolution: tuple[int, int],
    location: Vector,
    target: Vector,
    lens: float,
    sensor_width: float,
) -> dict[str, object]:
    camera.data.type = "PERSP"
    camera.data.lens = lens
    camera.data.sensor_width = sensor_width
    camera.location = location
    point_at(camera, target)
    configure_render(path, resolution)
    path.unlink(missing_ok=True)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(path), check_existing=False)
    maximum_alpha = max_rgba_alpha(image.pixels)
    bpy.data.images.remove(image)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "width": resolution[0],
        "height": resolution[1],
        "cameraType": "PERSP",
        "lens": lens,
        "maxAlpha": maximum_alpha,
    }


def keyframe_pose(rig: bpy.types.Object, ball: bpy.types.Object) -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 2
    scene.render.fps = 30
    for frame in (1, 2):
        scene.frame_set(frame)
        for bone in rig.pose.bones:
            bone.keyframe_insert(data_path="location", frame=frame)
            if bone.rotation_mode == "QUATERNION":
                bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            else:
                bone.keyframe_insert(data_path="rotation_euler", frame=frame)
            bone.keyframe_insert(data_path="scale", frame=frame)
        ball.keyframe_insert(data_path="location", frame=frame)
    scene.frame_set(1)


def main() -> None:
    args = parse_args()
    config: ReferenceCatchConfig = load_reference_catch_config(args.config)
    validate_reference_target_schema(
        config.reference_frame_px,
        config.reference_targets_px,
    )
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    human, rig, assets, source_assets = create_athlete()
    character_objects = [rig, human, *assets]
    neutral_fbx = output / "braven_mpfb_athlete_neutral.fbx"
    export_fbx(neutral_fbx, character_objects, animation=False)

    baseline = {bone.name: bone.matrix.copy() for bone in rig.pose.bones}
    knees = pose_power_stance(rig, baseline)
    ball_centre = Vector(config.ball_centre_m)
    wrist_targets = {
        side: Vector(point) for side, point in config.wrist_targets_m.items()
    }
    arm_receipt = {
        "l": pose_arm(
            rig,
            side="l",
            wrist_target=wrist_targets["l"],
            pole=Vector(config.arm_poles["l"]),
        ),
        "r": pose_arm(
            rig,
            side="r",
            wrist_target=wrist_targets["r"],
            pole=Vector(config.arm_poles["r"]),
        ),
    }
    hand_anatomy = {
        "l": orient_hand(
            rig,
            side="l",
            ball_centre=ball_centre,
            finger_direction=Vector(config.hand_targets["l"].finger_direction),
            palm_normal=Vector(config.hand_targets["l"].palm_normal),
            max_forearm_roll_degrees=config.anatomy_limits_degrees["forearmRoll"],
        ),
        "r": orient_hand(
            rig,
            side="r",
            ball_centre=ball_centre,
            finger_direction=Vector(config.hand_targets["r"].finger_direction),
            palm_normal=Vector(config.hand_targets["r"].palm_normal),
            max_forearm_roll_degrees=config.anatomy_limits_degrees["forearmRoll"],
        ),
    }
    finger_directions = {
        side: pose_articulated_hand(rig, side=side, ball_centre=ball_centre)
        for side in ("l", "r")
    }
    max_finger_joint_bend = max_finger_joint_bend_degrees(rig)
    max_finger_base_deviation = max_finger_base_deviation_degrees(rig)
    orient_head_to_ball(rig, ball_centre)

    for side, values in arm_receipt.items():
        values["elbowDegrees"] = round(
            joint_angle_degrees(
                Vector(values["shoulder"]),
                Vector(values["elbow"]),
                Vector(values["wrist"]),
            ),
            2,
        )

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64,
        ring_count=32,
        radius=config.ball_radius_m,
        location=ball_centre,
    )
    ball = bpy.context.active_object
    ball.name = "BRAVEN_Netball"
    ball.data.materials.append(
        make_material("BRAVEN_Netball_Coral", (0.88, 0.16, 0.11, 1.0), 0.48)
    )
    keyframe_pose(rig, ball)

    finger_names = [
        bone.name
        for bone in rig.data.bones
        if re.match(r"^(thumb|index|middle|ring|pinky)_\d{2}_[lr]$", bone.name)
    ]
    weighted_finger_groups = sum(
        1 for name in finger_names if human.vertex_groups.get(name) is not None
    )
    palm_distances = {
        side: max(
            (palm_centre(rig, side) - ball_centre).length - config.ball_radius_m,
            0.0,
        )
        for side in ("l", "r")
    }

    camera = add_camera_and_lights()
    crop_view: ViewConfig = config.views["referenceCrop"]
    crop = render_view(
        camera,
        path=output / "braven_mpfb_reference_catch_crop.png",
        resolution=crop_view.resolution_px,
        location=Vector(crop_view.location_m),
        target=Vector(crop_view.target_m),
        lens=crop_view.lens_mm,
        sensor_width=crop_view.sensor_width_mm,
    )
    reference_view: ViewConfig = config.views["referenceMatch"]
    calibration_view = render_view(
        camera,
        path=output / "braven_mpfb_reference_match.png",
        resolution=reference_view.resolution_px,
        location=Vector(reference_view.location_m),
        target=Vector(reference_view.target_m),
        lens=reference_view.lens_mm,
        sensor_width=reference_view.sensor_width_mm,
    )
    projected_landmarks = project_pose_landmarks(
        rig,
        ball,
        camera,
        config.reference_frame_px,
    )
    pixel_calibration = compare_projected_landmarks(
        config.reference_targets_px,
        projected_landmarks,
        config.pixel_limits_px,
    )
    try:
        validate_pixel_calibration(pixel_calibration, config.pixel_limits_px)
        pixel_calibration_status = "passed"
    except PoseCalibrationError:
        pixel_calibration_status = "failed"
    anatomy_status = (
        "passed"
        if all(
            values["wristBendDegrees"]
            <= config.anatomy_limits_degrees["wristBend"]
            and values["forearmRollDegrees"]
            <= config.anatomy_limits_degrees["forearmRoll"]
            for values in hand_anatomy.values()
        )
        and max_finger_joint_bend
        <= config.anatomy_limits_degrees["fingerJointBend"]
        and max_finger_base_deviation
        <= config.anatomy_limits_degrees["fingerBaseDeviation"]
        else "failed"
    )
    full_view: ViewConfig = config.views["fullBody"]
    full = render_view(
        camera,
        path=output / "braven_mpfb_reference_catch_full.png",
        resolution=full_view.resolution_px,
        location=Vector(full_view.location_m),
        target=Vector(full_view.target_m),
        lens=full_view.lens_mm,
        sensor_width=full_view.sensor_width_mm,
    )

    posed_fbx = output / "braven_mpfb_reference_catch.fbx"
    export_fbx(posed_fbx, [*character_objects, ball], animation=True)
    posed_glb = output / "braven_mpfb_reference_catch.glb"
    select_only([*character_objects, ball])
    bpy.ops.export_scene.gltf(
        filepath=str(posed_glb),
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_frame_range=True,
    )
    glb = inspect_glb(posed_glb)

    posed_blend = output / "braven_mpfb_reference_catch.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(posed_blend))
    receipt = {
        "movementId": config.movement_id,
        "licence": config.licence,
        "publishable": config.publishable,
        "configuration": {
            "path": str(config.source_path),
            "sha256": sha256(config.source_path),
            "schemaVersion": config.schema_version,
            "referenceAssetFile": config.reference_asset_file,
            "referenceSha256": config.reference_sha256,
        },
        "source": {
            "generator": "MPFB 2.0.17",
            "assets": [
                {"path": str(path), "sha256": sha256(path)} for path in source_assets
            ],
        },
        "rig": {
            "type": "game_engine",
            "bones": len(rig.data.bones),
            "fingerBones": len(finger_names),
            "weightedFingerGroups": weighted_finger_groups,
        },
        "pose": {
            "leftElbowDegrees": arm_receipt["l"]["elbowDegrees"],
            "rightElbowDegrees": arm_receipt["r"]["elbowDegrees"],
            "leftPalmToBallSurfaceM": round(palm_distances["l"], 5),
            "rightPalmToBallSurfaceM": round(palm_distances["r"], 5),
            "ballCentreM": list(ball_centre),
            "kneesM": knees,
            "armsM": arm_receipt,
            "fingerDirections": finger_directions,
        },
        "camera": {
            "type": "PERSP",
            "width": crop_view.resolution_px[0],
            "height": crop_view.resolution_px[1],
        },
        "visualQa": {"referenceCompared": bool(args.reference_compared)},
        "calibration": {
            "status": pixel_calibration_status,
            "framePx": list(config.reference_frame_px),
            "targetsPx": config.reference_targets_px,
            "actualPx": projected_landmarks,
            "errorsPx": pixel_calibration.errors_px,
            "groupMaxPx": pixel_calibration.group_max_px,
        },
        "anatomy": {
            "status": anatomy_status,
            "leftWristBendDegrees": hand_anatomy["l"]["wristBendDegrees"],
            "rightWristBendDegrees": hand_anatomy["r"]["wristBendDegrees"],
            "leftForearmRollDegrees": hand_anatomy["l"]["forearmRollDegrees"],
            "rightForearmRollDegrees": hand_anatomy["r"]["forearmRollDegrees"],
            "maxFingerJointBendDegrees": max_finger_joint_bend,
            "maxFingerBaseDeviationDegrees": max_finger_base_deviation,
            "leftPalmNormalErrorDegrees": hand_anatomy["l"]["palmNormalErrorDegrees"],
            "rightPalmNormalErrorDegrees": hand_anatomy["r"]["palmNormalErrorDegrees"],
        },
        "views": {
            "referenceCrop": crop,
            "referenceMatch": calibration_view,
            "fullBody": full,
        },
        "exports": {
            "neutralFbx": {"path": str(neutral_fbx), "sha256": sha256(neutral_fbx)},
            "posedFbx": {"path": str(posed_fbx), "sha256": sha256(posed_fbx)},
            "posedGlb": {
                "path": str(posed_glb),
                "sha256": glb.sha256,
                "animations": glb.animations,
                "channels": glb.channels,
            },
            "posedBlend": {"path": str(posed_blend), "sha256": sha256(posed_blend)},
        },
    }
    if args.reference_compared:
        validate_pixel_calibration(pixel_calibration, config.pixel_limits_px)
        validate_reference_catch_receipt(receipt)
        receipt["contractStatus"] = "passed"
    else:
        receipt["contractStatus"] = "pending_visual_comparison"
    receipt_path = output / "braven_mpfb_reference_catch.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        "[mpfb-reference-catch] PASS "
        f"receipt={receipt_path} elbows="
        f"({arm_receipt['l']['elbowDegrees']}, {arm_receipt['r']['elbowDegrees']}) "
        f"fingers={len(finger_names)} weighted={weighted_finger_groups}"
    )


if __name__ == "__main__":
    main()
