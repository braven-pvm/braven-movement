"""The authored carry TIMING, guarded through the code that reads it.

**A RETIMED VALUE NOTHING READS IS A VALUE THAT DOES NOTHING.** On 2026-09-10,
commit 828c5b7 moved `afterContact/drive` `atPhase` from 0.62 to 0.71 in
`netball_bounce_pass` and `netball_chest_pass`, after a sweep and a ruling on
its size. Until this file, **no test in this repository read either number**. A
person could move both keys and watch the whole suite pass.

`spikes/test_carry_route.py` does read these same files, and reads `across` to
keep a carry off her face. It never reads `atPhase`. It guards a ROUTE and not a
TIMING, and the two are different facts about the same four keys.

WHAT CONSUMES THE TIMING. `possession.carry_path` turns the authored keys into
the knots of the ball's carried path, and `possession.sample_offsets`
interpolates between them. That is the real consumer, so this guards it rather
than the file. It needs no solver and no character: the carry is arithmetic on
authored offsets, which is why this runs on the hosted runner.

**WHY A HALF-TRAVEL PHASE AND NOT `atPhase` ITSELF.** Asserting `atPhase ==
0.71` would be a guard on a constant, and this repository has several of those
that protected nothing. The quantity below is the phase at which the ball has
completed HALF its forward travel, read out of the consumer. It is a TIME, so:

    move a key's `atPhase`      it moves. Measured: the old 0.62 puts the bounce
                                pass at 0.5359 against 0.6243 today, a shift of
                                0.0884 -- forty times the tolerance here.
    scale every offset          it does not move. This is a guard on the
                                timing and not on the carry's size.

So the number under test is the engine's own output, and the authored phase is
what decides it.

**WHAT THIS DOES NOT GUARD, STATED BECAUSE IT LOOKS LIKE IT SHOULD.** The
definition files carry their own `phases`, and `netball_bounce_pass.json` and
`netball_chest_pass.json` both put a coaching phase named `drive` at 0.62 --
where the ball key was before the retiming. `movement_definition` grades the
frame at `round(at_phase * (frames - 1))` from THAT number, and
`export_blender_job.build` labels that frame `drive`. **The two `drive`s are now
different instants and nothing reconciles them.** They are not guarded together
here, because measured across the library they are not coupled: of the twelve
drills that have both files, SEVEN already disagree on at least one shared name
and five agree. A shared name is not a correspondence in this library, so a test
requiring agreement would be asserting a rule the authors never followed.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from possession import BallOffset, carry_path, sample_offsets
from technique import AfterContactKey

MOVEMENTS = Path(__file__).resolve().parent / "movements"


def carry_keys(drill: str) -> list[AfterContactKey]:
    """The drill's authored carry, in the shape the consumer takes."""
    data = json.loads(
        (MOVEMENTS / f"{drill}.technique.json").read_text(encoding="utf-8"))
    return [
        AfterContactKey(
            at_phase=float(entry["atPhase"]),
            name=str(entry["name"]),
            offset=BallOffset(float(entry["across"]), float(entry["up"]),
                              float(entry["ahead"])),
        )
        for entry in data["afterContact"]
    ]


def half_travel_phase(keys: list[AfterContactKey]) -> float:
    """The phase at which the ball has completed half its forward travel.

    Read THROUGH the consumer, never rebuilt. A hand-rolled interpolation here
    would agree with itself and prove nothing about the engine.
    """
    phases, offsets = carry_path(keys[0].at_phase, keys[0].offset, keys)
    target = (offsets[0].ahead + offsets[-1].ahead) / 2.0

    low, high = phases[0], phases[-1]
    for _ in range(200):
        middle = (low + high) / 2.0
        if sample_offsets(phases, offsets, middle).ahead < target:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


class TheCarryTimingIsLoadBearing(unittest.TestCase):
    """Recorded 2026-09-14 from the tracked files, on main at 12518ee."""

    # The consumer's own output, NOT an authored number. Moving any authored
    # phase moves these; scaling the offsets does not.
    HALF_TRAVEL = {
        "netball_bounce_pass": 0.624292,
        "netball_chest_pass": 0.669748,
    }

    # Forty times smaller than the shift the retiming itself made, so this
    # separates the shipped timing from the one it replaced rather than merely
    # being satisfied by it.
    TOLERANCE = 0.002

    def test_both_drills_still_carry_the_ball(self):
        """GUARDS THE GUARD. If a drill lost its carry, every assertion below
        would pass while reading nothing."""
        for drill in self.HALF_TRAVEL:
            with self.subTest(drill=drill):
                keys = carry_keys(drill)
                self.assertTrue(keys, f"{drill} authors no carry")
                self.assertGreaterEqual(
                    len(keys), 3,
                    "a carry with fewer than three keys has no interior "
                    "timing to move, so this guard would be vacuous")

    def test_the_ball_is_driven_when_the_technique_says(self):
        """Move an authored phase and this fails. That is the whole point."""
        for drill, expected in self.HALF_TRAVEL.items():
            with self.subTest(drill=drill):
                measured = half_travel_phase(carry_keys(drill))
                self.assertAlmostEqual(
                    measured, expected, delta=self.TOLERANCE,
                    msg=(
                        f"{drill}: the ball reaches half its forward travel at "
                        f"phase {measured:.6f}, and {expected:.6f} was recorded "
                        f"on 2026-09-14. AN AUTHORED CARRY PHASE HAS MOVED. If "
                        f"that was deliberate, re-record this number by running "
                        f"`half_travel_phase` and say in the commit which key "
                        f"moved and why. This is the only test that reads these "
                        f"timings, so an unexplained change here is a retiming "
                        f"nobody gated."))

    def test_the_recorded_number_is_not_reachable_from_the_old_timing(self):
        """PROVES THIS GUARD CAN FAIL, by building the case it must reject.

        The old 0.62 is applied to an in-memory copy. **No file under
        `spikes/movements/` is written**, which is gate-4 territory.

        Without this, the test above could be satisfied by any tolerance at all
        and nobody would know it had stopped discriminating.
        """
        for drill, expected in self.HALF_TRAVEL.items():
            with self.subTest(drill=drill):
                old = [
                    AfterContactKey(0.62, key.name, key.offset)
                    if key.name == "drive" else key
                    for key in carry_keys(drill)
                ]
                self.assertNotAlmostEqual(
                    half_travel_phase(old), expected, delta=self.TOLERANCE,
                    msg=(f"{drill}: the pre-retiming timing lands inside this "
                         f"guard's tolerance, so the guard cannot tell the "
                         f"shipped value from the one it replaced"))


if __name__ == "__main__":
    unittest.main()
