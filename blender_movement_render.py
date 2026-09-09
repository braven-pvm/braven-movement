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
SPIKE_DIR = MODULE_DIR / "spikes"
if str(SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(SPIKE_DIR))

from render_receipt import render_outcome  # noqa: E402
# What the receipt may claim about the assets that drew the figure. It has no
# Blender in it, so a test can call it; this module's own tests skip.
from asset_licences import source_asset_records  # noqa: E402
# The repository's ONE build stamp, shared with every other receipt this
# project writes, and the shape `archive_receipts.py` reads. It is cached
# for the life of the process, so every receipt of one run names one build.
from build_stamp import generated_from  # noqa: E402
# The girdle rule lives apart from Blender so it can be tested without it.
from girdle_agreement import (  # noqa: E402
    AGREES,
    DISAGREES,
    OUT_OF_REACH,
    UNAVAILABLE,
    agreement,
    classify,
    reachable_miss_mm,
    refuse_unrenderable_girdle,
    shoulder_position,
)
from reference_pose_config import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    load_reference_catch_config,
)
from blender_mpfb_reference_catch import (  # noqa: E402
    add_camera_and_lights,
    bake_shape_keys,
    create_athlete,
    create_panelled_netball,
    elbow_for_target,
    body_surface_clearance,
    finger_surface_clearance,
    make_material,
    orient_hand,
    orient_head_to_ball,
    pose_arm,
    pose_articulated_hand,
    render_view,
    rotate_bone_toward,
    select_only,
    set_alpha,
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


HELPER_GROUPS = ("HelperGeometry", "JointCubes")


def delete_helper_geometry(human) -> str:
    """Remove MakeHuman's fitting helpers before the model leaves Blender.

    The MakeHuman base mesh is 19158 vertices, of which only 13380 are the
    body. The rest are helpers: a tube round the legs that clothes are fitted
    to, cubes at every joint, and patches over the eyes, hair and teeth.
    Blender hides them through the alpha channel of the skin texture, so they
    never appear in a render.

    That masking does not survive the glTF export. The helpers arrive opaque,
    and the athlete has a skirt to the floor, ladders down her thighs and
    streaks across her face. The reference generator's own export has this
    too, so it predates this module.

    Deleting them is safe here because the clothes are already fitted and the
    model is on its way out.
    """
    import bmesh

    mesh = human.data
    wanted = {human.vertex_groups[name].index
              for name in HELPER_GROUPS if name in human.vertex_groups}
    if not wanted:
        return "no helper groups"
    keep = human.vertex_groups["body"].index if "body" in human.vertex_groups         else None

    doomed = []
    for vertex in mesh.vertices:
        groups = {g.group for g in vertex.groups if g.weight > 0.0}
        if groups & wanted and (keep is None or keep not in groups):
            doomed.append(vertex.index)
    if not doomed:
        return "no helper vertices"

    was = len(mesh.vertices)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in doomed], context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return f"{was} to {len(mesh.vertices)} vertices"


def bake_action(rig, first: int, last: int) -> None:
    """Rewrite the action by visual keying, for the exporter.

    Every bone here is posed by assigning a world matrix, because that is how
    the reference generator aims a limb at a target. Blender evaluates that
    correctly and renders it correctly. The glTF exporter samples the action
    instead, and the values a matrix assignment leaves behind do not survive
    that sampling, so the exported athlete arrives smeared while the rendered
    one is perfect.

    Visual keying reads the pose Blender actually evaluates and writes it back
    as plain translate, rotate and scale keys, which is what the format stores.
    """
    bpy.ops.object.mode_set(mode="OBJECT")
    for item in bpy.context.selected_objects:
        item.select_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(
        frame_start=first,
        frame_end=last,
        only_selected=True,
        visual_keying=True,
        clear_constraints=False,
        clear_parents=False,
        use_current_action=True,
        bake_types={"POSE"},
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    # Repeatable. Building the athlete costs about two minutes and the phases
    # cost fifteen seconds each, so eight drills in one session are far
    # cheaper than eight sessions.
    parser.add_argument("--job", type=Path, required=True, action="append")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
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
                 sensor_width, fps: int) -> Path:
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

    # Blender appends the frame range to a movie's name, so asking for
    # <movement>.mp4 produces <movement>0001-0049.mp4. The receipt used to
    # record the name that was asked for, which is a path to a file that does
    # not exist and a size of zero. Report what was actually written.
    stem = path.with_suffix("").name
    produced = sorted(
        item for item in path.parent.glob(f"{stem}*")
        if item.suffix.lower() == path.suffix.lower()
    )
    if not produced:
        raise SystemExit(f"the movie render wrote no file matching {stem}*{path.suffix}")
    return produced[-1]


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


