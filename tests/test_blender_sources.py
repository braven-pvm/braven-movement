import ast
import sys
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from finger_curl import (  # noqa: E402
    angle_between_degrees,
    cumulative_angles,
    curl_directions,
    dominance_margin,
    dominant_axis,
)
from movement_contract import normalization_transform  # noqa: E402

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
    for node in ast.walk(function):
        if isinstance(node, ast.Constant):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if not hasattr(node, "lineno"):
            continue
        text = ast.unparse(node)
        for needle in needles:
            if needle not in text:
                continue
            if needle not in found or len(text) < found[needle][1]:
                found[needle] = ((node.lineno, node.col_offset), len(text))
    return {needle: place for needle, (place, _) in found.items()}


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

    def test_the_flexion_axis_is_judged_by_dominance_and_not_by_purity(self):
        """The thumb's flexion is real and is not a clean single-axis turn.

        FLEXION_AXIS names one euler component per digit as flexion; the other
        two are deviation and carry a different licence. Nothing checked that
        name against the rig for a day. Name it wrong and real flexion is
        bounded by the deviation limit, or deviation gets the flexion licence,
        and neither raises.

        A purity test would be the obvious guard and would be WRONG: it fails
        on a correct thumb. The thumb turns mostly about its own Z and carries
        substantial X and Y with it.
        """
        # A thumb-like rotation: Z leads, and the other two are far from zero.
        thumb = (12.0, -9.0, 31.0)

        self.assertEqual(2, dominant_axis(thumb))
        self.assertAlmostEqual(19.0, dominance_margin(thumb), places=9)

        # A finger-like rotation: X leads.
        self.assertEqual(0, dominant_axis((44.0, 3.0, -6.0)))

        # And the dominant component is often NEGATIVE, because which way a
        # knuckle turns depends on the rig's axis orientation. `within_limits`
        # takes abs() of the flexion component for that reason. A dominance
        # test that compared signed values would name the wrong axis here and
        # every case above would still pass it.
        self.assertEqual(0, dominant_axis((-52.0, 7.0, 11.0)))
        self.assertEqual(2, dominant_axis((6.0, -8.0, -37.0)))

    def test_the_margin_shrinks_before_the_axis_flips(self):
        """The receipt carries the margin so drift is visible while it is drift.

        An assertion that only fires on the flip reports a fault that has
        already happened. The margin falls towards zero first, and the receipt
        carries it per digit for exactly that reason.
        """
        comfortable = (40.0, 5.0, 8.0)
        thin = (20.0, 19.0, 3.0)
        flipped = (18.0, 25.0, 3.0)

        self.assertGreater(dominance_margin(comfortable), dominance_margin(thin))
        self.assertEqual(0, dominant_axis(comfortable))
        self.assertEqual(0, dominant_axis(thin), "still correct, and only just")
        self.assertEqual(1, dominant_axis(flipped), "this one has gone")

    def test_the_solve_refuses_a_knuckle_whose_axis_lost_dominance(self):
        """The wrong axis must stop the render, not quietly bend a finger.

        A figure posed against swapped limits looks like a hand and is not one.
        This lane has shipped that class of picture before, so the solve raises
        rather than returns.
        """
        catch = (MODULE_DIR / "blender_mpfb_reference_catch.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("FLEXION_DOMINANCE_FLOOR_DEGREES", catch)
        self.assertIn("observed = dominant_axis(parts)", catch)
        self.assertIn("raise RuntimeError(", catch)
        # And the receipt reader exists beside the clearance profile.
        self.assertIn("def flexion_axis_dominance(", catch)
        renderer = (MODULE_DIR / "blender_movement_render.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('hands[side]["flexionAxis"]', renderer)

    def test_the_knuckle_takes_the_angle_it_is_given(self):
        """Defect 1, guarded at last by reading the angle instead of the text.

        `curved_directions` built its chain as `(0.0, first, first + second)`,
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
