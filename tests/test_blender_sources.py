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
    SOME_PHASES_FAILED,
    refuse_partial_receipt,
    undrawn_phases,
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

    def test_the_renderer_uses_the_repository_s_ONE_build_stamp(self):
        """`generatedFrom`, not a second name for the same idea.

        `spikes/build_stamp.py` already wrote a stamp, in the shape the whole
        repository shares, before this lane wrote a second one called `build`.
        The older is richer — `uncommittedPaths` and `uncommittedDiffSha256`
        tell two dirty builds apart rather than merely flagging one — and it is
        cached, so every receipt of a run names one build.

        The cost of the duplicate was not theoretical: `archive_receipts.py`
        reads `generatedFrom` and refused this lane's archive outright, so an
        irreplaceable set had to be hashed and described by hand.
        """
        renderer = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )
        receipt_module = (MODULE_DIR / "render_receipt.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('"generatedFrom": stamp', renderer)
        self.assertIn("from build_stamp import generated_from", renderer)
        self.assertNotIn('"build": stamp', renderer,
                         "the second name must be gone, not carried alongside")
        # And the duplicate implementation must not come back here.
        self.assertNotIn("def build_stamp(", receipt_module)
        self.assertNotIn("def git_build_stamp(", receipt_module)

    def test_the_build_is_read_once_for_the_session_not_per_receipt(self):
        """A commit made DURING a batch must not split it across two builds.

        Caught ten images into the first re-render. The shared helper is
        cached for the life of the process for the same reason, so this call
        site fixes the value; reading it inside `render_job` would invite a
        per-receipt read back in.
        """
        renderer = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("stamp = studio.build", renderer)
        self.assertIn(
            "generated_from",
            _code_positions(renderer, "__init__", ("generated_from",)),
            "the session must read the build once, where the athlete is built",
        )
        self.assertNotIn(
            "generated_from",
            _code_positions(renderer, "render_job", ("generated_from",)),
            "render_job must NOT read the build per receipt",
        )

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


class GirdleWiringTest(unittest.TestCase):
    """The girdle RULES are guarded elsewhere; this guards that Blender CALLS them.

    An independent review of 0b2495c mutated the call path five ways and left
    the 163-test suite green every time: deleting the
    `refuse_unrenderable_girdle` call, re-inlining the resolution in place of
    `shoulder_position`, dropping `ballAnchorErrorMm` from the receipt,
    returning AGREES instead of UNAVAILABLE for a missing field, and passing
    the torso where the clavicle's length belongs.

    That is the same fault this lane reported against itself a commit earlier:
    `classify` was mutation-tested in isolation and nobody asked whether its
    call site could reach the failing branch. A rule nothing invokes protects
    nothing, and this code runs only inside Blender, where these tests skip.

    Matched on AST shape, so a mention in a comment or a docstring cannot
    satisfy it.
    """

    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(
            (MODULE_DIR / "blender_movement_render.py").read_text(
                encoding="utf-8"
            )
        )
        cls.source = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )

    def function(self, name):
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == name:
                    return node
        self.fail(f"{name} is not defined in blender_movement_render.py")

    def calls(self, function_name, callee):
        for inner in ast.walk(self.function(function_name)):
            if (isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == callee):
                return inner
        return None

    def test_pose_phase_REFUSES_a_girdle_nobody_can_check(self):
        """Deleting this call renders the pre-fix figure and prints PASS."""
        self.assertIsNotNone(
            self.calls("pose_phase", "refuse_unrenderable_girdle"),
            "pose_phase must CALL the refusal, not merely import it",
        )

    def test_pose_girdle_uses_the_TESTED_resolution(self):
        """The guarded formula must be the executed formula.

        `shoulder_position` carried the tests and had no caller once already,
        while pose_girdle held a second inline copy of the same arithmetic.
        """
        self.assertIsNotNone(
            self.calls("pose_girdle", "shoulder_position"),
            "pose_girdle must resolve through shoulder_position",
        )

    def test_the_reachable_miss_is_measured_against_the_CLAVICLE(self):
        """Passing the torso here reads a 42 cm bone and nothing is out of reach."""
        call = self.calls("pose_girdle", "reachable_miss_mm")
        self.assertIsNotNone(call, "pose_girdle must measure the reachable miss")
        self.assertGreaterEqual(len(call.args), 3, "bone length argument missing")
        named = {
            node.value
            for node in ast.walk(call.args[2])
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertIn(
            "clavicle", named,
            "the bone length must come from rest['clavicle'], not the torso",
        )

    def test_a_missing_field_returns_the_NAME_and_not_a_string(self):
        """Returning AGREES here silently disables the refusal.

        The name is required rather than a literal, so that renaming the
        constant is a failure here and not a quiet change of behaviour.
        """
        found = False
        for node in ast.walk(self.function("pose_girdle")):
            if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
                continue
            for key, value in zip(node.value.keys, node.value.values):
                if (isinstance(key, ast.Constant) and key.value == "verdict"
                        and isinstance(value, ast.Name)
                        and value.id == "UNAVAILABLE"):
                    found = True
        self.assertTrue(
            found,
            "the missing-field branch must return the UNAVAILABLE name",
        )

    def test_the_receipt_carries_the_number_the_BALL_inherits(self):
        """`ballAnchorErrorMm` is what the figure carries; the per-shoulder miss is not.

        Dropping it leaves a reader with a 25 mm miss and a benign verdict and
        no way to tell which one the picture inherits.
        """
        keys = {
            key.value
            for node in ast.walk(self.function("pose_girdle"))
            if isinstance(node, ast.Dict)
            for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        for wanted in ("ballAnchorErrorMm", "renderedWidthMm", "wantedWidthMm",
                       "clavicleTurnedDegrees"):
            self.assertIn(wanted, keys, f"the receipt must carry {wanted}")

    def test_the_verdict_is_the_CONSTANT_and_never_a_bare_string(self):
        """The refusal compares against the imported name.

        A literal here would survive a rename of the constant and leave a
        verdict the refusal no longer recognises.
        """
        for node in ast.walk(self.function("pose_girdle")):
            if isinstance(node, ast.Constant) and node.value in (
                "disagrees", "out of reach", "agrees", "unavailable",
            ):
                self.fail(
                    f"pose_girdle contains the bare verdict string "
                    f"{node.value!r}; use the imported constant"
                )


class MeasuringScriptWiringTest(unittest.TestCase):
    """The scripts that produce published numbers must pose as `render_job` does.

    `fan_mirror_check.py` posed with the CONFIG's anatomy limits and `None` for
    the knuckle limits while `render_job` passes the JOB's own. On this library
    that changed no fan by 0.000000 cm, because every job's limits equal the
    config's, so nothing caught it and nothing would have. It is a latent fault
    and this is what stops it returning.

    It also pins the gate. The first version compared only the girdle, which
    `pose_girdle` computes before the ball, the arms and the hands are touched,
    and fed the result to a printed string, so a run could report 48 mismatches
    and still exit 0.
    """

    SCRIPTS = ("fan_mirror_check.py", "wrist_release_options.py")

    def tree(self, name):
        return ast.parse(
            (MODULE_DIR / "scripts" / name).read_text(encoding="utf-8")
        )

    def pose_call(self, name):
        for node in ast.walk(self.tree(name)):
            if not isinstance(node, ast.FunctionDef) or node.name != "pose":
                continue
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Attribute)
                        and inner.func.attr == "pose_phase"):
                    return inner
        return None

    def test_each_script_poses_with_the_JOBS_limits(self):
        for name in self.SCRIPTS:
            call = self.pose_call(name)
            self.assertIsNotNone(call, f"{name} has no pose_phase call")
            read = {
                node.value
                for node in ast.walk(call)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
            self.assertIn(
                "anatomyLimitsDegrees", read,
                f"{name} must pass the JOB's anatomy limits, not the config's",
            )
            self.assertIn(
                "knuckleLimitsDegrees", read,
                f"{name} must pass the JOB's knuckle limits, not None",
            )

    def gate(self):
        for node in ast.walk(self.tree("fan_mirror_check.py")):
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "refuse_unless_shipped"):
                return node
        self.fail("fan_mirror_check must have a gate that can stop the run")

    def test_EVERY_comparison_in_the_gate_can_raise(self):
        """One raise is not enough: each half must be able to stop the run.

        A first version of this test asserted only that the function contained
        a Raise. A mutation that turned the girdle branch into a bare `return`
        left the hands branch raising, and the test stayed green. The gate has
        two comparisons and both must be armed.
        """
        gate = self.gate()
        raises = [n for n in ast.walk(gate) if isinstance(n, ast.Raise)]
        self.assertGreaterEqual(
            len(raises), 2,
            "each comparison in the gate must raise; a bare return in one "
            "branch leaves that half of the pose unpinned",
        )

    def test_the_gate_pins_the_HANDS_and_not_only_the_girdle(self):
        """The girdle is computed before the hands are posed.

        A girdle-only comparison reads `same` with the forearm roll cut from 75
        degrees to 15 and the fans moved by 2.15 cm, so it cannot support a fan
        claim.

        Matched on the AST and not on the source text: a mutation that emptied
        the side loop to `for side in ()` left every field NAME in the file and
        a text search green, while the hands went unchecked.
        """
        gate = self.gate()
        sides = []
        fields = set()
        for node in ast.walk(gate):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple):
                values = [
                    element.value for element in node.iter.elts
                    if isinstance(element, ast.Constant)
                ]
                if set(values) == {"l", "r"}:
                    sides.append(node)
                fields.update(values)
        self.assertTrue(
            sides,
            "the gate must iterate BOTH sides; an emptied loop checks nothing",
        )
        for field in ("wristBendDegrees", "forearmRollDegrees",
                      "palmNormalErrorDegrees"):
            self.assertIn(
                field, fields,
                f"the gate must compare {field} inside a loop that runs",
            )
        self.assertIn(
            "jobSha256",
            {
                node.value
                for node in ast.walk(self.tree("fan_mirror_check.py"))
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            },
            "the run must pin the job digest against the receipt's",
        )

    def test_the_fan_gate_is_CALLED_and_not_only_defined(self):
        called = False
        for node in ast.walk(self.tree("fan_mirror_check.py")):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "refuse_unless_shipped"):
                called = True
        self.assertTrue(called, "the gate is defined but never invoked")


