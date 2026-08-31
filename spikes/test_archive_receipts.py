"""An archive is refused unless it is one build, and cannot be overwritten.

`build_stamp.py` made a receipt able to say which build produced it. That is
not the same as an archive existing. The set Erin Burger graded survived only
because somebody had copied it aside for an unrelated reason — the live
directory was overwritten four times in one session before anyone asked for it.

So the archiving step is a deliberate action, and these are the refusals that
make it worth running. Each one is a thing that has actually gone wrong.

No solver here either. The whole point of `archive_receipts.py` being stdlib is
that it runs, and is checked, wherever git runs.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from archive_receipts import digest, main, one_set, provenance, receipts, stamps

STAMP = {
    "commit": "a" * 40,
    "treeWasClean": True,
    "utcTimestamp": "2026-08-31T14:10:30+00:00",
}
OTHER = dict(STAMP, commit="b" * 40, utcTimestamp="2026-08-31T15:00:00+00:00")


def write(directory: Path, name: str, stamp: dict | None) -> Path:
    body: dict = {"movementId": name, "coaching": {}}
    if stamp is not None:
        body["generatedFrom"] = stamp
    path = directory / f"netball_{name}.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


class OneSetOrNothing(unittest.TestCase):
    def test_a_matching_set_is_one_set(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            here = Path(where)
            write(here, "a", STAMP)
            write(here, "b", STAMP)
            whole, why = one_set(stamps(here))
            self.assertTrue(whole, why)

    def test_two_builds_in_one_directory_are_refused(self) -> None:
        """The refusal the stamp exists to make possible.

        Before receipts carried a stamp, nothing could tell a half-rebuilt
        directory from a whole one, and a half-rebuilt one would have been
        archived as though it were a build somebody graded.
        """
        with tempfile.TemporaryDirectory() as where:
            here = Path(where)
            write(here, "a", STAMP)
            write(here, "b", OTHER)
            whole, why = one_set(stamps(here))
            self.assertFalse(whole)
            self.assertIn("more than one build", why)
            self.assertIn(STAMP["commit"][:8], why)
            self.assertIn(OTHER["commit"][:8], why)

    def test_an_unstamped_receipt_is_refused_and_named(self) -> None:
        """A receipt from before the stamp cannot say which build made it, and
        a set holding one cannot either. The Erin archive is exactly this
        case, which is why its provenance had to be argued rather than read."""
        with tempfile.TemporaryDirectory() as where:
            here = Path(where)
            write(here, "a", STAMP)
            write(here, "old", None)
            whole, why = one_set(stamps(here))
            self.assertFalse(whole)
            self.assertIn("netball_old.json", why)

    def test_an_empty_directory_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            whole, why = one_set(stamps(Path(where)))
            self.assertFalse(whole)
            self.assertIn("no receipts", why)


class WhatCountsAsAReceipt(unittest.TestCase):
    """Found by running the script on the real library rather than on
    fixtures. `proof.py` writes `{movement}.proof.json` beside the receipts,
    it carries no stamp, and a first version globbed it in and refused every
    real archive."""

    def test_a_proof_file_is_not_a_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            here = Path(where)
            write(here, "a", STAMP)
            (here / "netball_a.proof.json").write_text(
                json.dumps({"movementId": "a", "runs": []}), encoding="utf-8"
            )
            self.assertEqual([p.name for p in receipts(here)],
                             ["netball_a.json"])
            whole, why = one_set(stamps(here))
            self.assertTrue(whole, why)

    def test_but_it_is_still_carried_and_still_hashed(self) -> None:
        """It is part of the directory, so it travels with the set and any
        change to it changes the digest. It simply is not asked for a stamp."""
        with tempfile.TemporaryDirectory() as where:
            here = Path(where)
            write(here, "a", STAMP)
            proof = here / "netball_a.proof.json"
            proof.write_text('{"runs": []}', encoding="utf-8")
            before, per = digest(here)
            self.assertIn("netball_a.proof.json", per)
            proof.write_text('{"runs": [1]}', encoding="utf-8")
            after, _ = digest(here)
            self.assertNotEqual(before, after)


class TheDigest(unittest.TestCase):
    def test_the_provenance_file_is_outside_its_own_digest(self) -> None:
        """So that editing it — a retroactive note, a correction — cannot
        change the digest of the set it describes. The Erin archive was
        retro-stamped after publication and its digest had to survive that."""
        with tempfile.TemporaryDirectory() as where:
            here = Path(where)
            write(here, "a", STAMP)
            before, _ = digest(here)
            (here / "PROVENANCE.md").write_text("anything", encoding="utf-8")
            after, _ = digest(here)
            self.assertEqual(before, after)

    def test_a_rename_changes_the_digest(self) -> None:
        """The name goes into the roll before the content, so moving a
        receipt's bytes to another name is a different set."""
        with tempfile.TemporaryDirectory() as where:
            here = Path(where)
            path = write(here, "a", STAMP)
            before, _ = digest(here)
            path.rename(here / "netball_z.json")
            after, _ = digest(here)
            self.assertNotEqual(before, after)

    def test_a_changed_byte_changes_the_digest(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            here = Path(where)
            path = write(here, "a", STAMP)
            before, _ = digest(here)
            path.write_text(path.read_text(encoding="utf-8") + " ",
                            encoding="utf-8")
            after, _ = digest(here)
            self.assertNotEqual(before, after)


class TheWholeRun(unittest.TestCase):
    def test_it_archives_and_then_refuses_to_do_it_again(self) -> None:
        """An archive a later run can replace is not an archive."""
        with tempfile.TemporaryDirectory() as where:
            source = Path(where) / "library"
            source.mkdir()
            write(source, "a", STAMP)
            write(source, "b", STAMP)
            argv = ["archive_receipts.py", "--label", "test-set",
                    "--source", str(source)]
            self.assertEqual(main(argv), 0)
            destination = source.parent / "library-test-set"
            self.assertTrue((destination / "PROVENANCE.md").is_file())
            self.assertEqual(len(receipts(destination)), 2)
            self.assertEqual(main(argv), 1, "a second run overwrote the first")

    def test_a_mixed_directory_is_never_copied(self) -> None:
        """The refusal must happen BEFORE the copy, or a rejected set still
        lands on disk looking like an archive."""
        with tempfile.TemporaryDirectory() as where:
            source = Path(where) / "library"
            source.mkdir()
            write(source, "a", STAMP)
            write(source, "b", OTHER)
            argv = ["archive_receipts.py", "--label", "mixed",
                    "--source", str(source)]
            self.assertEqual(main(argv), 1)
            self.assertFalse((source.parent / "library-mixed").exists())

    def test_a_missing_source_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            argv = ["archive_receipts.py", "--label", "nothing",
                    "--source", str(Path(where) / "absent")]
            self.assertEqual(main(argv), 1)


class TheProvenanceSaysWhatItKnows(unittest.TestCase):
    def test_a_dirty_build_is_said_so_loudly(self) -> None:
        """A dirty build is archivable — most of a working day produces one —
        but "this commit plus edits nobody wrote down" is what made the first
        archive rest on an argument, so it is never silent."""
        dirty = dict(STAMP, treeWasClean=False,
                     uncommittedDiffSha256="c" * 64,
                     uncommittedPaths=["spikes/x.py"])
        text = provenance("label", dirty, "d" * 64, {"a.json": "e" * 64}, None)
        self.assertIn("The tree was NOT clean", text)
        self.assertIn("spikes/x.py", text)

    def test_a_clean_build_does_not_carry_the_warning(self) -> None:
        text = provenance("label", STAMP, "d" * 64, {"a.json": "e" * 64}, None)
        self.assertNotIn("NOT clean", text)
        self.assertIn(STAMP["commit"], text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
