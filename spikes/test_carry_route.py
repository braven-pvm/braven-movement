"""A carry must not interpolate the ball through the athlete's head.

`netball_deflect_high` authored two carry keys and no more: `control` on her
left at across +0.224, `send_on` on her right at -0.203. Between them the ball
travels in a straight line, and that line goes through her face. At the graded
phase the ball surface passed 6.6 cm from her eye. It graded 8 of 8, passed the
joint limits and passed 252 tests, because nothing asked the question.

The check is a MECHANISM and uses no measured number. It reads the authored
keys and asks whether two consecutive ones sit on opposite sides of her
midline, which is the arrangement that forces the straight line across her
face. Authoring a key at the crossing is what fixes it, and that is exactly
what this rule requires.

What it deliberately does NOT do: promise the ball clears her face. It cannot.
A key at the crossing controls WHERE IN FRONT the ball passes, and a coach has
to rule on how far in front. The worst clearance on `netball_deflect_high` is
now 8.3 cm at the authored `control` key itself, which this rule does not
touch and does not claim to.

No solver is needed. These read the authored files, so they run anywhere.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

MOVEMENTS = Path(__file__).resolve().parent / "movements"


def carries() -> dict[str, list[dict]]:
    """Every technique that carries the ball, with its authored keys."""
    found = {}
    for path in sorted(MOVEMENTS.glob("*.technique.json")):
        keys = json.loads(path.read_text(encoding="utf-8")).get("afterContact", [])
        if keys:
            found[path.name.replace(".technique.json", "")] = keys
    return found


def side(key: dict) -> int:
    """Which side of her midline this key sits on. Zero means on it.

    An authored 0.0 is exactly 0.0 in these files, so this needs no tolerance
    and therefore invents no number.
    """
    across = float(key.get("across", 0.0))
    return (across > 0.0) - (across < 0.0)


class ACarryDoesNotCrossHerFace(unittest.TestCase):
    def test_some_drill_carries_the_ball(self) -> None:
        """Guards the guard. If no drill carried a ball, everything below
        would pass while checking nothing."""
        self.assertTrue(carries(), "no drill authors a carry, so this is empty")

    def test_a_drill_actually_takes_the_ball_across_her(self) -> None:
        """The anti-hollow clause. The rule below is satisfied trivially by a
        library where the ball never leaves the midline, and most of this one
        is exactly that. It is worth nothing unless a drill really crosses."""
        crossing = [
            movement
            for movement, keys in carries().items()
            if {side(key) for key in keys} >= {1, -1}
        ]
        self.assertTrue(
            crossing, "no drill takes the ball from one side of her to the other"
        )

    def test_no_two_consecutive_keys_straddle_her_midline(self) -> None:
        """The rule. A key on her left followed by a key on her right draws a
        straight line between them, and that line passes through her."""
        for movement, keys in carries().items():
            with self.subTest(movement=movement):
                for before, after in zip(keys, keys[1:]):
                    if side(before) * side(after) >= 0:
                        continue
                    self.fail(
                        f"{movement}: '{before['name']}' at across "
                        f"{before.get('across')} is followed straight away by "
                        f"'{after['name']}' at across {after.get('across')}, so "
                        "the ball interpolates through her head. Author a key "
                        "at the crossing."
                    )

    def test_a_route_key_says_it_is_provisional(self) -> None:
        """A route is not a coached position, and the file must not read as
        though a coach set it. This is an honesty clause, not a style check:
        the number came from a measurement between its neighbours, and the
        next person has to know that before they build on it."""
        checked = 0
        for movement, keys in carries().items():
            for index in range(1, len(keys) - 1):
                if side(keys[index]) != 0:
                    continue
                if side(keys[index - 1]) * side(keys[index + 1]) >= 0:
                    continue
                checked += 1
                note = json.loads(
                    (MOVEMENTS / f"{movement}.technique.json").read_text(
                        encoding="utf-8"
                    )
                ).get("carryRouteNote", "")
                with self.subTest(movement=movement, key=keys[index]["name"]):
                    self.assertIn(
                        "PROVISIONAL",
                        note,
                        f"{movement} routes the ball across her on the "
                        f"'{keys[index]['name']}' key with an unmarked number. "
                        "Say in the file that no coach has seen it.",
                    )
        self.assertGreater(checked, 0, "no route key was found, so this is empty")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
