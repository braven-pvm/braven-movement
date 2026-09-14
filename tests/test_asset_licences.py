"""What a render receipt may claim about the assets that drew it.

The receipt behind every coach figure named its source assets by PATH and
never hashed them, and it recorded no licence at all. Refer to
`docs/FIGURE_AS_IT_IS.md` section 6.

These tests hold three things: the licence of an asset comes from
`docs/LICENSING.md` and is never invented, an asset with no determination is
REFUSED rather than written, and the table of selected assets cannot drift away
from the generator that selects them.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from asset_licences import (  # noqa: E402
    CC0,
    FACEUNITS_RULE,
    KIT_RULE,
    MPFB_RULE,
    OWN_WORK,
    LicenceUndetermined,
    SELECTED_MPFB_ASSETS,
    asset_path_calls,
    licence_for,
    source_asset_records,
)

GENERATOR = MODULE_DIR / "blender_mpfb_reference_catch.py"
LICENSING = MODULE_DIR / "docs" / "LICENSING.md"

# The archived receipts of the build a coach actually graded. Outside git, so a
# machine without it skips the one test that uses it, and only that one.
ARCHIVE = Path("F:/Repositories/braven-movement/.assets/archives/coach-figures-2413f9d")

# A stand-in for the repository's own hasher. Production passes the one
# `blender_movement_render.py` already imports; nothing here defines a second
# hashing implementation for the renderer to use.
def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TheLicenceComesFromTheDocument(unittest.TestCase):
    def test_every_selected_asset_resolves_to_cc0(self):
        for parts in SELECTED_MPFB_ASSETS:
            with self.subTest(asset="/".join(parts)):
                licence, source = licence_for(Path("mpfb", "data", *parts))
                self.assertEqual(licence, CC0)
                self.assertIn("docs/LICENSING.md", source)

    def test_a_face_target_resolves_by_rule_and_not_by_name(self):
        # There are dozens of these and the document licenses the PACK, so the
        # table must not list them one by one.
        licence, source = licence_for(
            Path("mpfb", "data", "targets", "faceunits", "browDownLeft.target")
        )
        self.assertEqual(licence, CC0)
        self.assertIn(FACEUNITS_RULE, source)

    def test_the_faceunits_manifest_resolves(self):
        licence, _ = licence_for(Path("mpfb", "data", "packs", "faceunits01.json"))
        self.assertEqual(licence, CC0)

    def test_the_two_families_are_told_apart(self):
        _, suit = licence_for(
            Path("clothes", "female_casualsuit02", "female_casualsuit02.mhclo")
        )
        _, target = licence_for(Path("targets", "faceunits", "mouthClose.target"))
        self.assertNotEqual(suit, target)

    def test_both_determinations_are_quoted_verbatim_from_the_document(self):
        # THE POINT OF THIS TEST. "Never invented" is a claim about where the
        # licence came from, and a claim needs an instrument. If a determination
        # is edited or withdrawn in the document, the module is quoting a
        # sentence that no longer exists and this fails.
        # The document wraps its sentences, so the comparison is on words and
        # not on line breaks. Collapsing whitespace is the only licence this
        # test takes; every word must still be there, in order.
        text = " ".join(LICENSING.read_text(encoding="utf-8").split())
        self.assertIn(" ".join(FACEUNITS_RULE.split()), text)
        self.assertIn(" ".join(MPFB_RULE.split()), text)

    def test_the_document_still_requires_reconfirmation(self):
        # The refusal exists to enforce this sentence. If the sentence goes, the
        # refusal is enforcing nothing and someone must decide what replaces it.
        text = LICENSING.read_text(encoding="utf-8")
        self.assertIn("Reconfirm the licence of every newly selected MPFB asset", text)


class AnUndeterminedAssetIsRefused(unittest.TestCase):
    def test_an_asset_outside_both_families_raises(self):
        with self.assertRaises(LicenceUndetermined):
            licence_for(Path("clothes", "team_bib_01", "team_bib_01.mhclo"))

    def test_the_refusal_names_the_asset_and_the_rule(self):
        with self.assertRaises(LicenceUndetermined) as caught:
            licence_for(Path("clothes", "team_bib_01", "team_bib_01.mhclo"))
        message = str(caught.exception)
        self.assertIn("team_bib_01.mhclo", message)
        self.assertIn("docs/LICENSING.md", message)

    def test_a_suit_under_the_wrong_category_is_not_accepted(self):
        # The table is the three parts the generator builds, not a basename.
        with self.assertRaises(LicenceUndetermined):
            licence_for(Path("hair", "female_casualsuit02", "female_casualsuit02.mhclo"))

    def test_a_record_refuses_before_it_hashes(self):
        with tempfile.TemporaryDirectory() as raw:
            unknown = Path(raw) / "clothes" / "team_bib_01" / "team_bib_01.mhclo"
            unknown.parent.mkdir(parents=True)
            unknown.write_bytes(b"a bib nobody has licensed")
            with self.assertRaises(LicenceUndetermined):
                source_asset_records([unknown], _sha256)

    def test_one_undetermined_asset_refuses_the_whole_list(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            good = root / "hair" / "ponytail01" / "ponytail01.mhclo"
            bad = root / "clothes" / "team_bib_01" / "team_bib_01.mhclo"
            for path in (good, bad):
                path.parent.mkdir(parents=True)
                path.write_bytes(b"x")
            with self.assertRaises(LicenceUndetermined):
                source_asset_records([good, bad], _sha256)


class TheRecordCarriesTheBytes(unittest.TestCase):
    def test_a_record_carries_path_sha256_and_licence(self):
        with tempfile.TemporaryDirectory() as raw:
            asset = Path(raw) / "hair" / "ponytail01" / "ponytail01.mhclo"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"a ponytail")
            [record] = source_asset_records([asset], _sha256)
        self.assertEqual(record["path"], str(asset))
        self.assertEqual(
            record["sha256"],
            hashlib.sha256(b"a ponytail").hexdigest(),
        )
        self.assertEqual(record["licence"], CC0)
        self.assertIn("docs/LICENSING.md", record["licenceSource"])

    def test_the_hash_follows_the_bytes_and_not_the_name(self):
        # A name is not a correspondence. Two assets at the same path with
        # different bytes must not produce the same record.
        with tempfile.TemporaryDirectory() as raw:
            asset = Path(raw) / "hair" / "ponytail01" / "ponytail01.mhclo"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"one")
            [first] = source_asset_records([asset], _sha256)
            asset.write_bytes(b"two")
            [second] = source_asset_records([asset], _sha256)
        self.assertEqual(first["path"], second["path"])
        self.assertNotEqual(first["sha256"], second["sha256"])

    def test_the_records_keep_the_order_they_were_given(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first = root / "hair" / "ponytail01" / "ponytail01.mhclo"
            second = root / "eyes" / "high-poly" / "high-poly.mhclo"
            for path in (first, second):
                path.parent.mkdir(parents=True)
                path.write_bytes(b"x")
            records = source_asset_records([first, second], _sha256)
        self.assertEqual([item["path"] for item in records], [str(first), str(second)])


class TheTableCannotDriftFromTheGenerator(unittest.TestCase):
    """`create_athlete` selects the assets. This table licenses them.

    Two lists of the same thing drift. The generator's calls are read from its
    SYNTAX rather than from its text, so a rename or a reformat cannot fool it
    and only a real change to the selection can.
    """

    def test_the_generator_selects_exactly_the_licensed_assets(self):
        self.assertEqual(asset_path_calls(GENERATOR), SELECTED_MPFB_ASSETS)

    def test_the_guard_sees_an_asset_added_to_the_generator(self):
        # THE GUARD IS PROVED FAILING, on a copy, so the working tree does not
        # move under any run.
        with tempfile.TemporaryDirectory() as raw:
            mutated = Path(raw) / "mutated_generator.py"
            shutil.copyfile(GENERATOR, mutated)
            source = mutated.read_text(encoding="utf-8")
            source = source.replace(
                '    hair = asset_path("hair", "ponytail01", "ponytail01.mhclo")',
                '    hair = asset_path("hair", "ponytail01", "ponytail01.mhclo")\n'
                '    bib = asset_path("clothes", "team_bib_01", "team_bib_01.mhclo")',
                1,
            )
            mutated.write_text(source, encoding="utf-8")
            found = asset_path_calls(mutated)
        self.assertIn(("clothes", "team_bib_01", "team_bib_01.mhclo"), found)
        self.assertNotEqual(found, SELECTED_MPFB_ASSETS)

    def test_the_guard_sees_an_asset_removed_from_the_generator(self):
        with tempfile.TemporaryDirectory() as raw:
            mutated = Path(raw) / "mutated_generator.py"
            shutil.copyfile(GENERATOR, mutated)
            source = mutated.read_text(encoding="utf-8")
            source = source.replace(
                '    hair = asset_path("hair", "ponytail01", "ponytail01.mhclo")',
                "    hair = None",
                1,
            )
            mutated.write_text(source, encoding="utf-8")
            found = asset_path_calls(mutated)
        self.assertNotIn(("hair", "ponytail01", "ponytail01.mhclo"), found)
        self.assertNotEqual(found, SELECTED_MPFB_ASSETS)

    def test_the_mutations_actually_changed_the_copy(self):
        # A replace() that matches nothing rewrites nothing, and the two tests
        # above would then be asserting about an unmodified file.
        source = GENERATOR.read_text(encoding="utf-8")
        self.assertIn(
            '    hair = asset_path("hair", "ponytail01", "ponytail01.mhclo")',
            source,
        )


class TheGradedBuildResolves(unittest.TestCase):
    """Every asset the graded library actually used has a determination.

    This is the one test that reads outside git. It is the only test in this
    file that can skip, and it skips on the ARCHIVE and on nothing else.
    """

    def test_every_asset_in_the_2413f9d_receipts_resolves(self):
        receipts = sorted(ARCHIVE.glob("*.render.json")) if ARCHIVE.is_dir() else []
        if not receipts:
            self.skipTest(f"the graded archive is not on this machine: {ARCHIVE}")
        seen = set()
        for path in receipts:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for asset in payload["sourceAssets"]:
                # The archived receipts carry the OLD shape, a bare string.
                seen.add(asset if isinstance(asset, str) else asset["path"])
        self.assertTrue(seen, "the receipts carried no source assets at all")
        for asset in sorted(seen):
            with self.subTest(asset=asset):
                licence, _ = licence_for(asset)
                self.assertEqual(licence, CC0)


class TheRendererWritesTheNewShape(unittest.TestCase):
    """The renderer imports bpy, so its own tests skip. This reads its syntax.

    `sourceAssets` had exactly one writer and no readers when this changed, so
    widening its shape broke nothing. That was checked, not assumed.
    """

    RENDERER = MODULE_DIR / "blender_movement_render.py"

    def _source_assets_value(self) -> ast.expr:
        """The expression the receipt assigns to `sourceAssets`, from the syntax."""
        tree = ast.parse(self.RENDERER.read_text(encoding="utf-8"))
        found = [
            value
            for node in ast.walk(tree)
            if isinstance(node, ast.Dict)
            for key, value in zip(node.keys, node.values)
            if isinstance(key, ast.Constant) and key.value == "sourceAssets"
        ]
        self.assertEqual(len(found), 1, "there must be exactly one writer")
        return found[0]

    def test_the_receipt_writes_the_licensed_records_and_not_the_raw_assets(self):
        # PIN THE VALUE, NOT THE CALL. An earlier version of this test asserted
        # only that `source_asset_records` was called SOMEWHERE in the module.
        # It still passed with the old bare-path list back in the receipt,
        # because the call in `Studio.__init__` satisfied it. A guard that
        # cannot fail on the change it exists to catch is a guard in name only.
        value = self._source_assets_value()
        self.assertIsInstance(value, ast.Attribute)
        self.assertEqual(value.attr, "source_asset_records")
        self.assertIsInstance(value.value, ast.Name)
        self.assertEqual(value.value.id, "studio")

    def test_the_licence_check_runs_before_any_figure_is_drawn(self):
        # The refusal is worth nothing at the receipt: half an hour of
        # rendering would already be spent. It belongs in `Studio.__init__`.
        tree = ast.parse(self.RENDERER.read_text(encoding="utf-8"))
        studio = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "Studio"
        )
        called = {
            node.func.id
            for node in ast.walk(studio)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("source_asset_records", called)

    def test_nothing_else_writes_a_bare_path_list(self):
        source = self.RENDERER.read_text(encoding="utf-8")
        self.assertNotIn("[str(path) for path in studio.source_assets]", source)


if __name__ == "__main__":
    unittest.main()


class TheRepositoryOwnsItsKit(unittest.TestCase):
    """The third family: assets this repository authors under `assets/kit/`.

    The receipt records ownership, not a licence, because the document says
    no licence has been chosen for them. The word is the owner's to set, and
    when it is set, the sentence here and the sentence there change together
    or the verbatim test fails.
    """

    def test_a_kit_asset_resolves_to_the_owners_work(self):
        licence, source = licence_for(Path("assets", "kit", "braven_netball_dress.mhclo"))
        self.assertEqual(licence, OWN_WORK)
        self.assertIn("docs/LICENSING.md", source)
        self.assertIn("Kit assets authored in this repository", source)

    def test_the_family_is_the_directory_pair_on_either_separator(self):
        windows = "\\".join(
            ("F:", "Repositories", "braven-movement", "assets", "kit", "bib_GS.png")
        )
        for path in (
            "F:/Repositories/braven-movement/assets/kit/bib_GS.png",
            windows,
            "assets/kit/deeper/some_sock.mhclo",
        ):
            with self.subTest(path=path):
                self.assertEqual(licence_for(path)[0], OWN_WORK)

    def test_a_neighbouring_directory_is_not_the_family(self):
        for path in (
            Path("assets", "kits", "braven_netball_dress.mhclo"),
            Path("kit", "braven_netball_dress.mhclo"),
            Path("assets", "braven_netball_dress.mhclo"),
        ):
            with self.subTest(path=str(path)):
                with self.assertRaises(LicenceUndetermined):
                    licence_for(path)

    def test_the_kit_sentence_is_quoted_verbatim_from_the_document(self):
        text = " ".join(LICENSING.read_text(encoding="utf-8").split())
        self.assertIn(" ".join(KIT_RULE.split()), text)

    def test_the_owners_line_is_not_a_licence_word(self):
        # The receipt must not claim CC0 for something the document says has
        # no licence yet.
        self.assertNotEqual(OWN_WORK, CC0)
        self.assertNotIn("CC0", OWN_WORK)

