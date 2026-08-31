import ast
import copy
import math
import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from finger_curl import (  # noqa: E402
    ASSERTED_DIGITS,
    angle_between_degrees,
    axis_complaint,
    axis_share,
    cumulative_angles,
    curl_directions,
    dominance_margin,
    dominant_axis,
    relative_rotation,
)
from movement_contract import normalization_transform  # noqa: E402
from render_receipt import (  # noqa: E402
    NOTHING_RENDERED,
    PASS,
    render_outcome,
)

HELPER_MODULE = "blender_mpfb_reference_catch"
IMPORTING_MODULES = ("blender_movement_render.py",)


def _signatures(source: str) -> dict[str, dict]:
    """Every top-level def in a module, by name, with its required arguments."""
    found = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        arguments = node.args
        positional = [item.arg for item in arguments.posonlyargs + arguments.args]
        found[node.name] = {
            "positional": positional,
            "positional_required": len(positional) - len(arguments.defaults),
            "keyword_required": {
                item.arg
                for item, default in zip(arguments.kwonlyargs, arguments.kw_defaults)
                if default is None
            },
            "keyword_all": {item.arg for item in arguments.kwonlyargs},
        }
    return found


def _calls_into_helpers(source: str, signatures: dict[str, dict]) -> list[str]:
    tree = ast.parse(source)
    imported = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == HELPER_MODULE:
            imported.update(alias.name for alias in node.names)

    complaints = []
    # A name imported from the helper that the helper no longer defines. The
    # call check below SKIPS these, because it looks the name up in the
    # signatures and finds nothing, so deleting a helper used to pass the guard
    # and fail only when Blender loaded the module. That happened today.
    for missing in sorted(imported - set(signatures)):
        complaints.append(
            f"{missing} is imported from {HELPER_MODULE}, which no longer "
            "defines it"
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        name = node.func.id
        if name not in imported or name not in signatures:
            continue
        signature = signatures[name]
        given = {keyword.arg for keyword in node.keywords if keyword.arg}
        supplied = len(node.args) + len(
            [item for item in signature["positional"] if item in given]
        )
        if supplied < signature["positional_required"]:
            complaints.append(
                f"line {node.lineno}: {name}() takes "
                f"{signature['positional_required']} positional arguments "
                f"{signature['positional']} and receives {supplied}"
            )
        missing = signature["keyword_required"] - given
        if missing:
            complaints.append(
                f"line {node.lineno}: {name}() is missing the required "
                f"keyword arguments {sorted(missing)}"
            )
        unknown = given - signature["keyword_all"] - set(signature["positional"])
        if unknown:
            complaints.append(
                f"line {node.lineno}: {name}() does not accept the keyword "
                f"arguments {sorted(unknown)}"
            )
    return complaints


def _code_positions(source: str, function_name: str, needles: tuple[str, ...]) -> dict:
    """Where each needle sits in the CODE of one function, not in its text.

    `source.index(needle)` finds a character offset anywhere in the file. It
    matches inside a comment and inside a docstring, and this lane has already
    been bitten by a comment that described the correct behaviour above a line
    doing the opposite. It also cannot tell that two statements moved into
    different functions, where the file order and the run order disagree.

    This reads the parsed tree, skips every string constant, and keeps the
    SMALLEST node that carries each needle, so the position belongs to the
    statement itself rather than to whatever block encloses it. A needle that
    survives only in a comment or a docstring is reported missing, which is
    what it is.
    """
    tree = ast.parse(source)
    function = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ),
        None,
    )
    if function is None:
        return {}

    found: dict[str, tuple[tuple[int, int], int]] = {}
    for node in _statements_that_run(function):
        text = _without_string_content(node)
        for needle in needles:
            if needle not in text:
                continue
            if needle not in found or len(text) < found[needle][1]:
                found[needle] = ((node.lineno, node.col_offset), len(text))
    return {needle: place for needle, (place, _) in found.items()}


