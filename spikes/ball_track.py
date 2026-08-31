"""Load a ball trajectory, and place the ball without asking the athlete.

Until now the ball was derived from the hands: the hands were authored, and the
ball was drawn at the midpoint of the wrists. So the ball followed the athlete,
it could never be the reason she moved, and it sat through her wrists rather
than in her palms. The manual says the opposite in every snatch drill: the
passer can pass the ball anywhere in the worker's arm span. The ball is the
variable and the athlete adapts.

This module holds the ball side of that inversion. It knows nothing about the
skeleton and nothing about the solver, which is deliberate: a ball position that
depended on a solved pose would be the old defect wearing a new name.

The stance frame
----------------

A trajectory is written in the athlete's own frame, in arm lengths, so the same
drill retargets from one body to another without rewriting numbers. That frame
is fixed at the start of the drill. It is anchored at the chest as the athlete
stands at phase 0, and oriented by the way she faces at phase 0.

It does not follow her. If the ball moved with the trunk, a turn would carry the
ball around with it and the athlete could never turn toward the ball, which is
the whole point of the change. The trunk moves inside a fixed frame; the ball
flies through it.

Axes match the rest of the engine. ``across`` is positive to the athlete's left,
because MHR places the left side at positive X. ``up`` is above the chest.
``ahead`` is in front of the chest.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from motion_track import _sample, turn_matrix

# A size 5 netball is 690 to 710 mm around, so about 11 cm in radius. On the
# 52.7 cm arm of the reference athlete that is 0.21 of an arm length.
SIZE_FIVE_NETBALL_RADIUS_CM = 11.0

MOVEMENT_DIR = Path(__file__).resolve().parent / "movements"
BALL_SUFFIX = ".ball.json"


def ball_path(movement_id: str, variant: str | None = None) -> Path:
    """Where one drill's ball lives.

    A drill may have more than one. The same technique against a ball placed
    high, centrally and wide is the same skill practised into three parts of
    the arm span, which is what the manual asks for and what proves that the
    hands are solved rather than authored.
    """
    if variant:
        return MOVEMENT_DIR / f"{movement_id}.{variant}{BALL_SUFFIX}"
    return MOVEMENT_DIR / (movement_id + BALL_SUFFIX)


def has_ball(movement_id: str, variant: str | None = None) -> bool:
    """A drill without a trajectory is not a defect. It has not been migrated."""
    return ball_path(movement_id, variant).is_file()


def ball_variants(movement_id: str) -> list[str | None]:
    """Every ball this drill has, the plain one first."""
    found: list[str | None] = [None] if has_ball(movement_id) else []
    for path in sorted(MOVEMENT_DIR.glob(f"{movement_id}.*{BALL_SUFFIX}")):
        name = path.name[len(movement_id) + 1 : -len(BALL_SUFFIX)]
        if name:
            found.append(name)
    return found


class BallTrackError(ValueError):
    pass


@dataclass(frozen=True)
class BallOffset:
    """Where the ball is, in arm lengths, in the stance frame.

    A POINT, not a per-hand position. This matters wherever an offset stands
    in for something a person holds with two hands, because both hands are
    then placed around this single point by the grip spread. An `across` of
    0.3 means the point sits to her left, not that each hand sits out to its
    own side, and two hands reaching for an off-centre point carry the far
    one across the body.

    Read `across` here as the motion track's `across` reversed: that one is
    per hand and this one is not. A per-hand form is a recorded design
    candidate in docs/KNOWN_ISSUES.md, deliberately not built until a second
    drill needs it.
    """

    across: float
    up: float
    ahead: float

    def as_array(self) -> np.ndarray:
        return np.array([self.across, self.up, self.ahead], dtype=np.float64)


@dataclass(frozen=True)
class Launch:
    """Where the athlete's own pass goes, and how fast, when the drill says.

    OPTIONAL AND ADDITIVE. Without it the outgoing pass is derived from the
    incoming flight — its target is where the passer stood and its speed is the
    speed he threw at — and every drill in the library at the time of writing
    does exactly that. Deriving is right for a catch-and-return: the ball goes
    back the way it came, at the pace it came.

    IT IS WRONG WHENEVER THERE IS NO MEANINGFUL INCOMING FLIGHT, which is what
    the content lane's pass family found. Two probes, both confidently wrong
    with no error raised:

    - A drill where she holds the ball from phase 0 has its release at 0, so
      the derived target is `offset_at(0)` — the ball in her own hands. The
      pass then launched BACKWARDS over her shoulder, [0, +486.3, -179.0]
      against a real catch's [0, +99.4, +594.2].
    - The derived speed is the flight's length over its duration, so a short
      fictional incoming flight authored only to satisfy `arrival` sets the
      throw: 0.02 of a phase gave 55.5 metres per second, 0.10 gave 11.1, 0.25
      gave 4.4, against the library's real 6.24. The earlier she holds it, the
      harder she throws it.

    `speed_cm_per_second` is NOT in arm lengths, and that is deliberate against
    this project's usual unit discipline. Reach is in arm lengths and carry in
    torso lengths because those are body-scaled quantities. How fast a ball
    leaves a hand is not: a netball crosses a court at a speed the throw sets,
    not one the thrower's arm length sets. `incoming_speed_cm` already returns
    centimetres per second for the same reason, and a second unit for one
    quantity is a conversion waiting to be forgotten.

    IT IS THE HORIZONTAL COMPONENT, not the speed the ball leaves the hand at.
    The vertical is solved from gravity so the ball arrives at the target, the
    same way `incoming_speed_cm` reads horizontal for the same reason: only the
    horizontal is steady, and it is what joins two points under gravity. An
    authored 624 leaves the hand at 655 on the test geometry, 624 along the
    ground and 200.6 upward. AN AUTHOR AIMING A LOB MUST KNOW THAT, because a
    lob's vertical is most of its speed and none of this field.

    `target` IS in arm lengths, because it is a place in the stance frame and
    every other offset in this file is.
    """

    target: BallOffset
    speed_cm_per_second: float


@dataclass(frozen=True)
class BallKey:
    at_phase: float
    name: str
    offset: BallOffset


@dataclass(frozen=True)
class BallTrack:
    """The incoming flight of one ball, and how big that ball is.

    Only the flight is authored, from ``release_phase`` to ``arrival_phase``.
    Before release the passer is holding the ball. After arrival the athlete is,
    and what she does with it belongs to the technique rather than to the ball.

    The flight is bounded at both ends for the same reason. The interpolator
    keeps its speed continuous through a key, so a stationary key next to a
    flying one forces the slope at the join to zero and the ball eases out of
    the passer's hand instead of leaving it at speed. Measured against a real
    parabola that cost 4.3 cm even with five keys, which is nearly half a ball.
    Holding the ball outside the flight, rather than keying it there, removes
    the join.
    """

    movement_id: str
    radius_fraction: float
    # A ball is a physical object, so a drill may state its radius directly and
    # keep it that size on every athlete. See ``radius_cm_for``.
    radius_cm: float | None
    release_phase: float
    arrival_phase: float
    keys: tuple[BallKey, ...]
    # None means "derive the outgoing pass from the incoming flight", which is
    # what every drill did before this field existed and what they all still do.
    launch: Launch | None = None

    def offset_at(self, phase: float) -> BallOffset:
        """Return the ball offset at this phase, smoothly between the keys.

        Outside the flight this holds the nearest end of it: the passer's hand
        before release, and the athlete's hands after arrival.
        """
        phases = [key.at_phase for key in self.keys]
        held = min(max(phase, self.release_phase), self.arrival_phase)
        return BallOffset(
            across=_sample([k.offset.across for k in self.keys], held, phases),
            up=_sample([k.offset.up for k in self.keys], held, phases),
            ahead=_sample([k.offset.ahead for k in self.keys], held, phases),
        )

    def in_flight(self, phase: float) -> bool:
        return self.release_phase <= phase < self.arrival_phase

    def held_by_passer(self, phase: float) -> bool:
        return phase < self.release_phase

    def state_at(self, phase: float) -> str:
        if self.held_by_passer(phase):
            return "held"
        return "flight" if self.in_flight(phase) else "carried"

    def radius_cm_for(self, arm_length_cm: float) -> float:
        """Return the ball radius on this athlete.

        A stated ``radiusCm`` wins, because a size 5 netball is the same ball
        whoever catches it. ``radiusFraction`` scales the ball with the athlete
        instead, which is what a drill wants when it is really saying "the ball
        a body this size uses".
        """
        if self.radius_cm is not None:
            return self.radius_cm
        return self.radius_fraction * arm_length_cm

    def key_phases(self) -> list[float]:
        return [key.at_phase for key in self.keys]


def read_offset(data: dict, name: str, error=None) -> BallOffset:
    """Read one stance frame offset. The technique file reads them too."""
    raised = BallTrackError if error is None else error
    try:
        return BallOffset(
            across=float(data["across"]),
            up=float(data["up"]),
            ahead=float(data["ahead"]),
        )
    except KeyError as missing:
        raise raised(f"key {name} is missing {missing}") from None


def load_ball(path: Path) -> BallTrack:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        arrival = float(data["arrival"]["atPhase"])
    except KeyError as error:
        raise BallTrackError(f"a ball trajectory needs arrival {error}") from None
    # A drill whose ball is already in the air on the first frame does not name
    # a release, and phase 0 is the right default for it.
    release = float(data.get("release", {}).get("atPhase", 0.0))

    keys = tuple(
        BallKey(
            at_phase=float(entry["atPhase"]),
            name=str(entry.get("name", f"key{number}")),
            offset=read_offset(entry, str(entry.get("name", number))),
        )
        for number, entry in enumerate(data.get("keys", []))
    )
    if len(keys) < 2:
        raise BallTrackError("a ball trajectory needs at least two keys")

    phases = [key.at_phase for key in keys]
    if phases != sorted(phases):
        raise BallTrackError("ball keys must be ordered by atPhase")
    if not 0.0 <= release < arrival:
        raise BallTrackError(
            f"the ball is released at phase {release} and arrives at {arrival}, "
            "which is not a flight"
        )
    if abs(phases[0] - release) > 1e-9:
        raise BallTrackError(
            f"the first ball key is at phase {phases[0]:.4f} but the ball is "
            f"released at {release:.4f}. The flight must start where the passer "
            "lets go, or the interpolator eases the ball out of the hand."
        )
    if not 0.0 < arrival <= 1.0:
        raise BallTrackError(
            f"arrival is at phase {arrival}, which is outside the movement"
        )
    if abs(phases[-1] - arrival) > 1e-9:
        raise BallTrackError(
            f"the last ball key is at phase {phases[-1]:.3f} but the ball arrives "
            f"at {arrival:.3f}. Only the incoming flight is authored, so the "
            "flight must end where the athlete takes the ball."
        )

    radius_fraction = float(data.get("radiusFraction", 0.0))
    radius_cm = data.get("radiusCm")
    radius_cm = None if radius_cm is None else float(radius_cm)
    if radius_cm is None and radius_fraction <= 0.0:
        raise BallTrackError(
            "a ball needs a size: either radiusFraction, in arm lengths, or "
            "radiusCm"
        )
    if radius_cm is not None and radius_cm <= 0.0:
        raise BallTrackError(f"radiusCm is {radius_cm}, which is not a ball")

    launch = None
    if "launch" in data:
        entry = data["launch"]
        try:
            speed = float(entry["speedCmPerSecond"])
        except (KeyError, TypeError, ValueError):
            raise BallTrackError(
                "a launch needs speedCmPerSecond, in centimetres per second. "
                "It is not in arm lengths: how fast a ball leaves a hand is "
                "not a body-scaled quantity."
            ) from None
        if speed <= 0.0:
            raise BallTrackError(
                f"the launch speed is {speed}, which is not a throw"
            )
        if "target" not in entry:
            raise BallTrackError(
                "a launch needs a target, in arm lengths, in the stance frame: "
                "where her own pass is going"
            )
        launch = Launch(
            target=read_offset(entry["target"], "launch target"),
            speed_cm_per_second=speed,
        )

    return BallTrack(
        movement_id=str(data["movementId"]),
        radius_fraction=radius_fraction,
        radius_cm=radius_cm,
        release_phase=release,
        arrival_phase=arrival,
        keys=keys,
        launch=launch,
    )


@dataclass(frozen=True)
class StanceFrame:
    """The fixed frame a ball trajectory is written in.

    Taken from the athlete at phase 0 and then left alone. The trunk turns and
    drops inside it; the frame itself never moves.
    """

    chest: np.ndarray
    rotation: np.ndarray
    arm_length_cm: float

    def place(self, offset: BallOffset) -> np.ndarray:
        """Return a stance frame offset as a world position, in centimetres."""
        return self.chest + self.rotation @ (offset.as_array() * self.arm_length_cm)


def stance_frame(
    chest_at_start: np.ndarray,
    arm_length_cm: float,
    turn_degrees_at_start: float = 0.0,
) -> StanceFrame:
    return StanceFrame(
        chest=np.asarray(chest_at_start, dtype=np.float64),
        rotation=turn_matrix(turn_degrees_at_start),
        arm_length_cm=float(arm_length_cm),
    )


def ball_centre(track: BallTrack, phase: float, frame: StanceFrame) -> np.ndarray:
    """Return the ball centre at this phase, in world centimetres."""
    return frame.place(track.offset_at(phase))


def describe(track: BallTrack) -> list[str]:
    lines = []
    for key in track.keys:
        lines.append(
            f"{key.name:9s} at {key.at_phase:4.2f}  "
            f"across {key.offset.across:5.2f}  up {key.offset.up:5.2f}  "
            f"ahead {key.offset.ahead:5.2f}"
        )
    return lines


GRAVITY_CM = 981.0


def solve_launch(
    release: np.ndarray, catch: np.ndarray, horizontal_speed_cm: float
) -> tuple[float, np.ndarray]:
    """Return the flight time and the launch velocity that joins two points.

    Horizontal motion is straight and steady. Only the vertical is accelerated,
    which is the whole of ballistics without drag.

    This lives here rather than in the tool that authors the incoming pass,
    because the outgoing pass is the same parabola read the other way round and
    two copies of it would drift apart.
    """
    ground = np.array([catch[0] - release[0], 0.0, catch[2] - release[2]])
    span = float(np.linalg.norm(ground))
    if span < 1e-6:
        raise ValueError("the passer is standing where the ball is caught")
    if horizontal_speed_cm <= 0.0:
        raise ValueError("a pass with no horizontal speed never arrives")
    seconds = span / horizontal_speed_cm
    rise = float(catch[1] - release[1])
    vertical = (rise + 0.5 * GRAVITY_CM * seconds * seconds) / seconds
    velocity = ground / seconds
    velocity[1] = vertical
    return seconds, velocity
