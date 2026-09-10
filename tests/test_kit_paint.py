"""What a painted kit may claim about the body it was cut from.

A sports kit can be a TEXTURE instead of a mesh. `kit_paint.py` cuts the
garment out of a map of the body's own rest-pose position, so there is no
geometry to intersect the body and no fitting step at all. These tests hold the
five claims that make it a mechanism rather than one picture.

- The layer READS NO SKIN. If it did, it would be a derivative of the skin it
  was drawn over, and the render receipt would name an asset whose pixels had
  been replaced.
- A garment boundary is a LEVEL ON THE BODY. A hem at 0.43 of her height is
  painted at 0.43 of her height and nowhere else.
- THE WINDING CANNOT CHANGE THE KIT. A face normal follows the mesh's winding,
  which an imported body decides and this repository does not. The bib is the
  same panel front and back, so the rule that reads the normals takes their
  absolute value, and a body wound inside out must paint the same kit.
- An EMPTY MASK IS REFUSED. A kit that painted nothing would render as the
  shipped athlete and look like a result.
- The per-body maps are CACHED BY THE BODY'S OWN HASH, so one body cannot be
  painted with another body's maps.

The body here is synthetic: an elliptical tube with a foot patch, small enough
to paint in a second. It is not the athlete, and it is not meant to be. It is a
body whose every level is known in advance, which is what lets a test say where
the hem should be.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

PAINTER = MODULE_DIR / "kit_paint.py"

HEIGHT = 1.600
RADIUS_ACROSS = 0.180
RADIUS_DEEP = 0.120
SEGMENTS = 24
RINGS = 32
SIZE = 128

# Every group `kit_paint.py` reads. A body dump that lacks one of them must
# fail loudly rather than paint a kit with an arm mask full of zeros.
ARM_GROUPS = ["upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r",
              "hand_l", "hand_r"] + [
    f"{name}_{number:02d}_{side}"
    for name in ("index", "middle", "pinky", "ring", "thumb")
    for number in (1, 2, 3)
    for side in ("l", "r")
]
OTHER_GROUPS = ["body", "head", "neck_01", "foot_l", "foot_r"]


def build_body(path: Path, *, inside_out: bool = False) -> None:
    """An elliptical tube with a foot patch, written as a body dump.

    Deeper than it is wide would make the across axis and the depth axis swap,
    so the ellipse is wider than it is deep exactly as a torso is. The foot
    patch reaches further FORWARD than backward, which is what the painter
    reads the front direction from.
    """
    positions = []
    uvs = []
    for ring in range(RINGS + 1):
        height = HEIGHT * ring / RINGS
        for segment in range(SEGMENTS + 1):
            angle = 2.0 * math.pi * segment / SEGMENTS
            positions.append((
                RADIUS_ACROSS * math.sin(angle),
                RADIUS_DEEP * math.cos(angle),
                height,
            ))
            uvs.append((segment / SEGMENTS, ring / RINGS))
    across_count = SEGMENTS + 1

    def index(ring: int, segment: int) -> int:
        return ring * across_count + segment

    quads = []
    for ring in range(RINGS):
        for segment in range(SEGMENTS):
            corners = [
                index(ring, segment),
                index(ring, segment + 1),
                index(ring + 1, segment + 1),
                index(ring + 1, segment),
            ]
            quads.append(corners[::-1] if inside_out else corners)

    # The foot patch: a flat square at the bottom, reaching to +0.10 in the
    # depth axis and only -0.02 the other way, so the toes are unambiguous.
    foot_start = len(positions)
    foot_grid = []
    for row in range(3):
        for column in range(3):
            positions.append((
                -0.05 + 0.05 * column,
                -0.02 + 0.06 * row,
                0.005,
            ))
            uvs.append((0.02 + 0.01 * column, 0.02 + 0.01 * row))
    for row in range(2):
        for column in range(2):
            base = foot_start + row * 3 + column
            foot_grid.append([base, base + 1, base + 4, base + 3])
    quads.extend(foot_grid)

    loop_start = []
    loop_total = []
    loop_vert = []
    loop_uv = []
    for corners in quads:
        loop_start.append(len(loop_vert))
        loop_total.append(len(corners))
        for corner in corners:
            loop_vert.append(corner)
            loop_uv.append(uvs[corner])

    count = len(positions)
    payload = {
        "co": np.asarray(positions, dtype=np.float32),
        "uv": np.asarray(loop_uv, dtype=np.float32),
        "loop_vert": np.asarray(loop_vert, dtype=np.int32),
        "loop_start": np.asarray(loop_start, dtype=np.int32),
        "loop_total": np.asarray(loop_total, dtype=np.int32),
    }
    for name in ARM_GROUPS + OTHER_GROUPS:
        payload[f"w_{name}"] = np.zeros(count, dtype=np.float32)
    payload["w_body"][:] = 1.0
    payload["w_foot_l"][foot_start:] = 1.0
    payload["w_foot_r"][foot_start:] = 1.0
    # A half isoline on each upper arm, so the shoulder can be placed. It sits
    # at the top of the tube, which is where a shoulder is.
    top = index(RINGS, 0)
    payload["w_upperarm_l"][top - across_count : top] = 0.5
    payload["w_upperarm_r"][top - across_count : top] = 0.5
    np.savez_compressed(path, **payload)


def paint(body: Path, output: Path, *arguments: str):
    return subprocess.run(
        [sys.executable, "-B", str(PAINTER),
         "--body", str(body), "--output", str(output), "--size", str(SIZE),
         *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


class PaintedKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls._directory.name)
        cls.body = cls.root / "body.npz"
        build_body(cls.body)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def layer(self, name: str, *arguments: str):
        from PIL import Image

        output = self.root / f"{name}.png"
        finished = paint(self.body, output, *arguments)
        self.assertEqual(
            finished.returncode, 0,
            f"kit_paint.py failed:\n{finished.stdout}\n{finished.stderr}",
        )
        self.assertIn("KIT PAINT OK", finished.stdout)
        with Image.open(output) as image:
            self.assertEqual(image.mode, "RGBA")
            pixels = np.asarray(image)
        receipt = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        return pixels, receipt, finished.stdout

    def test_it_reads_no_skin(self):
        """The painter takes no skin at all, so it cannot derive from one."""
        finished = paint(self.body, self.root / "rejected.png",
                         "--skin", "anything.png")
        self.assertNotEqual(finished.returncode, 0)
        self.assertIn("unrecognized arguments", finished.stderr)
        self.assertIn("readsNoSkin", PAINTER.read_text(encoding="utf-8"))

    def test_the_hem_is_a_level_on_the_body(self):
        """A hem at a fraction of her height is painted at that height.

        The tube's UV rows ARE its heights, so the row a hem lands on can be
        predicted before the painter runs rather than read off its output.
        """
        hem, neck = 0.30, 0.80
        pixels, receipt, _ = self.layer(
            "levels", "--hem-fraction", str(hem), "--neck-fraction", str(neck),
            "--no-bib",
        )
        alpha = pixels[:, :, 3]
        self.assertAlmostEqual(receipt["levelsM"]["hem"], hem * HEIGHT, places=3)
        self.assertAlmostEqual(receipt["levelsM"]["neck"], neck * HEIGHT, places=3)

        # Row 0 is the TOP of the texture and v = 1 is the top of the body, so
        # a height fraction f is at row (1 - f) * (SIZE - 1). Three pixels of
        # margin for the painter's soft edge.
        def row_of(fraction: float) -> int:
            return int(round((1.0 - fraction) * (SIZE - 1)))

        middle = alpha[row_of(0.5 * (hem + neck)), :]
        self.assertGreater(middle.max(), 250, "the garment did not reach mid torso")
        for outside in (hem - 0.06, neck + 0.06):
            row = alpha[row_of(outside), :]
            self.assertEqual(
                int(row.max()), 0,
                f"the garment reached {outside:.2f} of her height, outside its hem",
            )

    def test_the_winding_cannot_change_the_kit(self):
        """A body wound inside out paints the same kit.

        The bib is cut by how squarely the surface faces front or back, and a
        face normal points the other way when the winding is reversed. The rule
        takes the absolute value for exactly that reason. This test fails if
        somebody makes the facing test signed, which would silently make every
        kit depend on how its body was exported.
        """
        _, forward, _ = self.layer("wound_out")
        inverted = self.root / "inverted.npz"
        build_body(inverted, inside_out=True)
        image = self.root / "wound_in.png"
        finished = paint(inverted, image, "--size", str(SIZE))
        self.assertEqual(finished.returncode, 0, finished.stderr)
        backward = json.loads(image.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(forward["bibPixels"], backward["bibPixels"])
        self.assertEqual(forward["garmentPixels"], backward["garmentPixels"])
        self.assertGreater(forward["bibPixels"], 0, "the bib painted nothing")

    def test_the_facing_test_narrows_the_bib(self):
        """A bib that must face the camera more squarely covers less.

        This pins the DIRECTION of the facing parameter. A test that only
        checked the bib was non-empty would pass with the comparison reversed.
        """
        _, wide, _ = self.layer("facing_wide", "--bib-facing", "0.15")
        _, narrow, _ = self.layer("facing_narrow", "--bib-facing", "0.90")
        self.assertLess(narrow["bibPixels"], wide["bibPixels"])

    def test_an_empty_garment_is_refused(self):
        """A hem above the neckline and a sleeve above her head paint nothing.

        BOTH have to go. The sleeve is cut independently of the hem, so a hem
        above the neckline on its own still leaves a cap on the shoulder, and
        the first version of this test proved the BIB's refusal while claiming
        the garment's.
        """
        finished = paint(self.body, self.root / "empty.png",
                         "--hem-fraction", "0.90", "--neck-fraction", "0.20",
                         "--sleeve-fraction", "1.50", "--no-bib")
        self.assertNotEqual(finished.returncode, 0)
        self.assertIn("the garment mask is empty", finished.stdout + finished.stderr)

    def test_an_empty_bib_is_refused(self):
        """A bib with no panel left is refused rather than skipped."""
        finished = paint(self.body, self.root / "no_bib.png",
                         "--hem-fraction", "0.90", "--neck-fraction", "0.20")
        self.assertNotEqual(finished.returncode, 0)
        self.assertIn("the bib panel is empty", finished.stdout + finished.stderr)

    def test_the_sidecar_shape_is_pinned(self):
        """The sidecar's exact key set, so a reader cannot be left behind.

        A licence or provenance loader elsewhere in this repository reads this
        file, and a producer that WIDENS its shape while a reader stays on the
        old one is a fault this repository has already paid for. An earlier
        revision of the painter wrote `skin` and `skinSha256`, which existed
        only because it read the MPFB skin and derived from it. Anything that
        changes this set must change this test, and whoever changes it has to
        look at who reads the file.
        """
        _, receipt, _ = self.layer("shape")
        self.assertEqual(
            set(receipt),
            {
                "acrossAxis", "bibBorderFraction", "bibCornerPower", "bibFacing",
                "bibHalfWidthM", "bibPixels", "body", "bodySha256",
                "boundaryOverRootArea", "boundaryPixels", "coloursLinear",
                "coveredPixels", "depthAxis", "distinctOpaqueColours",
                "edgePixels", "font", "fractions", "frontSign", "garmentPixels",
                "heightM", "instrument", "levelsM", "output", "outputSha256",
                "position", "readsNoSkin", "secondsToPaint", "sleeveRadiusM",
                "textureSize", "upAxis",
            },
        )
        self.assertEqual(
            set(receipt["fractions"]),
            {"neck", "hem", "sleeve", "bibTop", "bibBottom"},
        )
        self.assertEqual(set(receipt["levelsM"]), {"neck", "hem", "sleeve"})
        self.assertEqual(set(receipt["coloursLinear"]), {"kit", "bib", "letters"})
        self.assertNotIn(
            "skin", receipt,
            "the layer reads no skin, so its sidecar must not name one",
        )

    def test_the_layer_records_its_own_bytes(self):
        """The sidecar's hash is of the file that was written."""
        import hashlib

        pixels, receipt, _ = self.layer("hashed")
        written = (self.root / "hashed.png").read_bytes()
        self.assertEqual(receipt["outputSha256"], hashlib.sha256(written).hexdigest())
        self.assertTrue(receipt["readsNoSkin"])
        self.assertEqual(receipt["textureSize"], SIZE)
        self.assertEqual(pixels.shape, (SIZE, SIZE, 4))

    def test_one_body_cannot_use_another_body_s_maps(self):
        """The cache is keyed by the dump's own hash, and it says so."""
        other = self.root / "other.npz"
        build_body(other, inside_out=True)
        self.layer("first_body")
        cache = self.body.with_name(f"{self.body.stem}.maps{SIZE}.npz")
        self.assertTrue(cache.is_file(), "the painter wrote no cache to reject")

        # The same maps under the other body's name. The painter must notice by
        # the hash rather than by the file being present.
        stolen = other.with_name(f"{other.stem}.maps{SIZE}.npz")
        stolen.write_bytes(cache.read_bytes())
        finished = paint(other, self.root / "second_body.png")
        self.assertEqual(finished.returncode, 0, finished.stderr)
        self.assertIn("is for another body; rebuilding", finished.stdout)


if __name__ == "__main__":
    unittest.main()
