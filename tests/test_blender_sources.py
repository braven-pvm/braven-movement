import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from movement_contract import normalization_transform  # noqa: E402


class BlenderSourceContractTest(unittest.TestCase):
    def test_normalization_scales_height_centres_xy_and_places_feet_at_zero(self):
        transform = normalization_transform(
            minimum=(-1.0, -0.5, 0.25),
            maximum=(1.0, 0.5, 2.25),
            target_height=1.75,
        )

        self.assertAlmostEqual(transform.scale, 0.875)
        self.assertAlmostEqual(transform.offset_x, 0.0)
        self.assertAlmostEqual(transform.offset_y, 0.0)
        self.assertAlmostEqual(transform.offset_z, -0.21875)

    def test_renderer_imports_glb_and_honours_job_timeline_and_transparency(self):
        source = (MODULE_DIR / "blender_glb_render.py").read_text(encoding="utf-8")

        self.assertIn("bpy.ops.import_scene.gltf", source)
        self.assertIn("read_job_manifest", source)
        self.assertIn("scene.render.fps = int(round(job.fps))", source)
        self.assertIn("scene.frame_start = job.frame_start", source)
        self.assertIn("scene.frame_end = job.frame_end", source)
        self.assertIn("scene.render.film_transparent = True", source)
        self.assertIn('scene.render.image_settings.color_mode = "RGBA"', source)
        self.assertIn("max_rgba_alpha(image.pixels)", source)

    def test_probe_uses_non_slicing_alpha_helper_for_both_engines(self):
        source = (MODULE_DIR / "blender_probe.py").read_text(encoding="utf-8")

        self.assertIn('render_engine("CYCLES")', source)
        self.assertIn('render_engine("BLENDER_EEVEE_NEXT")', source)
        self.assertIn("max_rgba_alpha(image.pixels)", source)
        self.assertNotIn("pixels[3::4]", source)


if __name__ == "__main__":
    unittest.main()
