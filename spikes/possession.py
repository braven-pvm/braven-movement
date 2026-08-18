"""Work out where the ball is, frame by frame, and who has it.

One rule carries the whole model:

    Possession transfers at contact. Before contact the ball drives the
    athlete. After contact the athlete drives the ball.

A drill that passes the ball back runs the sentence twice. She takes it, she
drives it, and at the release the hands stop being on it and it is a thing in
flight again, carrying the speed she gave it.

That sentence is also a statement about frames of reference, and this module is
where it becomes arithmetic. Before contact the ball flies through the stance
frame, which is fixed at the start of the drill and does not move with the
athlete. After contact the ball is in her hands, so it lives in her own frame
and travels with her trunk. The handover is the frame where one becomes the
other.

Contact is not authored. It is the first frame where the ball comes inside the
athlete's reach, with a margin, because nobody catches with a locked elbow. If
that frame never arrives, the drill is a dropped ball, and that is a real
coaching outcome rather than a failure to report.

The margin is not cosmetic. An arm at full extension is a kinematic
singularity: the elbow angle stops responding smoothly to where the hand goes,
and a ball placed wide, where the far arm is stretched across the body, swung
the elbow 21 degrees in one frame while the ball moved 1.5 cm.

Taking contact at the distance she waits at instead reverses the movement. Her
waiting hands are further out than the ball is when she takes it, so she pulls
back 10 cm to meet it and the elbow folds 28 degrees in one frame. A snatch
takes the ball early, at the edge of the reach, and draws it in afterwards.

Anticipation
------------

Before contact the hands do not chase the ball. They go to where it is going to
be, and wait there for it. That is what a catcher does, and it is also the only
model that makes the handover smooth: the ball arrives at hands that are already
in position, so nothing has to jump.

Chasing was tried first, by sending the hands along the line to the ball at a
fixed distance. It fails in two ways. Held further out than the catch, she pulls
back 10 cm in one frame to meet the ball and the elbow folds 28 degrees. Held at
the reach itself, she catches at full extension where the elbow angle is at its
most sensitive, and the movement got worse as the frame rate rose rather than
better: 9 degrees per frame at 24 frames per second but 34 at 72.

So the hands leave the ready position when the passer lets go, and arrive at the
interception point on the frame the ball does. They accelerate into it rather
than easing to a stop, because a snatch attacks the ball, and because arriving
with speed is what lets the hands give with it afterwards.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ball_track import BallOffset, BallTrack, StanceFrame
from motion_track import _sample

# How far out the athlete holds her hands while she waits, as a fraction of the
# distance at which she could touch the ball at full stretch.
#
# One is full extension, elbows locked, for the whole approach. That is not a
# ready position and it fails the coaching band for the ready phase, which asks
# for 15 to 70 degrees of elbow flexion. It must also stay below one so that
# taking the ball is an extension rather than a retraction.
READY_FRACTION = 0.82
# How far inside her reach the ball must come before she takes it. A person
# catches with a bent elbow, both because a straight one cannot give with the
# ball and because it is the configuration in which the arm has stopped being
# able to steer.
#
# Measured by sweeping it across six drills. Raising it straightens the arm at
# contact, from 95 degrees of elbow flexion at 0.86 to 59 at full reach, and
# costs nothing in smoothness until full reach, where the spike and the worst
# step both jump. 0.97 is the straightest arm that is still off the
# singularity.
CONTACT_FRACTION = 0.97


class PossessionError(ValueError):
    pass


# Gravity, in centimetres per second squared. A released ball is a thrown ball.
GRAVITY_CM = 981.0
# How long the hands keep extending along the line of the pass after she lets
# go. The manual asks for it directly: extend through the ball as it goes.
FOLLOW_THROUGH_SECONDS = 0.12


@dataclass(frozen=True)
class Frame:
    number: int
    phase: float
    # Where the ball actually is.
    centre: np.ndarray
    # What the hands are asked to hold. The ball itself once she has reached it.
    presented: np.ndarray
    state: str
    holding: bool
    # Which hands are on the ball. Empty before contact and after release.
    sides: tuple[str, ...] = ()


@dataclass(frozen=True)
class Possession:
    frames: tuple[Frame, ...]
    contact_frame: int | None

    @property
    def caught(self) -> bool:
        return self.contact_frame is not None

    def centres(self) -> np.ndarray:
        return np.array([frame.centre for frame in self.frames])

    def biggest_ball_step_cm(self) -> float:
        """The largest distance the ball moves between two frames.

        A jump at the handover shows up here and nowhere else, so this is the
        number that says whether possession transferred cleanly.
        """
        centres = self.centres()
        if len(centres) < 2:
            return 0.0
        return float(np.max(np.linalg.norm(np.diff(centres, axis=0), axis=1)))

    def ball_step_at(self, number: int) -> float:
        if number <= 0 or number >= len(self.frames):
            return 0.0
        return float(
            np.linalg.norm(self.frames[number].centre - self.frames[number - 1].centre)
        )


# A ball this far off the centre line is straight ahead as far as the athlete
# is concerned, and turning for it would be a twitch rather than a movement.
TURN_DEADBAND_DEGREES = 8.0


def turn_toward(
    arrival: BallOffset, maximum_degrees: float = 70.0
) -> float:
    """Return how far the athlete turns to take this ball, in degrees.

    Positive is toward her left, matching MHR. She turns to put the ball in
    front of her, and no further, which is the rule the design asks for. The
    turn is capped at what a trunk can do over planted feet, so a ball beyond
    that is still taken across the body and the drill says so by failing rather
    than by inventing footwork.
    """
    bearing = math.degrees(math.atan2(arrival.across, max(arrival.ahead, 1e-6)))
    if abs(bearing) < TURN_DEADBAND_DEGREES:
        return 0.0
    return max(-maximum_degrees, min(maximum_degrees, bearing))


def turn_profile(
    phases: list[float],
    release_phase: float,
    contact_phase: float,
    turn_degrees: float,
    base_degrees: list[float],
) -> list[float]:
    """Spread the turn over the flight, finishing as the ball arrives.

    The same squared ramp the hands use, so the trunk and the arms are doing
    one movement rather than two. Any turn the movement itself authored is kept
    underneath, because a drill that starts the athlete facing away means it.
    """
    span = max(contact_phase - release_phase, 1e-9)
    profile = []
    for phase, base in zip(phases, base_degrees):
        travel = min(1.0, max(0.0, (phase - release_phase) / span)) ** 2
        profile.append(base + turn_degrees * travel)
    return profile


def carry_path(
    contact_phase: float,
    contact_offset: BallOffset,
    after_contact,
) -> tuple[list[float], list[BallOffset]]:
    """Return the path the ball takes once the athlete has it.

    It always starts where the flight ended. The author writes where the ball
    goes, never where it starts, because where it starts was decided by the
    pass. Authoring both is how a ball comes to jump at the handover.
    """
    phases = [contact_phase]
    offsets = [contact_offset]
    for key in after_contact:
        # A key already in the past cannot be steered toward.
        if key.at_phase > contact_phase + 1e-9:
            phases.append(key.at_phase)
            offsets.append(key.offset)
    return phases, offsets


def sample_offsets(
    phases: list[float], offsets: list[BallOffset], phase: float
) -> BallOffset:
    if len(offsets) == 1:
        return offsets[0]
    return BallOffset(
        across=_sample([o.across for o in offsets], phase, phases),
        up=_sample([o.up for o in offsets], phase, phases),
        ahead=_sample([o.ahead for o in offsets], phase, phases),
    )


def to_offset(
    frame: StanceFrame, position: np.ndarray, arm_length_cm: float
) -> BallOffset:
    """Express a world position in a frame, in arm lengths."""
    local = frame.rotation.T @ (
        np.asarray(position, dtype=np.float64) - frame.chest
    )
    return BallOffset(
        across=float(local[0]) / arm_length_cm,
        up=float(local[1]) / arm_length_cm,
        ahead=float(local[2]) / arm_length_cm,
    )


def resolve(
    phases: list[float],
    ball: BallTrack,
    stance: StanceFrame,
    athlete_frames: list[StanceFrame],
    shoulder_mids: list[np.ndarray],
    after_contact,
    reach_limit_cm: float,
    arm_length_cm: float,
    ready_fraction: float = READY_FRACTION,
    contact_fraction: float = CONTACT_FRACTION,
    ready_offset: BallOffset | None = None,
    release_phase: float | None = None,
    sides_at=None,
    seconds_per_phase: float = 0.0,
) -> Possession:
    """Return where the ball is on every frame, and where the hands should go."""
    if not (len(phases) == len(athlete_frames) == len(shoulder_mids)):
        raise PossessionError("every frame needs a phase, a trunk and a shoulder line")
    if ready_fraction >= contact_fraction:
        raise PossessionError(
            f"she waits at {ready_fraction:.2f} of her reach and takes the ball "
            f"at {contact_fraction:.2f}, so taking it would be a retraction "
            "rather than a reach"
        )
    ready_distance = ready_fraction * reach_limit_cm
    contact_distance = contact_fraction * reach_limit_cm

    flight = [stance.place(ball.offset_at(phase)) for phase in phases]

    # The first frame she can take it with a bent elbow, not the first frame
    # she could touch it at full stretch.
    contact = None
    for number, (centre, shoulder) in enumerate(zip(flight, shoulder_mids)):
        if float(np.linalg.norm(centre - shoulder)) <= contact_distance:
            contact = number
            break

    carried_phases: list[float] = []
    carried_offsets: list[BallOffset] = []
    if contact is not None:
        carried_phases, carried_offsets = carry_path(
            phases[contact],
            to_offset(athlete_frames[contact], flight[contact], arm_length_cm),
            after_contact,
        )

    def toward(number: int, target: np.ndarray, distance_cm: float) -> np.ndarray:
        """A point on the line to the target, no further out than she reaches."""
        shoulder = np.asarray(shoulder_mids[number], dtype=np.float64)
        along = np.asarray(target, dtype=np.float64) - shoulder
        span = float(np.linalg.norm(along))
        if span < 1e-6:
            return shoulder
        return shoulder + along * (min(span, distance_cm) / span)

    def ready_point(number: int) -> np.ndarray:
        """Where she waits.

        Aimed at the passer by default, which is the manual's hands up and in
        front, showing the arm span. A drill may say otherwise: a high deflect
        waits with the hands beside the head, and aiming those at a passer
        standing two metres away put them at her waist.
        """
        if ready_offset is not None:
            return toward(
                number, athlete_frames[number].place(ready_offset), ready_distance
            )
        return toward(number, flight[0], ready_distance)

    def carried_at(number: int) -> np.ndarray:
        return athlete_frames[number].place(
            sample_offsets(carried_phases, carried_offsets, phases[number])
        )

    # Where the ball is when she lets go, and how fast. A released ball keeps
    # the speed she gave it, which is what makes the pass back a pass rather
    # than the ball stopping in mid air.
    thrown_from = None
    if contact is not None and release_phase is not None:
        going = [n for n, phase in enumerate(phases) if phase >= release_phase]
        if going and going[0] > contact:
            first = going[0]
            step = seconds_per_phase * (phases[first] - phases[first - 1])
            velocity = (
                (carried_at(first) - carried_at(first - 1)) / step
                if step > 1e-9
                else np.zeros(3)
            )
            thrown_from = (first, carried_at(first), velocity)

    frames = []
    for number, phase in enumerate(phases):
        released = thrown_from is not None and number >= thrown_from[0]
        holding = contact is not None and number >= contact and not released
        if released:
            thrown_at, origin, velocity = thrown_from
            at = seconds_per_phase * (phase - phases[thrown_at])
            centre = origin + velocity * at
            centre[1] -= 0.5 * GRAVITY_CM * at * at
            state = "released"
            # The hands follow the line the pass went out on, not the ball
            # itself. The ball falls, and following it down turned a deflect
            # into the athlete watching her hands drop to her waist.
            #
            # The aim point travels out along that line rather than appearing
            # at the end of it. Placing it two metres away straight away made
            # the hands jump 25 cm outward on the release frame, which showed
            # up as a 50 degree elbow step on every drill that passes the ball
            # back.
            along_the_pass = origin + velocity * min(at, FOLLOW_THROUGH_SECONDS)
        elif holding:
            centre = carried_at(number)
            state = "carried"
        else:
            centre = flight[number]
            state = ball.state_at(phase)

        if holding:
            presented = centre
        elif released:
            # Follow the ball she has just passed, out to where she can still
            # reach, then no further. Clamping this at the waiting distance
            # instead made her pull her hands back the moment she let go, and
            # the manual asks for the opposite: extend through the ball as it
            # goes. It is the same rule as presenting, so nothing jumps at the
            # release.
            presented = toward(number, along_the_pass, contact_distance)
        elif contact is None or phase <= ball.release_phase:
            presented = ready_point(number)
        else:
            # Leave the ready position when the passer lets go, and arrive at
            # the interception point on the frame the ball does. Squared rather
            # than linear so the hands start still and arrive at speed, which
            # is both what a snatch is and what makes the join to the carry
            # smooth: the hand speed at contact comes out within half a
            # centimetre per frame of the speed the carry starts at.
            travel = (phase - ball.release_phase) / max(
                phases[contact] - ball.release_phase, 1e-9
            )
            travel = min(1.0, max(0.0, travel)) ** 2
            waiting = ready_point(number)
            presented = waiting + (flight[contact] - waiting) * travel

        frames.append(
            Frame(
                number=number,
                phase=phase,
                sides=() if sides_at is None else tuple(sides_at(phase)),
                centre=centre,
                presented=presented,
                state=state,
                holding=holding,
            )
        )
    return Possession(frames=tuple(frames), contact_frame=contact)
