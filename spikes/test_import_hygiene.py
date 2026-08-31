"""Every test module must LOAD without a solver, whatever it then skips.

THIS EXISTS BECAUSE THE SAME FAULT HAS HAPPENED THREE TIMES, twice to one
author in one day. Continuous integration has no `pymomentum`. A test module
that imports it — directly, or through a module that does, which is the way it
always happens — cannot be loaded there, and unittest reports the whole file as
ONE `_FailedTest` error instead of running any of its cases.

  - `test_receipt_stamp` imported `build_library` for a stamp helper that
    needed nothing but git. Eleven checks became one error.
  - `test_authored_launch` imported `movement_engine.library`, which is a
    directory glob living in a module whose first job is to import the solver.
    Eleven checks became one error.

Both were caught by the hosted runner, after review, after a local suite passed
in the hundreds. The local environment has a solver, so it cannot see this: it
is the two-instrument rule, and the second instrument is a machine without
`pymomentum`.

A MODULE MAY SKIP. Most of the engine tests do, behind the usual
`skipUnless(SOLVER, ...)` guard, and that is correct for a test that genuinely
needs to solve. What no module may do is fail to import. A skip says "not
checked here"; a load error says "eleven checks became one error" while looking
like a single red line.

So this walks every test module and imports it in a subprocess with
`pymomentum` blocked at the import hook. It is the cheapest possible instrument
for a fault that has now cost three review cycles.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent

# Imports the module under an import hook that refuses `pymomentum`, exactly as
# a runner without one behaves. Prints nothing on success; the exit code is the
# whole answer.
PROBE = """
import builtins, sys
real = builtins.__import__


def blocked(name, *arguments, **keywords):
    if name == "pymomentum" or name.startswith("pymomentum."):
        raise ImportError("No module named 'pymomentum'")
    return real(name, *arguments, **keywords)


builtins.__import__ = blocked
sys.path.insert(0, {spikes!r})
import {module}
"""


def test_modules() -> list[str]:
    return sorted(
        path.stem
        for path in SPIKE_DIR.glob("test_*.py")
        if path.stem != Path(__file__).stem
    )


class EveryTestModuleLoadsWithoutASolver(unittest.TestCase):
    def test_the_library_has_test_modules_to_check(self) -> None:
        """Guards the guard. A glob that matches nothing passes everything."""
        found = test_modules()
        self.assertGreater(
            len(found), 10, f"only {len(found)} test modules were found"
        )

    def test_none_of_them_needs_a_solver_to_import(self) -> None:
        for module in test_modules():
            with self.subTest(module=module):
                done = subprocess.run(
                    [sys.executable, "-c",
                     PROBE.format(spikes=str(SPIKE_DIR), module=module)],
                    capture_output=True,
                    text=True,
                    cwd=SPIKE_DIR,
                )
                self.assertEqual(
                    done.returncode,
                    0,
                    f"{module}.py cannot be imported without pymomentum, so on "
                    "a runner without one every test in it becomes a single "
                    "load error rather than running or skipping.\n\n"
                    "Import the solver INSIDE the tests that need it, behind "
                    "the usual `skipUnless(SOLVER, ...)` guard — and check "
                    "what your other imports pull in: both instances of this "
                    "came through a module that merely happened to import the "
                    f"solver at its top.\n\n{done.stderr.strip()[-900:]}",
                )

    def test_the_probe_would_notice(self) -> None:
        """The anti-hollow clause, and it needs to be here.

        If the import hook stopped blocking — a rename upstream, a lazy import
        the hook cannot see — every subtest above would pass while checking
        nothing. So the probe is pointed at `pymomentum` itself, which must
        fail under it.
        """
        done = subprocess.run(
            [sys.executable, "-c",
             PROBE.format(spikes=str(SPIKE_DIR), module="pymomentum")],
            capture_output=True,
            text=True,
            cwd=SPIKE_DIR,
        )
        self.assertNotEqual(
            done.returncode,
            0,
            "the probe imported pymomentum despite the block, so every check "
            "above passed without testing anything",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
