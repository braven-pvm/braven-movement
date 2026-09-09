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
        """An empty dict is a well-formed statement that there are none."""
        self.assertIsNone(self.module.solve_parameters({"solveParameters": {}}))

    def test_an_explicit_null_is_not_parameters(self):
        """A receipt rendered from a job that predates the field round-trips."""
        self.assertIsNone(self.module.solve_parameters({"solveParameters": None}))

    def test_a_wrong_type_REFUSES_rather_than_reading_as_none(self):
        """THE THIRD STATE ON THE LINE THIS FIELD DRAWS.

        Raised by the character and animation lane on 2026-09-09. A job whose
        `solveParameters` is a list or a string used to return None, so the
        receipt said null, which reads as "this job carried no parameters". It
        carried some and they were unreadable, and those are different facts
        about a picture. A broken contract is refused, never guessed at.
        """
        for wrong in ("31.3", 31.3, ["ELBOW_POLE_ANGLE_DEGREES"], 0, True):
            with self.subTest(wrong=wrong):
                with self.assertRaises(SystemExit) as caught:
                    self.module.solve_parameters({"solveParameters": wrong})
                self.assertIn("not a mapping", str(caught.exception))
                self.assertIn(type(wrong).__name__, str(caught.exception))

    def test_the_three_states_are_distinguishable(self):
        """Absent, null-or-empty, and malformed must not read the same."""
        module = self.module
        self.assertIsNone(module.solve_parameters({}))
        self.assertIsNone(module.solve_parameters({"solveParameters": {}}))
        with self.assertRaises(SystemExit):
            module.solve_parameters({"solveParameters": "31.3"})


