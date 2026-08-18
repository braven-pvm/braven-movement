"""Load how an athlete meets the ball, separately from where the ball goes.

Splitting these two is what makes the possession model worth building. One
technique file against three ball files is the same skill practised into three
parts of the arm span, and that is milestone 4's whole test.

The technique never says where a hand is. It says which hands take the ball,
how far apart they sit around it, and what the athlete does with the ball once
she has it. The hands themselves are solved.

Three of the manual's drills need more than a catch. A one hand snatch names
which hand takes the ball and when the second one joins, because the manual
says in capitals to get two hands on it as quickly as possible. A drill that
passes the ball back names a release, which is the frame the hand constraints
stop and the ball goes back to being a thing in flight.
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
    # When the free hand joins the one that took the ball. The manual asks for
    # two hands on it as quickly as possible.
    # Whether this drill is solved by the possession model yet. A drill may be
    # authored and measured and still not be switched over, and saying so in
    # the file is better than leaving it out of the folder and forgetting why.
    possession_ready: bool
    # Where she waits, in her own frame, in arm lengths. Optional: without it
    # she waits with her hands aimed at the passer, which is what the snatch
    # drills ask for. A high deflect waits with the hands beside the head
    # instead, and the manual says so.
    ready: BallOffset | None
    second_hand_phase: float | None
    # When she lets go. After this the hands are no longer on the ball and the
    # ball is in flight again.
    release_phase: float | None
    after_contact: tuple[AfterContactKey, ...]

    @property
    def sides(self) -> tuple[str, ...]:
        return SIDES[self.hands]

    def sides_at(self, phase: float) -> tuple[str, ...]:
        """Which hands are on the ball at this phase."""
        if self.release_phase is not None and phase >= self.release_phase:
            return ()
        if self.second_hand_phase is not None and phase >= self.second_hand_phase:
            return ("l", "r")
        return self.sides

    @property
    def every_side(self) -> tuple[str, ...]:
        """Every hand this drill ever puts on the ball."""
        if self.second_hand_phase is not None:
            return ("l", "r")
        return self.sides

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
    second_hand = data.get("secondHand", {}).get("atPhase")
    second_hand = None if second_hand is None else float(second_hand)
    if second_hand is not None and hands == "both":
        raise TechniqueError(
            "a two hand catch has no second hand to bring in later"
        )
    release = data.get("release", {}).get("atPhase")
    release = None if release is None else float(release)
    if release is not None and not 0.0 < release <= 1.0:
        raise TechniqueError(
            f"the ball is released at phase {release}, which is outside the drill"
        )
    if (
        second_hand is not None
        and release is not None
        and second_hand >= release
    ):
        raise TechniqueError(
            f"the second hand joins at {second_hand} and the ball goes at "
            f"{release}, so it never gets there"
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
    ends_at = 1.0 if release is None else release
    if keys and abs(phases[-1] - ends_at) > 1e-9:
        raise TechniqueError(
            f"the last afterContact key is at phase {phases[-1]:.3f} but the "
            f"athlete has the ball until {ends_at:.3f}. A drill that drives the "
            "ball must say where the ball is when it stops driving it."
        )

    return Technique(
        movement_id=str(data["movementId"]),
        hands=hands,
        spread_degrees=spread,
        face_ball=bool(grip.get("faceBall", True)),
        turn_to_ball=bool(data.get("turnToBall", False)),
        possession_ready=bool(data.get("possessionReady", True)),
        ready=(
            read_offset(data["ready"], "ready", TechniqueError)
            if "ready" in data
            else None
        ),
        second_hand_phase=second_hand,
        release_phase=release,
        after_contact=tuple(keys),
    )