GIRDLE_FIELD = "shoulderShiftFromRestInTorsos"



def rest_girdle(rig) -> dict:
    """The rest geometry the transmitted girdle shift is resolved against.

    READ THIS WHILE THE RIG IS AT REST. `pose_phase` calls it on the line after
    `reset_pose`, which is the only moment in a pose when the rest values are
    readable without a second reset.

    `torso` is the MAGNITUDE of the pelvis to shoulder-midpoint span and not
    its vertical component. The two agree to 8 microns on this rig, because its
    rest torso is almost vertical, and on another body they need not.
    """
    pelvis = world_head(rig, "pelvis")
    shoulders = {
        side: world_head(rig, f"upperarm_{side}") for side in ("l", "r")
    }
    midpoint = (shoulders["l"] + shoulders["r"]) / 2.0
    return {
        "pelvis": pelvis,
        "offset": {side: shoulders[side] - pelvis for side in ("l", "r")},
        "torso": (midpoint - pelvis).length,
        # The clavicle's own length. It is the RADIUS of everything the girdle
        # can reach, because the bone rotates about its sternal end and does
        # not stretch.
        "clavicle": {
            side: (shoulders[side] - world_head(rig, f"clavicle_{side}")).length
            for side in ("l", "r")
        },
        # The rest direction of each clavicle, so the receipt can say HOW FAR
        # the bone was turned. A displacement in millimetres does not say
        # whether the girdle was nudged or wrenched.
        "clavicleAxis": {
            side: (shoulders[side] - world_head(rig, f"clavicle_{side}")).normalized()
            for side in ("l", "r")
        },
    }