class TheProducersStatedShapeTest(unittest.TestCase):
    """PIN the producer's shape without importing the producer.

    `spikes/export_blender_job.solve_parameters` cannot be imported here: it
    reaches `pymomentum` through `possession_solve`, and this suite runs under
    plain python. So the movement lane carries the spanning test and this pins
    the shape IT STATED.

    WHAT THIS PIN DOES NOT COVER, corrected by that lane on 2026-09-09 after
    this docstring first claimed it did. It pins the SHAPE and not the FIELD
    NAME. This test builds its own job dictionary, so it never reads the
    producer's key. If the producer renamed its key tomorrow:

        its guard      passes, using its own literal consistently on both sides
        this pin       passes, because the dictionary is built here
        this reader    returns None on a real job, silently
        the receipt    writes null, which reads as "carried no parameters"

    THAT IS THE FAULT THE THREE STATES EXIST TO PREVENT, arriving through the
    one door two independent pins leave open. Closing it needs one test that
    reads the PRODUCER's key with THIS module's constant.

    A SECOND ROUTE WAS PROPOSED AND IT DOES NOT WORK. Reading a real job file
    from `spikes/poc-output/` and asserting this reader finds the key needs the
    producer's ARTEFACT rather than its module, so it looked as though it could
    live here. IT CANNOT:

        `/spikes/poc-output/` is in `.gitignore` at line 13
        job files tracked in git                            0

    It is BUILD OUTPUT. A test reading it finds nothing on a fresh clone and
    nothing on the runner, which has neither `pymomentum` nor the MHR assets to
    produce one. **So it would SKIP, silently, while guarding a RENAME** -- the
    exact silent failure it was written for. A rename would land, the test would
    skip, the suite would be green and this receipt would write null.

    THE ZERO MEANT SOMETHING ELSE THAN IT LOOKED LIKE. "0 of 12 job files carry
    the field" was read here as "not yet". It is also "not ever, here", and the
    movement lane found the second reading because it looked at its own side.

    WHAT ACTUALLY CLOSES THE RENAME IS THE IMPORT, BY CONSTRUCTION. That
    producer imports `SOLVE_PARAMETERS` from this module rather than spelling
    it, so there is ONE spelling and a rename moves both ends together. It
    cannot skip and it cannot be falsified, which is why it beats any test of
    the key.

    SO DO NOT REMOVE THAT IMPORT AND KEEP THIS TEST. This test deliberately does
    not assert the key, so removing the import opens the hole and leaves the
    suite green.

    THE SHAPE, as that lane stated it on 2026-09-09:

        a flat mapping of str to float, exactly one entry today,
        never empty, never None, never any other type

    IT PINS RATHER THAN OBSERVES, deliberately. That producer always records the
    pole angle, using the ENGINE'S DEFAULT when a technique names no override,
    so the empty case is unreachable from it TODAY. A later change to "record
    only overrides" would read as a tidy-up and would make this receipt write
    null for every honest default solve. This is what would go red.
    """

    PRODUCED = {"ELBOW_POLE_ANGLE_DEGREES": 31.3}
    OVERRIDDEN = {"ELBOW_POLE_ANGLE_DEGREES": 37.3}

    def setUp(self):
        # NOT setUpClass. A refusal in this module raises SystemExit, which
        # `unittest` does not catch there and which would kill the module.
        self.module = _load()

    def test_the_producers_mapping_survives_the_reader_unchanged(self):
        for produced in (self.PRODUCED, self.OVERRIDDEN):
            with self.subTest(produced=produced):
                self.assertEqual(
                    self.module.solve_parameters({"solveParameters": produced}),
                    produced)

    def test_the_producers_mapping_is_never_read_as_carrying_none(self):
        """The failure neither lane can see from its own side.

        The reader returns None for an empty mapping and the receipt writes that
        as null, which reads as "this job carried no parameters". If the producer
        ever emitted `{}` for a default solve, the receipt would say that about
        an honest one.
        """
        self.assertIsNotNone(
            self.module.solve_parameters({"solveParameters": self.PRODUCED}))

    def test_two_produced_mappings_make_a_verifiable_pair(self):
        pair = self.module.refuse_unverifiable_pair(
            "ELBOW_POLE_ANGLE_DEGREES",
            {"movementId": "netball_deflect_high",
             "solveParameters": self.PRODUCED},
            {"movementId": "netball_deflect_high",
             "solveParameters": self.OVERRIDDEN})
        self.assertEqual(pair, (31.3, 37.3))


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
        """It CAN fail, which is not the same as being able to fail on real data.

        A pair whose second parameter also moved shows a difference the caption
        attributes to the first one. This test BUILDS that pair, because the
        producer cannot produce one. Refer to
        `TheFifthRefusalIsDormantTest` below.
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


class NoProducerOnThisBranchTest(unittest.TestCase):
    """CHECKS 2, 3 AND 4 CANNOT BE REACHED BY ANY RECEIPT THIS BRANCH PRODUCES.

    Found by the content lane on 2026-09-09, one step further back than this
    lane's own correction had gone.

    NO PRODUCER HERE WRITES THE FIELD. `spikes/export_blender_job.py` on this
    branch has zero mentions of it, real job files carry no such key, and
    `solve_parameters` therefore returns None for every one. So every receipt
    records `solveParameters: null` and two real receipts refuse at CHECK 1.

    A ONE-KEY PRODUCER EXISTS ON THE MOVEMENT LANE'S UNMERGED BRANCH, and check
    3 stays dormant even after it lands, because one recorded key leaves nothing
    to compare.

    AND THE TEST THIS REPLACES READ THAT OTHER LANE'S WORKTREE. It parsed
    `../amazing-chatelet-ed2e1c/spikes/export_blender_job.py` and pinned its key
    count. That is a test depending on a sibling worktree's unmerged, moving
    branch: it would pass, fail or skip according to what another lane had done
    since, and it made a fact about SOMEBODY ELSE'S branch look like a fact about
    this repository. That is exactly how the wrong claim was made in the first
    place -- the producer was read from there and reported as the tree's.

    SO THIS PINS ONLY WHAT THIS BRANCH CAN SEE. When a producer lands here, the
    first test goes RED, and that red is the field becoming reachable.

    PROVEN ABLE TO FAIL on 2026-09-09, and the first attempt at that proof did
    NOT run: its anchor string was absent, the assertion fired before any
    rewrite, and the claim "proven able to fail" reached a commit message
    unearned. The real run inserts a producer above `knuckle_limits` and kills
    `test_no_producer_on_this_branch_writes_the_field`. An assertion that a
    mutation string is present protects against a silent no-op; it does not
    protect against reporting the attempt as a result.
    """

    PARAMETER = "ELBOW_POLE_ANGLE_DEGREES"

    def setUp(self):
        self.module = _load()

    def test_no_producer_on_this_branch_writes_the_field(self):
        producer = REPO / "spikes" / "export_blender_job.py"
        self.assertTrue(producer.is_file(), producer)
        source = producer.read_text(encoding="utf-8")
        for spelling in ("solveParameters", "solve_parameters"):
            self.assertNotIn(
                spelling, source,
                "a producer now writes the field on THIS branch; checks 2 to 4 "
                "have become reachable and every note calling them unreachable "
                "must be corrected")

    def test_a_real_job_on_this_branch_yields_none(self):
        """Read from an artefact this branch actually has, not from a belief."""
        jobs = sorted((REPO / "spikes" / "poc-output").glob("*.job.json"))
        if not jobs:
            self.skipTest("no job files on this machine; they are build output")
        import json

        job = json.loads(jobs[0].read_text(encoding="utf-8"))
        self.assertIsNone(self.module.solve_parameters(job))

    def test_two_real_receipts_refuse_at_check_one(self):
        """Not at check 3, which is where this lane first said the wall was."""
        null = receipt_for("netball_deflect_high", None)
        with self.assertRaises(SystemExit) as caught:
            self.module.refuse_unverifiable_pair(self.PARAMETER, null, null)
        self.assertIn("no `solveParameters`", str(caught.exception))

    def test_check_three_stays_dormant_even_with_a_one_key_producer(self):
        """The movement lane's producer records one key, which compares nothing."""
        a = receipt_for("netball_deflect_high", {self.PARAMETER: 31.3})
        b = receipt_for("netball_deflect_high", {self.PARAMETER: 37.3})
        self.assertEqual(
            self.module.refuse_unverifiable_pair(self.PARAMETER, a, b),
            (31.3, 37.3),
            "a one-key pair reached check 3; it is no longer dormant")


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
