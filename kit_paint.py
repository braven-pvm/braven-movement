"""Draw a sports kit as its own texture layer, in the body's UV space.

Reads the body dump written by `kit_dump_uv.py`, rasterises the rest-pose
position of every body pixel into UV space, then cuts the garment out of that
position map with measured thresholds. No mesh, no vertex binding, no fitting.

The output is an RGBA layer that holds the kit and NOTHING ELSE. It reads no
skin texture, so it is not derived from one: the skin stays untouched under it
and keeps its own licence and its own record. The layer is cut from the
BASEMESH's UV space, not from a skin, so which skin lies under it is not a
property of the layer. Rendering with a different skin is a separate question,
because this repository has licensed exactly one.

    python -B kit_paint.py --body out/kit/body.npz --output out/kit/netball.png

Every parameter it used is written beside the layer as JSON, because a figure
that cannot be re-measured is not a measurement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kit_font import resolve as resolve_font


def linear_to_srgb(value: float) -> float:
    if value <= 0.0031308:
        return value * 12.92
    return 1.055 * value ** (1 / 2.4) - 0.055


def as_bytes(linear: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(int(round(255 * linear_to_srgb(c))) for c in linear)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def triangles(loop_start, loop_total):
    out = []
    for start, total in zip(loop_start.tolist(), loop_total.tolist()):
        for step in range(1, total - 1):
            out.append((start, start + step, start + step + 1))
    return np.asarray(out, dtype=np.int64)


def rasterise(uv, value, size):
    """Interpolate a per-vertex value into every pixel of the UV map."""
    height = width = size
    channels = value.shape[2]
    out = np.zeros((height, width, channels), dtype=np.float32)
    covered = np.zeros((height, width), dtype=bool)
    px = uv[:, :, 0] * (width - 1)
    py = (1.0 - uv[:, :, 1]) * (height - 1)
    for index in range(uv.shape[0]):
        left = int(np.floor(px[index].min()))
        right = int(np.ceil(px[index].max()))
        top = int(np.floor(py[index].min()))
        bottom = int(np.ceil(py[index].max()))
        if right < 0 or bottom < 0 or left >= width or top >= height:
            continue
        left, top = max(left, 0), max(top, 0)
        right, bottom = min(right, width - 1), min(bottom, height - 1)
        ax, ay = px[index, 0], py[index, 0]
        bx, by = px[index, 1], py[index, 1]
        cx, cy = px[index, 2], py[index, 2]
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(denominator) < 1e-12:
            continue
        ys, xs = np.mgrid[top : bottom + 1, left : right + 1]
        fx = xs + 0.5
        fy = ys + 0.5
        w0 = ((by - cy) * (fx - cx) + (cx - bx) * (fy - cy)) / denominator
        w1 = ((cy - ay) * (fx - cx) + (ax - cx) * (fy - cy)) / denominator
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -0.002) & (w1 >= -0.002) & (w2 >= -0.002)
        if not inside.any():
            continue
        rows = ys[inside]
        cols = xs[inside]
        blend = (
            w0[inside][:, None] * value[index, 0]
            + w1[inside][:, None] * value[index, 1]
            + w2[inside][:, None] * value[index, 2]
        )
        out[rows, cols] = blend
        covered[rows, cols] = True
    return out, covered


def smooth(mask, radius):
    """A soft edge on a boolean mask, in pixels."""
    image = Image.fromarray((mask * 255).astype(np.uint8))
    image = image.filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(image, dtype=np.float32) / 255.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=2048)
    parser.add_argument("--neck-fraction", type=float, default=0.828)
    parser.add_argument("--hem-fraction", type=float, default=0.430)
    parser.add_argument("--sleeve-fraction", type=float, default=0.760)
    parser.add_argument("--sleeve-radius", type=float, default=None,
                        help="metres from the measured shoulder joint; "
                             "replaces the weight-and-height sleeve cut")
    parser.add_argument("--bib-top-fraction", type=float, default=0.790)
    parser.add_argument("--bib-bottom-fraction", type=float, default=0.640)
    parser.add_argument("--bib-half-width", type=float, default=0.125)
    # 0.15 CAME FROM A SWEEP, not from taste. At 0.35 the facing test eats the
    # panel's top corners where the chest turns upward, and at 0.55 it carves
    # the whole top edge around the bust. 0.15 removes the side of the ribcage
    # and nothing else, which is all this test is for.
    parser.add_argument("--bib-facing", type=float, default=0.15,
                        help="how squarely the surface must face front or back "
                             "for the bib to reach it, 0 to 1")
    parser.add_argument("--bib-corner", type=float, default=4.0,
                        help="superellipse power: 2 is an ellipse, 8 is a "
                             "rectangle, 4 rounds the corners")
    parser.add_argument("--bib-border", type=float, default=0.10,
                        help="border width, as a fraction of the panel's half "
                             "size; 0 removes the border")
    # NOT THE KIT COLOUR. A trim drawn in the colour of the kit around it is
    # invisible, and the first bib with a border looked exactly like the bib
    # without one.
    parser.add_argument("--border-colour", default=None,
                        help="linear RGB; the letter colour when not given")
    parser.add_argument("--position", default="GS")
    # LINEAR RGB, the same numbers as config/reference_catch.v1.json, because a
    # kit authored against the manual's own colours must not be retyped in
    # another space. `linear_to_srgb` converts them for the texture.
    parser.add_argument("--kit-colour", default="0.018,0.024,0.036")
    parser.add_argument("--bib-colour", default="0.94,0.92,0.82")
    parser.add_argument("--letter-colour", default="0.015,0.36,0.42")
    parser.add_argument("--font", default=None,
                        help="path to a .ttf or .otf, or 'pillow' for the "
                             "face Pillow carries; the default is Pillow's")
    parser.add_argument("--edge-pixels", type=float, default=1.6)
    parser.add_argument("--no-bib", action="store_true")
    arguments = parser.parse_args()

    started = time.time()
    data = np.load(arguments.body)
    co = data["co"]
    uv = data["uv"]
    loop_vert = data["loop_vert"]
    body = data["w_body"] > 0.0

    faces = triangles(data["loop_start"], data["loop_total"])
    vertex = loop_vert[faces]
    keep = body[vertex].all(axis=1)
    faces, vertex = faces[keep], vertex[keep]
    print(f"[kit-paint] body triangles {faces.shape[0]} of {keep.shape[0]}")

    # THE KIT IS ITS OWN LAYER AND IT READS NO SKIN. An earlier version painted
    # into a copy of the MPFB skin texture, which made the output a DERIVATIVE
    # of that asset: two thirds of its pixels were MakeHuman's, and the render
    # receipt then named a skin whose pixels had been overwritten. This layer
    # holds the kit's colours and nothing else, so the skin stays untouched and
    # separately recorded, and one kit fits any of the twenty-three skins.
    size = arguments.size
    uv_faces = uv[faces]

    # THE MAPS BELONG TO THE BODY, NOT TO THE GARMENT. Rasterising the position
    # and the twenty-one bone weights is most of the cost of the first kit, and
    # none of it changes when the next kit is cut differently. The cache is
    # keyed by the dump's own hash, so a new body cannot read the old body's
    # maps.
    body_hash = sha256(arguments.body)
    cache_path = arguments.body.with_name(arguments.body.stem + f".maps{size}.npz")
    cache = None
    if cache_path.is_file():
        candidate = np.load(cache_path)
        if str(candidate["bodySha256"]) != body_hash:
            print(f"[kit-paint] {cache_path.name} is for another body; rebuilding")
        elif "normal" not in candidate.files:
            print(f"[kit-paint] {cache_path.name} predates the normal map; rebuilding")
        else:
            cache = candidate
            print(f"[kit-paint] body maps read from {cache_path.name}")

    if cache is not None:
        position = cache["position"]
        covered = cache["covered"]
    else:
        position, covered = rasterise(uv_faces, co[vertex], size)
    if not covered.any():
        raise SystemExit("[kit-paint] the rasteriser covered no pixel at all")
    print(
        f"[kit-paint] covered {covered.sum()} of {size * size} pixels "
        f"({100 * covered.mean():.1f} %) in {time.time() - started:.1f} s"
    )

    # THE AXES ARE MEASURED, NOT ASSUMED. Up is the axis the body is longest
    # in. Front is the direction the TOES point: a foot reaches much further
    # from the ankle towards the toe than towards the heel, so the side of the
    # foot group's median that its extreme lies on is the front.
    span = co[body].max(axis=0) - co[body].min(axis=0)
    up = int(np.argmax(span))
    low = float(co[body][:, up].min())
    high = float(co[body][:, up].max())
    others = [axis for axis in (0, 1, 2) if axis != up]
    depth = others[int(np.argmin([span[axis] for axis in others]))]
    across_axis = [axis for axis in others if axis != depth][0]
    feet = (data["w_foot_l"] > 0.5) | (data["w_foot_r"] > 0.5)
    toes = co[feet][:, depth]
    middle = float(np.median(toes))
    forward = -1.0 if (middle - toes.min()) > (toes.max() - middle) else 1.0
    print(
        f"[kit-paint] up axis {up} height {high - low:.3f} m; depth axis {depth}; "
        f"front is {'negative' if forward < 0 else 'positive'} "
        f"(foot median {middle:.3f}, range {toes.min():.3f}..{toes.max():.3f})"
    )

    def level(fraction: float) -> float:
        return low + fraction * (high - low)

    tall = position[:, :, up]
    deep = position[:, :, depth]
    across = position[:, :, across_axis]

    def weight(name: str) -> np.ndarray:
        """A vertex-group weight, rasterised the way the position was."""
        values = data[f"w_{name}"][vertex][:, :, None].astype(np.float32)
        painted, _ = rasterise(uv_faces, np.repeat(values, 3, axis=2), size)
        return painted[:, :, 0]

    # THE FINGERS ARE THEIR OWN BONES, and the first painted kit put the dress
    # colour on every finger because `hand_l` does not contain them.
    arm_groups = ["upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r",
                  "hand_l", "hand_r"]
    arm_groups += [
        f"{name}_{number:02d}_{side}"
        for name in ("index", "middle", "pinky", "ring", "thumb")
        for number in (1, 2, 3)
        for side in ("l", "r")
    ]
    missing = [name for name in arm_groups if f"w_{name}" not in data]
    if missing:
        raise SystemExit(
            f"[kit-paint] the body dump has no weights for {missing}. Re-run "
            f"kit_dump_uv.py: without them the garment lands on her fingers."
        )
    if cache is not None:
        limb, upper, skull = cache["limb"], cache["upper"], cache["skull"]
        normal = cache["normal"]
    else:
        limb = np.zeros((size, size), dtype=np.float32)
        for name in arm_groups:
            limb = np.maximum(limb, weight(name))
        upper = np.maximum(weight("upperarm_l"), weight("upperarm_r"))
        skull = np.maximum(weight("head"), weight("neck_01"))

        # WHICH WAY THE SURFACE FACES. A bib is a flat panel on the front and
        # the back, and a rule written in position alone wraps it round the
        # ribs. The face normals are area weighted and accumulated to the
        # vertices.
        #
        # THEIR SIGN IS NOT DETERMINED HERE, AND THAT IS DELIBERATE. A face
        # normal follows the mesh's winding, so an imported body decides it.
        # The only rule that reads this map takes the ABSOLUTE value, because a
        # bib is the same panel front and back, so the winding cannot change
        # the kit. A ONE-SIDED rule would need the sign, and the way to measure
        # it is the agreement between the normal and the direction from the
        # body's own centre. An earlier revision measured it and then took the
        # absolute value anyway, which is a measurement nothing reads.
        corner = co[vertex]
        face_normal = np.cross(
            corner[:, 1] - corner[:, 0], corner[:, 2] - corner[:, 0]
        )
        vertex_normal = np.zeros_like(co)
        for column in range(3):
            np.add.at(vertex_normal, vertex[:, column], face_normal)
        length = np.linalg.norm(vertex_normal, axis=1, keepdims=True)
        vertex_normal = vertex_normal / np.maximum(length, 1e-12)
        normal, _ = rasterise(uv_faces, vertex_normal[vertex], size)
        np.savez_compressed(
            cache_path,
            bodySha256=body_hash,
            position=position,
            covered=covered,
            limb=limb,
            upper=upper,
            skull=skull,
            normal=normal,
        )
        print(
            f"[kit-paint] body maps written to {cache_path.name} in "
            f"{time.time() - started:.1f} s; the next kit on this body skips it"
        )

    neck = level(arguments.neck_fraction)
    hem = level(arguments.hem_fraction)
    sleeve = level(arguments.sleeve_fraction)

    torso = covered & (tall < neck) & (tall > hem) & (limb < 0.30) & (skull < 0.10)
    if arguments.sleeve_radius is None:
        # A WEIGHT ISOLINE IS NOT A HEM. The sleeve's visible edge is where the
        # upper-arm weight crosses a threshold, and a skinning weight wanders
        # around the deltoid. It renders as a ragged edge on the shoulder.
        cap = covered & (upper >= 0.30) & (tall > sleeve) & (skull < 0.10)
        cut = f"weight >= 0.30 and above {sleeve:.3f} m"
    else:
        # A SPHERE ROUND THE MEASURED SHOULDER. The joint is the centroid of the
        # vertices whose upper-arm weight is the half isoline, which is where
        # the bone's influence changes hands. The sleeve edge is then a circle
        # on the arm and it carries no weight isoline at all.
        joints = []
        for side in ("l", "r"):
            arm = data[f"w_upperarm_{side}"]
            ring = body & (arm > 0.45) & (arm < 0.55)
            if int(ring.sum()) < 10:
                raise SystemExit(
                    f"[kit-paint] only {int(ring.sum())} vertices on the "
                    f"upperarm_{side} half isoline, so the shoulder cannot be "
                    f"placed from it."
                )
            joints.append(co[ring].mean(axis=0))
            print(
                f"[kit-paint] shoulder {side} at "
                f"{np.round(joints[-1], 4).tolist()} from {int(ring.sum())} "
                f"vertices"
            )
        reach = np.minimum(
            np.linalg.norm(position - joints[0], axis=2),
            np.linalg.norm(position - joints[1], axis=2),
        )
        cap = (
            covered
            & (reach < arguments.sleeve_radius)
            & (upper >= 0.05)
            & (skull < 0.10)
        )
        cut = f"within {arguments.sleeve_radius:.3f} m of the shoulder"
    garment = torso | cap
    edge = garment & ~(
        np.roll(garment, 1, 0) & np.roll(garment, -1, 0)
        & np.roll(garment, 1, 1) & np.roll(garment, -1, 1)
    )
    ragged = float(edge.sum()) / float(np.sqrt(max(garment.sum(), 1)))
    print(
        f"[kit-paint] garment covers {garment.sum()} pixels; sleeve cut by "
        f"{cut}; boundary {int(edge.sum())} pixels, "
        f"boundary / sqrt(area) = {ragged:.2f}"
    )
    # A FRACTION OF THE BODY, NOT A PIXEL COUNT. The texture size is a
    # parameter, so an absolute threshold means a different garment at every
    # size: 1000 pixels passed a sleeve-only kit at 2048 and refused the same
    # kit at 128.
    if garment.sum() < 0.002 * covered.sum():
        raise SystemExit(
            f"[kit-paint] the garment mask is empty: {int(garment.sum())} "
            f"pixels of {int(covered.sum())} covered. Check the thresholds."
        )

    def colour_of(text: str, name: str) -> np.ndarray:
        parts = [float(part) for part in text.split(",")]
        if len(parts) != 3:
            raise SystemExit(f"[kit-paint] --{name} needs three numbers: {text!r}")
        return np.asarray(as_bytes(tuple(parts)), dtype=np.float32)

    kit = colour_of(arguments.kit_colour, "kit-colour")
    bib_colour = colour_of(arguments.bib_colour, "bib-colour")
    letter_colour = colour_of(arguments.letter_colour, "letter-colour")
    print(
        f"[kit-paint] colours sRGB: kit {kit.astype(int).tolist()} "
        f"bib {bib_colour.astype(int).tolist()} "
        f"letters {letter_colour.astype(int).tolist()}"
    )

    alpha = smooth(garment, arguments.edge_pixels)[:, :, None]
    painted = np.tile(kit[None, None, :], (size, size, 1)).astype(np.float32)

    # NO BIB MEANS NO LETTERS MEANS NO FONT, and the sidecar says so
    # rather than naming a font that drew nothing.
    bib_used = None
    font_used = None
    if not arguments.no_bib:
        top = level(arguments.bib_top_fraction)
        bottom = level(arguments.bib_bottom_fraction)
        half = arguments.bib_half_width
        middle = 0.5 * (top + bottom)
        reach = 0.5 * (top - bottom)

        # A BIB IS A FLAT PANEL, NOT A BAND ROUND THE RIBS. A rule written in
        # position alone wraps the panel round her sides, and the letters on it
        # stretch along the way. The surface normal is what says where the body
        # stops facing the camera, so the panel stops there too.
        facing = np.abs(
            normal[:, :, depth]
            / np.maximum(np.linalg.norm(normal, axis=2), 1e-9)
        )

        # A SUPERELLIPSE, NOT A BOX. A rectangle in body coordinates gives the
        # straight horizontal cut across her waist that a bib does not have.
        # The power decides how square the corners are.
        shape = (
            np.abs(across / half) ** arguments.bib_corner
            + np.abs((tall - middle) / reach) ** arguments.bib_corner
        )
        reachable = garment & (limb < 0.30) & (facing > arguments.bib_facing)
        panel = reachable & (shape < 1.0)
        inset = max(0.0, 1.0 - arguments.bib_border) ** arguments.bib_corner
        inner = reachable & (shape < inset)
        border = panel & ~inner
        if panel.sum() < 0.001 * covered.sum():
            raise SystemExit(
                f"[kit-paint] the bib panel is empty: {int(panel.sum())} "
                f"pixels of {int(covered.sum())} covered. Check the thresholds."
            )
        # A border under a hundredth of its panel is a line nobody sees.
        if arguments.bib_border > 0 and border.sum() < 0.01 * panel.sum():
            raise SystemExit(
                f"[kit-paint] the border is {int(border.sum())} pixels wide, "
                f"which is nothing. Raise --bib-border or lower --bib-corner."
            )
        border_colour = (
            letter_colour if arguments.border_colour is None
            else colour_of(arguments.border_colour, "border-colour")
        )
        bib_alpha = smooth(panel, arguments.edge_pixels)[:, :, None]
        painted = painted * (1 - bib_alpha) + border_colour[None, None, :] * bib_alpha
        inner_alpha = smooth(inner, arguments.edge_pixels)[:, :, None]
        painted = painted * (1 - inner_alpha) + bib_colour[None, None, :] * inner_alpha
        print(
            f"[kit-paint] bib panel {int(panel.sum())} pixels, of which "
            f"{int(border.sum())} are border; facing above "
            f"{arguments.bib_facing}, corner power {arguments.bib_corner}"
        )

        glyph = 512
        card = Image.new("L", (glyph, glyph), 0)
        draw = ImageDraw.Draw(card)
        font, font_used = resolve_font(arguments.font, int(glyph * 0.62))
        box = draw.textbbox((0, 0), arguments.position, font=font)
        draw.text(
            ((glyph - (box[2] - box[0])) / 2 - box[0],
             (glyph - (box[3] - box[1])) / 2 - box[1]),
            arguments.position,
            fill=255,
            font=font,
        )
        card = np.asarray(card, dtype=np.float32) / 255.0

        # A bib carries the same letters front and back, and the back's letters
        # are mirrored in the body's own coordinates. Splitting the panel at the
        # median of its depth is what keeps both readable.
        front = (deep * forward) < np.median(deep[panel] * forward)
        keep_in = max(1e-6, 1.0 - arguments.bib_border)
        columns = (across / (half * keep_in) + 1.0) / 2.0
        columns = np.where(front, columns, 1.0 - columns)
        rows = ((middle + reach * keep_in) - tall) / (2.0 * reach * keep_in)
        xs = np.clip((columns * (glyph - 1)).astype(int), 0, glyph - 1)
        ys = np.clip((rows * (glyph - 1)).astype(int), 0, glyph - 1)
        letters = np.where(inner, card[ys, xs], 0.0)[:, :, None]
        painted = painted * (1 - letters) + letter_colour[None, None, :] * letters
        bib_used = int(panel.sum())

    # RGBA. The alpha is the garment, and it does two jobs: it decides where the
    # kit covers the skin, and it drives the kit's roughness and specular. One
    # file, so a render cannot pick up the colour of one kit and the surface of
    # another.
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    layer = np.concatenate(
        [painted.clip(0, 255), (alpha * 255).clip(0, 255)], axis=2
    ).astype(np.uint8)
    Image.fromarray(layer, mode="RGBA").save(arguments.output)

    # THE PALETTE IS THE PROOF THAT NOTHING WAS COPIED. Every opaque pixel of
    # this layer came from one of the three declared colours or a blend of them,
    # so a small palette is what an independently drawn texture looks like. A
    # layer built from somebody else's photograph would have thousands.
    opaque = layer[:, :, 3] > 250
    palette = np.unique(layer[:, :, :3][opaque].reshape(-1, 3), axis=0)
    print(
        f"[kit-paint] {int(opaque.sum())} opaque pixels carry "
        f"{palette.shape[0]} distinct colours"
    )
    elapsed = time.time() - started

    receipt = {
        "instrument": "kit_paint.py",
        "body": str(arguments.body),
        "bodySha256": sha256(arguments.body),
        "readsNoSkin": True,
        "textureSize": size,
        "distinctOpaqueColours": int(palette.shape[0]),
        "output": str(arguments.output),
        "outputSha256": sha256(arguments.output),
        "font": font_used,
        "upAxis": up,
        "depthAxis": depth,
        "acrossAxis": across_axis,
        "frontSign": forward,
        "heightM": high - low,
        "levelsM": {"neck": neck, "hem": hem, "sleeve": sleeve},
        "sleeveRadiusM": arguments.sleeve_radius,
        "boundaryPixels": int(edge.sum()),
        "boundaryOverRootArea": ragged,
        "fractions": {
            "neck": arguments.neck_fraction,
            "hem": arguments.hem_fraction,
            "sleeve": arguments.sleeve_fraction,
            "bibTop": arguments.bib_top_fraction,
            "bibBottom": arguments.bib_bottom_fraction,
        },
        "bibHalfWidthM": arguments.bib_half_width,
        "bibFacing": arguments.bib_facing,
        "bibCornerPower": arguments.bib_corner,
        "bibBorderFraction": arguments.bib_border,
        "coloursLinear": {
            "kit": arguments.kit_colour,
            "bib": arguments.bib_colour,
            "letters": arguments.letter_colour,
        },
        "position": arguments.position,
        "edgePixels": arguments.edge_pixels,
        "garmentPixels": int(garment.sum()),
        "bibPixels": bib_used,
        "coveredPixels": int(covered.sum()),
        "secondsToPaint": elapsed,
    }
    arguments.output.with_suffix(".json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )
    print(f"[kit-paint] wrote {arguments.output} in {elapsed:.1f} s")
    print("KIT PAINT OK", flush=True)


if __name__ == "__main__":
    main()