def pose_girdle(rig, phase: dict, rest: dict) -> dict:
    """Put the shoulder girdle where the solve put it, and report the fit.

    Until 2026-09-04 this renderer never posed a clavicle. It held one girdle
    for all 43 graded phases of ten drills while the engine's travelled 8.45 cm
    inside the overhead pass alone, and the ball is placed from the shoulder
    midpoint, so the ball carried the whole of that error. 15 of 43 figures
    passed a one-centimetre rule.

    The job now sends each shoulder's displacement from its OWN rest position,
    pelvis-relative on both sides of the subtraction, over its own rest torso.
    Resolving it here is a within-rig operation: this rig's rest girdle, this
    rig's rest torso, this rig's posed pelvis. Nothing of the other body's
    geometry enters, which is why the two rigs' 2.5 cm rest-posture difference
    cannot leak in.

    THE CLAVICLE ROTATES AND DOES NOT STRETCH, so the shoulder lands on a
    sphere about the clavicle's own head and a target off that sphere cannot be
    reached. The residual is MEASURED and reported rather than forced. Scaling
    a clavicle to hit a number would invent an anatomy no solve produced, which
    is the fault this whole field exists to remove.

    `out of reach` IS NOT EVIDENCE THAT THE AIM IS RIGHT, and it must not be
    read as one. `rotate_bone_toward` lands on the radial projection of the
    target BY CONSTRUCTION, so `beyondReachableMm` is zero on every one of the
    102 targets measured and the `disagrees` branch is unreachable from this
    caller as the code stands. It is a TRIPWIRE for a later change that clamps
    the rotation, constrains the bone or moves the pivot, not a check that has
    passed. The number that says whether the FIGURE is right is
    `ballAnchorErrorMm`, which is not an identity and does fail: 2 of 51 phases
    exceed the ten-millimetre rule.

    A phase with no field leaves the girdle at rest and reports `unavailable`.
    It must never read as agreement: the defect this replaces was a missing
    landmark behaving like a satisfied one.
    """
    shift = phase.get(GIRDLE_FIELD)
    if shift is None:
        return {
            "verdict": UNAVAILABLE,
            "restTorsoM": round(rest["torso"], 6),
            "worstOffsetMm": None,
            "sides": {},
        }

    pelvis = world_head(rig, "pelvis")
    # THE TESTED FUNCTION, NOT A SECOND COPY OF IT. This formula was written
    # out inline here once, beside a `shoulder_position` in girdle_agreement
    # that carried its guards and had no caller. Two copies of one rule means
    # the tested one is not the one that runs.
    wanted = {
        side: Vector(shoulder_position(
            shift[side], tuple(rest["offset"][side]), tuple(pelvis),
            rest["torso"],
        ))
        for side in ("l", "r")
    }
    for side in ("l", "r"):
        # The reference module's `pose_shoulder_girdle` is this same call per
        # side. It is made directly here because each side's residual is
        # measured separately, and a girdle can change WIDTH as well as move.
        rotate_bone_toward(
            rig, f"clavicle_{side}", f"upperarm_{side}", wanted[side]
        )
    bpy.context.view_layer.update()

    sides, worst, excess = {}, 0.0, 0.0
    for side in ("l", "r"):
        rendered = world_head(rig, f"upperarm_{side}")
        report = agreement(tuple(rendered), tuple(wanted[side]))
        # THE SMALLEST MISS THE ANATOMY ALLOWS. The shoulder lands on a sphere
        # of the clavicle's length about the clavicle's head, so a target off
        # that sphere costs at least the difference in radius. Reporting this
        # beside the miss separates two things a single number would merge: an
        # aim this lane got wrong, and a reach this rig does not have.
        pivot = world_head(rig, f"clavicle_{side}")
        reachable = reachable_miss_mm(
            tuple(wanted[side]), tuple(pivot), rest["clavicle"][side]
        )
        over = report["offsetMm"] - reachable
        worst = max(worst, report["offsetMm"])
        excess = max(excess, over)
        turned = math.degrees(
            rest["clavicleAxis"][side].angle(
                (rendered - pivot).normalized()
            )
        )
        sides[side] = {
            "verdict": classify(report["offsetMm"], reachable),
            "clavicleTurnedDegrees": round(turned, 3),
            "offsetMm": round(report["offsetMm"], 4),
            "reachableMissMm": round(reachable, 4),
            "beyondReachableMm": round(over, 4),
            "perAxisMm": [round(value, 4) for value in report["perAxisMm"]],
            "shiftInTorsos": shift[side],
        }
    # THE NUMBER THE BALL CARRIES. The ball is placed from the shoulder
    # MIDPOINT, so a per-shoulder miss is not what lands in the figure. The two
    # shoulders fall short outward along their own clavicles and those errors
    # largely cancel here, which is why the ball can be right while the girdle
    # is narrow. Without this a reader sees 25 mm and a benign verdict and
    # cannot tell which one the figure inherits.
    wanted_mid = (wanted["l"] + wanted["r"]) / 2.0
    rendered_mid = (world_head(rig, "upperarm_l")
                    + world_head(rig, "upperarm_r")) / 2.0
    verdicts = {entry["verdict"] for entry in sides.values()}
    if verdicts == {AGREES}:
        verdict = AGREES
    elif verdicts <= {AGREES, OUT_OF_REACH}:
        # The aim is exact and the bone is too short. That is this rig's
        # anatomy, not a defect in the resolution, and it must not read as one.
        verdict = OUT_OF_REACH
    else:
        # THE CONSTANT, NOT THE LITERAL. `refuse_unrenderable_girdle` compares
        # against the imported name, so a rename here would leave a string the
        # refusal no longer recognises. That fails closed, but by accident.
        verdict = DISAGREES
    return {
        "verdict": verdict,
        "restTorsoM": round(rest["torso"], 6),
        "worstOffsetMm": round(worst, 4),
        "worstBeyondReachableMm": round(excess, 4),
        # What the BALL inherits, in millimetres.
        "ballAnchorErrorMm": round((rendered_mid - wanted_mid).length * 1000.0, 4),
        "renderedWidthMm": round(
            (world_head(rig, "upperarm_l")
             - world_head(rig, "upperarm_r")).length * 1000.0, 4),
        "wantedWidthMm": round((wanted["l"] - wanted["r"]).length * 1000.0, 4),
        "sides": sides,
    }


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


