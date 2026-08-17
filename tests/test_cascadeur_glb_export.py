import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from cascadeur_glb_export import (  # noqa: E402
    ExportError,
    build_export_expression,
    parse_frame_range,
    require_ok,
)


class CascadeurGlbExportTest(unittest.TestCase):
    def test_expression_pins_animation_error_selection_and_fps_options(self):
        expression = build_export_expression(
            Path(r"C:\braven movement\sample.glb"),
            fps=60.0,
        )

        self.assertIn("setattr(o, 'include_animation', True)", expression)
        self.assertIn("setattr(o, 'throw_exception', True)", expression)
        self.assertIn("setattr(o, 'for_selected_objects', False)", expression)
        self.assertIn("setattr(o, 'fps', 60.0)", expression)
        self.assertIn("C:/braven movement/sample.glb", expression)
        self.assertIn("csc.glb.process_export(scene", expression)

    def test_require_ok_refuses_cascadeur_error_response(self):
        with self.assertRaisesRegex(ExportError, "free tier blocked export"):
            require_ok({"ok": False, "error": "free tier blocked export"})

    def test_parse_frame_range_reads_expression_value(self):
        self.assertEqual(parse_frame_range({"ok": True, "value": "(0, 100)"}), (0, 100))

    def test_parse_frame_range_rejects_reversed_range(self):
        with self.assertRaisesRegex(ExportError, "invalid frame range"):
            parse_frame_range({"ok": True, "value": "(100, 0)"})


if __name__ == "__main__":
    unittest.main()
