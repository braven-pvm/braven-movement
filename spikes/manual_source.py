"""Read the coaches manual, so a generated page quotes it rather than me.

The coaching definitions in this repository carry cues I wrote from the manual.
They are paraphrases, and for a page that is going into a manual that is not
good enough: the words a coach reads have to be the words the manual uses.

This pulls the drill blocks straight out of the converted manual and hands them
over verbatim. Nothing here rewrites, tidies or corrects them. The manual says
"Worker show the passer your arm span (range hands can reach)", and that is
what a page will say, ampersands and all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
MANUAL = (
    SPIKE_DIR.parent
    / "references"
    / "202526 updated coaches manual"
    / "202526 updated coaches manual.md"
)

# Which drill in the manual each movement in the library is. The manual's
# titles are its own, punctuation included.
TITLES = {
    "netball_two_hand_catch_chest": "2 HANDS CATCH",
    "netball_two_hand_snatch_pull_in": "2 HAND SNATCHES & PULL IN",
    "netball_two_hand_snatch_straight_back": "2 HAND SNATCHES & STRAIGHT BACK",
    "netball_one_hand_snatch_to_other_hand": "1 HAND SNATCHES TO OTHER HAND",
    "netball_deflect_high": "DEFLECTS - HIGH",
    "netball_hooks_outside_hand": "HOOKS OUTSIDE HAND",
    "netball_hooks_jump_pull_in": "HOOKS JUMP AND PULL IN BALL",
}
# The footwork drill is described in prose in the manual rather than as a
# numbered drill, so it has no block to quote.
WITHOUT_A_BLOCK = ("netball_double_foot_landing",)


class ManualError(ValueError):
    pass


@dataclass(frozen=True)
class Drill:
    title: str
    # The lines above the numbered list. The manual uses them for the objective.
    intro: tuple[str, ...]
    steps: tuple[str, ...]


def _blocks(text: str) -> dict[str, Drill]:
    found: dict[str, Drill] = {}
    for title, body in re.findall(
        r"#{2,4}\s*\*{0,2}(.+?)\*{0,2}\s*\n(.*?)(?=\n#{2,4}\s|\Z)", text, re.S
    ):
        steps = tuple(re.findall(r"^\s*[-*]?\s*\d+\.\s+(.+?)\s*$", body, re.M))
        if len(steps) < 2:
            continue
        intro = tuple(
            line.strip()
            for line in body.splitlines()
            if line.strip()
            and not line.strip().startswith(("!", "#", "-", "*", ">"))
            and not re.match(r"^\s*\d+\.", line.strip())
        )
        found.setdefault(title.strip(), Drill(title.strip(), intro, steps))
    return found


def load(path: Path | None = None) -> dict[str, Drill]:
    """Return every numbered drill in the manual, by its own title."""
    source = MANUAL if path is None else path
    if not source.is_file():
        raise ManualError(f"the manual is not at {source}")
    return _blocks(source.read_text(encoding="utf-8", errors="replace"))


def for_movement(movement_id: str, drills: dict[str, Drill] | None = None):
    """Return the manual's own words for this drill, or None if it has none."""
    if movement_id in WITHOUT_A_BLOCK:
        return None
    title = TITLES.get(movement_id)
    if title is None:
        return None
    found = (load() if drills is None else drills).get(title)
    if found is None:
        raise ManualError(
            f"{movement_id} says it is {title!r} in the manual, and the manual "
            "has no drill by that name"
        )
    return found
