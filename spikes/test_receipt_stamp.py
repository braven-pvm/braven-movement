"""A receipt says which build produced it.

Principle P1, ruled 2026-08-30: comparability is per-build. A coach's marks are
scored against the receipts of the build that coach actually graded, and the
live engine improves freely without invalidating them.

That only works if a receipt can name its build. On 2026-08-31 the set Erin
Burger graded had to be identified by ARGUMENT — the value she marked, plus a
reading of the commit history showing the solver had not moved between her
review and the copy — because a receipt recorded nothing at all about its
origin. The stamp exists so the next archive rests on the file instead.

This file does not need a solver. The stamp is metadata, and testing it by
solving eight drills would make a slow test out of a fast question.

IT MUST ALSO IMPORT WITHOUT ONE. The stamp began inside `build_library.py`,
which imports `pymomentum` at module level. The hosted runner has none, so this
file could not LOAD there and eleven working guards became a single import
error. `build_stamp.py` exists so that cannot happen again, and the last test
below is what holds it that way.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from build_stamp import generated_from, git_output, uncommitted_paths

SPIKE_DIR = Path(__file__).resolve().parent


class TheStampNamesItsBuild(unittest.TestCase):
    def test_it_carries_the_three_fields_the_shape_promises(self) -> None:
        """The same shape `export_reference_curves.py` writes. A second shape
        for the same idea is a second thing to keep in step."""
        stamp = generated_from()
        self.assertIn("commit", stamp)
        self.assertIn("treeWasClean", stamp)
        self.assertIn("utcTimestamp", stamp)
        self.assertIsInstance(stamp["treeWasClean"], bool)
        self.assertRegex(str(stamp["commit"]), r"^[0-9a-f]{40}$")
        self.assertRegex(
            stamp["utcTimestamp"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        )

    def test_the_commit_is_the_one_git_reports(self) -> None:
        """Measured against git rather than against the same call that wrote
        it, so this cannot pass by agreeing with itself."""
        expected = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=SPIKE_DIR,
        ).stdout.strip()
        self.assertEqual(generated_from()["commit"], expected)

    def test_the_clean_flag_is_the_one_git_reports(self) -> None:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=SPIKE_DIR,
        ).stdout.strip()
        self.assertEqual(generated_from()["treeWasClean"], not dirty)

    def test_one_run_stamps_one_set(self) -> None:
        """The cache is the point, not an optimisation.

        Every receipt written by one run must carry the SAME stamp, or a
        directory half rebuilt from two builds would look like one set. That is
        exactly the mistake the archive above was nearly made by.
        """
        first, second = generated_from(), generated_from()
        self.assertIs(first, second)
        self.assertEqual(first["utcTimestamp"], second["utcTimestamp"])


class ThePorcelainParse(unittest.TestCase):
    """The parse had a real defect, and these are the samples that caught it.

    `git status --porcelain` puts the status in the first two columns, so a
    file modified in the worktree reads " M path" with a LEADING space. An
    earlier version stripped the whole output before splitting, which ate that
    space on the first line only and cost that path its first character:
    "pikes/build_library.py". One entry wrong, quietly, and only ever the first
    one, so a spot check of a later entry would have said it worked.
    """

    def test_a_worktree_modification_keeps_its_first_character(self) -> None:
        self.assertEqual(
            uncommitted_paths(" M spikes/build_library.py"),
            ["spikes/build_library.py"],
        )

    def test_the_first_line_is_not_special(self) -> None:
        """The defect only ever touched the first line, so a sample with one
        line before the interesting one would have passed while broken."""
        self.assertEqual(
            uncommitted_paths(" M spikes/one.py\n M spikes/two.py"),
            ["spikes/one.py", "spikes/two.py"],
        )

    def test_the_staged_and_untracked_forms_parse_too(self) -> None:
        self.assertEqual(
            uncommitted_paths("M  spikes/staged.py\n?? spikes/new.py\nA  x.py"),
            ["spikes/new.py", "spikes/staged.py", "x.py"],
        )

    def test_a_rename_is_left_whole(self) -> None:
        """Reported with its arrow rather than split. A stamp that silently
        reported half a rename would be worse than one that reports both."""
        self.assertEqual(
            uncommitted_paths("R  spikes/old.py -> spikes/new.py"),
            ["spikes/old.py -> spikes/new.py"],
        )

    def test_nothing_is_nothing(self) -> None:
        self.assertEqual(uncommitted_paths(""), [])


class GitOutputKeepsLeadingWhitespace(unittest.TestCase):
    """The guard on the helper itself, rather than on the parse downstream.

    `uncommitted_paths` can be correct and the stamp still wrong, if what
    reaches it has already lost the leading space. This asserts the property
    that made the defect possible, on a command whose output is known.
    """

    def test_a_leading_space_survives(self) -> None:
        # `git status --porcelain` on a clean tree returns nothing, so the
        # property is asserted against a command that always produces a
        # leading space regardless of the state of the worktree.
        got = git_output("show", "-s", "--format=%x20%H", "HEAD")
        self.assertTrue(
            got.startswith(" "),
            f"git_output stripped a leading space: {got!r}. `git status "
            "--porcelain` puts a leading space on every worktree-modified "
            "line, and losing it costs that path its first character.",
        )

    def test_the_trailing_newline_is_still_removed(self) -> None:
        self.assertFalse(git_output("rev-parse", "HEAD").endswith("\n"))


class TheStampModuleNeedsNoSolver(unittest.TestCase):
    """The guard on the reason `build_stamp.py` is a separate module.

    Continuous integration has no `pymomentum`. When the stamp lived in
    `build_library.py`, importing it here raised and every check in this file
    was reported as one error rather than run. Skipping instead would have been
    worse: a green run saying nothing was checked.
    """

    def test_importing_the_stamp_does_not_pull_in_the_solver(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import build_stamp; "
                "print(any('pymomentum' in m for m in sys.modules))",
            ],
            capture_output=True,
            text=True,
            cwd=SPIKE_DIR,
        )
        self.assertEqual(
            result.returncode, 0, f"build_stamp did not import: {result.stderr}"
        )
        self.assertEqual(
            result.stdout.strip(),
            "False",
            "importing build_stamp pulled in pymomentum, so this file will "
            "fail to load on any runner without a solver, exactly as it did on "
            "2026-08-31",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