class FailedPhaseOutcomeTest(unittest.TestCase):
    """A run that could not draw a phase must not say PASS.

    On 2026-09-07 one unposable phase of one drill aborted the whole library
    render and cost eleven good drills, twice, at forty minutes each. The loop
    now carries on. That trade is only worth making if the run still says
    plainly what it could not draw, or a loud failure has become a quiet one.
    """

    def test_a_failed_phase_outranks_a_successful_run(self):
        self.assertEqual(SOME_PHASES_FAILED, render_outcome(3, None, 1))

    def test_a_failed_phase_outranks_NOTHING_RENDERED(self):
        """Both are true at once when the only phase asked for failed.

        The reader needs the one that names a cause.
        """
        self.assertEqual(SOME_PHASES_FAILED, render_outcome(0, None, 1))

    def test_a_failed_phase_outranks_a_finished_animation(self):
        self.assertEqual(
            SOME_PHASES_FAILED, render_outcome(4, {"frames": 49}, 2))

    def test_the_DEFAULT_still_reports_the_old_two_outcomes(self):
        """Called with no failure count, as every older caller does.

        A default is not exercised by callers that pass the argument
        explicitly, so it is pinned here on its own.
        """
        self.assertEqual(PASS, render_outcome(4, None))
        self.assertEqual(NOTHING_RENDERED, render_outcome(0, None))

    def test_zero_failures_is_not_a_failure(self):
        self.assertEqual(PASS, render_outcome(4, None, 0))
        self.assertEqual(NOTHING_RENDERED, render_outcome(0, None, 0))


