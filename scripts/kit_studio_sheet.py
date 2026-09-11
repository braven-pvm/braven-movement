"""Ten studio views of a kit, standing and in a drill phase, with a measured
clearance between the skirt and the skin. The iteration instrument for a kit:
one Blender session, EEVEE, about 100 s, then LOOK at every panel.

Under Blender it renders and measures:

    blender -b --python-exit-code 9 -P scripts/kit_studio_sheet.py -- \\
        --config config/netball_kit.v1.json \\
        --job spikes/poc-output/netball_double_foot_landing.job.json \\
        --phase absorb --out out/kit-studio

Under plain Python (the pixi env, which has PIL) it composes the sheet:

    pixi run --frozen python ../scripts/kit_studio_sheet.py --compose ../out/kit-studio

The clearance is the signed distance of every skirt vertex to the skin,
armature only, through a BVH of the skin faces. A negative number is the thigh
pushing through the skirt, which no look at a contact sheet reliably shows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW_NAMES = [
    "stand-front", "stand-side", "stand-back", "stand-top-front", "stand-top-back",
    "stand-hip-low", "phase-front", "phase-side", "phase-back", "phase-hip-side",
]


def compose(folder: Path) -> Path:
    from PIL import Image, ImageDraw

    folder = folder.resolve()
    tiles = [(name, folder / f"{name}.png") for name in VIEW_NAMES if (folder / f"{name}.png").exists()]
    if not tiles:
        raise SystemExit(f"no rendered views named {VIEW_NAMES[0]}.png ... in {folder}")
    columns, width, height = 5, 720, 960
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (width + 8), rows * (height + 34)), (40, 40, 40))
    canvas = ImageDraw.Draw(sheet)
    for index, (name, path) in enumerate(tiles):
        image = Image.open(path).convert("RGB")
        image.thumbnail((width, height))
        x, y = (index % columns) * (width + 8), (index // columns) * (height + 34)
        sheet.paste(image, (x, y + 30))
        canvas.text((x + 6, y + 8), name, fill=(255, 255, 255))
    target = folder / "sheet.png"
    sheet.save(target)
    print(f"[kit-studio] sheet {target} {sheet.size} from {len(tiles)} views")
    return target


def render(args) -> int:
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import blender_movement_render as movement  # noqa: E402
    from reference_pose_config import load_reference_catch_config  # noqa: E402

    config = load_reference_catch_config(args.config)
    studio = movement.Studio(config)
    human, rig, assets = studio.human, studio.rig, studio.assets
    garment = assets[0]
    # ABSOLUTE, because Blender resolves a relative render path against its
    # own notion of the current directory and writes the stills somewhere else
    # without a word; the JSON beside them came from Python and landed here.
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    camera = studio.camera

    # The garment's build sidecar says where its skirt starts in vertex order.
    # WHICH VERTICES ARE MEASURED. A dress is a bodysuit then a skirt, and the
    # skirt is the part that can pass through a thigh, so only the skirt is
    # measured. A SHORTS-ONLY kit has no skirt, and then the whole garment is
    # the part that stands off the body, so all of it is measured. Measuring
    # "the vertices after the bodysuit" on a shorts kit would measure none.
    n_body = None
    measured = "skirt"
    shorts = None
    if config.presentation.kit.garment:
        sidecar = ROOT / Path(config.presentation.kit.garment).with_suffix(".build.json")
        if sidecar.is_file():
            counts = json.loads(sidecar.read_text(encoding="utf-8"))
            for part in counts.get("parts", []):
                if part.get("shorts"):
                    shorts = part["shorts"]
            if counts.get("nSkirtVertices", 0) > 0:
                n_body = counts["nBodysuitVertices"]
            else:
                n_body = 0
                measured = "the whole garment"

    def clearance(label: str) -> dict | None:
        if n_body is None:
            return None
        # THE SKIN, NOT THE SKIN MINUS WHAT THE CLOTHES HIDE. MPFB gives every
        # fitted garment a `Delete.<asset>` mask that removes the body under
        # it, so the first version of this instrument measured the distance to
        # the nearest SURVIVING skin and overstated the clearance exactly where
        # a garment sits. The helper mask stays on: the helpers stand outside
        # the skin, so keeping them would be the opposite error. The vertex
        # group filter is gone with it, because every face of this mesh is
        # skin, and filtering EVALUATED polygons by BASE-mesh indices was only
        # ever correct by accident.
        off = []
        for item in (human, garment):
            for modifier in item.modifiers:
                if (modifier.type == "SUBSURF" or modifier.name.startswith("Delete.")) \
                        and modifier.show_viewport:
                    modifier.show_viewport = False
                    off.append((item, modifier.name))
        graph = bpy.context.evaluated_depsgraph_get()
        human_eval, garment_eval = human.evaluated_get(graph), garment.evaluated_get(graph)
        points = [human_eval.matrix_world @ v.co for v in human_eval.data.vertices]
        faces = [list(p.vertices) for p in human_eval.data.polygons]
        tree = BVHTree.FromPolygons(points, faces)
        # THE REGIONS ARE REPORTED SEPARATELY. A waistband is meant to hug and
        # a front panel is meant to stand off, so one minimum over the whole
        # garment cannot say whether the panel worked. The panel is the region
        # the authoring script shaped, read from that script's own sidecar, so
        # the two cannot disagree about where it is.
        signed = []
        panel = []
        for vertex in garment.data.vertices:
            if vertex.index < n_body:
                continue
            point = garment_eval.matrix_world @ garment_eval.data.vertices[vertex.index].co
            location, normal, _, distance = tree.find_nearest(point)
            value = distance if (point - location).dot(normal) >= 0 else -distance
            signed.append(value)
            rest = garment.data.vertices[vertex.index].co
            if (shorts and rest.y < 0.0 and abs(rest.x) <= shorts["frontSpanM"]
                    and rest.z <= shorts["crotchTopZ"]):
                panel.append(value)
        for item, name in off:
            for modifier in item.modifiers:
                if modifier.name == name:
                    modifier.show_viewport = True
        report = {
            "state": label,
            "measured": measured,
            "skinFaces": len(faces),
            "modifiersOff": [name for _, name in off],
            "skirtVertices": len(signed),
            "insideSkin": sum(1 for value in signed if value < 0),
            "within4mm": sum(1 for value in signed if 0 <= value < 0.004),
            "minimumMm": round(min(signed) * 1000, 1),
            "frontPanelVertices": len(panel),
            "frontPanelMinimumMm": round(min(panel) * 1000, 1) if panel else None,
            "frontPanelInsideSkin": sum(1 for value in panel if value < 0),
        }
        print(f"[kit-studio] clearance {report}")
        return report

    def shoot(name, location, target, lens, size):
        camera.location = Vector(location)
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = lens
        scene.render.resolution_x, scene.render.resolution_y = size
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[kit-studio] {name}")

    full = (720, 960)
    reports = [clearance("rest")]
    shoot("stand-front", (0.0, -4.4, 1.0), (0.0, 0.0, 0.9), 50, full)
    shoot("stand-side", (4.4, 0.0, 1.0), (0.0, 0.0, 0.9), 50, full)
    shoot("stand-back", (0.0, 4.4, 1.0), (0.0, 0.0, 0.9), 50, full)
    shoot("stand-top-front", (0.0, -1.7, 1.3), (0.0, 0.0, 1.28), 85, (800, 800))
    shoot("stand-top-back", (0.0, 1.7, 1.3), (0.0, 0.0, 1.28), 85, (800, 800))
    shoot("stand-hip-low", (0.0, -2.6, 0.55), (0.0, 0.0, 0.85), 70, (800, 800))

    if args.job is not None:
        job = json.loads(args.job.read_text(encoding="utf-8"))
        phase = next(item for item in job["phases"] if item["name"] == args.phase)
        movement.pose_phase(
            rig, phase, job["anatomyLimitsDegrees"], studio.basis, studio.foot_baseline,
            config.finger_curl_degrees, job.get("knuckleLimitsDegrees"),
        )
        reports.append(clearance(args.phase))
        shoot("phase-front", (0.0, -4.4, 1.0), (0.0, -0.1, 0.8), 50, full)
        shoot("phase-side", (4.4, -0.3, 1.0), (0.0, -0.1, 0.8), 50, full)
        shoot("phase-back", (0.0, 4.4, 1.0), (0.0, -0.1, 0.8), 50, full)
        shoot("phase-hip-side", (1.15, -0.30, 0.72), (0.0, -0.10, 0.66), 85, (800, 800))

    (out / "clearance.json").write_text(
        json.dumps({"config": str(args.config), "job": str(args.job), "phase": args.phase,
                    "clearance": [r for r in reports if r]}, indent=2),
        encoding="utf-8",
    )
    return 0


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description="ten studio views of a kit")
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "netball_kit.v1.json")
    parser.add_argument("--job", type=Path, default=None)
    parser.add_argument("--phase", default="absorb")
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "kit-studio")
    parser.add_argument("--compose", type=Path, default=None, help="compose sheet.png from a rendered folder")
    args = parser.parse_args(argv)
    if args.compose is not None:
        compose(args.compose)
        return 0
    return render(args)


if __name__ == "__main__":
    raise SystemExit(main())
