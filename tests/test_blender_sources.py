import ast
import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from movement_contract import normalization_transform  # noqa: E402

HELPER_MODULE = "blender_mpfb_reference_catch"
IMPORTING_MODULES = ("blender_movement_render.py",)


def _signatures(source: str) -> dict[str, dict]:
    """Every top-level def in a module, by name, with its required arguments."""
    found = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        arguments = node.args
        positional = [item.arg for item in arguments.posonlyargs + arguments.args]
        found[node.name] = {
            "positional": positional,
            "positional_required": len(positional) - len(arguments.defaults),
            "keyword_required": {
                item.arg
                for item, default in zip(arguments.kwonlyargs, arguments.kw_defaults)
                if default is None
            },
            "keyword_all": {item.arg for item in arguments.kwonlyargs},
        }
    return found


def _calls_into_helpers(source: str, signatures: dict[str, dict]) -> list[str]:
    tree = ast.parse(source)
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == HELPER_MODULE:
            imported.update(alias.name for alias in node.names)

    complaints = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name not in imported or name not in signatures:
            continue
        signature = signatures[name]
        given = {keyword.arg for keyword in node.keywords if keyword.arg}
        supplied = len(node.args) + len(
            [item for item in signature["positional"] if item in given]
        )
        if supplied < signature["positional_required"]:
            complaints.append(
                f"line {node.lineno}: {name}() takes "
                f"{signature['positional_required']} positional arguments "
                f"{signature['positional']} and receives {supplied}"
            )
        missing = signature["keyword_required"] - given
        if missing:
            complaints.append(
                f"line {node.lineno}: {name}() is missing the required "
                f"keyword arguments {sorted(missing)}"
            )
        unknown = given - signature["keyword_all"] - set(signature["positional"])
        if unknown:
            complaints.append(
                f"line {node.lineno}: {name}() does not accept the keyword "
                f"arguments {sorted(unknown)}"
            )
    return complaints


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

    def test_movement_renderer_calls_match_the_reference_helper_signatures(self):
        """The posing helpers are shared, and only Blender links the two sides.

        A helper gains an argument on one branch while the renderer keeps the
        old call on another. The files never collide, so a merge is clean and
        the break appears only when Blender loads the module. This reads both
        signatures without importing bpy, so it fails in the ordinary suite.
        """
        signatures = _signatures(
            (MODULE_DIR / f"{HELPER_MODULE}.py").read_text(encoding="utf-8")
        )

        for name in IMPORTING_MODULES:
            with self.subTest(module=name):
                complaints = _calls_into_helpers(
                    (MODULE_DIR / name).read_text(encoding="utf-8"), signatures
                )
                self.assertEqual([], complaints, f"{name}\n" + "\n".join(complaints))


if __name__ == "__main__":
    unittest.main()