class RenderLoopControlFlowTest(unittest.TestCase):
    """The loop must record a failed phase and CARRY ON, and still fail loudly.

    Matched on AST shape: the behaviour runs only inside Blender, where these
    tests skip, and a comment describing it would otherwise satisfy any check.
    """

    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(
            (MODULE_DIR / "blender_movement_render.py").read_text(
                encoding="utf-8"
            )
        )

    def function(self, name):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        self.fail(f"{name} is not defined")

    def phase_try(self):
        for node in ast.walk(self.function("render_job")):
            if not isinstance(node, ast.Try):
                continue
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Name)
                        and inner.func.id == "pose_phase"):
                    return node
        self.fail("the phase loop does not guard pose_phase")

    def phase_loop(self):
        """The FOR whose body holds the guarded try.

        The first version of these guards walked the HANDLERS only, so a raise
        placed in the loop body after the try passed every one of them and
        aborted the library exactly as before. The claim that a moved raise
        must fail the guard was refuted for that placement.
        """
        guarded = self.phase_try()
        for node in ast.walk(self.function("render_job")):
            if isinstance(node, ast.For) and any(
                inner is guarded for inner in ast.walk(node)
            ):
                return node
        self.fail("the guarded try is not inside a loop")

    def failure_list(self):
        """The NAME the handler appends its failures to.

        Pinning the name is what stops a constant taking its place.
        """
        for handler in self.phase_try().handlers:
            for node in ast.walk(handler):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "append"
                        and isinstance(node.func.value, ast.Name)):
                    return node.func.value.id
        self.fail("the handler appends the failure nowhere")

    def test_a_failing_phase_does_not_stop_the_loop(self):
        """Without the `continue` the handler falls through into the render."""
        handlers = self.phase_try().handlers
        self.assertTrue(handlers, "the guard catches nothing")
        carries_on = any(
            isinstance(node, ast.Continue)
            for handler in handlers for node in ast.walk(handler)
        )
        self.assertTrue(
            carries_on,
            "a failed phase must be recorded and the loop must continue",
        )

    def test_the_guard_catches_EVERY_failure_and_not_one_kind(self):
        """A narrowed `except RuntimeError` lets a KeyError abort the library.

        The phases come from a job file this lane does not write, so a
        malformed one raises something else entirely.
        """
        for handler in self.phase_try().handlers:
            self.assertTrue(
                handler.type is None
                or (isinstance(handler.type, ast.Name)
                    and handler.type.id == "Exception"),
                "the phase guard must catch Exception and not one subclass: a "
                "narrower catch aborts the library on anything else",
            )

    def test_a_failing_phase_is_not_swallowed(self):
        """It must record the CAUGHT error, not merely carry an `error` key.

        `"error": "failed"` keeps the key and loses the reason.
        """
        for handler in self.phase_try().handlers:
            bound = handler.name
            self.assertTrue(bound, "the handler does not bind the error")
            for node in ast.walk(handler):
                if not isinstance(node, ast.Dict):
                    continue
                names = [
                    key.value for key in node.keys
                    if isinstance(key, ast.Constant)
                ]
                for wanted in ("name", "frame", "failed", "error"):
                    self.assertIn(wanted, names,
                                  f"a failure must carry {wanted}")
                reason = node.values[names.index("error")]
                self.assertTrue(
                    any(isinstance(inner, ast.Name) and inner.id == bound
                        for inner in ast.walk(reason)),
                    "the recorded reason must be the CAUGHT error, not a "
                    "constant standing in for it",
                )
                return
        self.fail("the handler records no failure")

    def test_NOTHING_in_the_phase_loop_re_raises(self):
        """Not the handler: the whole loop.

        A raise placed in the loop body after the try aborts the library once
        one good phase follows a bad one, and a guard that walks only the
        handlers cannot see it.
        """
        for node in ast.walk(self.phase_loop()):
            self.assertNotIsInstance(
                node, ast.Raise,
                "raising anywhere in the phase loop costs every later phase "
                "and every later drill",
            )

    def test_the_animation_export_is_REFUSED_when_a_frame_failed(self):
        """A still with a hole is one missing figure. An animation with a hole
        plays over the gap and says nothing, because the frames either side
        close across it. So the frame loop records and the EXPORT is refused,
        while the receipt is still written: the old behaviour raised out of
        `render_job` and left no receipt at all, the stale one having already
        been unlinked.
        """
        guarded = [
            node for node in ast.walk(self.function("render_job"))
            if isinstance(node, ast.Try)
            and any(isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == "pose_phase"
                    for inner in ast.walk(node))
        ]
        self.assertGreaterEqual(
            len(guarded), 2,
            "the ANIMATION frame loop must guard pose_phase too, not only the "
            "phase loop",
        )

        wanted = self.failure_list()
        exports = [
            node for node in ast.walk(self.function("render_job"))
            if isinstance(node, ast.If)
            and any(isinstance(inner, ast.Name) and inner.id == wanted
                    for inner in ast.walk(node.test))
            and any(isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == "bake_action"
                    for inner in ast.walk(node))
        ]
        self.assertTrue(
            exports,
            f"the animation export must be conditional on {wanted}: an "
            f"animation with a missing frame must not be written",
        )

    def test_the_receipt_carries_THE_FAILURES_not_an_empty_list(self):
        """`"failedPhases": []` keeps the key and loses every finding."""
        wanted = self.failure_list()
        for node in ast.walk(self.function("render_job")):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant)
                        and key.value == "failedPhases"):
                    self.assertTrue(
                        isinstance(value, ast.Name) and value.id == wanted,
                        f"the receipt must carry the {wanted} list itself, "
                        f"not a literal standing in for it",
                    )
                    return
        self.fail("the receipt does not name the phases it could not draw")

    def test_the_outcome_is_told_the_REAL_count(self):
        """A constant 0 satisfies "three arguments" and reports PASS."""
        wanted = self.failure_list()
        for node in ast.walk(self.function("render_job")):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "render_outcome"):
                self.assertGreaterEqual(
                    len(node.args), 3,
                    "render_outcome must be given the failure count",
                )
                third = node.args[2]
                self.assertTrue(
                    isinstance(third, ast.Call)
                    and isinstance(third.func, ast.Name)
                    and third.func.id == "len"
                    and any(isinstance(inner, ast.Name) and inner.id == wanted
                            for inner in ast.walk(third)),
                    f"the count must be len({wanted}) and not a constant",
                )
                return
        self.fail("render_job never calls render_outcome")

    def test_main_FAILS_the_run_but_only_after_every_drill(self):
        """The exit code must stay honest without costing the later drills.

        A raise inside the job loop is the original defect wearing a different
        hat: it would still abandon every drill after the failing one.
        """
        main = self.function("main")
        loops = [node for node in main.body if isinstance(node, ast.For)]
        self.assertTrue(loops, "main does not loop over the jobs")
        for loop in loops:
            for node in ast.walk(loop):
                self.assertNotIsInstance(
                    node, ast.Raise,
                    "raising inside the job loop abandons the later drills",
                )
        after = main.body[main.body.index(loops[-1]) + 1:]
        raises = [
            node for statement in after for node in ast.walk(statement)
            if isinstance(node, ast.Raise)
        ]
        self.assertTrue(
            raises,
            "a run that could not draw a phase must exit non-zero, after the "
            "rest of the library has been rendered",
        )


