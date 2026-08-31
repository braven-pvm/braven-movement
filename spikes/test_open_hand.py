"""A hand that is not on the ball is open.

`possession_solve.py` says what should happen, and has said it all along: "The
fingers close on the ball only once she has it. Before that they stay open,
which is what a hand waiting to receive actually does."

It stopped being true on `2b01aef`, when the backward sweep landed. `close_fingers`
runs inside the per-frame solve and its answer becomes the next frame's SEED.
While the only sweep ran forward that was harmless, because every frame after
contact is holding anyway. The backward sweep seeds each frame from its
SUCCESSOR, so the curl from the end of the drill travelled back through every
pre-contact frame. The curl parameters are frozen in the main solve, so a seeded
curl passes straight through to the answer untouched.

Measured on `e1b2ca8`: at frame zero, where she is not holding, 20 of the 30
curl parameters were non-zero and the largest was 1.570 radians. That is a hand
closed to a fist while she waits to receive.

IT IS MEASURED PER SIDE, and a frame-level version of this file missed half the
fault. `close_fingers` curls only the hands in `frame.sides`, so a hand off the
ball on a frame where the OTHER hand holds it is neither curled nor reset — it
keeps the seed's fist. That is 15 frames on the outside-hand hooks and 12 on
the one-hand snatch, about two tenths of a second each, exactly while she takes
the ball one-handed. Grouped by frame it is invisible: SOME finger on that
frame is legitimately curled, so the frame passes.

WHY THIS FILE EXISTS RATHER THAN A COMMENT. Nothing in the library measures a
finger. Not one coaching checkpoint, not the clip contract, not the snap check.
So 311 tests, two independent reviews and the manual clip gate all passed over
a fist, and it was found only by asking why frame zero's fingers did not match
the pose the solve starts from. A comment saying the fingers stay open had been
sitting directly above the code that stopped keeping them open.
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

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    from ball_track import has_ball
    from finger_wrap import curl_parameters
    from movement_engine import library, load_character
    from possession_solve import solve_movement
    from technique import has_technique, load_technique, technique_path

# A parameter this far from the open posture is a curled finger rather than
# solver noise. The values that made this fail read 1.570, so the bound is not
# doing any work; it is here so a floating-point tail cannot fail the file.
OPEN_TOLERANCE = 1e-4


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class AHandOffTheBallIsOpen(unittest.TestCase):
    """Solves the library, so it is one of the slow ones."""

    @classmethod
    def setUpClass(cls) -> None:
        character = load_character()
        names = list(character.parameter_transform.names)
        cls.drills: dict[str, dict] = {}
        for movement_id in sorted(library()):
            if not (has_ball(movement_id) and has_technique(movement_id)):
                continue
            method = load_technique(technique_path(movement_id))
            if not method.possession_ready:
                continue
            result = solve_movement(character, movement_id)
            motion = result["motion"]
            where = {
                side: [
                    names.index(name)
                    for name in curl_parameters(character, (side,))
                ]
                for side in method.every_side
            }
            # One record per HAND per frame, not per frame. The distinction is
            # the whole point: a frame can hold the ball in one hand while the
            # other waits.
            on_ball, off_ball, partial = [], [], []
            for frame in result["possession"].frames:
                for side, at in where.items():
                    curled = sum(
                        abs(float(motion[frame.number][one])) > OPEN_TOLERANCE
                        for one in at
                    )
                    # The exact condition `possession_solve` uses to APPLY the
                    # curl, so the two cannot drift apart.
                    if frame.holding and side in frame.sides:
                        on_ball.append((frame.number, side, curled))
                    else:
                        off_ball.append((frame.number, side, curled))
                        if frame.holding:
                            partial.append((frame.number, side))
            cls.drills[movement_id] = {
                "onBall": on_ball,
                "offBall": off_ball,
                "partial": partial,
                "parameters": len(next(iter(where.values()))),
            }

    def test_the_library_has_hand_frames_of_each_kind(self) -> None:
        """Guards the guard. A library where every hand holds the ball on
        every frame would pass the rule below while proving nothing."""
        self.assertTrue(self.drills, "no drill was solved")
        self.assertTrue(
            [m for m, f in self.drills.items() if f["offBall"]],
            "no hand is ever off the ball",
        )
        self.assertTrue(
            [m for m, f in self.drills.items() if f["onBall"]],
            "no hand is ever on the ball",
        )

    def test_a_partial_hold_is_among_them(self) -> None:
        """The anti-hollow clause, and the one this file was missing.

        The residual a frame-level version could not see needs a hand OFF the
        ball on a frame where the other hand is ON it. Without such a case in
        the library, the per-side rule below is a per-frame rule wearing a
        different shape, and the fist it exists to catch would return unseen.
        """
        with_partial = {
            movement_id: len(found["partial"])
            for movement_id, found in self.drills.items()
            if found["partial"]
        }
        self.assertTrue(
            with_partial,
            "no drill has a hand off the ball while the other hand holds it, "
            "so the per-side granularity below is untested",
        )

    def test_no_hand_is_curled_while_it_is_off_the_ball(self) -> None:
        """The rule, per hand."""
        for movement_id, found in sorted(self.drills.items()):
            curled = [row for row in found["offBall"] if row[2]]
            with self.subTest(movement=movement_id):
                # The message is built ONLY when there is something to report.
                # Python evaluates an assertion's message argument eagerly, so
                # a first version that called max() inline turned every PASSING
                # subtest into an error: max() of an empty list. An assertion
                # message that only survives the failing path is a test that
                # cannot pass.
                if curled:
                    worst = max(curled, key=lambda row: row[2])
                    while_held = [row for row in curled if row[:2] in
                                  [tuple(one) for one in found["partial"]]]
                    self.fail(
                        f"{movement_id}: {len(curled)} hand-frames where that "
                        f"hand is NOT on the ball carry curled fingers, "
                        f"{len(while_held)} of them on frames where the OTHER "
                        f"hand holds it. The worst is the {worst[1]} hand at "
                        f"frame {worst[0]}, {worst[2]} of "
                        f"{found['parameters']} curl parameters away from "
                        "open. A hand off the ball is open."
                    )

    def test_the_hand_still_closes_once_it_has_the_ball(self) -> None:
        """The other half, and the one that would catch a fix that simply
        switched the curl off. A hand on the ball with no finger curled has
        lost its grip rather than gained an open hand."""
        ever = 0
        for movement_id, found in sorted(self.drills.items()):
            curled = [row for row in found["onBall"] if row[2]]
            ever += len(curled)
            with self.subTest(movement=movement_id):
                self.assertTrue(
                    curled,
                    f"{movement_id}: a hand is on the ball on "
                    f"{len(found['onBall'])} hand-frames and not one curls a "
                    "finger, so the curl has been switched off rather than "
                    "confined to the hands that need it.",
                )
        self.assertGreater(ever, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