def pose_phase(rig, phase: dict, limits: dict, basis: dict, foot_baseline: dict,
               finger_curl_degrees: dict, knuckle_limits: dict | None = None,
               body=None):
    reset_pose(rig, basis)
    # THE RIG IS AT REST ON THIS LINE AND NOWHERE LATER, so the girdle's rest
    # geometry is read here and passed forward.
    rest = rest_girdle(rig)
    stance = pose_stance(rig, phase["stance"], foot_baseline)
    # The girdle moves BEFORE the ball is placed and before the arms are aimed,
    # because the ball is placed from the shoulder midpoint and every arm is
    # aimed from its own shoulder. Posing it afterwards would move the
    # shoulders out from under targets already computed.
    girdle = pose_girdle(rig, phase, rest)
    # A frame nobody can check must not reach a coach. `out of reach` passes,
    # because a bone that cannot stretch is anatomy; a MISSING field does not,
    # because it renders the pre-fix figure and would otherwise print PASS.
    refuse_unrenderable_girdle(girdle, f"{phase.get('name', '?')}")

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
        # Per HAND, not per phase. A one handed catch carries a grip for the
        # catching hand only, so a phase can be holding while this hand is
        # free. Reading the phase's grip as "both hands hold it" raised
        # KeyError: 'l' on the two one handed drills the moment the movement
        # lane stopped exporting a grip for a hand that was not gripping.
        holds = bool(grip) and side in grip
        if not holds:
            # Free, whether or not the other hand has the ball. The arm says
            # where this hand goes.
            target = shoulder + Vector(wanted["direction"]) * (
                wanted["reachFraction"] * reach
            )
        else:
            # This hand has it. The ball says where the hand goes.
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
        # The radius closes the knuckles onto the surface, so it is passed
        # ONLY when she is holding the ball. Passing it always sent every
        # finger chasing a ball still in flight metres away: unreachable, so
        # each one flexed to the limit of its joint and stopped there, and the
        # ready phase came out with a hand mangled across her face. Before
        # contact the arm decides where the hand goes, which is the same rule
        # the possession model states for the wrist.
        # What the knuckle flexion actually turned, against what FLEXION_AXIS
        # says it turns. Filled by the solve, which measures the DIFFERENCE
        # from the unflexed pose; reading matrix_basis after the fact would
        # carry the aim and the splay with it and report the wrong quantity.
        axis_report: dict[str, dict] = {}
        pose_articulated_hand(
            rig,
            side=side,
            ball_centre=ball_centre,
            finger_curl_degrees=finger_curl_degrees,
            ball_radius=radius if (grip and side in grip) else None,
            knuckle_limits=knuckle_limits,
            axis_report=axis_report,
        )
        # Millimetres from the ball surface, negative inside it. A fingertip
        # out of the top of the ball is the only symptom a coach sees, so the
        # receipt carries the number that proves it did not happen.
        hands[side]["surfaceClearanceMm"] = finger_surface_clearance(
            rig, side=side, ball_centre=ball_centre, radius=radius
        )
        # Which axis the knuckle actually turned about, against the one the
        # limits assume. The solve raises on an outright flip; this carries the
        # margin so the drift towards one is readable in the receipt first.
        hands[side]["flexionAxis"] = axis_report
    orient_head_to_ball(rig, ball_centre)
    receipt = {
        # Whether she is holding it, so a reader never has to guess why a hand
        # is 1.6 m from the ball. Without this the report called every hand on
        # a non-holding phase "short", which reads as a defect and is not one.
        "holding": bool(grip),
        "stance": stance,
        # Whether this rig actually followed the transmitted girdle, and by how
        # far it missed. A figure whose girdle did not follow is a figure whose
        # ball is in the wrong place, because the ball is placed from the
        # shoulder midpoint.
        "girdle": girdle,
        "arms": arms,
        "hands": hands,
    }
    if body is not None:
        # The second instrument. The per digit table says whether the fingers
        # met the surface; this says whether anything else is inside the ball.
        receipt["bodyClearanceMm"] = body_surface_clearance(
            body, ball_centre=ball_centre, radius=radius
        )
    return ball_centre, receipt


