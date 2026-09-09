"""Every tracked Python file parses on the interpreter that is running.

WHAT THIS CANNOT SEE, and it must be read before a green result is trusted. It
proves that a file is SYNTACTICALLY VALID on the running interpreter, and it
proves nothing else. A file that parses on 3.11 can still die on 3.11: a
standard-library call that moved, a default that changed, a function that was
removed. **A green walk is not version compatibility.**

WHY IT WALKS RATHER THAN IMPORTS. CI catches a syntax error only where
something imports the file. On 2026-09-09 four video modules were imported by
no test at all, so nothing on the runner ever parsed them. Parsing needs no
imports, no assets and no environment, so it covers a file whether anything
reaches it or not.

WHY THE WHOLE TREE AND NOT ONE DIRECTORY. The development environment pins
Python 3.12 and the hosted runner pins 3.11, so a construct added in 3.12 is
invisible here and fatal there. That split belongs to the repository and not to
a directory: the walk finds 172 tracked files, of which 132 are under `spikes/`.
A guard scoped to one directory teaches the next reader that the others are
covered.

THE FAULT THAT PRODUCED THIS. `spikes/video_sync.py:256` held
`f"peak {measure_entry["peak"]:.4f}"`, nested double quotes inside an f-string,
which is PEP 701 and arrived in 3.12. Its three neighbouring lines already used
single quotes. It parsed for every lane and could not be parsed by CI, and
nothing noticed because no test imports that module. **This guard was run on
3.11 and reported that file BEFORE the fix went in**, which is the only moment
that evidence could be collected.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Invalid under every version of Python, so the checker's own case does not
# depend on the interpreter running it.
ALWAYS_INVALID = "def f(:\n    pass\n"

# Valid from 3.12 and a SyntaxError before it: nested double quotes inside an
# f-string. This is the exact class that produced the guard.
NESTED_QUOTES = 'x = {"k": 1}\ny = f"{x["k"]}"\n'


def tracked_python_files() -> list[Path]:
    """Every `.py` file git tracks, so an untracked scratch file cannot fail
    the suite and a tracked one cannot escape it."""
    listed = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / name for name in listed.stdout.split()]


def parse_failure(source: str, name: str) -> str | None:
    """The message and line if this source does not parse here, else None."""
    try:
        ast.parse(source, filename=name)
    except SyntaxError as refusal:
        return f"{name}:{refusal.lineno}: {refusal.msg}"
    return None


class TheCheckerCanFail(unittest.TestCase):
    """A guard whose failing case must be FOUND in the tree guards nothing.
    After the fix every tracked file parses, so these build the case instead."""

    def test_the_checker_reports_source_no_python_accepts(self):
        found = parse_failure(ALWAYS_INVALID, "built.py")

        self.assertIsNotNone(found)
        self.assertIn("built.py:1", found)

    def test_the_checker_accepts_source_every_python_accepts(self):
        self.assertIsNone(parse_failure("x = 1\n", "built.py"))

    def test_the_checker_sees_THE_CLASS_that_produced_this_guard(self):
        """Version-aware on purpose. Nested quotes in an f-string are a
        SyntaxError before 3.12 and valid from 3.12, so this asserts that the
        checker follows the interpreter rather than a rule of its own."""
        found = parse_failure(NESTED_QUOTES, "built.py")

        if sys.version_info >= (3, 12):
            self.assertIsNone(found)
        else:
            self.assertIsNotNone(
                found, "this interpreter should refuse PEP 701 syntax")
            self.assertIn("built.py:2", found)


class EveryTrackedFileParses(unittest.TestCase):

    def test_the_walk_reaches_the_whole_tree(self):
        """A walk of one directory would teach a reader that the others are
        covered. This asserts it is wider than the directory that produced it."""
        files = tracked_python_files()
        outside = [p for p in files if "spikes" not in p.parts]

        self.assertGreater(len(files), 100)
        self.assertGreater(len(outside), 10)

    def test_every_tracked_python_file_parses_here(self):
        failures = []
        for path in tracked_python_files():
            found = parse_failure(
                path.read_text(encoding="utf-8"),
                str(path.relative_to(ROOT)).replace("\\", "/"))
            if found:
                failures.append(found)

        self.assertEqual(failures, [], "\n".join(
            ["these files do not parse on Python "
             f"{sys.version.split()[0]}:"] + failures))


if __name__ == "__main__":
    unittest.main()
