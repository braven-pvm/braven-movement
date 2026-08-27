"""A waiting hand must stay on its own side of the athlete.

Nothing pinned this before. `netball_deflect_high` waited with its right wrist
5.9 cm to the athlete's LEFT, fanned across her face, and it passed all 245
tests, passed the joint limits, and graded eight of eight. The fault reached a
published coach pack and was found by eye in a render, which is the whole
reason this file exists.

The check is a mechanism rather than a datum. It does not pin an offset, a
distance or a drill: it asks whether either wrist has crossed the midline of
the athlete's own trunk while she waits. Pinning the number would pass the
next drill that authors the same mistake with a different value.

These run only where the solver is installed, which is the pixi environment.
A green system-python run says nothing about them.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent

# Only a genuinely absent solver may skip. Catching every exception here would
# swallow a break in the code under test and skip the guard in silence.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    import possession_solve
    from ball_track import has_ball
    from movement_engine import load_character, library
    from technique import has_technique, load_technique, technique_path


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class AWaitingHandStaysOnItsOwnSide(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.character = load_character()
        cls.index = {
            name: number
            for number, name in enumerate(cls.character.skeleton.joint_names)
        }

    @staticmethod
    def authors_a_ready_offset(movement_id: str) -> bool:
        path = SPIKE_DIR / "movements" / f"{movement_id}.technique.json"
        return "ready" in json.loads(path.read_text(encoding="utf-8"))

    def drills(self) -> list[str]:
        return [
            name
            for name in library()
            if has_ball(name)
            and has_technique(name)
            and load_technique(technique_path(name)).possession_ready
        ]

    def test_a_drill_authors_a_ready_offset(self) -> None:
        """Guards the guard. If none did, every test below would pass vacuously
        while checking nothing, which is the failure mode this file is about."""
        self.assertTrue(
            any(self.authors_a_ready_offset(name) for name in self.drills()),
            "no drill authors a ready offset, so the check below is empty",
        )

    def test_neither_wrist_crosses_the_midline_while_she_waits(self) -> None:
        """Measured in the athlete's own trunk frame, not in world X.

        Left and right stop meaning anything in world coordinates the moment a
        drill turns, and this repository has been caught by that twice.
        """
        for movement_id in self.drills():
            if not self.authors_a_ready_offset(movement_id):
                continue
            with self.subTest(movement=movement_id):
                result = possession_solve.solve_movement(self.character, movement_id)
                points = result["points"][0]
                shoulders = {
                    side: points[self.index[f"{side}_uparm"]] for side in ("l", "r")
                }
                middle = (shoulders["l"] + shoulders["r"]) / 2.0
                # The athlete's own left, from her own shoulder line, so a turn
                # cannot make this read backwards.
                sideways = shoulders["l"] - shoulders["r"]
                sideways = sideways / np.linalg.norm(sideways)

                for side, sign in (("l", 1.0), ("r", -1.0)):
                    wrist = points[self.index[f"{side}_wrist"]]
                    across = float(np.dot(wrist - middle, sideways)) * sign
                    self.assertGreater(
                        across,
                        0.0,
                        f"{movement_id}: the {side} wrist waits {abs(across):.1f} cm "
                        "on the wrong side of her midline",
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
