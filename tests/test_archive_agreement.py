"""The guard that says whether this tree still solves what the figures show.

Every two-bodies number compares an engine side solved on this tree against a
rendered side read from an archived receipt. `archive_agreement` refuses when
the two can no longer be one solve. It must REFUSE and not report, because an
instrument that warns and then prints its table has published the numbers.

Each test builds its own archive and its own job directory, so nothing here
depends on the machine holding `.assets/archives`.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "scripts" / "archive_agreement.py"


def _load():
    spec = importlib.util.spec_from_file_location("archive_agreement", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ArchiveAgreementTest(unittest.TestCase):
    def setUp(self):
        self.module = _load()
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.archive = root / "archive"
        self.jobs = root / "jobs"
        self.archive.mkdir()
        self.jobs.mkdir()

    def _write(self, movement_id: str, job_text: str, recorded: str | None = None,
               stamp: str = "2413f9d") -> None:
        """Write one job file and the receipt that claims to have consumed it."""
        job = self.jobs / f"{movement_id}.job.json"
        job.write_text(job_text, encoding="utf-8")
        digest = recorded or hashlib.sha256(job.read_bytes()).hexdigest()
        (self.archive / f"{movement_id}.render.json").write_text(
            json.dumps({"movementId": movement_id, "jobSha256": digest,
                        "generatedFrom": {"commit": stamp}}),
            encoding="utf-8")

    def test_it_passes_when_every_job_matches(self):
        self._write("netball_a", '{"one": 1}')
        self._write("netball_b", '{"two": 2}')
        result = self.module.refuse_if_the_tree_has_moved(self.archive, self.jobs)
        self.assertEqual(result["identical"], ["netball_a", "netball_b"])
        self.assertEqual(result["moved"], [])

    def test_it_refuses_when_a_job_file_changed(self):
        self._write("netball_a", '{"one": 1}')
        (self.jobs / "netball_a.job.json").write_text('{"one": 2}', encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            self.module.refuse_if_the_tree_has_moved(self.archive, self.jobs)
        self.assertIn("netball_a", str(caught.exception))
        self.assertIn("have moved", str(caught.exception))

    def test_it_refuses_when_a_job_file_is_absent(self):
        """An absent job is the same failure with less evidence, not a pass."""
        self._write("netball_a", '{"one": 1}')
        (self.jobs / "netball_a.job.json").unlink()
        with self.assertRaises(SystemExit) as caught:
            self.module.refuse_if_the_tree_has_moved(self.archive, self.jobs)
        self.assertIn("netball_a", str(caught.exception))

    def test_it_refuses_two_build_stamps_in_one_archive(self):
        self._write("netball_a", '{"one": 1}', stamp="2413f9d")
        self._write("netball_b", '{"two": 2}', stamp="aa3f244")
        with self.assertRaises(SystemExit) as caught:
            self.module.refuse_if_the_tree_has_moved(self.archive, self.jobs)
        self.assertIn("build stamps", str(caught.exception))

    def test_it_refuses_an_empty_archive(self):
        with self.assertRaises(SystemExit):
            self.module.refuse_if_the_tree_has_moved(self.archive, self.jobs)

    def test_one_moved_job_among_many_still_refuses(self):
        """The failing case must be BUILT, not hoped for in the data."""
        for index in range(6):
            self._write(f"netball_{index}", json.dumps({"n": index}))
        (self.jobs / "netball_4.job.json").write_text('{"n": 99}', encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            self.module.refuse_if_the_tree_has_moved(self.archive, self.jobs)
        self.assertIn("netball_4", str(caught.exception))
        self.assertNotIn("netball_3", str(caught.exception))

    def test_the_printed_statement_refuses_too(self):
        """`state_the_agreement` must not print a table's warrant it cannot give."""
        self._write("netball_a", '{"one": 1}')
        (self.jobs / "netball_a.job.json").write_text('{"one": 2}', encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.module.state_the_agreement(self.archive, self.jobs)


class WiredIntoEveryInstrumentTest(unittest.TestCase):
    """The guard must be CALLED, not only imported.

    A guard nothing executes is unchecked. This matches on the parsed source, so
    an import left behind after the call was deleted does not pass.
    """

    INSTRUMENTS = ("two_bodies_compare.py", "two_bodies_angles.py",
                   "two_bodies_ready_and_join.py")

    def test_each_two_bodies_instrument_calls_the_guard(self):
        import ast

        for name in self.INSTRUMENTS:
            with self.subTest(instrument=name):
                tree = ast.parse((REPO / "scripts" / name).read_text(encoding="utf-8"))
                called = [node for node in ast.walk(tree)
                          if isinstance(node, ast.Call)
                          and isinstance(node.func, ast.Name)
                          and node.func.id == "state_the_agreement"]
                self.assertTrue(called, f"{name} never calls state_the_agreement")


if __name__ == "__main__":
    unittest.main()
