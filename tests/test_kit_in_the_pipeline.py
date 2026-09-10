"""The kit this repository authors, and how the pipeline wears it.

Three things are held here. The config carries the kit as three OPTIONAL keys
under `presentation.kit`, and a config without them builds the figure it
always built. A kit path is refused anywhere but under `assets/kit/`, at load
time. And the committed dress is the thing its own build sidecar says it is:
the same vertex count, the same header, a licence line the licence module
resolves.

No Blender here. The authoring and the wearing are Blender scripts, and their
proof is a render that a person looks at; what a test can hold is the contract
around them.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))
sys.path.insert(0, str(MODULE_DIR / "scripts"))

from asset_licences import OWN_WORK, licence_for  # noqa: E402
from make_bib_image import bib_boxes_px  # noqa: E402
from reference_pose_config import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    MaterialPresentation,
    ReferencePoseConfigError,
    kit_asset_path,
    load_reference_catch_config,
    mhclo_obj_path,
)

KIT_CONFIG = MODULE_DIR / "config" / "netball_kit.v1.json"
KIT_FILE = MODULE_DIR / "config" / "kit" / "netball_dress.v1.json"
DRESS = MODULE_DIR / "assets" / "kit" / "braven_netball_dress.mhclo"
SIDECAR = MODULE_DIR / "assets" / "kit" / "braven_netball_dress.build.json"
BIB = MODULE_DIR / "assets" / "kit" / "bib_GS.png"


def _config_with_kit(**kit) -> Path:
    """A copy of the reference config whose kit block carries `kit`."""
    data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["presentation"]["kit"].update(kit)
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    with handle:
        json.dump(data, handle)
    return Path(handle.name)


class TheKitIsOptional(unittest.TestCase):
    def test_the_reference_config_wears_no_kit(self):
        kit = load_reference_catch_config().presentation.kit
        self.assertIsNone(kit.garment)
        self.assertIsNone(kit.bib_image)
        self.assertIsNone(kit.sock_top_m)

    def test_the_dataclass_defaults_match_an_absent_block(self):
        # `create_athlete` branches on these being None; a default that was
        # anything else would wear a garment nobody configured.
        kit = MaterialPresentation(base_color=(0.0, 0.0, 0.0, 1.0), roughness=0.5)
        self.assertEqual((kit.garment, kit.bib_image, kit.sock_top_m), (None, None, None))

    def test_the_example_config_wears_the_dress(self):
        kit = load_reference_catch_config(KIT_CONFIG).presentation.kit
        self.assertEqual(kit.garment, "assets/kit/braven_netball_dress.mhclo")
        self.assertEqual(kit.bib_image, "assets/kit/bib_GS.png")
        self.assertEqual(kit.sock_top_m, 0.175)

    def test_a_null_key_reads_as_absent(self):
        kit = load_reference_catch_config(_config_with_kit(garment=None, sockTopM=None)).presentation.kit
        self.assertIsNone(kit.garment)
        self.assertIsNone(kit.sock_top_m)

    def test_a_sock_top_at_or_below_the_floor_is_refused(self):
        with self.assertRaises(ReferencePoseConfigError):
            load_reference_catch_config(_config_with_kit(sockTopM=0.0))

    def test_an_empty_garment_string_is_refused(self):
        with self.assertRaises(ReferencePoseConfigError):
            load_reference_catch_config(_config_with_kit(garment=""))


class AKitPathIsRefusedOutsideTheKitDirectory(unittest.TestCase):
    def test_the_committed_dress_resolves(self):
        self.assertEqual(kit_asset_path("assets/kit/braven_netball_dress.mhclo"), DRESS)

    def test_a_missing_file_is_refused_with_its_path(self):
        with self.assertRaises(ReferencePoseConfigError) as caught:
            kit_asset_path("assets/kit/no_such_dress.mhclo")
        self.assertIn("no_such_dress.mhclo", str(caught.exception))

    def test_every_other_place_is_refused(self):
        for relative in (
            "../assets/kit/braven_netball_dress.mhclo",
            "assets/kit/../../config/reference_catch.v1.json",
            "config/reference_catch.v1.json",
            "/assets/kit/braven_netball_dress.mhclo",
            "F:/somewhere/braven_netball_dress.mhclo",
            "assets\\kit\\braven_netball_dress.mhclo",
            "assets/kits/braven_netball_dress.mhclo",
        ):
            with self.subTest(relative=relative):
                with self.assertRaises(ReferencePoseConfigError):
                    kit_asset_path(relative)

    def test_the_refusal_happens_at_load_and_not_at_render(self):
        with self.assertRaises(ReferencePoseConfigError):
            load_reference_catch_config(_config_with_kit(garment="config/reference_catch.v1.json"))


class TheCommittedDressIsWhatItsSidecarSays(unittest.TestCase):
    def setUp(self):
        self.header = [
            line for line in DRESS.read_text(encoding="utf-8").splitlines()[:40]
        ]
        self.sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
        self.kit = json.loads(KIT_FILE.read_text(encoding="utf-8"))

    def test_the_header_names_the_asset_the_basemesh_and_the_obj(self):
        self.assertIn("basemesh hm08", self.header)
        self.assertIn(f"name {self.kit['name']}", self.header)
        self.assertIn(f"obj_file {self.kit['name']}.obj", self.header)
        self.assertTrue(DRESS.with_suffix(".obj").is_file())

    def test_the_header_carries_the_owners_line_the_licence_module_resolves(self):
        self.assertIn(f"# license: {self.kit['licence']}", self.header)
        self.assertEqual(self.kit["licence"], OWN_WORK)
        licence, source = licence_for(DRESS)
        self.assertEqual(licence, OWN_WORK)
        self.assertIn("Kit assets authored in this repository", source)

    def test_the_obj_has_exactly_the_vertices_the_sidecar_counted(self):
        obj = DRESS.with_suffix(".obj").read_text(encoding="utf-8")
        vertices = sum(1 for line in obj.splitlines() if line.startswith("v "))
        self.assertEqual(vertices, self.sidecar["nBodysuitVertices"] + self.sidecar["nSkirtVertices"])

    def test_the_sidecar_pins_its_two_inputs_by_hash(self):
        # CRLF is folded before hashing on both sides, so the same commit
        # gives the same value on a Windows checkout and on the Linux runner.
        import hashlib

        def folded(path: Path) -> str:
            return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

        self.assertEqual(self.sidecar["kitSha256"], folded(KIT_FILE))
        self.assertEqual(self.sidecar["authoringConfigSha256"], folded(DEFAULT_CONFIG_PATH))

    def test_the_check_the_sidecar_records_passed(self):
        self.assertTrue(self.sidecar["check"]["all_checks_ok"])
        self.assertEqual(self.sidecar["parts"][0]["faceSizes"], [3])
        self.assertEqual(self.sidecar["parts"][1]["faceSizes"], [3])

    def test_the_hems_in_the_mesh_are_the_hems_in_the_kit_file(self):
        heights = self.kit["heightsM"]
        body, skirt = self.sidecar["parts"]
        self.assertAlmostEqual(body["zMinM"], heights["briefsHem"], places=3)
        self.assertAlmostEqual(skirt["zMinM"], heights["skirtHem"], places=3)

    def test_the_sidecar_carries_the_provenance_claim_and_the_output_hashes(self):
        # `readsNoSkin` is the key the painted-kit sidecar uses for the same
        # claim, so one family has one provenance claim whatever the arity.
        import hashlib

        self.assertIs(self.sidecar["readsNoSkin"], True)
        self.assertIn("CC0", self.sidecar["derivedFrom"])
        self.assertEqual(self.sidecar["output"], DRESS.name)
        self.assertEqual(self.sidecar["outputSha256"], hashlib.sha256(DRESS.read_bytes()).hexdigest())
        self.assertEqual(
            self.sidecar["objSha256"], hashlib.sha256(DRESS.with_suffix(".obj").read_bytes()).hexdigest()
        )

    def test_the_mhclo_names_the_obj_the_receipt_must_hash(self):
        self.assertEqual(mhclo_obj_path(DRESS), DRESS.with_suffix(".obj"))
        self.assertTrue(mhclo_obj_path(DRESS).is_file())


class TheBibImageCarriesItsOwnSidecar(unittest.TestCase):
    def test_the_sidecar_claims_no_skin_was_read_and_hashes_the_image(self):
        import hashlib

        sidecar = json.loads(BIB.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertIs(sidecar["readsNoSkin"], True)
        self.assertEqual(sidecar["output"], BIB.name)
        self.assertEqual(sidecar["outputSha256"], hashlib.sha256(BIB.read_bytes()).hexdigest())
        self.assertEqual(sidecar["letters"], "GS")
        self.assertEqual(sidecar["kitFile"], "config/kit/netball_dress.v1.json")


class TheBibSitsWhereTheKitFileSaysOnTheDress(unittest.TestCase):
    def setUp(self):
        self.kit = json.loads(KIT_FILE.read_text(encoding="utf-8"))

    def test_the_two_boxes_follow_from_the_frame_and_the_square(self):
        # By hand: x +-0.07 in a frame -0.21..0.21 is u 1/6..1/3 of the front
        # half, so pixels 341..682 of 2048; z 1.16..1.30 in 0.78..1.44 is
        # v 0.576..0.788, so rows 217..434 of 1024 counted from the top.
        front, back = bib_boxes_px(self.kit)
        self.assertEqual(front, (341, 217, 682, 434))
        self.assertEqual(back, (1365, 217, 1706, 434))

    def test_the_committed_image_is_white_in_the_box_and_clear_outside_it(self):
        from PIL import Image

        image = Image.open(BIB).convert("RGBA")
        self.assertEqual(image.size, tuple(self.kit["bib"]["imagePx"]))
        front, back = bib_boxes_px(self.kit)
        for box in (front, back):
            with self.subTest(box=box):
                inset = (box[0] + 30, box[1] + 30)
                self.assertGreater(image.getpixel(inset)[3], 250, "opaque inside the square")
                self.assertGreater(min(image.getpixel(inset)[:3]), 200, "white inside the square")
        outside = ((front[2] + 40, front[1]), (10, 10), (back[0] - 40, back[3]))
        for point in outside:
            with self.subTest(point=point):
                self.assertEqual(image.getpixel(point)[3], 0, "transparent outside the square")

    def test_the_letters_darken_the_centre_of_the_square(self):
        from PIL import Image

        image = Image.open(BIB).convert("RGBA")
        front, _ = bib_boxes_px(self.kit)
        centre_row = (front[1] + front[3]) // 2
        darkest = min(
            min(image.getpixel((x, centre_row))[:3]) for x in range(front[0] + 20, front[2] - 20)
        )
        self.assertLess(darkest, 60, "the letters cross the centre row")


if __name__ == "__main__":
    unittest.main()
