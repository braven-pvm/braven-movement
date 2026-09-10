"""Render the athlete wearing a kit that is PAINTED rather than modelled.

Wraps `blender_movement_render.py` and changes nothing in the tree. It lays a
kit texture over the body's own skin, gives that area cloth's surface instead of
skin's, removes the modelled kit, and then runs the ordinary render.

    blender -b --python-exit-code 9 -P kit_paint_render.py -- \
        --kit-layer out/kit/netball_gs.png --remove-modelled-kit \
        --job spikes/poc-output/<id>.job.json --output out/painted --phase land

Every substitution is printed, and the script REFUSES to render when a
substitution finds nothing to change. A painted kit that silently did not apply
renders as the shipped athlete and looks like a result.

Every other argument is passed to `blender_movement_render.py` unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy

REPO = Path(__file__).resolve().parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# The body material and its two nodes, read out of the built athlete by
# `kit_probe.py` rather than assumed. The graph is three links:
#     DiffuseTexture.Color -> Principled BSDF.Base Color
#     AlphaMapTexture.Alpha -> Principled BSDF.Alpha
#     Principled BSDF.BSDF -> Material Output.Surface
BODY_MATERIAL = "BRAVEN_Athlete.body"
DIFFUSE_NODE = "DiffuseTexture"

# The modelled kit, and the modifier it puts on the BODY. MPFB deletes the body
# vertices under a garment. Remove the garment and leave the modifier, and the
# athlete renders with a hole where the kit was, which looks exactly like a
# painted kit that failed.
KIT_OBJECT = "BRAVEN_Athlete.female_casualsuit02"
KIT_MASK_MODIFIER = "Delete.female_casualsuit02"
# Its source file, dropped from the record when the object is removed. A
# receipt that still names it would claim an asset that drew nothing, which is
# the same fault as leaving out an asset that did.
KIT_ASSET_STEM = "female_casualsuit02"

# What the kit's own surface is, against the skin's. Read off the shader at run
# time and printed, never assumed.
KIT_SURFACE = (("Roughness", 0.74), ("Subsurface Weight", 0.0),
               ("Specular IOR Level", 0.22))


def split_argv():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    layer: Path | None = None
    modelled: Path | None = None
    remove_kit = False
    strict = False
    rest: list[str] = []
    index = 0
    while index < len(argv):
        if argv[index] == "--kit-layer":
            layer = Path(argv[index + 1]).resolve()
            index += 2
        elif argv[index] == "--modelled-kit":
            modelled = Path(argv[index + 1]).resolve()
            index += 2
        elif argv[index] == "--remove-modelled-kit":
            remove_kit = True
            index += 1
        elif argv[index] == "--licence-strict":
            strict = True
            index += 1
        else:
            rest.append(argv[index])
            index += 1
    return layer, modelled, remove_kit, strict, rest


KIT_LAYER, MODELLED, REMOVE_KIT, STRICT, PASSTHROUGH = split_argv()

for label, path in (("kit layer", KIT_LAYER), ("modelled kit", MODELLED)):
    if path is not None and not path.is_file():
        raise SystemExit(f"[kit-paint] the {label} is missing: {path}")

import blender_movement_render as mr  # noqa: E402

_build_athlete = mr.create_athlete


def socket(sockets, identifier):
    """One socket by its identifier, because two of them share a name.

    `ShaderNodeMix` carries a Factor, an A and a B for every data type it can
    mix, and they are all called Factor, A and B. Picking by name picks the
    first one, which is the float pair, and wiring a colour into it silently
    averages the colour to grey.
    """
    for item in sockets:
        if item.identifier == identifier:
            return item
    raise SystemExit(
        f"[kit-paint] no socket {identifier!r} on this node. "
        f"Sockets: {[item.identifier for item in sockets]}"
    )


def apply_kit_layer(human) -> None:
    """Lay the kit over the skin, and give it cloth's surface.

    The kit is a separate RGBA image. Its colour goes over the skin's, its alpha
    decides where, and the SAME alpha drives roughness, specular and subsurface.
    The skin texture is not touched, so the receipt's record of that skin stays
    true and one kit layer fits any skin.
    """
    material = human.data.materials.get(BODY_MATERIAL)
    if material is None:
        raise SystemExit(
            f"[kit-paint] the body material {BODY_MATERIAL!r} is not on the "
            f"athlete. Slots: {[m.name for m in human.data.materials if m]}"
        )
    tree = material.node_tree
    diffuse = tree.nodes.get(DIFFUSE_NODE)
    if diffuse is None or diffuse.type != "TEX_IMAGE":
        raise SystemExit(
            f"[kit-paint] {BODY_MATERIAL}/{DIFFUSE_NODE} is not an image node. "
            f"Nodes: {[n.name for n in tree.nodes]}"
        )
    shader = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if shader is None:
        raise SystemExit(
            f"[kit-paint] {BODY_MATERIAL} has no Principled BSDF. "
            f"Nodes: {[(n.name, n.type) for n in tree.nodes]}"
        )

    image = bpy.data.images.load(str(KIT_LAYER), check_existing=False)
    image.colorspace_settings.name = "sRGB"
    if image.channels < 4:
        raise SystemExit(
            f"[kit-paint] {KIT_LAYER.name} has {image.channels} channels. The "
            f"kit layer must carry an alpha: without it the kit covers her "
            f"whole body."
        )
    texture = tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.label = "BRAVEN kit layer"
    texture.location = (shader.location[0] - 900, shader.location[1] - 300)

    colour = tree.nodes.new("ShaderNodeMix")
    colour.data_type = "RGBA"
    colour.label = "BRAVEN kit over skin"
    colour.location = (shader.location[0] - 300, shader.location[1] - 100)
    base = shader.inputs["Base Color"]
    if not base.is_linked:
        raise SystemExit(
            "[kit-paint] Base Color is not linked, so the skin is not a "
            "texture here and the kit has nothing to lie over."
        )
    was = base.links[0].from_node.name
    tree.links.new(texture.outputs["Alpha"], socket(colour.inputs, "Factor_Float"))
    tree.links.new(base.links[0].from_socket, socket(colour.inputs, "A_Color"))
    tree.links.new(texture.outputs["Color"], socket(colour.inputs, "B_Color"))
    tree.links.new(socket(colour.outputs, "Result_Color"), base)
    print(f"[kit-paint] Base Color was {was}, now the kit over {was}", flush=True)

    driven = []
    for name, value in KIT_SURFACE:
        target = shader.inputs.get(name)
        if target is None:
            print(f"[kit-paint] no {name!r} input on this shader", flush=True)
            continue
        mix = tree.nodes.new("ShaderNodeMix")
        mix.data_type = "FLOAT"
        mix.location = (shader.location[0] - 300, shader.location[1] - 500)
        tree.links.new(texture.outputs["Alpha"], socket(mix.inputs, "Factor_Float"))
        if target.is_linked:
            tree.links.new(target.links[0].from_socket, socket(mix.inputs, "A_Float"))
            before = "a link"
        else:
            socket(mix.inputs, "A_Float").default_value = target.default_value
            before = f"{target.default_value:.3f}"
        socket(mix.inputs, "B_Float").default_value = value
        tree.links.new(socket(mix.outputs, "Result_Float"), target)
        driven.append(f"{name} {before} -> {value}")
    if not driven:
        raise SystemExit(
            "[kit-paint] the kit layer drove no surface value. The shader's "
            f"inputs are {[item.name for item in shader.inputs]}"
        )
    print(f"[kit-paint] kit alpha drives: {'; '.join(driven)}", flush=True)


def strip_modelled_kit(human, assets: list) -> list:
    """Delete the modelled kit and the hole it cuts in the body."""
    removed = [m.name for m in human.modifiers if m.name == KIT_MASK_MODIFIER]
    if not removed:
        raise SystemExit(
            f"[kit-paint] no {KIT_MASK_MODIFIER!r} modifier on the body. "
            f"Removing the kit without it would leave the body's own vertices "
            f"deleted. Modifiers: {[(m.name, m.type) for m in human.modifiers]}"
        )
    for name in removed:
        human.modifiers.remove(human.modifiers[name])
    kept = [item for item in assets if item.name != KIT_OBJECT]
    gone = [item for item in assets if item.name == KIT_OBJECT]
    if not gone:
        raise SystemExit(
            f"[kit-paint] no {KIT_OBJECT!r} among the assets: "
            f"{[item.name for item in assets]}"
        )
    for item in gone:
        bpy.data.objects.remove(item, do_unlink=True)
    print(f"[kit-paint] removed body modifier(s): {', '.join(removed)}", flush=True)
    print(f"[kit-paint] removed object(s): {KIT_OBJECT}", flush=True)
    return kept


def add_modelled_kit(human, presentation) -> object:
    """Fit one .mhclo garment and give it the manual's own kit material."""
    from bl_ext.blender_org.mpfb.services.humanservice import HumanService

    from blender_mpfb_reference_catch import make_fabric_material

    garment = HumanService.add_mhclo_asset(
        str(MODELLED),
        human,
        asset_type="Clothes",
        subdiv_levels=1,
        material_type="GAMEENGINE",
    )
    garment.data.materials.clear()
    garment.data.materials.append(make_fabric_material(presentation))
    print(f"[kit-paint] fitted modelled kit {MODELLED} as {garment.name!r}", flush=True)
    return garment