class PartialReceiptTest(unittest.TestCase):
    """A receipt for a drill that could not be fully drawn must stop its readers.

    The render loop began writing receipts for partly-drawn drills on
    2026-09-07. Before that a failing drill produced NO receipt, so no reader
    could be fooled: the run died and the stale receipt had already been
    unlinked. The producer widened its shape and its readers stayed on the old
    assumption, and `export_manual_page` built a two-figure page for a
    three-phase drill, exited 0, and said nothing.
    """

    WHOLE = {"movementId": "d", "phases": [{"name": "a"}], "failedPhases": []}
    PARTIAL = {
        "movementId": "netball_one_hand_high_pass",
        "phases": [{"name": "lift"}, {"name": "release"}],
        "failedPhases": [
            {"name": "ready", "frame": 0, "failed": True,
             "error": "RuntimeError: FLEXION_AXIS: r index ..."},
        ],
    }

    def test_a_whole_receipt_passes_and_reports_nothing_undrawn(self):
        self.assertEqual([], refuse_partial_receipt("d", self.WHOLE))

    def test_an_OLD_receipt_with_no_such_key_is_whole(self):
        """Receipts written before this field exist and must still be read.

        Absence means whole, because a drill that failed used to produce no
        receipt at all.
        """
        self.assertEqual([], refuse_partial_receipt("d", {"phases": []}))

    def test_a_partial_receipt_STOPS_the_reader(self):
        with self.assertRaises(SystemExit) as caught:
            refuse_partial_receipt("netball_one_hand_high_pass", self.PARTIAL)

        self.assertIn("netball_one_hand_high_pass", str(caught.exception))
        self.assertIn("ready", str(caught.exception))

    def test_the_refusal_carries_the_REASON_and_not_only_the_name(self):
        """A reader told only that `ready` is missing has to go hunting.

        The cause is in the receipt; it belongs in the sentence.
        """
        with self.assertRaises(SystemExit) as caught:
            refuse_partial_receipt("d", self.PARTIAL)

        self.assertIn("FLEXION_AXIS", str(caught.exception))

    def test_allow_partial_is_explicit_and_returns_what_is_missing(self):
        """It must not silence the finding, only permit it deliberately."""
        undrawn = refuse_partial_receipt("d", self.PARTIAL, True)

        self.assertEqual(1, len(undrawn))
        self.assertEqual("ready", undrawn[0]["name"])

    def test_an_EMPTY_list_is_whole_and_a_populated_one_is_not(self):
        """`"failedPhases": []` is the mutation that empties the finding."""
        self.assertEqual([], undrawn_phases(self.WHOLE))
        self.assertEqual(1, len(undrawn_phases(self.PARTIAL)))