class Studio:
    """The athlete and the room. Built once, then posed for every job."""

    def __init__(self, config):
        self.config = config
        # ONE BUILD PER SESSION. `generated_from` is cached for the life of
        # the process for exactly this reason, so this call fixes the value and
        # every later one returns it. Reading a stamp per receipt would let a
        # commit made DURING a batch split one render across two builds.
        self.build = generated_from()
        self.world_colour = config.presentation.studio.world_color
        (
            self.human,
            self.rig,
            self.assets,
            self.source_assets,
        ) = create_athlete(config.athlete, config.presentation)
        # THE LICENCE IS CHECKED HERE, BEFORE ANY FIGURE IS DRAWN, and not at
        # the receipt. An asset this repository has not licensed must not cost
        # a coach half an hour of rendering before it is refused, and a receipt
        # written for such a run would claim a licence it does not have.
        # `docs/LICENSING.md` requires every newly selected MPFB asset to be
        # reconfirmed before publication; until now nothing enforced it.
        self.source_asset_records = source_asset_records(self.source_assets, sha256)
        self.basis = {
            bone.name: bone.matrix_basis.copy() for bone in self.rig.pose.bones
        }
        self.foot_baseline = {
            f"foot_{side}": self.rig.pose.bones[f"foot_{side}"].matrix.copy()
            for side in ("l", "r")
        }
        self.camera, self.lights = add_camera_and_lights(config.presentation)
        add_floor()
        self.ball = None
        self.ball_seams = []

    def add_ball(self, radius: float) -> None:
        # The reference generator builds the ball a coach recognises: panels,
        # a seam colour and six embossed seam loops. This drew a plain coral
        # sphere of its own. The seams are parented to the ball, so moving the
        # ball still moves the whole thing.
        self.ball, self.ball_seams = create_panelled_netball(
            Vector((0.0, 0.0, 0.0)), radius, self.config.presentation
        )


