"""The rig check, pinned on files it builds itself.

`scripts/tactics_rig_check.py` answers whether a shipped Tactics figure carries
every bone the app asks of a character. The Tactics checkout is a sibling of
this one and may be absent, so a test that read it would skip, and a guard that
skips guards nothing. These build a glTF container and a `skinned.ts` in a
temporary directory and never skip.
"""

from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR / "scripts"))

from tactics_rig_check import (  # noqa: E402
    CHUNK_JSON,
    GLB_MAGIC,
    RigCheckError,
    check,
    node_names,
    required_bones,
)

SKINNED_SOURCE = """
/** A comment with a 'quoted phrase' in it that is not a bone. */
export const BONES = {
  root: 'root',
  pelvis: 'pelvis',
  /** The trunk, in three, and it has to be 'three'. */
  waist: 'spine_01',
  armL: { upper: 'upperarm_l', lower: 'lowerarm_l', end: 'hand_l' },
} as const

export const NOT_BONES = { decoy: 'decoy_bone' }
"""


def _glb(names: list[str], magic: bytes = GLB_MAGIC, chunk: int = CHUNK_JSON) -> Path:
    """A minimal binary glTF whose nodes carry the given names."""
    document = {"asset": {"version": "2.0"}, "nodes": [{"name": n} for n in names]}
    payload = json.dumps(document).encode("utf-8")
    payload += b" " * ((4 - len(payload) % 4) % 4)
    header = magic + struct.pack("<II", 2, 12 + 8 + len(payload))
    body = struct.pack("<II", len(payload), chunk) + payload
    path = Path(tempfile.mkdtemp()) / "figure.glb"
    path.write_bytes(header + body)
    return path


def _skinned(source: str = SKINNED_SOURCE) -> Path:
    path = Path(tempfile.mkdtemp()) / "skinned.ts"
    path.write_text(source, encoding="utf-8")
    return path


class TheWantedNamesComeFromTheFarSide(unittest.TestCase):
    def test_it_reads_the_values_and_not_the_keys(self):
        # `waist` is the key and `spine_01` is the name the asset must carry.
        wanted = required_bones(_skinned())
        self.assertIn("spine_01", wanted)
        self.assertNotIn("waist", wanted)

    def test_it_reads_nested_limb_objects(self):
        wanted = required_bones(_skinned())
        for name in ("upperarm_l", "lowerarm_l", "hand_l"):
            self.assertIn(name, wanted)

    def test_a_quoted_word_in_a_comment_is_not_a_bone(self):
        # The comment inside the block contains 'three' in quotes. Reading every
        # quoted string in the block would take it for a bone name.
        self.assertNotIn("three", required_bones(_skinned()))

    def test_a_quoted_phrase_outside_the_block_is_not_a_bone(self):
        wanted = required_bones(_skinned())
        self.assertNotIn("quoted phrase", wanted)
        self.assertNotIn("decoy_bone", wanted)

    def test_a_source_without_the_block_refuses(self):
        with self.assertRaises(RigCheckError):
            required_bones(_skinned("const OTHER = { a: 'b' }"))

    def test_an_unterminated_block_refuses(self):
        with self.assertRaises(RigCheckError):
            required_bones(_skinned("export const BONES = {\n  root: 'root',\n"))


class TheNamesComeOutOfTheAsset(unittest.TestCase):
    def test_it_reads_every_named_node(self):
        self.assertEqual(node_names(_glb(["root", "pelvis"])), ("root", "pelvis"))

    def test_an_unnamed_node_is_skipped_and_does_not_raise(self):
        path = _glb(["root"])
        document = {"asset": {"version": "2.0"}, "nodes": [{"name": "root"}, {}]}
        payload = json.dumps(document).encode("utf-8")
        payload += b" " * ((4 - len(payload) % 4) % 4)
        path.write_bytes(
            GLB_MAGIC
            + struct.pack("<II", 2, 20 + len(payload))
            + struct.pack("<II", len(payload), CHUNK_JSON)
            + payload
        )
        self.assertEqual(node_names(path), ("root",))

    def test_a_file_that_is_not_a_glb_refuses(self):
        with self.assertRaises(RigCheckError):
            node_names(_glb(["root"], magic=b"NOPE"))

    def test_a_first_chunk_that_is_not_json_refuses(self):
        with self.assertRaises(RigCheckError):
            node_names(_glb(["root"], chunk=0x004E4942))


class TheCheckCanFail(unittest.TestCase):
    """A check that cannot report a missing bone has verified nothing."""

    WANTED = ("root", "pelvis", "spine_01", "hand_l")

    def test_a_complete_asset_reports_nothing_missing(self):
        have, missing = check(_glb(list(self.WANTED)), self.WANTED)
        self.assertEqual(missing, [])
        self.assertEqual(have, list(self.WANTED))

    def test_a_missing_bone_is_named(self):
        have, missing = check(_glb(["root", "pelvis", "spine_01"]), self.WANTED)
        self.assertEqual(missing, ["hand_l"])
        self.assertNotIn("hand_l", have)

    def test_every_bone_missing_is_reported_and_not_just_the_first(self):
        have, missing = check(_glb(["root"]), self.WANTED)
        self.assertEqual(missing, ["pelvis", "spine_01", "hand_l"])
        self.assertEqual(have, ["root"])

    def test_an_extra_bone_in_the_asset_is_not_a_failure(self):
        # 69 named nodes ship against 21 wanted. Everything else is ignored.
        have, missing = check(_glb([*self.WANTED, "twist_01", "ik_hand_root"]), self.WANTED)
        self.assertEqual(missing, [])
        self.assertEqual(len(have), len(self.WANTED))

    def test_a_near_miss_name_does_not_satisfy_the_contract(self):
        # The retarget looks the name up exactly. `Hand_L` is not `hand_l`.
        _, missing = check(_glb(["root", "pelvis", "spine_01", "Hand_L"]), self.WANTED)
        self.assertEqual(missing, ["hand_l"])


if __name__ == "__main__":
    unittest.main()