def create_athlete(athlete, presentation):
    human, rig, assets, source_assets = _build_athlete(athlete, presentation)
    if KIT_LAYER is not None:
        apply_kit_layer(human)
    if REMOVE_KIT:
        assets = strip_modelled_kit(human, assets)
        before = len(source_assets)
        source_assets = [
            path for path in source_assets if KIT_ASSET_STEM not in str(path)
        ]
        if len(source_assets) != before - 1:
            raise SystemExit(
                f"[kit-paint] removing the modelled kit dropped "
                f"{before - len(source_assets)} source asset(s) and not one. "
                f"The receipt would name what it did not draw."
            )
        print(
            f"[kit-paint] dropped the removed kit from sourceAssets "
            f"({before} -> {len(source_assets)})",
            flush=True,
        )
    if MODELLED is not None:
        assets = [*assets, add_modelled_kit(human, presentation)]
    # EVERY FILE THAT DREW THE FIGURE GOES IN THE RECORD, INCLUDING OURS.
    #
    # `sourceAssets` carries a LICENCE for every entry, and `docs/LICENSING.md`
    # states no licence for a file this repository generates. Its first bullet
    # says no licence has been chosen for this repository's own source code at
    # all, so a kit layer is undetermined for the same open reason. Under
    # `--licence-strict` the layer goes into `sourceAssets` and the run REFUSES
    # before a figure is drawn, which is the module working as designed.
    #
    # Otherwise the layer is recorded after the render as PROVENANCE and claims
    # nothing: path, bytes, the instrument and its parameters. That is the same
    # treatment `docs/LICENSING.md` already gives the reference photograph,
    # whose "configured hash is provenance evidence, not a redistribution
    # permission".
    if STRICT:
        for path in (KIT_LAYER, MODELLED):
            if path is not None:
                source_assets = [*source_assets, path]
                print(f"[kit-paint] recorded in sourceAssets: {path}", flush=True)
    elif MODELLED is not None:
        source_assets = [*source_assets, MODELLED]
        print(f"[kit-paint] recorded in sourceAssets: {MODELLED}", flush=True)
    return human, rig, assets, source_assets


