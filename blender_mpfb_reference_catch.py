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
    BallPresentation,
    DEFAULT_CONFIG_PATH,
    PresentationConfig,
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


def pose_shoulder_girdle(
    armature: bpy.types.Object,
    shoulder_targets: dict[str, Vector],
) -> None:
    for side in ("l", "r"):
        rotate_bone_toward(
            armature,
            f"clavicle_{side}",
            f"upperarm_{side}",
            shoulder_targets[side],
        )


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
    # The signed cross product is part of the mirrored MPFB rig convention.
    # Do not force both hands to the same sign: the approved reference view
    # depends on this exact projection of the two thumbs.
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
    finger_curl_degrees: dict[str, tuple[float, float]],
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

    def curved_directions(
        base_direction: Vector,
        digit: str,
    ) -> list[Vector]:
        base = base_direction.normalized()
        bend = toward_ball - base * toward_ball.dot(base)
        if bend.length < 1e-8:
            raise RuntimeError(f"cannot establish {side} {digit} curl plane")
        bend.normalize()
        first, second = finger_curl_degrees[digit]
        cumulative = (0.0, first, first + second)
        return [
            (
                base * math.cos(math.radians(angle))
                + bend * math.sin(math.radians(angle))
            ).normalized()
            for angle in cumulative
        ]

    for digit, spread in splay.items():
        chain = [f"{digit}_{index:02d}_{side}" for index in (1, 2, 3)]
        base_direction = (
            palm_direction + lateral * spread + toward_ball * 0.04
        ).normalized()
        directions = curved_directions(base_direction, digit)
        for index, (name, direction) in enumerate(zip(chain, directions)):
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
    thumb_base_direction = (
        palm_direction * 0.50 + lateral * 0.72 + toward_ball * 0.12
    ).normalized()
    thumb_directions = curved_directions(thumb_base_direction, "thumb")
    for index, (name, thumb_direction) in enumerate(
        zip(thumb_chain, thumb_directions)
    ):
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


def finger_joint_bends_degrees(armature: bpy.types.Object) -> list[float]:
    bends: list[float] = []
    for side in ("l", "r"):
        for digit in ("thumb", "index", "middle", "ring", "pinky"):
            directions = [
                (
                    world_tail(armature, f"{digit}_{index:02d}_{side}")
                    - world_head(armature, f"{digit}_{index:02d}_{side}")
                ).normalized()
                for index in (1, 2, 3)
            ]
            bends.extend(
                math.degrees(directions[index].angle(directions[index + 1]))
                for index in (0, 1)
            )
    return bends


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


def hand_depth_range(
    armature: bpy.types.Object,
    side: str,
    camera_location: Vector,
    camera_axis: Vector,
) -> tuple[float, float]:
    names = [f"hand_{side}"] + [
        f"{digit}_{index:02d}_{side}"
        for digit in ("thumb", "index", "middle", "ring", "pinky")
        for index in (1, 2, 3)
    ]
    depths = [
        (point - camera_location).dot(camera_axis)
        for name in names
        for point in (
            world_head(armature, name),
            world_tail(armature, name),
        )
    ]
    return min(depths), max(depths)


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


