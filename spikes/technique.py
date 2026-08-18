"""Load how an athlete meets the ball, separately from where the ball goes.

Splitting these two is what makes the possession model worth building. One
technique file against three ball files is the same skill practised into three
parts of the arm span, and that is milestone 4's whole test.

The technique never says where a hand is. It says which hands take the ball,
how far apart they sit around it, and what the athlete does with the ball once
she has it. The hands themselves are solved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ball_track import MOVEMENT_DIR, BallOffset, read_offset

TECHNIQUE_SUFFIX = ".technique.json"

# Two palms flat against each other are 0 apart and cannot hold anything. Two
# palms 180 apart are on opposite poles of the ball, which is a squeeze rather
# than a catch and puts both elbows past their limits.
MINIMUM_SPREAD_DEGREES = 20.0
MAXIMUM_SPREAD_DEGREES = 160.0

HANDS = ("both", "left", "right")
SIDES = {"both": ("l", "r"), "left": ("l",), "right": ("r",)}


class TechniqueError(ValueError):
    pass


def technique_path(movement_id: str) -> Path:
    return MOVEMENT_DIR / (movement_id + TECHNIQUE_SUFFIX)


def has_technique(movement_id: str) -> bool:
    return technique_path(movement_id).is_file()


@dataclass(frozen=True)
class AfterContactKey:
    at_phase: float
    name: str
    offset: BallOffset


@dataclass(frozen=True)
class Technique:
    movement_id: str
    hands: str
    spread_degrees: float
    face_ball: bool
    # Whether the athlete turns toward the ball rather than taking it square.
    # A wide ball caught square puts the far arm across the body at nearly full
    # extension, which is both awkward and the configuration in which the elbow
    # stops steering smoothly.
    turn_to_ball: bool
    after_contact: tuple[AfterContactKey, ...]

    @property
    def sides(self) -> tuple[str, ...]:
        return SIDES[self.hands]

    def drives_the_ball(self) -> bool:
        return bool(self.after_contact)


def load_technique(path: Path) -> Technique:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    hands = str(data.get("hands", "both"))
    if hands not in HANDS:
        raise TechniqueError(
            f"hands is {hands!r}, which is not one of {', '.join(HANDS)}"
        )

    grip = data.get("grip", {})
    try:
        spread = float(grip["spreadDegrees"])
    except KeyError:
        raise TechniqueError("a grip needs spreadDegrees") from None
    if not MINIMUM_SPREAD_DEGREES <= spread <= MAXIMUM_SPREAD_DEGREES:
        raise TechniqueError(
            f"the palms are {spread:.0f} degrees apart around the ball, outside "
            f"{MINIMUM_SPREAD_DEGREES:.0f} to {MAXIMUM_SPREAD_DEGREES:.0f}, "
            "which is not a grip a person can hold"
        )
    keys: list[AfterContactKey] = []
    for number, entry in enumerate(data.get("afterContact", [])):
        name = str(entry.get("name", f"after{number}"))
        keys.append(
            AfterContactKey(
                at_phase=float(entry["atPhase"]),
                name=name,
                offset=read_offset(entry, name, TechniqueError),
            )
        )
    phases = [key.at_phase for key in keys]
    if phases != sorted(phases):
        raise TechniqueError("afterContact keys must be ordered by atPhase")
    if keys and abs(phases[-1] - 1.0) > 1e-9:
        raise TechniqueError(
            f"the last afterContact key is at phase {phases[-1]:.3f}. A drill "
            "that drives the ball must say where the ball is when it ends."
        )

    return Technique(
        movement_id=str(data["movementId"]),
        hands=hands,
        spread_degrees=spread,
        face_ball=bool(grip.get("faceBall", True)),
        turn_to_ball=bool(data.get("turnToBall", False)),
        after_contact=tuple(keys),
    )