def render_job(studio: Studio, job: dict, job_path: Path, args,
               output: Path) -> list[dict]:
    # Delete any receipt from an earlier run BEFORE rendering. The solve can
    # raise part way through, and `--output` reuses its directory, so a PASS
    # receipt from a previous run would otherwise sit beside the fresh partial
    # images of a failed one and describe them.
    stale = output / f"{job['movementId']}.render.json"
    if stale.exists():
        stale.unlink()
    config, world_colour = studio.config, studio.world_colour
    rig, human, assets = studio.rig, studio.human, studio.assets
    basis, foot_baseline = studio.basis, studio.foot_baseline
    camera, ball, ball_seams = studio.camera, studio.ball, studio.ball_seams

    wanted = args.phase or [phase["name"] for phase in job["phases"]]
    phases = [phase for phase in job["phases"] if phase["name"] in wanted]
    if not phases:
        raise SystemExit(f"no phase of {job['movementId']} matches {wanted}")

    rendered, failed = [], []
    for phase in phases if not args.no_stills else []:
        # ONE BAD PHASE MUST COST ONE FIGURE AND NOT A LIBRARY. On 2026-09-07
        # `netball_one_hand_high_pass/ready` raised out of the whole run and
        # took eleven good drills with it, twice, at forty minutes a time. The
        # failure is RECORDED rather than swallowed: it goes in the receipt
        # with its reason, the run's word stops being PASS, and the process
        # exits non-zero at the end. A loop that carried on quietly would have
        # traded a loud failure for a silent one.
        try:
            centre, receipt = pose_phase(
                rig, phase, job["anatomyLimitsDegrees"], basis, foot_baseline,
                config.finger_curl_degrees, job.get("knuckleLimitsDegrees"),
                studio.human,
            )
        except Exception as error:
            failed.append({
                "name": phase["name"],
                "frame": phase["frame"],
                "failed": True,
                "error": f"{type(error).__name__}: {error}",
            })
            print(
                f"[movement-render] FAILED {phase['name']} frame "
                f"{phase['frame']}: {type(error).__name__}: {error}"
            )
            continue
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
                world_colour=world_colour,
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
                    world_colour=world_colour,
                )
        receipt["views"] = images
        rendered.append(receipt)
        print(
            f"[movement-render] {phase['name']} frame {phase['frame']} "
            f"-> {len(images)} views",
            flush=True,
        )

    animation = None
    if args.animate:
        frames = job.get("frames") or []
        if not frames:
            raise SystemExit(
                "the job carries no frames. Export it with --every=N."
            )
        # Every job keyframes the same rig, so the previous drill's animation
        # has to go. Clearing it off the OBJECTS is not enough: the action
        # itself survives in bpy.data.actions, and the glTF exporter writes
        # every action it finds there, not only the assigned one. The second
        # drill of a session therefore shipped 1063 curves against the first
        # drill's 533, carrying both movements, and an importer binds the
        # first action it meets. Every later drill played the first one's
        # movement while looking like a correct file.
        for item in (rig, ball):
            item.animation_data_clear()
        for action in list(bpy.data.actions):
            action.use_fake_user = False
            bpy.data.actions.remove(action)

        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = len(frames)
        fps = max(1, round(job["framesPerSecond"] / max(job["frameStep"], 1)))
        # Set this BEFORE the glTF export, not only inside render_movie. glTF
        # stores animation in seconds, so the scene's rate is what turns frames
        # into times. render_movie used to be the only thing that set it, and
        # it runs after the export, so the first drill of a session exported
        # against Blender's default rate and every later drill inherited the
        # previous drill's movie rate. Two drills in one session came back as
        # 49 frames and 40: the same poses, played too fast.
        bpy.context.scene.render.fps = fps
        # Set the frame before posing. Once keys exist, changing the frame
        # evaluates them and would replace whatever was posed first.
        # THE SAME RULE AS THE PHASE LOOP, WITH THE OPPOSITE ANSWER. A still
        # with a hole in it is one missing figure; an ANIMATION with a hole in
        # it is a movement that plays wrongly and says nothing, because the
        # frames either side close over the gap. So a failed frame is recorded
        # and the EXPORT IS REFUSED, while the receipt is still written: the
        # old behaviour raised out of `render_job` and left no receipt at all,
        # with the stale one already unlinked.
        for number, frame in enumerate(frames, start=1):
            scene.frame_set(number)
            try:
                centre, _ = pose_phase(
                    rig, frame, job["anatomyLimitsDegrees"], basis,
                    foot_baseline, config.finger_curl_degrees,
                    job.get("knuckleLimitsDegrees"),
                )
            except Exception as error:
                failed.append({
                    "name": f"frame {number}",
                    "frame": number,
                    "failed": True,
                    "error": f"{type(error).__name__}: {error}",
                })
                print(
                    f"[movement-render] FAILED animation frame {number}: "
                    f"{type(error).__name__}: {error}",
                    flush=True,
                )
                continue
            ball.location = centre
            keyframe(rig, ball, number)
        scene.frame_set(1)

        if failed:
            print(
                f"[movement-render] REFUSING the animation export: "
                f"{len(failed)} frame(s) could not be posed, and an animation "
                f"with a hole in it plays over the gap without saying so. The "
                f"receipt is still written.",
                flush=True,
            )

        if failed:
            animation = None
        else:
            bake_action(rig, 1, len(frames))
            # With the masks applied the skin's texture alpha has nothing left to
            # hide, and all it does is dither: angular patches over the legs, arms
            # and face wherever it is neither one nor zero. Hair, lashes and brows
            # keep theirs, because they are cut-out cards. So do the eyes, whose
            # cornea is transparent over the iris: opaque gives her blank white
            # discs and no pupil.
            solid = [human] + [a for a in assets if "casualsuit" in a.name]
            print(f"[movement-render] alpha: {', '.join(set_alpha(solid, 'OPAQUE'))}")
            glb = output / f"{job['movementId']}.glb"
            baked = bake_shape_keys([human, *assets])
            if baked:
                print(f"[movement-render] baked shape keys: {', '.join(baked)}")
            select_only([rig, human, *assets, ball, *ball_seams])
            bpy.ops.export_scene.gltf(
                filepath=str(glb),
                export_format="GLB",
                use_selection=True,
                export_animations=True,
                export_frame_range=True,
                # MPFB hides the fitting helpers and the body under the clothes
                # with two mask modifiers. The exporter ignores modifiers unless
                # it is asked, so both masks were dropped and the athlete arrived
                # wearing a skirt of helper geometry with her chest through her
                # shirt. This is what applies them. It also disables shape key
                # export, which is why they are baked first.
                export_apply=True,
            )
            movie = output / f"{job['movementId']}.mp4"
            view = job["views"]["quarter"]
            movie = render_movie(
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
    # WHICH BUILD DREW THIS: the session's, fixed when the athlete was built.
    # Never passed in by a caller, because a stamp a caller supplies is a claim
    # about a build rather than a reading of one.
    stamp = studio.build
    receipt = {
        "movementId": job["movementId"],
        "skill": job["skill"],
        # `generatedFrom`, not `build`: one name for one concept, and the name
        # `archive_receipts.py` reads. A render receipt is archivable by the
        # project's own tool because of this line.
        "generatedFrom": stamp,
        "jobSha256": sha256(job_path),
        # Path, sha256 AND licence per asset, the shape the reference generator
        # already writes. A path alone cannot tell two MPFB installations apart,
        # and `docs/ARCHITECTURE.md` rule 7 asks for the hashes. Resolved once
        # when the athlete was built, so this line cannot fail here.
        "sourceAssets": studio.source_asset_records,
        "animation": animation,
        # The phases that DREW, then the phases that could not, each with its
        # reason. A reader counting `phases` alone would see a short list and
        # no cause; a reader seeing only the failures would not know what was
        # produced beside them.
        "phases": rendered,
        "failedPhases": failed,
    }
    # The stamp is the point of the receipt for anyone asking which pictures
    # predate a fix, so it is checked before the file is written rather than
    # discovered missing by whoever reads it months later.
    assert "commit" in receipt["generatedFrom"], "the receipt must name a build"
    assert "treeWasClean" in receipt["generatedFrom"], (
        "the receipt must say whether the tree was clean: a commit named from "
        "a dirty tree names a build that never existed"
    )
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    if receipt["generatedFrom"]["treeWasClean"] is not True:
        print(
            "[movement-render] NOTE: "
            f"tree not verified clean ({receipt['generatedFrom']['commit']}), "
            "so these "
            "pictures cannot be reproduced from that commit alone"
        )
    # Never the bare word PASS. A run that posed no phase measured nothing,
    # and `--no-stills` took exactly that path over eight drills and printed
    # PASS eight times.
    print(
        f"[movement-render] "
        f"{render_outcome(len(rendered), animation, len(failed))} "
        f"receipt={receipt_path}"
    )
    return failed


def main() -> None:
    # BLOCK-BUFFERED UNDER REDIRECTION. Blender's stdout is buffered when it is
    # not a terminal and its stderr is not, so a saved log showed the run's
    # final SystemExit six lines ABOVE the first drill it described. Nothing
    # was wrong and the log read as though the raise came first.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):  # pragma: no cover - older streams
        pass
    args = parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    jobs = [json.loads(path.read_text(encoding="utf-8")) for path in args.job]

    radii = {job["phases"][0]["ball"]["radiusM"] for job in jobs}
    if len(radii) > 1:
        raise SystemExit(f"the jobs disagree about the ball radius: {sorted(radii)}")

    studio = Studio(load_reference_catch_config(args.config))
    studio.add_ball(radii.pop())

    unposable = []
    for number, (job, path) in enumerate(zip(jobs, args.job), start=1):
        print(f"[movement-render] {number}/{len(jobs)} {job['movementId']}")
        for entry in render_job(studio, job, path, args, output):
            unposable.append(f"{job['movementId']}/{entry['name']}")

    # AFTER every drill, never during one. Raising here is what keeps the exit
    # code honest without costing the drills that would have followed.
    if unposable:
        raise SystemExit(
            f"[movement-render] {len(unposable)} phase(s) could not be posed "
            f"and are missing from the library: {', '.join(unposable)}. Every "
            f"other phase was rendered and every receipt was written; each "
            f"failure is in its receipt's `failedPhases` with its reason."
        )


if __name__ == "__main__":
    main()
