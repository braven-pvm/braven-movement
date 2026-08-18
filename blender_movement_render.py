"""Pose and render the solved movement on the MPFB athlete.

`blender_mpfb_reference_catch.py` builds one pose from one photograph and
proves it against that photograph. This renders many poses from the movement
engine, which has already solved them and graded them against the coaches
manual. The posing, the athlete and the anatomy limits are that module's, and
this one supplies the targets and the loop.

The job carries nothing absolute except the ball, because the MPFB athlete is
not the size or the shape of the one the engine solves on. Reach arrives as a
direction and a fraction of an arm, stance as a fraction of a leg, and the ball
as an offset in arms from the point between the wrists. Refer to
spikes/export_blender_job.py, which writes it.

    blender -b --python-exit-code 9 -P blender_movement_render.py -- \
        --job spikes/poc-output/<movement>.job.json --output <directory>
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from blender_mpfb_reference_catch import (  # noqa: E402
    add_camera_and_lights,
    create_athlete,
    elbow_for_target,
    make_material,
    orient_hand,
    orient_head_to_ball,
    pose_arm,
    pose_articulated_hand,
    render_view,
    rotate_bone_toward,
    select_only,
    sha256,
    translate_bone_world,
    world_head,
)

# The knee leads forward. The athlete faces negative Y.
KNEE_POLE = Vector((0.0, -1.0, 0.0))


def add_floor() -> None:
    """Give her something to stand on.

    A figure with no floor and no contact shadow reads as floating, and a
    coach cannot tell a landing from a jump. The reference generator makes
    one pose against a photograph and does not need this. A sequence of
    phases does.
    """
    bpy.ops.mesh.primitive_plane_add(size=14.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.active_object
    floor.name = "BRAVEN_Floor"
    floor.data.materials.append(
        make_material("BRAVEN_Floor", (0.20, 0.21, 0.23, 1.0), 0.85)
    )


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", action="append", default=None)
    parser.add_argument("--turntable", type=int, default=0)
    parser.add_argument("--animate", action="store_true")
    parser.add_argument("--no-stills", action="store_true")
    return parser.parse_args(argv)


def turntable(count: int, target: Vector, radius: float, height: float):
    """Camera positions all the way round, starting at the front.

    Three fixed views leave a pose ambiguous. A hand behind a ball and a hand
    beside it look the same from one angle and different from the next one
    round, and a coach cannot judge which it is from three pictures.
    """
    for step in range(count):
        angle = 2.0 * math.pi * step / count
        yield (
            f"turn{round(math.degrees(angle)):03d}",
            Vector((
                target.x + radius * math.sin(angle),
                target.y - radius * math.cos(angle),
                height,
            )),
        )


def keyframe(rig, ball, frame: int) -> None:
    for bone in rig.pose.bones:
        bone.keyframe_insert(data_path="location", frame=frame)
        if bone.rotation_mode == "QUATERNION":
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        else:
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        bone.keyframe_insert(data_path="scale", frame=frame)
    ball.keyframe_insert(data_path="location", frame=frame)


def render_movie(camera, *, path: Path, resolution, location, target, lens,
                 sensor_width, fps: int) -> None:
    scene = bpy.context.scene
    camera.data.type = "PERSP"
    camera.data.lens = lens
    camera.data.sensor_width = sensor_width
    camera.location = location
    camera.rotation_euler = (
        target - camera.location
    ).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = str(path.with_suffix(""))
    scene.render.use_file_extension = True
    bpy.ops.render.render(animation=True)


def bone_chain_length(rig, *bones: str) -> float:
    total = 0.0
    for parent, child in zip(bones, bones[1:]):
        total += (world_head(rig, child) - world_head(rig, parent)).length
    return total


def reset_pose(rig, basis: dict) -> None:
    """Put every bone back where the athlete was made, before posing again."""
    for bone in rig.pose.bones:
        bone.matrix_basis = basis[bone.name].copy()
    bpy.context.view_layer.update()


def pose_stance(rig, stance: dict, foot_baseline: dict) -> dict:
    """Place the feet from the job, and keep them flat on the floor.

    Flat is not a detail. The engine has no floor constraint and holds the
    ankle 48 to 62 degrees plantarflexed on every drill, which drives the ball
    of the foot through the floor. Restoring the foot's own world matrix after
    the leg is aimed is how the reference generator keeps it flat, and it is
    what stops that defect reaching the page.
    """
    leg = sum(
        bone_chain_length(rig, f"thigh_{side}", f"calf_{side}", f"foot_{side}")
        for side in ("l", "r")
    ) / 2.0
    wanted = {
        side: Vector(stance["ankleFromPelvisInLegs"][side]) * leg
        for side in ("l", "r")
    }

    # Put the lower foot on the floor the athlete was built standing on.
    floor = min(world_head(rig, f"foot_{side}").z for side in ("l", "r"))
    pelvis = world_head(rig, "pelvis")
    target = Vector((
        pelvis.x,
        pelvis.y,
        floor - min(wanted[side].z for side in ("l", "r")),
    ))
    translate_bone_world(rig, "pelvis", target - pelvis)

    pelvis = world_head(rig, "pelvis")
    placed = {}
    for side in ("l", "r"):
        ankle = pelvis + wanted[side]
        thigh, calf, foot = f"thigh_{side}", f"calf_{side}", f"foot_{side}"
        hip = world_head(rig, thigh)
        knee = elbow_for_target(
            hip,
            ankle,
            (world_head(rig, calf) - hip).length,
            (world_head(rig, foot) - world_head(rig, calf)).length,
            KNEE_POLE,
        )
        rotate_bone_toward(rig, thigh, calf, knee)
        rotate_bone_toward(rig, calf, foot, ankle)
        rig.pose.bones[foot].matrix = foot_baseline[foot]
        bpy.context.view_layer.update()
        placed[side] = list(world_head(rig, foot))
    return placed


def pose_phase(rig, phase: dict, limits: dict, basis: dict, foot_baseline: dict):
    reset_pose(rig, basis)
    stance = pose_stance(rig, phase["stance"], foot_baseline)

    # The ball is placed from the body, and it is the one absolute size in the
    # scene. A grip on it cannot be carried across as a direction from the
    # shoulder, because narrower shoulders would then hold it with narrower
    # hands, which is not how holding a ball works.
    arm = bone_chain_length(rig, "upperarm_l", "lowerarm_l", "hand_l")
    shoulders = (
        world_head(rig, "upperarm_l") + world_head(rig, "upperarm_r")
    ) / 2.0
    ball_centre = shoulders + Vector(phase["ball"]["fromShouldersInArms"]) * arm
    radius = phase["ball"]["radiusM"]
    grip = phase.get("grip")

    arms = {}
    for side in ("l", "r"):
        wanted = phase["arms"][side]
        shoulder = world_head(rig, f"upperarm_{side}")
        reach = bone_chain_length(
            rig, f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"
        )
        if grip is None:
            # Still reaching for it. The arm says where the hand goes.
            target = shoulder + Vector(wanted["direction"]) * (
                wanted["reachFraction"] * reach
            )
        else:
            # She has it. The ball says where the hand goes.
            target = ball_centre + Vector(grip[side]["outward"]) * (
                radius + grip[side]["wristFromSurfaceInArms"] * reach
            )
        arms[side] = pose_arm(
            rig, side=side, wrist_target=target, pole=Vector(wanted["pole"])
        )

    hands = {}
    for side in ("l", "r"):
        hands[side] = orient_hand(
            rig,
            side=side,
            ball_centre=ball_centre,
            finger_direction=Vector(phase["hands"][side]["fingerDirection"]),
            palm_normal=Vector(phase["hands"][side]["palmNormal"]),
            max_forearm_roll_degrees=limits["forearmRoll"],
        )
        pose_articulated_hand(rig, side=side, ball_centre=ball_centre)
    orient_head_to_ball(rig, ball_centre)
    return ball_centre, {"stance": stance, "arms": arms, "hands": hands}


def main() -> None:
    args = parse_args()
    job = json.loads(args.job.read_text(encoding="utf-8"))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    wanted = args.phase or [phase["name"] for phase in job["phases"]]
    phases = [phase for phase in job["phases"] if phase["name"] in wanted]
    if not phases:
        raise SystemExit(f"no phase of {job['movementId']} matches {wanted}")

    human, rig, assets, source_assets = create_athlete()
    basis = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones}
    foot_baseline = {
        f"foot_{side}": rig.pose.bones[f"foot_{side}"].matrix.copy()
        for side in ("l", "r")
    }
    camera = add_camera_and_lights()
    add_floor()

    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64, ring_count=32, radius=job["phases"][0]["ball"]["radiusM"]
    )
    ball = bpy.context.active_object
    ball.name = "BRAVEN_Netball"
    ball.data.materials.append(
        make_material("BRAVEN_Netball_Coral", (0.88, 0.16, 0.11, 1.0), 0.48)
    )

    rendered = []
    for phase in phases if not args.no_stills else []:
        centre, receipt = pose_phase(
            rig, phase, job["anatomyLimitsDegrees"], basis, foot_baseline
        )
        ball.location = centre
        bpy.context.view_layer.update()

        images = {}
        for name, view in job["views"].items():
            path = output / f"{job['movementId']}.{phase['name']}.{name}.png"
            images[name] = render_view(
                camera,
                path=path,
                resolution=tuple(view["resolutionPx"]),
                location=Vector(view["locationM"]),
                target=Vector(view["targetM"]),
                lens=view["lensMm"],
                sensor_width=view["sensorWidthMm"],
            )
        receipt["name"] = phase["name"]
        receipt["frame"] = phase["frame"]
        receipt["ballCentreM"] = list(centre)
        if args.turntable:
            target = Vector(job["views"]["front"]["targetM"])
            front = Vector(job["views"]["front"]["locationM"])
            radius = math.hypot(front.x - target.x, front.y - target.y)
            for name, location in turntable(
                args.turntable, target, radius, front.z
            ):
                path = output / (
                    f"{job['movementId']}.{phase['name']}.{name}.png"
                )
                images[name] = render_view(
                    camera,
                    path=path,
                    resolution=tuple(job["views"]["front"]["resolutionPx"]),
                    location=location,
                    target=target,
                    lens=job["views"]["front"]["lensMm"],
                    sensor_width=job["views"]["front"]["sensorWidthMm"],
                )
        receipt["views"] = images
        rendered.append(receipt)
        print(
            f"[movement-render] {phase['name']} frame {phase['frame']} "
            f"-> {len(images)} views"
        )

    animation = None
    if args.animate:
        frames = job.get("frames") or []
        if not frames:
            raise SystemExit(
                "the job carries no frames. Export it with --every=N."
            )
        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = len(frames)
        fps = max(1, round(job["framesPerSecond"] / max(job["frameStep"], 1)))
        # Set the frame before posing. Once keys exist, changing the frame
        # evaluates them and would replace whatever was posed first.
        for number, frame in enumerate(frames, start=1):
            scene.frame_set(number)
            centre, _ = pose_phase(
                rig, frame, job["anatomyLimitsDegrees"], basis, foot_baseline
            )
            ball.location = centre
            keyframe(rig, ball, number)
        scene.frame_set(1)

        glb = output / f"{job['movementId']}.glb"
        select_only([rig, human, *assets, ball])
        bpy.ops.export_scene.gltf(
            filepath=str(glb),
            export_format="GLB",
            use_selection=True,
            export_animations=True,
            export_frame_range=True,
        )
        movie = output / f"{job['movementId']}.mp4"
        view = job["views"]["quarter"]
        render_movie(
            camera,
            path=movie,
            resolution=tuple(view["resolutionPx"]),
            location=Vector(view["locationM"]),
            target=Vector(view["targetM"]),
            lens=view["lensMm"],
            sensor_width=view["sensorWidthMm"],
            fps=fps,
        )
        animation = {
            "frames": len(frames),
            "framesPerSecond": fps,
            "glb": {"path": str(glb), "bytes": glb.stat().st_size,
                    "sha256": sha256(glb)},
            "movie": {"path": str(movie),
                      "bytes": movie.stat().st_size if movie.is_file() else 0},
        }
        print(
            f"[movement-render] animated {len(frames)} frames at {fps} fps "
            f"-> {glb.name} ({glb.stat().st_size // 1024} KB), {movie.name}"
        )

    receipt_path = output / f"{job['movementId']}.render.json"
    receipt_path.write_text(
        json.dumps(
            {
                "movementId": job["movementId"],
                "skill": job["skill"],
                "jobSha256": sha256(args.job),
                "sourceAssets": [str(path) for path in source_assets],
                "animation": animation,
                "phases": rendered,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[movement-render] PASS receipt={receipt_path}")


if __name__ == "__main__":
    main()