def make_fabric_material(
    presentation: PresentationConfig,
) -> bpy.types.Material:
    material = bpy.data.materials.new("BRAVEN_Graphite_Training_Kit")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = presentation.kit.base_color
    shader.inputs["Roughness"].default_value = presentation.kit.roughness
    sheen = shader.inputs.get("Sheen Weight")
    if sheen is not None:
        sheen.default_value = 0.08

    coordinates = nodes.new("ShaderNodeTexCoord")
    weave = nodes.new("ShaderNodeTexNoise")
    weave.inputs["Scale"].default_value = 150.0
    weave.inputs["Detail"].default_value = 2.0
    weave.inputs["Roughness"].default_value = 0.42
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.045
    bump.inputs["Distance"].default_value = 0.0007
    links.new(coordinates.outputs["Generated"], weave.inputs["Vector"])
    links.new(weave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def make_netball_material(ball_style: BallPresentation) -> bpy.types.Material:
    material = bpy.data.materials.new("BRAVEN_Netball_Panel_Surface")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = ball_style.roughness

    coordinates = nodes.new("ShaderNodeTexCoord")
    graphic = nodes.new("ShaderNodeTexWave")
    graphic.wave_type = "BANDS"
    graphic.bands_direction = "X"
    graphic.inputs["Scale"].default_value = 0.72
    graphic.inputs["Distortion"].default_value = 3.0
    graphic.inputs["Detail"].default_value = 2.5
    graphic.inputs["Detail Scale"].default_value = 1.8
    graphic.inputs["Detail Roughness"].default_value = 0.48
    colours = nodes.new("ShaderNodeValToRGB")
    colours.color_ramp.interpolation = "CONSTANT"
    colours.color_ramp.elements[0].position = 0.0
    colours.color_ramp.elements[0].color = ball_style.primary_color
    accent = colours.color_ramp.elements.new(0.38)
    accent.color = ball_style.accent_color
    secondary = colours.color_ramp.elements.new(0.52)
    secondary.color = ball_style.secondary_color
    colours.color_ramp.elements[1].position = 0.74
    colours.color_ramp.elements[1].color = ball_style.primary_color

    grip = nodes.new("ShaderNodeTexNoise")
    grip.inputs["Scale"].default_value = ball_style.grip_scale
    grip.inputs["Detail"].default_value = 1.6
    grip.inputs["Roughness"].default_value = 0.62
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.2
    bump.inputs["Distance"].default_value = 0.0014

    links.new(coordinates.outputs["Generated"], graphic.inputs["Vector"])
    links.new(graphic.outputs["Fac"], colours.inputs["Fac"])
    links.new(colours.outputs["Color"], shader.inputs["Base Color"])
    links.new(coordinates.outputs["Generated"], grip.inputs["Vector"])
    links.new(grip.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def create_panelled_netball(
    centre: Vector,
    radius: float,
    presentation: PresentationConfig,
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=96,
        ring_count=64,
        radius=radius,
        location=centre,
    )
    ball = bpy.context.active_object
    ball.name = "BRAVEN_Netball"
    ball.data.materials.append(make_netball_material(presentation.ball))
    for polygon in ball.data.polygons:
        polygon.use_smooth = True

    seam_material = make_material(
        "BRAVEN_Netball_Embossed_Seams",
        presentation.ball.seam_color,
        0.64,
    )
    seam_normals = (
        Vector((0.0, 0.0, 1.0)),
        Vector((1.0, 0.0, 0.0)),
        Vector((0.5, 0.8660254, 0.0)),
        Vector((-0.5, 0.8660254, 0.0)),
        Vector((0.24, -0.16, 1.0)).normalized(),
        Vector((-0.2, 0.3, 1.0)).normalized(),
    )
    seams: list[bpy.types.Object] = []
    for index, normal in enumerate(
        seam_normals[: presentation.ball.seam_loop_count],
        start=1,
    ):
        bpy.ops.mesh.primitive_torus_add(
            align="WORLD",
            major_segments=128,
            minor_segments=12,
            location=centre,
            major_radius=radius * 1.0005,
            minor_radius=0.00155,
        )
        seam = bpy.context.active_object
        seam.name = f"BRAVEN_Netball_Seam_{index:02d}"
        seam.rotation_mode = "QUATERNION"
        seam.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(
            normal
        )
        seam.data.materials.append(seam_material)
        for polygon in seam.data.polygons:
            polygon.use_smooth = True
        world_matrix = seam.matrix_world.copy()
        seam.parent = ball
        seam.matrix_world = world_matrix
        seams.append(seam)
    ball.rotation_mode = "XYZ"
    ball.rotation_euler = tuple(math.radians(value) for value in (18.0, -14.0, 24.0))
    return ball, seams


def asset_path(*parts: str) -> Path:
    path = ASSET_DATA.joinpath(*parts)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def create_athlete(
    presentation: PresentationConfig,
) -> tuple[bpy.types.Object, bpy.types.Object, list[bpy.types.Object], list[Path]]:
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
    trainers = asset_path("clothes", "shoes05", "shoes05.mhclo")
    hair = asset_path("hair", "ponytail01", "ponytail01.mhclo")
    eyes = asset_path("eyes", "high-poly", "high-poly.mhclo")
    brows = asset_path("eyebrows", "eyebrow006", "eyebrow006.mhclo")
    lashes = asset_path("eyelashes", "eyelashes01", "eyelashes01.mhclo")
    source_assets = [skin, suit, trainers, hair, eyes, brows, lashes]

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
            (trainers, "Clothes"),
            (hair, "Hair"),
            (eyes, "Eyes"),
            (brows, "Eyebrows"),
            (lashes, "Eyelashes"),
        )
    ]
    sportswear = assets[0]
    sportswear.data.materials.clear()
    sportswear.data.materials.append(make_fabric_material(presentation))
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