def _statements_that_run(function: ast.AST):
    """Every node in the function body, but NOT inside a nested definition.

    A statement moved into a nested `def` still parses inside the function and
    still has a line number in the right order, and it never runs unless
    something calls it. Skipping every constant was not enough on its own.
    """
    def walk(node):
        for child in ast.iter_child_nodes(node):
            # A nested definition is a child of the body like any other
            # statement, so there is no level at which this exemption is safe.
            # Exempting the outermost one, which a first version did, let the
            # nested-def case straight through.
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.Lambda, ast.ClassDef)):
                continue
            if _is_dead_branch(child):
                # `if False:` parses, keeps its line numbers, and never runs.
                # The else branch still does.
                for statement in child.orelse:
                    yield statement
                    yield from walk(statement)
                continue
            if hasattr(child, "lineno"):
                yield child
            yield from walk(child)

    yield from walk(function)


def _is_dead_branch(node: ast.AST) -> bool:
    """An `if` or `while` whose test is a literal that is always false."""
    if not isinstance(node, (ast.If, ast.While)):
        return False
    return isinstance(node.test, ast.Constant) and not node.test.value


def _without_string_content(node: ast.AST) -> str:
    """The node's source with every string literal blanked.

    Skipping `Constant` nodes does NOT hide a string, because every enclosing
    node's unparse carries the text back. A needle sitting only in a docstring
    was found at the enclosing function, which is how a commented-out line and
    a docstring line could both read as live code. Blank the strings first,
    then match.
    """
    class Blank(ast.NodeTransformer):
        def visit_Constant(self, node):
            if isinstance(node.value, str):
                return ast.copy_location(ast.Constant(value=""), node)
            return node

        def visit_JoinedStr(self, node):
            return ast.copy_location(ast.Constant(value=""), node)

        def visit_Lambda(self, node):
            # A lambda's body does not run where the lambda is written, and
            # skipping the Lambda NODE is not enough: the enclosing assignment
            # unparses the body straight back, exactly as it did for strings.
            return ast.copy_location(ast.Constant(value=""), node)

        def visit_If(self, node):
            return self._prune(node)

        def visit_While(self, node):
            # `while False:` is dead exactly as `if False:` is, and the walker
            # already skipped both. The transformer covered only If, so a dead
            # while NESTED inside a live for or with was carried back by the
            # enclosing node's unparse. Unnested it was hidden, which is why
            # the hole survived a decoy set that only tested unnested cases.
            return self._prune(node)

        def _prune(self, node):
            if _is_dead_branch(node):
                kept = [self.visit(item) for item in node.orelse]
                return kept or ast.copy_location(ast.Pass(), node)
            return self.generic_visit(node)

    copied = Blank().visit(copy.deepcopy(node))
    ast.fix_missing_locations(copied)
    try:
        return ast.unparse(copied)
    except (AttributeError, TypeError, ValueError):
        return ""


