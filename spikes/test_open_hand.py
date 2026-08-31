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

Measured on `e1b2ca8`: at frame zero, where she is not holding, 20 of the 32
curl parameters were non-zero and the largest was 1.570 radians. That is a hand
closed to a fist while she waits to receive.

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
            where = [
                names.index(name)
                for name in curl_parameters(character, method.every_side)
            ]
            open_frames, held_frames = [], []
            for frame in result["possession"].frames:
                curled = [
                    abs(float(motion[frame.number][at])) > OPEN_TOLERANCE
                    for at in where
                ]
                # The exact condition `possession_solve` uses to APPLY the
                # curl, so the two cannot drift apart.
                if frame.holding and frame.sides:
                    held_frames.append((frame.number, sum(curled)))
                else:
                    open_frames.append((frame.number, sum(curled)))
            cls.drills[movement_id] = {
                "open": open_frames,
                "held": held_frames,
                "parameters": len(where),
            }

    def test_the_library_has_frames_of_each_kind(self) -> None:
        """Guards the guard. A library where she holds the ball on every frame
        would pass the rule below while proving nothing."""
        self.assertTrue(self.drills, "no drill was solved")
        with_open = [m for m, f in self.drills.items() if f["open"]]
        with_held = [m for m, f in self.drills.items() if f["held"]]
        self.assertTrue(with_open, "no drill has a frame where she is not holding")
        self.assertTrue(with_held, "no drill has a frame where she is holding")

    def test_no_hand_is_curled_before_she_has_the_ball(self) -> None:
        """The rule."""
        for movement_id, found in sorted(self.drills.items()):
            curled = [(number, count) for number, count in found["open"] if count]
            with self.subTest(movement=movement_id):
                # The message is built ONLY when there is something to report.
                # Python evaluates an assertion's message argument eagerly, so
                # a first version that called max() inline turned every PASSING
                # subtest into an error: max() of an empty list. An assertion
                # message that only survives the failing path is a test that
                # cannot pass.
                if curled:
                    worst = max(curled, key=lambda pair: pair[1])
                    self.fail(
                        f"{movement_id}: {len(curled)} frames where she is NOT "
                        f"holding the ball carry curled fingers. The worst is "
                        f"frame {worst[0]} with {worst[1]} of "
                        f"{found['parameters']} curl parameters away from "
                        "open. A hand waiting to receive is open."
                    )

    def test_the_hand_still_closes_once_she_has_it(self) -> None:
        """The other half, and the one that would catch a fix that simply
        switched the curl off. A drill where she holds the ball and no finger
        ever curls has lost its grip, not gained an open hand."""
        ever = 0
        for movement_id, found in sorted(self.drills.items()):
            curled = [count for _, count in found["held"] if count]
            ever += len(curled)
            with self.subTest(movement=movement_id):
                self.assertTrue(
                    curled,
                    f"{movement_id}: she holds the ball on "
                    f"{len(found['held'])} frames and not one of them curls a "
                    "finger, so the curl has been switched off rather than "
                    "confined to the frames that need it.",
                )
        self.assertGreater(ever, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
