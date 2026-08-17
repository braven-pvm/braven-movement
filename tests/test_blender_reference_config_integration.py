import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPOSITORY_ROOT / "config" / "reference_catch.v1.json"
GENERATOR_PATH = REPOSITORY_ROOT / "blender_mpfb_reference_catch.py"
BLENDER_PATH = Path(
    os.environ.get(
        "BRAVEN_BLENDER_EXE",
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    )
)


@unittest.skipUnless(
    os.environ.get("BRAVEN_RUN_BLENDER_INTEGRATION") == "1",
    "set BRAVEN_RUN_BLENDER_INTEGRATION=1 to run Blender/MPFB integration",
)
class BlenderReferenceConfigIntegrationTest(unittest.TestCase):
    def test_generator_uses_the_supplied_config_for_the_receipt(self):
        self.assertTrue(BLENDER_PATH.is_file(), f"Blender not found: {BLENDER_PATH}")
        data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        data["movementId"] = "portable_config_probe"

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            config_path = temporary / "reference.json"
            output_path = temporary / "output"
            config_path.write_text(json.dumps(data), encoding="utf-8")
            expected_config_sha256 = _sha256(config_path)
            completed = subprocess.run(
                [
                    str(BLENDER_PATH),
                    "-b",
                    "--python-exit-code",
                    "9",
                    "-P",
                    str(GENERATOR_PATH),
                    "--",
                    "--config",
                    str(config_path),
                    "--output",
                    str(output_path),
                ],
                cwd=temporary,
                text=True,
                capture_output=True,
                timeout=180,
                check=False,
            )
            self.assertEqual(
                completed.returncode,
                0,
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
            )
            receipt = json.loads(
                (output_path / "braven_mpfb_reference_catch.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(receipt["movementId"], "portable_config_probe")
        self.assertEqual(receipt["configuration"]["schemaVersion"], 1)
        self.assertEqual(receipt["configuration"]["sha256"], expected_config_sha256)


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