class ReceiptReaderWiringTest(unittest.TestCase):
    """Both readers must CALL the refusal, not merely be able to.

    A rule nothing invokes protects nothing, and these two run under pixi
    rather than in this suite.
    """

    def tree(self, name):
        return ast.parse(
            (MODULE_DIR / "spikes" / name).read_text(encoding="utf-8")
        )

    def calls(self, tree, callee):
        return any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == callee
            for node in ast.walk(tree)
        )

    def test_the_page_builder_refuses_a_partial_receipt(self):
        self.assertTrue(
            self.calls(self.tree("export_manual_page.py"),
                       "refuse_partial_receipt"),
            "export_manual_page must refuse before it builds a page",
        )

    def test_the_page_builder_DRAWS_the_missing_phase_when_allowed(self):
        """--allow-partial must not mean --say-nothing.

        The template emits an <img> for every figure, so the slot has to be an
        image or the reader sees a broken box.
        """
        tree = self.tree("export_manual_page.py")
        self.assertTrue(
            self.calls(tree, "undrawn_figure"),
            "an allowed partial page must still show what is missing",
        )
        source = (MODULE_DIR / "spikes" / "export_manual_page.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("--allow-partial", source)

    def test_the_archive_refuses_a_partial_library(self):
        """`one_set` checks stamps, and a partial receipt carries a whole one.

        So the stamp check cannot see this and a separate one is needed.
        """
        tree = self.tree("archive_receipts.py")
        self.assertTrue(
            self.calls(tree, "whole_drills"),
            "archive_receipts must check that every drill was fully drawn",
        )
        source = (MODULE_DIR / "spikes" / "archive_receipts.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("--allow-partial", source)

    def test_both_readers_gate_on_the_flag_and_not_on_nothing(self):
        """A refusal that ignores its own flag is a refusal nobody can pass."""
        for name, flag in (("export_manual_page.py", "allow_partial"),
                           ("archive_receipts.py", "allow_partial")):
            names = {
                node.attr
                for node in ast.walk(self.tree(name))
                if isinstance(node, ast.Attribute)
            }
            self.assertIn(
                flag, names,
                f"{name} must read its own --allow-partial",
            )


class ExecutableMainTest(unittest.TestCase):
    """RUN `main()`, do not only read it.

    Three faults survive every AST check that describes this function: a job
    loop emptied of its `render_job` call, an inverted `if not unposable`, and a
    narrowed `except`. All three are about what the code DOES, and the shapes
    that express them are indistinguishable from the correct ones.

    `blender_movement_render` imports `bpy` and the MPFB services, so it is
    stubbed. If it ever stops importing under those stubs the test SKIPS and
    says why, rather than passing quietly.
    """

    STUBS = (
        "bpy", "bpy_extras", "bpy_extras.object_utils", "mathutils", "bmesh",
        "bl_ext", "bl_ext.blender_org", "bl_ext.blender_org.mpfb",
        "bl_ext.blender_org.mpfb.services",
        "bl_ext.blender_org.mpfb.services.humanservice",
        "bl_ext.blender_org.mpfb.services.faceservice",
        "bl_ext.blender_org.mpfb.services.targetservice",
    )

    def run_main(self, failures_for):
        """Call `main()` over two jobs and report what happened.

        `failures_for` names the movement whose `render_job` returns a failure.
        """
        import json
        import tempfile
        import types
        from unittest import mock

        stubs = {name: mock.MagicMock() for name in self.STUBS}
        with mock.patch.dict(sys.modules, stubs):
            sys.modules.pop("blender_movement_render", None)
            try:
                import blender_movement_render as renderer
            except Exception as error:  # pragma: no cover - stub drift
                self.skipTest(
                    f"blender_movement_render no longer imports under these "
                    f"stubs, so this test cannot run it: {error}"
                )
            try:
                with tempfile.TemporaryDirectory() as room:
                    out = Path(room)
                    jobs = []
                    for movement in ("a", "b"):
                        path = out / f"{movement}.job.json"
                        path.write_text(json.dumps({
                            "movementId": movement,
                            "phases": [{"name": "ready", "frame": 0,
                                        "ball": {"radiusM": 0.1}}],
                        }), encoding="utf-8")
                        jobs.append(path)

                    calls = []

                    def fake_render_job(studio, job, path, args, output):
                        calls.append(job["movementId"])
                        if job["movementId"] == failures_for:
                            return [{"name": "ready", "frame": 0,
                                     "failed": True,
                                     "error": "RuntimeError: FLEXION_AXIS"}]
                        return []

                    args = types.SimpleNamespace(
                        job=jobs, output=out / "render", config=None,
                        phase=None, turntable=0, animate=False,
                        no_stills=False,
                    )
                    raised = None
                    with mock.patch.object(renderer, "parse_args",
                                           return_value=args), \
                            mock.patch.object(renderer, "Studio"), \
                            mock.patch.object(renderer,
                                              "load_reference_catch_config"), \
                            mock.patch.object(renderer, "render_job",
                                              fake_render_job):
                        try:
                            renderer.main()
                        except SystemExit as error:
                            raised = str(error)
                    return calls, raised
            finally:
                sys.modules.pop("blender_movement_render", None)

    def test_a_failing_drill_does_not_cost_the_LATER_drills(self):
        """The whole point. An emptied job loop passes every AST check."""
        calls, raised = self.run_main("a")

        self.assertEqual(
            ["a", "b"], calls,
            "the second drill must still be rendered after the first fails",
        )
        self.assertIsNotNone(
            raised, "a run that could not draw a phase must exit non-zero"
        )
        self.assertIn("a/ready", raised)

    def test_a_clean_run_returns_normally(self):
        """An inverted condition fails HERE and nowhere else.

        `if not unposable: raise` keeps the raise, keeps it after the loop and
        keeps its message. Only running it tells the two apart.
        """
        calls, raised = self.run_main("neither")

        self.assertEqual(["a", "b"], calls)
        self.assertIsNone(
            raised,
            "a run in which every phase drew must not raise: an inverted "
            "condition would fail every clean render in the project",
        )
