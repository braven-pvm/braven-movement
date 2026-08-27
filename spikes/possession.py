"""Work out where the ball is, frame by frame, and who has it.

One rule carries the whole model:

    Possession transfers at contact. Before contact the ball drives the
    athlete. After contact the athlete drives the ball.

A drill that passes the ball back runs the sentence twice. She takes it, she
drives it, and at the release the hands stop being on it and it is a thing in
flight again, carrying the speed she gave it.

It is also a statement about units. A ball in flight is reached for, so its
trajectory is in arm lengths. A ball she is holding sits against her chest, so
its path from there is in torso lengths. Using the arm for both gave two
athletes of the same height, differing only in reach, different places to hold
the same ball.

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

from ball_track import BallOffset, BallTrack, StanceFrame, solve_launch
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
    # Where the athlete waits on this frame. A hand that is not part of the
    # catch stays here until it is: the free hand of a one hand snatch does not
    # reach for the interception point, it comes in afterwards. Presented is
    # the ball itself once she is holding it, so a hand still on its way needs
    # somewhere else to be or it arrives before it has travelled.
    waiting: np.ndarray
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


def incoming_speed_cm(
    ball: BallTrack, stance: StanceFrame, seconds_per_phase: float
) -> float:
    """How fast the passer's ball travelled, horizontally, in cm per second.

    Derived from the authored flight rather than read from a field: the two
    ends of the flight and how long it takes are all already in the track, and
    a stored speed would be a second copy of the same fact that could disagree
    with the keys.

    Horizontal, not total, because that is what joins two points under gravity.
    """
    seconds = (ball.arrival_phase - ball.release_phase) * seconds_per_phase
    if seconds <= 1e-9:
        return 0.0
    passer = stance.place(ball.offset_at(ball.release_phase))
    caught = stance.place(ball.offset_at(ball.arrival_phase))
    ground = np.array([caught[0] - passer[0], 0.0, caught[2] - passer[2]])
    return float(np.linalg.norm(ground)) / seconds


def return_velocity(
    ball: BallTrack,
    stance: StanceFrame,
    released_at: np.ndarray,
    seconds_per_phase: float,
) -> np.ndarray:
    """The velocity that sends the ball back to the passer who threw it.

    PROVISIONAL. That the athlete returns the ball to the passer is a reading
    of the manual's cues and no coach has confirmed it. What is NOT provisional
    is the arithmetic: given that target and that speed, this is the launch,
    and it is solved rather than typed.

    A zero vector where the return cannot be solved, which is a ball that stops
    in mid air. That is visibly wrong rather than quietly wrong, and it is what
    the old one-frame difference produced anyway when the carry did not move.
    """
    speed = incoming_speed_cm(ball, stance, seconds_per_phase)
    if speed <= 0.0:
        return np.zeros(3)
    passer = stance.place(ball.offset_at(ball.release_phase))
    try:
        _, velocity = solve_launch(np.asarray(released_at, dtype=np.float64), passer, speed)
    except ValueError:
        # She is standing where the passer is, so there is no pass to solve.
        return np.zeros(3)
    return velocity


def resolve(
    phases: list[float],
    ball: BallTrack,
    stance: StanceFrame,
    athlete_frames: list[StanceFrame],
    shoulder_mids: list[np.ndarray],
    after_contact,
    reach_limit_cm: float,
    arm_length_cm: float,
    carry_frames: list[StanceFrame] | None = None,
    torso_length_cm: float | None = None,
    ready_fraction: float = READY_FRACTION,
    contact_fraction: float = CONTACT_FRACTION,
    ready_offset: BallOffset | None = None,
    release_phase: float | None = None,
    sides_at=None,
    seconds_per_phase: float = 0.0,
    shoulder_places: list[dict] | None = None,
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
    # The carry is measured from the chest, in torso lengths. Without a torso
    # frame it falls back to the arm, which is what it used to do.
    carry_frames = athlete_frames if carry_frames is None else carry_frames
    carry_scale = arm_length_cm if torso_length_cm is None else torso_length_cm

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
            to_offset(carry_frames[contact], flight[contact], carry_scale),
            after_contact,
        )

    def toward(number: int, target: np.ndarray, distance_cm: float) -> np.ndarray:
        """A point on the line to the target, at most `distance_cm` from the
        MIDPOINT of her shoulders.

        That is not the same as "no further out than she reaches", which is
        what this said until the waiting-distance pack proved otherwise. For a
        square athlete the two agree, because both shoulders are equidistant
        from the middle. For a turned one they do not: on a drill starting at
        -44 degrees the same point sat 66.4 cm from one shoulder and 39.1 cm
        from the other, against a 52.7 cm arm.

        `within_every_shoulder` is what makes the reach guarantee true, and
        only `ready_point` wraps this in it. The two remaining callers are the
        released follow-through, where extending through the ball is the point.
        Refer to "Two callers still measure the reach from the midpoint" in
        docs/KNOWN_ISSUES.md before adding a third.
        """
        shoulder = np.asarray(shoulder_mids[number], dtype=np.float64)
        along = np.asarray(target, dtype=np.float64) - shoulder
        span = float(np.linalg.norm(along))
        if span < 1e-6:
            return shoulder
        return shoulder + along * (min(span, distance_cm) / span)

    def within_every_shoulder(number: int, point: np.ndarray) -> np.ndarray:
        """Pull a waiting point back until every shoulder can reach it.

        `toward` measures from the MIDPOINT of the shoulders. Its own docstring
        says "no further out than she reaches", and for a square athlete that
        is true, because both shoulders are the same distance from the middle.
        A TURNED athlete is a different matter: on
        `netball_hooks_outside_hand`, which starts facing away at -44 degrees,
        a waiting point 50.8 cm from the midpoint sits 66.4 cm from her left
        shoulder and 39.1 cm from her right. The same point, 27 cm apart.

        She then waited with that arm locked out, 0.93 to 0.999 of full
        extension, where every other arm in the library waits between 0.33 and
        0.89. And a hand target past full reach has no elbow triangle, so
        `elbow_poles` skipped that arm entirely: the elbow was unconstrained
        for 41 frames, drifted 46 degrees from where the pole wanted it, and
        was corrected all at once when the target finally came inside her
        reach. That single frame was the largest step in the library.

        `READY_FRACTION` is not touched. It was tuned so the elbow is flexed
        at the ready phase and it does that correctly on every square drill.
        What is corrected is the MEASURE it is spent against: a distance the
        hand has to cover belongs to the shoulder that covers it, not to the
        point between her shoulders.
        """
        if shoulder_places is None:
            return np.asarray(point, dtype=np.float64)
        shoulders = shoulder_places[number]
        middle = np.asarray(shoulder_mids[number], dtype=np.float64)
        along = np.asarray(point, dtype=np.float64) - middle
        span = float(np.linalg.norm(along))
        if span < 1e-6:
            return np.asarray(point, dtype=np.float64)
        worst = max(
            float(np.linalg.norm(point - np.asarray(place, dtype=np.float64)))
            for place in shoulders.values()
        )
        if worst <= ready_distance:
            return np.asarray(point, dtype=np.float64)
        # Walk back along the same line until the furthest shoulder is inside
        # the waiting distance. The direction is what the drill asked for and
        # is preserved; only how far out she holds it changes.
        low, high = 0.0, 1.0
        for _ in range(40):
            middle_step = (low + high) / 2.0
            candidate = middle + along * middle_step
            if max(
                float(np.linalg.norm(candidate - np.asarray(place, dtype=np.float64)))
                for place in shoulders.values()
            ) > ready_distance:
                high = middle_step
            else:
                low = middle_step
        return middle + along * low

    def ready_point(number: int) -> np.ndarray:
        """Where she waits.

        Aimed at the passer by default, which is the manual's hands up and in
        front, showing the arm span. A drill may say otherwise: a high deflect
        waits with the hands beside the head, and aiming those at a passer
        standing two metres away put them at her waist.
        """
        if ready_offset is not None:
            return within_every_shoulder(
                number,
                toward(
                    number,
                    athlete_frames[number].place(ready_offset),
                    ready_distance,
                ),
            )
        return within_every_shoulder(number, toward(number, flight[0], ready_distance))

    def carried_at(number: int) -> np.ndarray:
        return carry_frames[number].place(
            sample_offsets(carried_phases, carried_offsets, phases[number])
        )

    # Where the ball is when she lets go, and how fast. A released ball keeps
    # the speed she gave it, which is what makes the pass back a pass rather
    # than the ball stopping in mid air.
    #
    # The return answers the pass along its own corridor: it goes back to the
    # passer, at the speed the passer used. The manual asks for exactly that on
    # these drills, in the cues "pass it straight back" and "use the momentum of
    # the catch to pass the ball back straight away".
    #
    # Nothing here is typed. The passer's hand, the arrival point and the flight
    # duration are all already authored in the incoming track, and the return is
    # the same parabola solved the other way round.
    #
    # This replaces a one-frame difference of the carry path. That difference
    # was a fair reading of what was authored, and what was authored was a carry
    # that is almost stationary at the moment of release, so it read 0.36 to
    # 1.22 m/s against an incoming pass of about 6.3. It was also noisy: frames
    # are about 7.5 ms apart, which is a very short base for a derivative.
    thrown_from = None
    if contact is not None and release_phase is not None:
        going = [n for n, phase in enumerate(phases) if phase >= release_phase]
        if going and going[0] > contact:
            first = going[0]
            thrown_from = (
                first,
                carried_at(first),
                return_velocity(ball, stance, carried_at(first), seconds_per_phase),
            )

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
            #
            # It travels at HAND speed, not at ball speed. Driving it with the
            # ball's velocity was harmless while the release was 0.5 m/s, and
            # wrong: on a real 6 m/s return the aim point moved 10 cm a frame,
            # so the hands reached the limit of her reach two frames after the
            # release and the elbow stepped 34 degrees between frames. A
            # follow-through is a distance the arm travels, and the arm has a
            # length. It ends at extension whatever the ball does.
            #
            # So the aim point runs from the ball to the far end of her reach
            # along the pass line, over the follow-through. The far end is
            # found with the same reach rule every other hand target in this
            # module uses, so no distance is invented here and no constant
            # needs a coach.
            speed = float(np.linalg.norm(velocity))
            if speed > 1e-9 and FOLLOW_THROUGH_SECONDS > 0.0:
                extended = toward(
                    number,
                    origin + velocity / speed * reach_limit_cm,
                    contact_distance,
                )
                # Eased out rather than linear, for the mirror of the reason
                # the reach is eased in above: the hands are already moving
                # when she lets go, because they drove the ball, and they come
                # to rest at full extension rather than stopping dead. It also
                # measures better, worst step 11.7 degrees against 15.4, but
                # that is corroboration and not the reason.
                out = min(1.0, at / FOLLOW_THROUGH_SECONDS)
                out = 1.0 - (1.0 - out) ** 2
                along_the_pass = origin + (extended - origin) * out
            else:
                along_the_pass = origin
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
                waiting=ready_point(number),
                state=state,
                holding=holding,
            )
        )
    return Possession(frames=tuple(frames), contact_frame=contact)
