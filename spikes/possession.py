"""Work out where the ball is, frame by frame, and who has it.

One rule carries the whole model:

    Possession transfers at contact. Before contact the ball drives the
    athlete. After contact the athlete drives the ball.

That sentence is also a statement about frames of reference, and this module is
where it becomes arithmetic. Before contact the ball flies through the stance
frame, which is fixed at the start of the drill and does not move with the
athlete. After contact the ball is in her hands, so it lives in her own frame
and travels with her trunk. The handover is the frame where one becomes the
other.

Contact is not authored. It is the first frame where the ball comes inside the
athlete's reach, which is the same test the reach report already applies. If
that frame never arrives, the drill is a dropped ball, and that is a real
coaching outcome rather than a failure to report.

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


class PossessionError(ValueError):
    pass


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
) -> Possession:
    """Return where the ball is on every frame, and where the hands should go."""
    if not (len(phases) == len(athlete_frames) == len(shoulder_mids)):
        raise PossessionError("every frame needs a phase, a trunk and a shoulder line")
    ready_distance = ready_fraction * reach_limit_cm

    flight = [stance.place(ball.offset_at(phase)) for phase in phases]

    # The first frame she can touch it. Same test as the reach report.
    contact = None
    for number, (centre, shoulder) in enumerate(zip(flight, shoulder_mids)):
        if float(np.linalg.norm(centre - shoulder)) <= reach_limit_cm:
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

    def ready_point(number: int) -> np.ndarray:
        """Hands up and in front, aimed at the passer, at the waiting distance."""
        shoulder = np.asarray(shoulder_mids[number], dtype=np.float64)
        toward = flight[0] - shoulder
        distance = float(np.linalg.norm(toward))
        if distance < 1e-6:
            return shoulder
        return shoulder + toward * (ready_distance / distance)

    frames = []
    for number, phase in enumerate(phases):
        holding = contact is not None and number >= contact
        if holding:
            centre = athlete_frames[number].place(
                sample_offsets(carried_phases, carried_offsets, phase)
            )
            state = "carried"
        else:
            centre = flight[number]
            state = ball.state_at(phase)

        if holding:
            presented = centre
        elif phase <= ball.release_phase or contact is None:
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
            start = ready_point(number)
            presented = start + (flight[contact] - start) * travel

        frames.append(
            Frame(
                number=number,
                phase=phase,
                centre=centre,
                presented=presented,
                state=state,
                holding=holding,
            )
        )
    return Possession(frames=tuple(frames), contact_frame=contact)
