"""The receipt must say what the solve was set to, or a pair cannot be verified.

`docs/COACH_REVIEW_SPEC_INTERFACE.md` section 4 gives this lane the form
`render_pair(parameter, value_a, value_b)`. Before 2026-09-09 a receipt could not
verify one. Two jobs at two parameter values produce two different `jobSha256`,
so the receipts are distinguishable, and nothing said which hash meant which
value. A picture whose parameter cannot be named is a picture a coach cannot mark
against a build.

The rule refuses four ways and every one of them has a failure that reads as
success, so each is built here rather than looked for in data.
"""

from __future__ import annotations

import ast
import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECEIPT = REPO / "render_receipt.py"
RENDERER = REPO / "blender_movement_render.py"


def _load():
    spec = importlib.util.spec_from_file_location("render_receipt", RECEIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def receipt_for(movement_id: str, parameters) -> dict:
    return {"movementId": movement_id, "solveParameters": parameters}


class SolveParametersTest(unittest.TestCase):
    def setUp(self):
        self.module = _load()

    def test_a_job_that_carries_parameters_yields_them(self):
        job = {"solveParameters": {"ELBOW_POLE_ANGLE_DEGREES": 31.3}}
        self.assertEqual(self.module.solve_parameters(job),
                         {"ELBOW_POLE_ANGLE_DEGREES": 31.3})

    def test_a_job_that_carries_none_yields_none(self):
        self.assertIsNone(self.module.solve_parameters({}))

    def test_an_empty_mapping_is_not_parameters(self):
        """An empty dict says nothing and must not read as "recorded"."""
        self.assertIsNone(self.module.solve_parameters({"solveParameters": {}}))

    def test_a_wrong_type_is_not_parameters(self):
        for wrong in ("31.3", 31.3, ["a"], None):
            with self.subTest(wrong=wrong):
                self.assertIsNone(
                    self.module.solve_parameters({"solveParameters": wrong}))


class RefuseUnverifiablePairTest(unittest.TestCase):
    PARAMETER = "ELBOW_POLE_ANGLE_DEGREES"

    def setUp(self):
        self.module = _load()

    def _refuse(self, a, b):
        with self.assertRaises(SystemExit) as caught:
            self.module.refuse_unverifiable_pair(self.PARAMETER, a, b)
        return str(caught.exception)

    def test_a_real_pair_passes_and_returns_both_values(self):
        a = receipt_for("netball_deflect_high", {self.PARAMETER: 31.3})
        b = receipt_for("netball_deflect_high", {self.PARAMETER: 37.3})
        self.assertEqual(
            self.module.refuse_unverifiable_pair(self.PARAMETER, a, b),
            (31.3, 37.3))

    def test_it_refuses_a_receipt_with_no_parameters_at_all(self):
        a = receipt_for("netball_deflect_high", None)
        b = receipt_for("netball_deflect_high", {self.PARAMETER: 37.3})
        self.assertIn("no `solveParameters`", self._refuse(a, b))
        self.assertIn("no `solveParameters`", self._refuse(b, a))

    def test_it_refuses_when_the_named_parameter_is_absent(self):
        a = receipt_for("netball_deflect_high", {"SOMETHING_ELSE": 1.0})
        b = receipt_for("netball_deflect_high", {self.PARAMETER: 37.3})
        self.assertIn("does not name", self._refuse(a, b))

    def test_it_refuses_two_pictures_at_the_same_value(self):
        """A caller that fetched one job twice must not be told it has a pair."""
        a = receipt_for("netball_deflect_high", {self.PARAMETER: 31.3})
        b = receipt_for("netball_deflect_high", {self.PARAMETER: 31.3})
        self.assertIn("not a pair", self._refuse(a, b))

    def test_it_refuses_when_another_parameter_also_moved(self):
        """The rule that carries the weight.

        A pair whose second parameter also moved shows a difference the caption
        attributes to the first one.
        """
        a = receipt_for("netball_deflect_high",
                        {self.PARAMETER: 31.3, "STANCE_WIDTH": 0.40})
        b = receipt_for("netball_deflect_high",
                        {self.PARAMETER: 37.3, "STANCE_WIDTH": 0.44})
        message = self._refuse(a, b)
        self.assertIn("STANCE_WIDTH", message)
        self.assertIn("could not be attributed", message)

    def test_a_parameter_present_on_one_side_only_counts_as_moved(self):
        a = receipt_for("netball_deflect_high",
                        {self.PARAMETER: 31.3, "STANCE_WIDTH": 0.40})
        b = receipt_for("netball_deflect_high", {self.PARAMETER: 37.3})
        self.assertIn("STANCE_WIDTH", self._refuse(a, b))

    def test_it_refuses_two_different_drills(self):
        a = receipt_for("netball_deflect_high", {self.PARAMETER: 31.3})
        b = receipt_for("netball_chest_pass", {self.PARAMETER: 37.3})
        self.assertIn("not a pair", self._refuse(a, b))


class RendererWritesItTest(unittest.TestCase):
    """The receipt must actually CARRY the key, matched on the parsed source.

    A guard on text is not a guard on code. This finds the receipt dictionary in
    `blender_movement_render.py` and requires an entry whose key is the module
    constant and whose value is a CALL to the reader, so a hard-coded value or a
    caller-supplied one does not pass.
    """

    def setUp(self):
        self.tree = ast.parse(RENDERER.read_text(encoding="utf-8"))

    def _receipt_dict(self):
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = [k.value for k in node.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            if "movementId" in keys and "jobSha256" in keys:
                return node
        self.fail("no receipt dictionary found in the renderer")

    def test_the_receipt_carries_the_solve_parameters_key(self):
        node = self._receipt_dict()
        named = [k for k in node.keys
                 if isinstance(k, ast.Name) and k.id == "SOLVE_PARAMETERS"]
        self.assertTrue(named, "the receipt does not carry SOLVE_PARAMETERS")

    def test_its_value_is_read_from_the_job_and_not_supplied(self):
        node = self._receipt_dict()
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Name) and key.id == "SOLVE_PARAMETERS":
                self.assertIsInstance(
                    value, ast.Call,
                    "the parameters must be READ, never a literal or an argument")
                self.assertEqual(value.func.id, "solve_parameters")
                self.assertEqual(len(value.args), 1)
                self.assertEqual(value.args[0].id, "job",
                                 "they must be read from the JOB")
                return
        self.fail("SOLVE_PARAMETERS is not a key of the receipt")


if __name__ == "__main__":
    unittest.main()