def add_camera_and_lights(
    presentation: PresentationConfig,
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.name = "BRAVEN_Reference_Camera"
    bpy.context.scene.camera = camera

    lights: list[bpy.types.Object] = []
    target = Vector(presentation.studio.light_target_m)
    for light in presentation.lights:
        data = bpy.data.lights.new(light.name, type="AREA")
        data.energy = light.energy
        data.shape = "DISK"
        data.size = light.size_m
        data.color = light.color
        item = bpy.data.objects.new(light.name, data)
        bpy.context.collection.objects.link(item)
        item.location = light.location_m
        item.rotation_euler = (target - item.location).to_track_quat(
            "-Z", "Y"
        ).to_euler()
        lights.append(item)
    return camera, lights


def add_studio_environment(
    presentation: PresentationConfig,
) -> bpy.types.Object:
    profile = [(-3.2, 0.0), (1.0, 0.0)]
    profile.extend(
        (
            1.0 + math.cos(math.radians(angle)),
            1.0 + math.sin(math.radians(angle)),
        )
        for angle in (-75, -60, -45, -30, -15, 0)
    )
    profile.append((2.0, 4.2))
    vertices = [
        (x, y, z)
        for y, z in profile
        for x in (-10.0, 10.0)
    ]
    faces = [
        (index * 2, index * 2 + 1, index * 2 + 3, index * 2 + 2)
        for index in range(len(profile) - 1)
    ]
    mesh = bpy.data.meshes.new("BRAVEN_Studio_Cyclorama_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    cyclorama = bpy.data.objects.new("BRAVEN_Studio_Cyclorama", mesh)
    bpy.context.collection.objects.link(cyclorama)
    cyclorama.data.materials.append(
        make_material(
            "BRAVEN_Studio_Navy",
            presentation.studio.cyclorama_color,
            presentation.studio.cyclorama_roughness,
        )
    )
    for polygon in cyclorama.data.polygons:
        polygon.use_smooth = True
    return cyclorama


def configure_render(
    path: Path,
    resolution: tuple[int, int],
    world_colour: tuple[float, float, float],
) -> None:
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
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (*world_colour, 1.0)
    background.inputs["Strength"].default_value = 0.22


def render_view(
    camera: bpy.types.Object,
    *,
    path: Path,
    resolution: tuple[int, int],
    location: Vector,
    target: Vector,
    lens: float,
    sensor_width: float,
    world_colour: tuple[float, float, float],
) -> dict[str, object]:
    camera.data.type = "PERSP"
    camera.data.lens = lens
    camera.data.sensor_width = sensor_width
    camera.location = location
    point_at(camera, target)
    configure_render(path, resolution, world_colour)
    path.unlink(missing_ok=True)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(str(path), check_existing=False)
    maximum_alpha = max_rgba_alpha(image.pixels)
    width, height = (int(value) for value in image.size)

    def corner_rgb(x: int, y: int) -> list[float]:
        offset = (y * width + x) * 4
        return [
            round(float(image.pixels[offset + channel]), 4)
            for channel in range(3)
        ]

    corners = {
        "bottomLeft": corner_rgb(0, 0),
        "bottomRight": corner_rgb(width - 1, 0),
        "topLeft": corner_rgb(0, height - 1),
        "topRight": corner_rgb(width - 1, height - 1),
    }
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
        "cornerRgb": corners,
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

    human, rig, assets, source_assets = create_athlete(config.presentation)
    character_objects = [rig, human, *assets]
    neutral_fbx = output / "braven_mpfb_athlete_neutral.fbx"
    export_fbx(neutral_fbx, character_objects, animation=False)

    baseline = {bone.name: bone.matrix.copy() for bone in rig.pose.bones}
    knees = pose_power_stance(rig, baseline)
    pose_shoulder_girdle(
        rig,
        {
            side: Vector(point)
            for side, point in config.shoulder_targets_m.items()
        },
    )
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
        side: pose_articulated_hand(
            rig,
            side=side,
            ball_centre=ball_centre,
            finger_curl_degrees=config.finger_curl_degrees,
        )
        for side in ("l", "r")
    }
    finger_joint_bends = finger_joint_bends_degrees(rig)
    min_finger_joint_bend = round(min(finger_joint_bends), 2)
    max_finger_joint_bend = round(max(finger_joint_bends), 2)
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

    ball, ball_seams = create_panelled_netball(
        ball_centre,
        config.ball_radius_m,
        config.presentation,
    )
    ball_objects = [ball, *ball_seams]
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

    reference_view: ViewConfig = config.views["referenceMatch"]
    reference_camera_location = Vector(reference_view.location_m)
    reference_camera_axis = (
        Vector(reference_view.target_m) - reference_camera_location
    ).normalized()
    _, foreground_hand_back_depth = hand_depth_range(
        rig,
        "l",
        reference_camera_location,
        reference_camera_axis,
    )
    rear_hand_front_depth, _ = hand_depth_range(
        rig,
        "r",
        reference_camera_location,
        reference_camera_axis,
    )
    ball_depth_ordering = {
        "foregroundHandSide": "left",
        "rearHandSide": "right",
        "foregroundHandBackDepthM": round(foreground_hand_back_depth, 5),
        "ballCentreDepthM": round(
            (ball_centre - reference_camera_location).dot(reference_camera_axis),
            5,
        ),
        "rearHandFrontDepthM": round(rear_hand_front_depth, 5),
    }

    studio = add_studio_environment(config.presentation)
    camera, lights = add_camera_and_lights(config.presentation)
    world_colour = config.presentation.studio.world_color
    crop_view: ViewConfig = config.views["referenceCrop"]
    crop = render_view(
        camera,
        path=output / "braven_mpfb_reference_catch_crop.png",
        resolution=crop_view.resolution_px,
        location=Vector(crop_view.location_m),
        target=Vector(crop_view.target_m),
        lens=crop_view.lens_mm,
        sensor_width=crop_view.sensor_width_mm,
        world_colour=world_colour,
    )
    calibration_view = render_view(
        camera,
        path=output / "braven_mpfb_reference_match.png",
        resolution=reference_view.resolution_px,
        location=Vector(reference_view.location_m),
        target=Vector(reference_view.target_m),
        lens=reference_view.lens_mm,
        sensor_width=reference_view.sensor_width_mm,
        world_colour=world_colour,
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
        world_colour=world_colour,
    )

    posed_fbx = output / "braven_mpfb_reference_catch.fbx"
    export_fbx(posed_fbx, [*character_objects, *ball_objects], animation=True)
    posed_glb = output / "braven_mpfb_reference_catch.glb"
    select_only([*character_objects, *ball_objects])
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
            "ballDepthOrdering": ball_depth_ordering,
            "kneesM": knees,
            "armsM": arm_receipt,
            "fingerDirections": finger_directions,
        },
        "camera": {
            "type": "PERSP",
            "width": crop_view.resolution_px[0],
            "height": crop_view.resolution_px[1],
        },
        "presentation": {
            "style": config.presentation.style,
            "kit": {
                "material": "procedural_fabric",
                "roughness": config.presentation.kit.roughness,
                "footwear": "sports_trainers",
            },
            "ball": {
                "type": "panelled_netball",
                "diameterM": round(config.ball_radius_m * 2.0, 3),
                "seamLoops": len(ball_seams),
                "surface": "procedural_dimple_grip",
                "graphic": "clean_three_colour_panel_graphic",
            },
            "studio": {
                "cyclorama": studio.name == "BRAVEN_Studio_Cyclorama",
                "lightCount": len(lights),
            },
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
            "minimumFingerJointBendDegrees": min_finger_joint_bend,
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
