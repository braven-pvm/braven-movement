"""A job records what its pose was solved with, or it does not leave.

WHY THE FIELD EXISTS. The rendering lane refuses to call two pictures a pair
five ways, and one of them is that **every other parameter must be equal** —
because a pair whose second parameter also moved shows a difference the caption
attributes to the first. It cannot check that against a job that does not say.

WHY THIS GUARD EXISTS SEPARATELY. **The failure is invisible in the artefact.**
A job solved with an override and recording the default looks exactly like a
job solved with the default: same shape, same fields, same everything a reader
can see. Two such jobs would be handed over as a pair differing in one
parameter while differing in none, and a coach would be shown a caption that is
false about the only thing the picture is for.

**THE FAILING CASE IS CONSTRUCTED AND NOT FOUND.** No technique file in the
library sets `elbowAngleDegrees` today -- 0 of 12 -- so the tree supplies no
job with an override at all, and a guard that waited to meet one would never
fire. Every case below is built here.

No solve runs. `check_solve_parameters` takes a job dictionary and a technique,
so both are made by hand.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

from contact_solve import ELBOW_POLE_ANGLE_DEGREES
from export_blender_job import check_solve_parameters, solve_parameters

# The value a coach is being ASKED to move to. It is not in any file and
# nothing in the library uses it; it is here because this guard's whole job is
# the case the library cannot supply.
A_CANDIDATE = 37.3


def technique(angle: float | None) -> SimpleNamespace:
    """The one field of a technique this checker reads."""
    return SimpleNamespace(elbow_angle_degrees=angle)


def job_for(method) -> dict:
    return {"movementId": "probe", "solveParameters": solve_parameters(method)}


class TheMappingRecordsWhatTheSolveUsed(unittest.TestCase):
    def test_no_override_records_the_engines_default(self) -> None:
        """A technique naming nothing solved on the default, and says so.

        Recording NOTHING would make this job and a job with no mapping the
        same artefact.
        """
        recorded = solve_parameters(technique(None))
        self.assertEqual(
            recorded["ELBOW_POLE_ANGLE_DEGREES"], float(ELBOW_POLE_ANGLE_DEGREES)
        )

    def test_an_override_records_the_override(self) -> None:
        recorded = solve_parameters(technique(A_CANDIDATE))
        self.assertEqual(recorded["ELBOW_POLE_ANGLE_DEGREES"], A_CANDIDATE)

    def test_the_two_differ_or_this_guards_nothing(self) -> None:
        """Guards the guard.

        If the candidate ever equalled the default, every test in this file
        would pass on a checker that ignored the technique entirely.
        """
        self.assertNotEqual(float(ELBOW_POLE_ANGLE_DEGREES), A_CANDIDATE)


class TheCheckerRefusesAJobThatDoesNotSay(unittest.TestCase):
    """Every case here is CONSTRUCTED. The library cannot produce one."""

    def test_a_job_with_no_mapping_at_all(self) -> None:
        with self.assertRaises(ValueError) as caught:
            check_solve_parameters({"movementId": "probe"}, technique(None))
        self.assertIn("records no solveParameters", str(caught.exception))

    def test_a_mapping_that_is_not_a_mapping(self) -> None:
        with self.assertRaises(ValueError):
            check_solve_parameters(
                {"solveParameters": ["ELBOW_POLE_ANGLE_DEGREES"]}, technique(None)
            )

    def test_a_mapping_missing_the_parameter_the_solve_used(self) -> None:
        with self.assertRaises(ValueError) as caught:
            check_solve_parameters({"solveParameters": {}}, technique(A_CANDIDATE))
        self.assertIn("ELBOW_POLE_ANGLE_DEGREES", str(caught.exception))

    def test_AN_OVERRIDE_RECORDED_AS_THE_DEFAULT(self) -> None:
        """THE CASE THIS GUARD EXISTS FOR, and the one nothing else can see.

        The solve used the candidate. The job says the default. Nothing in the
        artefact distinguishes it from a job that honestly solved on the
        default, and a pair built from it would carry a caption claiming a
        difference that is not there.
        """
        pretending = {
            "solveParameters": {
                "ELBOW_POLE_ANGLE_DEGREES": float(ELBOW_POLE_ANGLE_DEGREES)
            }
        }
        with self.assertRaises(ValueError) as caught:
            check_solve_parameters(pretending, technique(A_CANDIDATE))
        self.assertIn("wrong value", str(caught.exception))

    def test_the_default_recorded_as_an_override(self) -> None:
        """The same fault the other way round, which is just as misleading."""
        pretending = {"solveParameters": {"ELBOW_POLE_ANGLE_DEGREES": A_CANDIDATE}}
        with self.assertRaises(ValueError):
            check_solve_parameters(pretending, technique(None))


class BuildActuallyCallsTheChecker(unittest.TestCase):
    """A checker nothing executes is not a guard.

    Every test above drives `check_solve_parameters` directly, so all of them
    pass on a `build` that never calls it. THIS IS THE HOLE THAT LEAVES, and it
    is the fault this repository records as "a consumer nothing executes is
    unchecked".

    The call is pinned by AST rather than by text, so a rename or a comment
    cannot satisfy it, and the assertion is on `build`'s OWN body rather than
    on the module, so moving the call into a function nobody calls fails too.
    """

    def build_function(self) -> ast.FunctionDef:
        import export_blender_job

        source = Path(export_blender_job.__file__).read_text(encoding="utf-8")
        for node in ast.parse(source).body:
            if isinstance(node, ast.FunctionDef) and node.name == "build":
                return node
        self.fail("export_blender_job has no build function")

    def test_build_calls_the_checker(self) -> None:
        called = {
            node.func.id
            for node in ast.walk(self.build_function())
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("check_solve_parameters", called)

    def test_build_also_fills_the_mapping(self) -> None:
        """Calling the checker on a job with no mapping would only raise."""
        called = {
            node.func.id
            for node in ast.walk(self.build_function())
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("solve_parameters", called)

    def test_the_walk_would_notice_an_absence(self) -> None:
        """Guards the guard: prove the check can report a missing name."""
        called = {
            node.func.id
            for node in ast.walk(self.build_function())
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("a_name_that_is_not_called_anywhere", called)


class TheCheckerAcceptsAnHonestJob(unittest.TestCase):
    """A guard that refuses everything protects nothing either."""

    def test_the_default_honestly_recorded(self) -> None:
        method = technique(None)
        check_solve_parameters(job_for(method), method)

    def test_an_override_honestly_recorded(self) -> None:
        method = technique(A_CANDIDATE)
        check_solve_parameters(job_for(method), method)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