class BlenderSourceContractTest(unittest.TestCase):
    def test_normalization_scales_height_centres_xy_and_places_feet_at_zero(self):
        transform = normalization_transform(
            minimum=(-1.0, -0.5, 0.25),
            maximum=(1.0, 0.5, 2.25),
            target_height=1.75,
        )

        self.assertAlmostEqual(transform.scale, 0.875)
        self.assertAlmostEqual(transform.offset_x, 0.0)
        self.assertAlmostEqual(transform.offset_y, 0.0)
        self.assertAlmostEqual(transform.offset_z, -0.21875)

    def test_renderer_imports_glb_and_honours_job_timeline_and_transparency(self):
        source = (MODULE_DIR / "blender_glb_render.py").read_text(encoding="utf-8")

        self.assertIn("bpy.ops.import_scene.gltf", source)
        self.assertIn("read_job_manifest", source)
        self.assertIn("scene.render.fps = int(round(job.fps))", source)
        self.assertIn("scene.frame_start = job.frame_start", source)
        self.assertIn("scene.frame_end = job.frame_end", source)
        self.assertIn("scene.render.film_transparent = True", source)
        self.assertIn('scene.render.image_settings.color_mode = "RGBA"', source)
        self.assertIn("max_rgba_alpha(image.pixels)", source)

    def test_probe_uses_non_slicing_alpha_helper_for_both_engines(self):
        source = (MODULE_DIR / "blender_probe.py").read_text(encoding="utf-8")

        self.assertIn('render_engine("CYCLES")', source)
        self.assertIn('render_engine("BLENDER_EEVEE_NEXT")', source)
        self.assertIn("max_rgba_alpha(image.pixels)", source)
        self.assertNotIn("pixels[3::4]", source)

    def test_a_wrong_flexion_axis_is_refused_by_calling_the_rule(self):
        """The rule that stops a render must be exercised, not asserted about.

        The only guard this had was an `assertIn` on the source text, which is
        the guard class defect 1 was fixed to stop relying on. It sat green at
        76 tests while every real render failed, because the code it guarded
        runs only inside Blender and those tests skip.

        Numbers from the rig, 170 knuckle rotations over all eight drills,
        measured on the solves before and after the cold-start sweep: the four
        fingers turn about X with a share of 1.000 in every one of 136
        readings. Naming Y instead would carry at most 0.09 and naming Z at
        most 0.18.
        """
        turned_like_a_finger = (58.3, -4.7, 8.5)

        self.assertIsNone(
            axis_complaint("index", turned_like_a_finger, 0, floor_degrees=5.0),
            "the correct axis must not complain",
        )
        complaint = axis_complaint("index", turned_like_a_finger, 2, floor_degrees=5.0)
        self.assertIsNotNone(complaint, "naming Z for a finger must be refused")
        self.assertIn("0.15", complaint)
        self.assertIsNotNone(
            axis_complaint("index", turned_like_a_finger, 1, floor_degrees=5.0),
            "naming Y for a finger must be refused",
        )

    def test_a_knuckle_that_has_barely_turned_is_not_judged(self):
        """Below the floor the rotation has no direction to name.

        The bisection calls this at every trial angle, including tiny ones. A
        rule that judged those would fire on noise.
        """
        # The share here is 0.12, far below the floor a real turn must clear,
        # so this case FAILS the share rule and must be saved by the floor
        # alone. A case whose share already passes would prove nothing: the
        # rule returns None either way and deleting the floor leaves it green.
        barely = (0.4, -0.2, 0.05)
        self.assertLess(axis_share(barely, 2), 0.5)

        self.assertIsNone(
            axis_complaint("index", barely, 2, floor_degrees=5.0),
            "a knuckle that has not turned has no axis to judge",
        )
        # And the same shape, once it HAS turned, is refused.
        self.assertIsNotNone(
            axis_complaint("index", (40.0, -20.0, 5.0), 2, floor_degrees=5.0)
        )

    def test_the_thumb_is_recorded_and_never_refused(self):
        """The calibration is finished, and the answer is record-only.

        Measured 2026-08-31 over all eight drills, 34 gripping hands, on the
        solves before and after the cold-start sweep: the named-Z share runs
        0.599 to 1.000, median 0.831 — and on EVERY reading the other
        curl-plane axis, X, carries 0.989 or more, because the curl plane
        runs 47 to 61 degrees off the thumb's own flexion axis. A floor low
        enough to pass every correct reading is passed by a mis-named thumb
        more comfortably than by a correct one, so no share threshold
        separates right from wrong for this digit. An assertion here could
        never catch the swap it exists to catch, and could still refuse a
        correct pose. The share stays in the receipt as the drift record.
        """
        self.assertNotIn("thumb", ASSERTED_DIGITS)

        # The worst CORRECT reading in the library: two_hand_snatch_pull_in
        # at pull_in, right hand. The named Z carries 0.599 of the turn.
        worst_correct = (33.363, 6.042, -19.977)
        self.assertAlmostEqual(0.599, axis_share(worst_correct, 2), places=3)
        self.assertIsNone(
            axis_complaint("thumb", worst_correct, 2, floor_degrees=5.0),
            "the thumb must never stop a render on a rule that cannot tell "
            "right from wrong for it",
        )
        # The same turn judged by the WRONG name: X is the dominant axis of
        # this correct pose, so a mis-named thumb reads a BETTER share than a
        # correctly named one. That pair of numbers is the whole ruling.
        self.assertAlmostEqual(1.0, axis_share(worst_correct, 0), places=6)

    def test_a_run_that_rendered_nothing_does_not_report_a_pass(self):
        """PASS must mean something was produced, not that the code returned.

        `--no-stills` without `--animate` skips the phase loop. Run that way
        over the eight drills it printed PASS eight times and wrote eight
        receipts carrying zero phases. The receipts were honest and the word
        was not, and a script reading the console, or the exit code, sees a
        clean run over nothing.

        It must not say FAILED either. A turntable-only or animation-only run
        is legitimate. It says what happened.
        """
        self.assertEqual(NOTHING_RENDERED, render_outcome(0, None))
        self.assertEqual(NOTHING_RENDERED, render_outcome(0, {}))

        self.assertEqual(PASS, render_outcome(4, None))
        self.assertEqual(PASS, render_outcome(0, {"frames": 49}))

    def test_a_stale_receipt_cannot_outlive_the_run_that_replaces_it(self):
        """The solve can raise part way, and --output reuses its directory.

        The receipt is written once at the end. A run that raises never
        reaches it, so a PASS receipt from an earlier run would sit beside the
        fresh partial images of a failed one and describe them.
        """
        renderer = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )

        places = _code_positions(
            renderer, "render_job", ("stale.unlink", "receipt_path.write_text")
        )
        self.assertIn("stale.unlink", places, "no earlier receipt is deleted")
        self.assertLess(
            places["stale.unlink"],
            places["receipt_path.write_text"],
            "delete the earlier receipt BEFORE the render, not after it",
        )

    def test_the_flexion_delta_is_a_relative_rotation_not_a_subtraction(self):
        """What flexion turned is `rest` inverted then `now`, and nothing else.

        Two wrong answers look right in a receipt. Subtracting euler components
        is not a delta, because rotations do not commute; measured on the rig
        it was wrong by up to 4.5 degrees on one axis. Reading `now` alone
        carries the aim and the splay, which is the error that fired an
        assertion on a correct rig and killed a render.
        """
        def about_x(degrees):
            radians = math.radians(degrees)
            cosine, sine = math.cos(radians), math.sin(radians)
            return ((1.0, 0.0, 0.0), (0.0, cosine, -sine), (0.0, sine, cosine))

        rest, now = about_x(30.0), about_x(50.0)

        turned = relative_rotation(rest, now)

        # 50 from 30 is 20, not 50, and not 80.
        for row, expected in enumerate(about_x(20.0)):
            for column, value in enumerate(expected):
                self.assertAlmostEqual(value, turned[row][column], places=9)

        # And a rest of no rotation leaves `now` untouched, which is the only
        # case where reading `now` alone would have been right.
        identity = about_x(0.0)
        for row in range(3):
            for column in range(3):
                self.assertAlmostEqual(
                    now[row][column],
                    relative_rotation(identity, now)[row][column],
                    places=9,
                )

    def test_the_receipt_drift_fields_rank_by_magnitude_and_not_by_sign(self):
        """`dominantAxis` and `dominanceMarginDegrees` are the drift instrument.

        Which way a knuckle turns depends on the rig's axis orientation, and
        the two hands mirror, so the dominant component is negative about half
        the time. `within_limits` takes abs() of the flexion component for that
        reason. A ranking that compared signed values would name the wrong axis
        on every left hand and the receipt would report drift that is not
        there.

        THIS COVERAGE WAS LOST ONCE ALREADY. It was added when the abs()
        mutation first came back green, and then deleted by a later rewrite
        that replaced this block wholesale instead of adding to it, which put
        both functions back to being called by no test while they still fed
        two receipt fields. Mutation lists have to be cumulative.
        """
        self.assertEqual(0, dominant_axis((-52.0, 7.0, 11.0)))
        self.assertEqual(2, dominant_axis((6.0, -8.0, -37.0)))
        self.assertEqual(2, dominant_axis((12.0, -9.0, 31.0)))
        self.assertEqual(0, dominant_axis((44.0, 3.0, -6.0)))

        # The margin is the gap to the next largest, by magnitude, so a big
        # negative runner-up narrows it exactly as a big positive one would.
        self.assertAlmostEqual(19.0, dominance_margin((12.0, -9.0, 31.0)), places=9)
        self.assertAlmostEqual(15.0, dominance_margin((-52.0, 37.0, 11.0)), places=9)

    def test_the_solve_calls_the_axis_rule_and_fills_the_receipt(self):
        """The rule is tested; this checks that Blender code CALLS it.

        Deleting the whole `axis_complaint` call from `within_limits` left the
        suite green, and so did deleting the block that fills `axis_report`.
        A rule nothing invokes protects nothing, and the code that invokes it
        runs only inside Blender, where these tests skip.

        Matched on AST shape rather than on source text, so a mention in a
        comment or a docstring cannot satisfy it.
        """
        catch = ast.parse(
            (MODULE_DIR / "blender_mpfb_reference_catch.py").read_text(
                encoding="utf-8"
            )
        )

        def calls_named(function_name: str, callee: str) -> bool:
            for node in ast.walk(catch):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name != function_name:
                    continue
                for inner in ast.walk(node):
                    if (
                        isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Name)
                        and inner.func.id == callee
                    ):
                        return True
            return False

        self.assertTrue(
            calls_named("within_limits", "axis_complaint"),
            "within_limits must CALL the axis rule, not merely mention it",
        )
        self.assertTrue(
            calls_named("pose_articulated_hand", "axis_share"),
            "the solve must fill the receipt's share from the same measurement",
        )

        # And the receipt block must actually write into axis_report.
        writes = [
            node
            for node in ast.walk(catch)
            if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "axis_report"
        ]
        self.assertTrue(writes, "nothing fills axis_report")

    def test_the_share_is_a_fraction_of_the_largest_turn(self):
        """Rank flips on the thumb between hands; share does not."""
        self.assertAlmostEqual(1.0, axis_share((58.3, -4.7, 8.5), 0), places=6)
        self.assertAlmostEqual(8.5 / 58.3, axis_share((58.3, -4.7, 8.5), 2), places=6)
        self.assertEqual(0.0, axis_share((0.0, 0.0, 0.0), 0))

    def test_the_order_check_is_not_fooled_by_strings_or_a_nested_def(self):
        """Four ways a needle can look like running code and not be one.

        A comment was closed by moving to the tree. The rest were not: skipping
        `Constant` nodes does not hide a string, because every enclosing node's
        unparse carries the text back, and a statement moved into a nested
        `def` keeps its line number and never runs.
        """
        needles = ("bpy.context.scene.render.fps = fps", "bpy.ops.export_scene.gltf")
        decoys = {
            "plain string": ['    x = "bpy.ops.export_scene.gltf"'],
            "f-string": ['    x = f"bpy.ops.export_scene.gltf {s}"'],
            "docstring": ['    """mentions bpy.ops.export_scene.gltf"""'],
            "comment": ["    # bpy.ops.export_scene.gltf(x)"],
            "nested def": ["    def later():",
                           "        bpy.ops.export_scene.gltf(x)"],
            "lambda body": ["    f = lambda: bpy.ops.export_scene.gltf(x)"],
            "dead branch": ["    if False:",
                            "        bpy.ops.export_scene.gltf(x)"],
            "dead loop": ["    while False:",
                          "        bpy.ops.export_scene.gltf(x)"],
            # NESTED, because an unnested decoy proves less than it looks.
            # Unnested, nothing encloses the dead body but the function, which
            # this walker never yields, so it is hidden whether the transformer
            # prunes it or not. Inside a live block the enclosing node IS
            # yielded and unparses the dead body straight back. A dead `while`
            # inside a `for` was fooled for exactly that reason, while the same
            # `while` unnested looked closed.
            "dead branch in a for": ["    for i in r:",
                                     "        if False:",
                                     "            bpy.ops.export_scene.gltf(x)"],
            "dead loop in a for": ["    for i in r:",
                                   "        while False:",
                                   "            bpy.ops.export_scene.gltf(x)"],
            "dead loop in a with": ["    with open(p) as f:",
                                    "        while False:",
                                    "            bpy.ops.export_scene.gltf(x)"],
            "lambda in a for": ["    for i in r:",
                                "        f = lambda: bpy.ops.export_scene.gltf(x)"],
        }
        for name, body in decoys.items():
            with self.subTest(decoy=name):
                source = "\n".join(
                    ["def render_job(s, j):"]
                    + body
                    + ["    bpy.context.scene.render.fps = fps", ""]
                )
                places = _code_positions(source, "render_job", needles)
                self.assertNotIn(
                    "bpy.ops.export_scene.gltf", places,
                    f"a needle in a {name} was read as running code",
                )

        real = "\n".join([
            "def render_job(s, j):",
            "    bpy.context.scene.render.fps = fps",
            "    bpy.ops.export_scene.gltf(x)",
            "",
        ])
        self.assertIn("bpy.ops.export_scene.gltf",
                      _code_positions(real, "render_job", needles),
                      "real running code must still be found")

        # The ELSE of a dead branch does run, and must still be found. Pruning
        # the whole statement would be the opposite error to the one above.
        live_else = "\n".join([
            "def render_job(s, j):",
            "    bpy.context.scene.render.fps = fps",
            "    if False:",
            "        pass",
            "    else:",
            "        bpy.ops.export_scene.gltf(x)",
            "",
        ])
        self.assertIn("bpy.ops.export_scene.gltf",
                      _code_positions(live_else, "render_job", needles),
                      "the else of a dead branch is live code")

    def test_the_knuckle_takes_the_angle_it_is_given(self):
        """Defect 1, guarded at last by reading the angle instead of the text.

        The solve built its chain as `(0.0, first, first + second)`,
        so the FIRST bone of every finger took zero rotation. Only the middle
        and distal joints bent, by 8 and 12 degrees. A grip flexes the knuckle
        hardest and that one did not flex it at all, so every finger pointed
        away from the ball. It shipped 99 images looking plausible, with the
        receipt reading PASS.

        For a day this had no guard, because the function is a closure in a
        module that imports `bpy`. A guard on the source text would pass on a
        file that computes the wrong angle. This calls the function.
        """
        base = (1.0, 0.0, 0.0)
        bend = (0.0, 0.0, 1.0)

        directions = curl_directions(base, bend, 40.0, (8.0, 12.0))

        # The knuckle bone itself must have turned by the angle asked for.
        self.assertAlmostEqual(
            40.0, angle_between_degrees(base, directions[0]), places=6,
            msg="the knuckle bone did not take the knuckle angle",
        )
        # And the two joints beyond it continue from there, never restart.
        self.assertAlmostEqual(48.0, angle_between_degrees(base, directions[1]), places=6)
        self.assertAlmostEqual(60.0, angle_between_degrees(base, directions[2]), places=6)

    def test_a_flexed_finger_closes_further_along_every_joint(self):
        """A grip falls from knuckle to tip. A pointing finger climbs.

        The defect's signature was a clearance profile running the wrong way:
        +46 mm at the knuckle out to +76 at the tip, when a real grip runs
        about 40 down to 7. Each bone must turn FURTHER than the one before it,
        for any knuckle angle including zero.
        """
        base, bend = (0.0, 1.0, 0.0), (0.0, 0.0, -1.0)

        for knuckle in (0.0, 15.0, 40.0, 80.0):
            with self.subTest(knuckle=knuckle):
                angles = [
                    angle_between_degrees(base, direction)
                    for direction in curl_directions(base, bend, knuckle, (8.0, 12.0))
                ]
                self.assertEqual(sorted(angles), angles, "the chain must close")
                self.assertLess(angles[0], angles[1])
                self.assertLess(angles[1], angles[2])

    def test_the_knuckle_angle_reaches_all_three_bones(self):
        """Every bone moves when the knuckle moves, because they follow it.

        The defect held the first bone still while the others bent. Testing
        only the tip would have passed it: the tip DID move, just not from the
        joint that matters.
        """
        curl = (8.0, 12.0)

        straight = cumulative_angles(0.0, curl)
        flexed = cumulative_angles(40.0, curl)

        self.assertEqual((0.0, 8.0, 20.0), straight)
        self.assertEqual((40.0, 48.0, 60.0), flexed)
        for before, after in zip(straight, flexed):
            self.assertAlmostEqual(40.0, after - before, places=9)

    def test_every_rendered_phase_records_how_near_the_hands_came(self):
        """Whether she touched the ball must be a number, not an opinion.

        This lane once reported the fingers going through the ball, from a
        picture, and it was the opposite of the truth. The receipt carries the
        millimetres now. Anything that reads a receipt may rely on the field
        being there for both hands of every phase.
        """
        renderer = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )
        catch = (MODULE_DIR / "blender_mpfb_reference_catch.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("def finger_surface_clearance(", catch)
        self.assertIn("finger_surface_clearance", renderer)
        self.assertIn('hands[side]["surfaceClearanceMm"]', renderer)

        # Per segment, and never a bare minimum over the hand. That minimum
        # sits on the thumb's base knuckle, which flexion rotates about and so
        # cannot move, and it twice reported a flat response while every
        # fingertip moved underneath it.
        for key in ("knuckle", "mid", "distal", "tip", "knuckleToTip"):
            self.assertIn(f'"{key}"', catch, f"the clearance profile lost {key}")
        self.assertNotIn('nearest["worst"]', catch)

    def test_the_receipt_names_the_movie_that_was_actually_written(self):
        """Blender appends the frame range to a movie's name.

        Asking for <movement>.mp4 produces <movement>0001-0049.mp4, so a
        receipt that records the name it asked for carries a path to nothing
        and a size of zero. Anyone consuming those paths, and the coach pack
        does, gets a broken list.
        """
        source = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("movie = render_movie(", source)
        self.assertIn("return produced[-1]", source)
        self.assertIn("path.parent.glob(", source)

    def test_the_scene_rate_is_set_before_the_animation_is_exported(self):
        """glTF stores animation in seconds, so the scene rate sets the timebase.

        render_movie sets it, and render_movie runs AFTER the export. So the
        first drill of a session exported against Blender's default rate and
        every later drill inherited the previous drill's movie rate. Two drills
        in one session came back as 49 frames and 40: the same poses, played
        too fast. The rate must be set before the exporter reads it.
        """
        source = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )

        rate, export = "bpy.context.scene.render.fps = fps", "bpy.ops.export_scene.gltf"
        places = _code_positions(source, "render_job", (rate, export))

        # Both must be CODE, in the one function, so file order is run order.
        self.assertIn(rate, places, "the scene rate is not set in render_job")
        self.assertIn(export, places, "the export does not run in render_job")
        self.assertLess(
            places[rate],
            places[export],
            "the scene rate must be set before the glTF export reads it",
        )

    def test_a_session_does_not_carry_the_previous_drill_s_animation(self):
        """Clearing animation data off the objects does not delete the action.

        It survives in bpy.data.actions, and the glTF exporter writes every
        action it finds. The second drill of a session shipped 1063 curves
        against the first drill's 533, carrying both movements, and an
        importer binds the first action it meets. Every later drill played the
        first one's movement while looking like a correct file.
        """
        source = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("item.animation_data_clear()", source)
        self.assertIn("bpy.data.actions.remove(action)", source)
        self.assertIn("action.use_fake_user = False", source)

        purge, export = "bpy.data.actions.remove", "bpy.ops.export_scene.gltf"
        places = _code_positions(source, "render_job", (purge, export))

        self.assertIn(purge, places, "the actions are not purged in render_job")
        self.assertIn(export, places, "the export does not run in render_job")
        self.assertLess(places[purge], places[export],
                        "purge the actions before exporting")

    def test_the_receipt_carries_a_second_instrument_and_a_holding_flag(self):
        """One table cannot say whether the figure is right.

        The per digit table answers whether the FINGERS met the ball. It
        passed a figure at +7 to +9 mm per finger while the ball sat through
        the athlete's face: 406 vertices and 22.6 mm inside, none of them a
        finger. So the receipt carries a body measurement beside it, and a
        holding flag, because a hand 1.6 m from a ball in flight is not short
        of anything.
        """
        renderer = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )
        catch = (MODULE_DIR / "blender_mpfb_reference_catch.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("def body_surface_clearance(", catch)
        self.assertIn('"bodyClearanceMm"', renderer)
        self.assertIn('"holding": bool(grip)', renderer)
        for key in ("nearestMm", "verticesInside", "deepestMm"):
            self.assertIn(f'"{key}"', catch)

    def test_the_report_never_reads_missing_data_as_a_clean_result(self):
        """Silence is not a pass, and this instrument exists to say so."""
        report = (MODULE_DIR / "scripts" / "report_clearance.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("body_missing", report)
        self.assertIn("carry NO body measurement", report)
        self.assertIn("measured for it", report)
        self.assertIn("body_measured", report)

    def test_the_grip_solve_lands_on_a_measured_angle_never_an_interval_end(self):
        """A bisection end is not a result. It is a bound on one.

        The loop kept `low` and `high` and applied `high`, which is the side
        where the gap is at or BELOW the target, so it is the INSIDE. When the
        tolerance break fired on a good `middle` the loop exited and applied
        `high` anyway, discarding the angle it had just measured and landing
        the finger up to 4 mm inside the ball, about 12 mm of skin.

        The comment above it said "land on the near side of contact, never
        inside it", which is what it was meant to do and the opposite of what
        it did, so the comment could not catch it either.
        """
        catch = (MODULE_DIR / "blender_mpfb_reference_catch.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("best_angle, best_gap", catch)
        self.assertIn("apply(digit, best_angle)", catch)
        # Only a positive clearance may be accepted, so the chosen angle is
        # never one that put the finger through the surface.
        self.assertIn("gap >= 0.0", catch)
        # The angle finally applied must be the measured one. `apply(digit,
        # high)` still appears once, probing the ceiling to see whether the
        # finger can reach at all, and that is not what lands the pose.
        applied = catch.index("apply(digit, best_angle)")
        retreat = catch.index("retreat_into_limits(digit, best_angle)")
        self.assertLess(applied, retreat)

    def test_a_grip_is_read_per_hand_and_never_per_phase(self):
        """A one handed catch grips with one hand and leaves the other free.

        The job carries grip for the CATCHING hand only on those drills, so a
        phase can be holding while this hand is not. Reading the phase's grip
        as "both hands hold it" raised KeyError: 'l' on two drills the moment
        the movement lane stopped exporting a grip for a hand that was not
        gripping.
        """
        source = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("holds = bool(grip) and side in grip", source)
        self.assertIn("if not holds:", source)
        self.assertIn("radius if (grip and side in grip) else None", source)
        # Indexing a side without checking it is present is the defect itself.
        self.assertNotIn("if grip is None:", source)

    def test_movement_renderer_calls_match_the_reference_helper_signatures(self):
        """The posing helpers are shared, and only Blender links the two sides.

        A helper gains an argument on one branch while the renderer keeps the
        old call on another. The files never collide, so a merge is clean and
        the break appears only when Blender loads the module. This reads both
        signatures without importing bpy, so it fails in the ordinary suite.
        """
        signatures = _signatures(
            (MODULE_DIR / f"{HELPER_MODULE}.py").read_text(encoding="utf-8")
        )

        for name in IMPORTING_MODULES:
            with self.subTest(module=name):
                complaints = _calls_into_helpers(
                    (MODULE_DIR / name).read_text(encoding="utf-8"), signatures
                )
                self.assertEqual([], complaints, f"{name}\n" + "\n".join(complaints))


if __name__ == "__main__":
    unittest.main()