def record_painted_kit() -> None:
    """Write the kit layer's provenance into the receipt the render just made.

    A post-write, and it is a POC shape rather than the finished one: the field
    belongs in `blender_movement_render.py` beside `sourceAssets`, which is the
    rendering lane's file. It refuses loudly if it cannot find the receipt,
    because a provenance block that silently did not land is worse than none.
    """
    import hashlib
    import json

    jobs = [
        Path(PASSTHROUGH[index + 1])
        for index, item in enumerate(PASSTHROUGH)
        if item == "--job"
    ]
    output = next(
        (Path(PASSTHROUGH[index + 1])
         for index, item in enumerate(PASSTHROUGH) if item == "--output"),
        None,
    )
    if output is None or not jobs:
        raise SystemExit("[kit-paint] cannot find --output or --job to record against")

    sidecar = KIT_LAYER.with_suffix(".json")
    parameters = (
        json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.is_file() else None
    )
    if parameters is None:
        raise SystemExit(
            f"[kit-paint] {sidecar.name} is missing, so the kit layer's "
            f"parameters cannot be recorded and the receipt would name a "
            f"texture nobody can redraw."
        )
    digest = hashlib.sha256(KIT_LAYER.read_bytes()).hexdigest()
    if digest != parameters.get("outputSha256"):
        raise SystemExit(
            f"[kit-paint] {KIT_LAYER.name} has changed since its parameters "
            f"were written: {digest[:16]} against "
            f"{str(parameters.get('outputSha256'))[:16]}. Re-run kit_paint.py."
        )

    written = []
    for job in jobs:
        movement = json.loads(job.read_text(encoding="utf-8"))["movementId"]
        receipt_path = output.resolve() / f"{movement}.render.json"
        if not receipt_path.is_file():
            raise SystemExit(f"[kit-paint] no receipt to record against: {receipt_path}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["paintedKit"] = {
            "layer": str(KIT_LAYER),
            "sha256": digest,
            "instrument": "kit_paint.py",
            "parameters": parameters,
            "recordedAs": (
                "provenance, not a licence. docs/LICENSING.md makes no "
                "determination about a texture this repository generates, and "
                "its first bullet records that no licence has been chosen for "
                "this repository's own source code either. Run with "
                "--licence-strict to put this file through the licence gate "
                "instead, which refuses until a determination exists."
            ),
        }
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        again = json.loads(receipt_path.read_text(encoding="utf-8"))
        if again.get("paintedKit", {}).get("sha256") != digest:
            raise SystemExit(f"[kit-paint] the receipt did not keep the block: {receipt_path}")
        written.append(str(receipt_path))
    print(f"[kit-paint] paintedKit recorded in: {', '.join(written)}", flush=True)


mr.create_athlete = create_athlete
sys.argv = [sys.argv[0], "--", *PASSTHROUGH]
print(f"[kit-paint] kit-layer={KIT_LAYER} modelled-kit={MODELLED} "
      f"remove-modelled-kit={REMOVE_KIT}", flush=True)
print(f"[kit-paint] passing to movement render: {' '.join(PASSTHROUGH)}", flush=True)
mr.main()
if KIT_LAYER is not None and not STRICT:
    record_painted_kit()
print("KIT PAINT RENDER OK", flush=True)
