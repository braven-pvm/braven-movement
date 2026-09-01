"""A preview may change what a coach watches. It may not change the library.

`preview_variants.py` patches one constant for the duration of one export, so
that a look decision can be watched as A against B. That is a mechanism for
changing the solver at run time, living in a script that ships, and the only
thing standing between it and a library quietly changed by someone reaching for
it from the default path is this file.

THE THIRD GUARD, and the one the orchestrator added to my own two: a solve must
be UNCHANGED after a preview context has opened and closed. A leaked patch
would not raise, would not fail a gate, and would not show in a diff. It would
show here.

The other two guards are cases as well: a preview may never be written where
the coach pack reads, and every preview payload says at its top what it is.

Most of this needs no solver, and it says so where it does.

AN IRONY WORTH KEEPING, NOW HISTORY. The retired `mirror` variant had to patch
BOTH bindings of `spread_fingers`, because `possession_solve` copied the
function into its own namespace. A first version patched only the module and
produced a preview BYTE-IDENTICAL to the build it claimed to differ from,
carrying a stamp that said otherwise — a file that would have gone in front of
a coach as the option she was choosing between. It was caught by the test that
solves, never by the one that inspects a binding, which is why the guards below
are written on the solve.

That variant was retired on 2026-09-01 when the fix shipped. The lesson is kept
here because the mechanism it exposed did not go anywhere: `pole-37.3` patches
a module constant, and the next variant somebody writes may well patch a
function that a caller has already copied.

They are skipped rather than reworked: without `contact_solve` importable there
is genuinely no patched constant to guard, so there is nothing to check.
"""

from __future__ import annotations

import unittest

# Only a genuinely absent solver may skip. Catching every exception here would
# swallow a break in the code under test and skip the guard in silence.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

from preview_variants import SHIPPED, VARIANTS, applied, preview_output, stamp

# The variant in play patches a constant in `contact_solve`, which imports the
# solver, so the leak guards below observe that constant and skip without one.
ONLY_VARIANT = "pole-37.3"


class TheDefaultPathIsUntouched(unittest.TestCase):
    """The claim that this machinery is confined to the preview path."""

    @unittest.skipUnless(SOLVER, "the patched constant lives in contact_solve")
    def test_no_variant_is_a_no_op(self) -> None:
        import contact_solve

        before = contact_solve.ELBOW_POLE_ANGLE_DEGREES
        with applied(None) as found:
            self.assertIsNone(found)
            self.assertEqual(contact_solve.ELBOW_POLE_ANGLE_DEGREES, before)
        self.assertEqual(contact_solve.ELBOW_POLE_ANGLE_DEGREES, before)

    @unittest.skipUnless(SOLVER, "the patched constant lives in contact_solve")
    def test_a_variant_is_undone_when_its_block_ends(self) -> None:
        import contact_solve

        before = contact_solve.ELBOW_POLE_ANGLE_DEGREES
        with applied(ONLY_VARIANT):
            self.assertNotEqual(
                contact_solve.ELBOW_POLE_ANGLE_DEGREES, before,
                f"the {ONLY_VARIANT} variant did not take effect, so this file "
                "is guarding a patch that never happens",
            )
        self.assertEqual(
            contact_solve.ELBOW_POLE_ANGLE_DEGREES, before,
            f"the {ONLY_VARIANT} variant leaked out of its block. Every solve "
            "after it in this process would carry it, including a default "
            "export.",
        )

    @unittest.skipUnless(SOLVER, "the patched constant lives in contact_solve")
    def test_it_is_undone_even_when_the_block_raises(self) -> None:
        """A patch that survives an exception is the worst form of leak: the
        run that failed is the one nobody looks at afterwards."""
        import contact_solve

        before = contact_solve.ELBOW_POLE_ANGLE_DEGREES
        with self.assertRaises(RuntimeError):
            with applied(ONLY_VARIANT):
                raise RuntimeError("something went wrong mid-export")
        self.assertEqual(contact_solve.ELBOW_POLE_ANGLE_DEGREES, before)

    def test_an_unknown_variant_is_refused_by_name(self) -> None:
        with self.assertRaises(KeyError) as caught:
            with applied("no-such-option"):
                pass
        self.assertIn(ONLY_VARIANT, str(caught.exception))


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class ASolveIsTheSameAfterAPreview(unittest.TestCase):
    """The guard that matters, stated on the thing itself rather than on the
    patch. Two solves of one drill, with a preview opened and closed between
    them, must agree to the last decimal."""

    def test_the_drill_solves_identically_either_side_of_a_preview(self) -> None:
        import numpy as np
        from movement_engine import load_character
        from possession_solve import solve_movement

        character = load_character()
        drill = "netball_two_hand_catch_chest"
        before = np.asarray(solve_movement(character, drill)["motion"])

        with applied(ONLY_VARIANT):
            solve_movement(character, drill)

        after = np.asarray(solve_movement(character, drill)["motion"])
        worst = float(np.abs(after - before).max())
        self.assertEqual(
            worst, 0.0,
            f"the solve moved by {worst} after two previews ran, so a variant "
            "leaked and the library is being changed by a preview",
        )

    def test_a_preview_actually_changes_the_solve(self) -> None:
        """The anti-hollow clause for the test above. If a variant did nothing,
        the equality would hold for the wrong reason."""
        import numpy as np
        from movement_engine import load_character
        from possession_solve import solve_movement

        character = load_character()
        drill = "netball_two_hand_catch_chest"
        shipped = np.asarray(solve_movement(character, drill)["motion"])
        with applied(ONLY_VARIANT):
            previewed = np.asarray(solve_movement(character, drill)["motion"])
        self.assertGreater(
            float(np.abs(previewed - shipped).max()), 0.0,
            f"the {ONLY_VARIANT} preview solves identically to the shipped "
            "build, so there is nothing for a coach to compare and nothing to "
            "guard. This is what the retired mirror variant became once its "
            "fix shipped, and why it was retired rather than left in the list.",
        )


class APreviewSaysWhatItIs(unittest.TestCase):
    def test_it_is_never_written_where_the_pack_reads(self) -> None:
        for variant in sorted(VARIANTS):
            with self.subTest(variant=variant):
                where = preview_output(variant)
                self.assertNotEqual(where.resolve(), SHIPPED.resolve())
                self.assertIn("preview-", where.parent.name)

    def test_every_variant_stamps_its_constant_and_both_values(self) -> None:
        for variant in sorted(VARIANTS):
            with self.subTest(variant=variant):
                found = stamp(variant)
                for field in ("variant", "constant", "shipped", "previewed",
                              "question", "evidence", "note"):
                    self.assertIn(field, found)
                self.assertEqual(found["variant"], variant)
                self.assertNotEqual(
                    found["shipped"], found["previewed"],
                    "a preview whose two values are the same is not an option",
                )
                self.assertIn("PREVIEW", found["note"])

    def test_the_shipped_path_is_the_one_the_pack_reads(self) -> None:
        """Guards the guard above. If `SHIPPED` ever stopped naming the real
        output file, the refusal would be refusing nothing."""
        self.assertEqual(SHIPPED.name, "animations.json")
        self.assertEqual(SHIPPED.parent.name, "coach")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
