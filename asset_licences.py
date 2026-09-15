"""What a receipt may claim about the assets that drew a figure.

The movement render receipt named its source assets by PATH and never hashed
them, and it recorded no licence at all. The reference generator, building the
same athlete from the same assets, records path AND sha256 for every one of
them. `docs/ARCHITECTURE.md` rule 7 asks for the hashes. Refer to
`docs/FIGURE_AS_IT_IS.md` section 6 for the reading that found it.

Three things follow, and this module holds all three.

**A PATH IS NOT AN IDENTITY.** The recorded paths point into a named user's
Blender profile. If MPFB is updated, the same path names different bytes and no
receipt can tell the two builds apart. This project has already paid a day for
pairing by name, so the record carries the bytes.

**THE LICENCE IS QUOTED, NEVER INVENTED.** `docs/LICENSING.md` makes exactly two
asset licence determinations, and both are transcribed below with the sentence
they come from. A third family, the kit this repository authors under
`assets/kit/`, is recorded as the owner's work with the document's own words
that no licence has been chosen for it. Nothing here decides a licence. An asset
that no family covers has no licence in this repository, and this module says
so rather than guessing.

**AN UNDETERMINED ASSET IS REFUSED.** `docs/LICENSING.md` requires the licence of
every NEWLY selected MPFB asset to be reconfirmed before publication. That
sentence is a rule about people, and until now nothing enforced it. Adding an
asset to the generator without adding its determination here now stops the run,
before a single figure is drawn, rather than producing a receipt that quietly
claims nothing.

There is no Blender in this module, so a test can call it. That is the same
reason `render_receipt.py` and `finger_curl.py` exist.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Callable, Iterable, Sequence

CC0 = "CC0"

# EACH DETERMINATION, QUOTED VERBATIM FROM `docs/LICENSING.md`. A test asserts
# that both strings are still substrings of that document, so a determination
# that is edited or withdrawn there fails here rather than living on in a
# receipt. These are quotes and not summaries for exactly that reason.
FACEUNITS_RULE = (
    "the official MakeHuman Community pack page declares this functional asset "
    "pack CC0"
)
MPFB_RULE = (
    "the current receipt labels the selected MPFB-derived model output as CC0"
)

FACEUNITS_SOURCE = (
    f"docs/LICENSING.md, 'Faceunits 01 expression assets': {FACEUNITS_RULE}. "
    "The pack is licensed, so its target files are matched by rule and are not "
    "listed one by one."
)

MPFB_SOURCE = (
    f"docs/LICENSING.md, 'Generated MPFB character assets': {MPFB_RULE}. "
    "The same bullet requires the licence of every newly selected MPFB asset to "
    "be reconfirmed before publication, which is why the selected assets are "
    "listed by name here instead of a whole directory being licensed at once."
)

# THE ASSETS `create_athlete` SELECTS TODAY, as the three parts it builds each
# path from. A tuple and not a basename: the category is part of the identity,
# and two assets in different categories may not share a determination.
#
# `tests/test_asset_licences.py` reads these three-part calls out of the
# generator's SYNTAX and fails if this set and that set disagree, so the two
# lists cannot drift apart in silence.
SELECTED_MPFB_ASSETS = frozenset(
    {
        ("skins", "young_caucasian_female", "young_caucasian_female.mhmat"),
        ("clothes", "female_casualsuit02", "female_casualsuit02.mhclo"),
        ("clothes", "shoes05", "shoes05.mhclo"),
        ("hair", "ponytail01", "ponytail01.mhclo"),
        ("eyes", "high-poly", "high-poly.mhclo"),
        ("eyebrows", "eyebrow006", "eyebrow006.mhclo"),
        ("eyelashes", "eyelashes01", "eyelashes01.mhclo"),
    }
)

# The manifest of the licensed pack, by its last two parts.
FACEUNITS_MANIFEST = ("packs", "faceunits01.json")

# Every target file of that pack lives under these two segments.
FACEUNITS_TARGETS = ("targets", "faceunits")

# THE REPOSITORY'S OWN KIT. The config loader refuses a kit path anywhere but
# under `assets/kit/`, so that directory pair is the whole family. What the
# receipt records for these is OWNERSHIP and not a licence: the document says
# no redistribution licence has been chosen, and this module quotes it rather
# than choosing one.
KIT_ASSETS = ("assets", "kit")
OWN_WORK = "Braven Performance Lab (own work, no licence selected)"
KIT_RULE = (
    "They are the work of Braven Performance Lab and no redistribution licence "
    "has been selected for them yet, as for the source code."
)
KIT_SOURCE = (
    f"docs/LICENSING.md, 'Kit assets authored in this repository': {KIT_RULE} "
    "The licence word is the repository owner's to set; until then the receipt "
    "records who made the asset and not the terms it is offered under."
)


class LicenceUndetermined(Exception):
    """An asset this repository has not licensed reached a receipt."""


def _parts(path: object) -> tuple[str, ...]:
    """The path's segments, from a Windows path or a POSIX one.

    A receipt written on Windows is read on the hosted runner, which is a
    different machine with a different separator. Splitting on both is the
    difference between this working there and only working here.
    """
    text = str(path).replace("\\", "/")
    return tuple(part for part in text.split("/") if part not in ("", "."))


def licence_for(path: object) -> tuple[str, str]:
    """The licence of one asset, and the sentence it is quoted from.

    Raises `LicenceUndetermined` when neither determination covers the asset.
    The pack rule is tried first, because a target file's own three parts are
    not in the selected table and never will be.
    """
    parts = _parts(path)
    lowered = tuple(part.lower() for part in parts)

    for index in range(len(lowered) - 1):
        if lowered[index : index + 2] == FACEUNITS_TARGETS:
            return CC0, FACEUNITS_SOURCE
    if lowered[-2:] == FACEUNITS_MANIFEST:
        return CC0, FACEUNITS_SOURCE

    for index in range(len(lowered) - 1):
        if lowered[index : index + 2] == KIT_ASSETS:
            return OWN_WORK, KIT_SOURCE

    if lowered[-3:] in SELECTED_MPFB_ASSETS:
        return CC0, MPFB_SOURCE

    raise LicenceUndetermined(
        f"no licence is recorded for {parts[-1] if parts else path!r}: "
        f"{path}. docs/LICENSING.md requires the licence of every newly "
        f"selected MPFB asset to be reconfirmed before publication. Add the "
        f"determination to asset_licences.SELECTED_MPFB_ASSETS after reading "
        f"the asset's own licence, and never before. "
        # THE ADVICE ABOVE SENDS A PERSON TO THE WRONG TABLE when the file is
        # one THIS REPOSITORY made. A painted kit texture reached this refusal
        # on 2026-09-10 and the message told its author to add it to a table
        # keyed by an MPFB category, folder and file. The third family is the
        # answer for such a file, and the message says so.
        f"IF THIS FILE IS ONE THIS REPOSITORY GENERATED, that table is the "
        f"wrong place: it is keyed by an MPFB category, folder and file. Put "
        f"the file under assets/kit/ and it is recorded as own work; refer to "
        f"the third family, 'Kit assets authored in this repository', in "
        f"docs/LICENSING.md. That bullet records that no licence has been "
        f"chosen for the repository's own files, as for its source code, "
        f"which is a decision for the repository owner."
    )


def source_asset_record(path: object, sha256: Callable[[Path], str]) -> dict:
    """One asset, with its bytes and its licence.

    THE LICENCE IS RESOLVED BEFORE THE FILE IS READ. Hashing an asset this
    repository has not licensed wastes nothing, but it does put the bytes of an
    unlicensed file into memory on the way to refusing them, and the order here
    says which check is the gate.
    """
    licence, source = licence_for(path)
    return {
        "path": str(path),
        "sha256": sha256(Path(path)),
        "licence": licence,
        "licenceSource": source,
    }


def source_asset_records(
    paths: Iterable[object], sha256: Callable[[Path], str]
) -> list[dict]:
    """Every asset, in the order given, or nothing at all.

    ONE UNDETERMINED ASSET REFUSES THE WHOLE LIST. A receipt that carried the
    licensed assets and quietly dropped the rest would be worse than no receipt,
    because it would read as complete.
    """
    return [source_asset_record(path, sha256) for path in paths]


def asset_path_calls(module_path: Path) -> frozenset[tuple[str, ...]]:
    """Every `asset_path(...)` call in a module, read from its syntax.

    Read from the SYNTAX and not from the text. A guard that matched on source
    text would pass on a file that had been reformatted and would fail on a
    comment, and this repository has already shipped four guards that guarded
    nothing for that reason.

    A call with an argument that is not a string literal raises, because such a
    call selects an asset this module cannot name, and a guard that silently
    dropped it would be a guard in name only.
    """
    tree = ast.parse(Path(module_path).read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "asset_path":
            continue
        parts = []
        for argument in node.args:
            if not isinstance(argument, ast.Constant) or not isinstance(
                argument.value, str
            ):
                raise LicenceUndetermined(
                    f"{Path(module_path).name} line {node.lineno} builds an asset "
                    f"path from something this module cannot read as a name, so "
                    f"the asset it selects cannot be licensed here."
                )
            parts.append(argument.value)
        found.add(tuple(parts))
    return frozenset(found)


def undetermined(paths: Sequence[object]) -> list[str]:
    """The assets with no determination, named rather than counted.

    For a caller that wants to report every one of them instead of stopping at
    the first. Nothing in the render path uses this yet; it exists so that a
    person adding four assets is told about four.
    """
    missing = []
    for path in paths:
        try:
            licence_for(path)
        except LicenceUndetermined:
            missing.append(str(path))
    return missing
