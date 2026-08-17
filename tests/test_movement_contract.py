import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from movement_contract import (  # noqa: E402
    ContractError,
    inspect_glb,
    max_rgba_alpha,
    read_job_manifest,
    write_job_manifest,
)


def glb_bytes(*, animations: int = 1, channels: int = 2) -> bytes:
    payload = {
        "asset": {"version": "2.0"},
        "nodes": [{"name": "figure"}, {"name": "rig"}],
        "animations": [
            {"name": f"animation_{index}", "channels": [{} for _ in range(channels)]}
            for index in range(animations)
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    total = 12 + 8 + len(encoded)
    return b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I4s", len(encoded), b"JSON") + encoded


class UnsliceablePixels:
    def __init__(self, values):
        self._values = values

    def __iter__(self):
        return iter(self._values)

    def __getitem__(self, index):
        raise TypeError("slice indices are not supported")


class MovementContractTest(unittest.TestCase):
    def test_inspect_glb_counts_real_animation_channels(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "movement.glb"
            path.write_bytes(glb_bytes(animations=1, channels=3))

            inspection = inspect_glb(path)

            self.assertEqual(inspection.nodes, 2)
            self.assertEqual(inspection.animations, 1)
            self.assertEqual(inspection.channels, 3)
            self.assertEqual(inspection.bytes, path.stat().st_size)
            self.assertEqual(len(inspection.sha256), 64)

    def test_inspect_glb_refuses_animation_free_statue(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "statue.glb"
            path.write_bytes(glb_bytes(animations=0, channels=0))

            with self.assertRaisesRegex(ContractError, "no animation channels"):
                inspect_glb(path)

    def test_max_rgba_alpha_does_not_slice_blender_pixel_collection(self):
        pixels = UnsliceablePixels([0.1, 0.2, 0.3, 0.0, 0.4, 0.5, 0.6, 1.0])

        self.assertEqual(max_rgba_alpha(pixels), 1.0)

    def test_manifest_round_trip_resolves_asset_relative_to_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            asset = root / "cascy.glb"
            asset.write_bytes(glb_bytes(animations=1, channels=2))
            inspection = inspect_glb(asset)

            manifest_path = write_job_manifest(
                root / "job.json",
                movement_id="cascy_internal_probe",
                asset_path=asset,
                fps=30.0,
                frame_start=0,
                frame_end=100,
                inspection=inspection,
                publishable=False,
            )
            job = read_job_manifest(manifest_path)

            self.assertEqual(job.version, 1)
            self.assertEqual(job.movement_id, "cascy_internal_probe")
            self.assertEqual(job.asset_path, asset)
            self.assertEqual(job.asset_format, "glb")
            self.assertEqual(job.fps, 30.0)
            self.assertEqual((job.frame_start, job.frame_end), (0, 100))
            self.assertFalse(job.publishable)
            self.assertEqual(job.asset_sha256, inspection.sha256)


if __name__ == "__main__":
    unittest.main()
