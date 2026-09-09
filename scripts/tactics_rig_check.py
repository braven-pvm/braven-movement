"""Does a shipped figure satisfy the rig Braven Tactics asks for.

The Tactics side names the bones it drives in `BONES`, in `src/engine/skinned.ts`,
and calls that list "the whole of what the app asks of a character". The contract
lane read that list and recorded, in its own section 6, that it did NOT open
either GLB: the names are what the CODE asks for, not what the shipped assets
contain, and confirming the assets is character-lane work.

This confirms it. It reads the required names out of the Tactics source rather
than repeating them, and it reads the node names out of the GLB rather than
trusting a file name.

    python scripts/tactics_rig_check.py --tactics F:/Repositories/braven-tactics

BOTH SIDES ARE READ, AND NEITHER IS RETYPED. A list of bones copied into this
file would be a second source of truth for a contract this repository does not
own, and it would stop agreeing with the far side without anybody noticing.

Nothing here changes either repository. It reads and it reports.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

# The chunk type of the JSON chunk in a binary glTF container, little-endian
# ASCII for "JSON". The binary chunk that follows it holds the mesh data and is
# not read here, because a bone is a node and every node name is in the JSON.
GLB_MAGIC = b"glTF"
CHUNK_JSON = 0x4E4F534A

DEFAULT_TACTICS = Path("F:/Repositories/braven-tactics")
SKINNED = Path("src") / "engine" / "skinned.ts"
FIGURES = Path("public") / "figures"


class RigCheckError(Exception):
    """The check could not be made, which is not the same as a failing check."""


def required_bones(skinned_ts: Path) -> tuple[str, ...]:
    """Every bone name inside the `BONES` object, read from the Tactics source.

    The block is bounded rather than the whole file scanned, so an unrelated
    quoted string elsewhere in the module cannot be read as a bone. The keys are
    not read at all: only the VALUES matter, because a value is the name the
    asset must carry.
    """
    text = skinned_ts.read_text(encoding="utf-8")
    start = text.find("export const BONES = {")
    if start < 0:
        raise RigCheckError(f"no `export const BONES = {{` in {skinned_ts}")
    end = text.find("} as const", start)
    if end < 0:
        raise RigCheckError(f"the BONES object in {skinned_ts} is not terminated")
    block = text[start:end]
    # A bone name is the string on the right of a colon. Reading every quoted
    # string would also pick up prose from the block's own comments.
    names = re.findall(r":\s*'([^']+)'", block)
    if not names:
        raise RigCheckError(f"the BONES object in {skinned_ts} names no bone")
    return tuple(names)


def node_names(glb: Path) -> tuple[str, ...]:
    """Every named node in a binary glTF file.

    A bone is a node in glTF. A skin lists which of them are joints, and this
    does not narrow to those: a name present but unused by a skin is still a
    name the retarget can find, and reporting the wider set cannot hide a
    missing bone.
    """
    raw = glb.read_bytes()
    if raw[:4] != GLB_MAGIC:
        raise RigCheckError(f"{glb.name} does not start with the glTF magic")
    if len(raw) < 20:
        raise RigCheckError(f"{glb.name} is too short to hold a chunk")
    length, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != CHUNK_JSON:
        raise RigCheckError(f"{glb.name}'s first chunk is not JSON")
    payload = raw[20 : 20 + length]
    document = json.loads(payload.decode("utf-8"))
    return tuple(
        node["name"] for node in document.get("nodes", []) if node.get("name")
    )


def check(glb: Path, wanted: tuple[str, ...]) -> tuple[list[str], list[str]]:
    """The wanted names this asset has, and the ones it does not."""
    present = set(node_names(glb))
    have = [name for name in wanted if name in present]
    missing = [name for name in wanted if name not in present]
    return have, missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tactics", type=Path, default=DEFAULT_TACTICS)
    arguments = parser.parse_args(argv)

    skinned = arguments.tactics / SKINNED
    figures = arguments.tactics / FIGURES
    if not skinned.is_file():
        print(f"the Tactics checkout is not on this machine: {skinned}")
        return 1

    wanted = required_bones(skinned)
    print(f"{len(wanted)} bones are asked for by {skinned}")
    print()

    assets = sorted(figures.glob("*.glb"))
    if not assets:
        print(f"no figure asset under {figures}")
        return 1

    failed = 0
    for asset in assets:
        have, missing = check(asset, wanted)
        nodes = node_names(asset)
        verdict = "SATISFIES" if not missing else "MISSING"
        print(
            f"{asset.name:16s} {len(nodes):4d} named nodes, "
            f"{len(have)} of {len(wanted)} wanted   {verdict}"
        )
        for name in missing:
            print(f"    missing: {name}")
            failed += 1
    print()
    if failed:
        print(
            "A missing bone is not cosmetic. `applySkinnedPose` turns each named "
            "bone from its bind pose, so a name it cannot find is a limb that "
            "does not move."
        )
        return 1
    print("Every shipped figure carries every bone the app asks of a character.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
