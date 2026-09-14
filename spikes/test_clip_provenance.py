"""A clip must be able to say which build made it.

Until 2026-09-14 it could not. A clip carried `movementId`, `skill` and
`graded`, and no engine build. The last time anybody asked which build the live
clips came from, the answer had to be reconstructed from a commit message in the
OTHER repository: the shipped `clips.json` was byte-matched to a `braven-tactics`
commit whose message read "Exported fresh from movement main f0172cf".

**A COMMIT MESSAGE IS NOT PROVENANCE.** It is not on the artefact, it does not
survive a copy, and a consumer holding the file cannot read it.

It matters more here than in most places. Comparability is per build: a coach's
marks are scored against the build she graded. A receipt could name its build
and a clip could not, so the two halves of one evidence chain had different
traceability and the half the coach actually looked at was the weaker one.

**WHY THESE TESTS PARSE THE EXPORTER RATHER THAN RUN IT.**
`export_tactics_clip` imports `movement_engine`, which imports `pymomentum`,
which is absent on this machine and on the hosted runner. `build()` also calls
`load_character()` and reads a 4.5 GB asset directory. So the exporter cannot be
imported here at all, and the two facts about it that matter -- that it writes
the field, and that it checks before it writes -- are read off its parsed source.
The guard itself lives in `clip_geometry`, which imports cleanly, and is CALLED
for real below.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

from build_stamp import generated_from
from clip_geometry import refuse_unstamped

EXPORTER = Path(__file__).resolve().parent / "export_tactics_clip.py"
FIELD = "generatedFrom"


def stamped(**changes) -> dict:
    """A clip carrying the shape the exporter writes."""
    stamp = {"commit": "0123456789abcdef", "treeWasClean": True,
             "utcTimestamp": "2026-09-14T07:50:00+00:00", "variant": None}
    stamp.update(changes)
    return {"clipId": "pass.netball.chest-pass", FIELD: stamp}


def clip_dict(tree: ast.Module) -> ast.Dict:
    """The dictionary `build` returns, found by two keys no other dict has."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [k.value for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if "clipId" in keys and "movementId" in keys:
            return node
    raise AssertionError("no clip dictionary found in the exporter")


class TheGuardRefuses(unittest.TestCase):
    """EVERY BRANCH IS BUILT AND FIRED. A refusal nothing reaches is not a
    refusal, and this repository has shipped several of those."""

    def test_it_accepts_a_stamped_clip(self):
        """The positive control. Without it every test below passes if the
        guard simply raises on everything."""
        refuse_unstamped(stamped())

    def test_it_refuses_a_clip_with_no_stamp_at_all(self):
        with self.assertRaises(ValueError) as caught:
            refuse_unstamped({"clipId": "pass.netball.chest-pass"})
        self.assertIn("carries no", str(caught.exception))

    def test_it_refuses_a_stamp_that_is_not_an_object(self):
        """A bare commit string is the shape the proposal in
        `docs/TACTICS_CONTRACT_QUESTIONS.md` first suggested, so it is the one
        somebody is most likely to write."""
        for wrong in ("0123456789abcdef", ["0123456"], None, 7):
            with self.subTest(wrong=wrong):
                with self.assertRaises(ValueError):
                    refuse_unstamped({"clipId": "x", FIELD: wrong})

    def test_it_refuses_a_stamp_with_no_commit(self):
        clip = stamped()
        del clip[FIELD]["commit"]
        with self.assertRaises(ValueError) as caught:
            refuse_unstamped(clip)
        self.assertIn("commit", str(caught.exception))

    def test_it_refuses_a_stamp_that_will_not_say_the_tree_was_clean(self):
        """THE ONE A BARE COMMIT WOULD HAVE MISSED. A clip built from a dirty
        tree names a build that never existed, so the commit alone is not
        enough to reproduce it and the reader has no way to know that."""
        clip = stamped()
        del clip[FIELD]["treeWasClean"]
        with self.assertRaises(ValueError) as caught:
            refuse_unstamped(clip)
        self.assertIn("treeWasClean", str(caught.exception))

    def test_it_refuses_a_null_commit(self):
        """`build_stamp` writes null when git could not be read. A field that
        says nothing still reads as provenance."""
        with self.assertRaises(ValueError):
            refuse_unstamped(stamped(commit=None))

    def test_a_dirty_tree_is_recorded_and_NOT_refused(self):
        """Refusing would stop every lane exporting for most of a working day.
        The stamp carries the fact instead, and the exporter prints it."""
        refuse_unstamped(stamped(treeWasClean=False))


class TheRealStampSatisfiesTheGuard(unittest.TestCase):
    def test_the_repositorys_own_stamp_passes(self):
        """PAIRS THE GUARD WITH ITS PRODUCER. Both sides are built here, and a
        guard written against a shape its producer does not write would pass
        every test above and refuse every real clip."""
        stamp = generated_from()
        refuse_unstamped({"clipId": "x", FIELD: {**stamp, "variant": None}})
        self.assertIsNotNone(stamp["commit"], "git could not be read here")
        self.assertIn("treeWasClean", stamp)


class TheExporterWritesItAndChecksFirst(unittest.TestCase):
    """Matched on the parsed source, because the exporter cannot be imported
    without the solver. A guard on text would pass on a comment."""

    def setUp(self):
        self.tree = ast.parse(EXPORTER.read_text(encoding="utf-8"))

    def test_the_clip_carries_the_field(self):
        keys = [k.value for k in clip_dict(self.tree).keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        self.assertIn(FIELD, keys, "the clip the exporter builds has no stamp")

    def test_the_stamp_is_READ_and_is_not_a_literal(self):
        """A hard-coded commit is the failure this field exists to prevent: it
        would name a build with no relation to the one that ran."""
        node = clip_dict(self.tree)
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == FIELD:
                calls = [
                    sub.func.id for sub in ast.walk(value)
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                ]
                self.assertIn(
                    "generated_from", calls,
                    "the stamp must be READ from `build_stamp.generated_from`, "
                    "never written as a literal or passed in by a caller")
                return
        self.fail(f"{FIELD} is not a key of the clip")

    def test_the_guard_runs_BEFORE_the_file_is_written(self):
        """THE ORDER IS THE POINT, and nothing else here checks it.

        A refusal after the write leaves an unstamped clip on disk and exits
        non-zero, which is the state somebody then ships by hand. Both calls
        are found by their own names and their positions compared, so moving
        the guard below the write turns this red.
        """
        for node in ast.walk(self.tree):
            if not (isinstance(node, ast.FunctionDef) and node.name == "main"):
                continue
            checks, writes = [], []
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                if isinstance(sub.func, ast.Name) and sub.func.id == "refuse_unstamped":
                    checks.append(sub.lineno)
                if isinstance(sub.func, ast.Attribute) and sub.func.attr == "write_text":
                    writes.append(sub.lineno)
            self.assertTrue(checks, "`main` never calls `refuse_unstamped`")
            self.assertTrue(writes, "`main` never writes a clip")
            self.assertLess(
                min(checks), min(writes),
                "the clip is written before it is checked, so an unstamped "
                "clip reaches the disk")
            return
        self.fail("no `main` in the exporter")


if __name__ == "__main__":
    unittest.main()
