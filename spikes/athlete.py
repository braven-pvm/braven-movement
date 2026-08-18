"""Build an athlete of a given size, so the library can be run on more than one.

Everything in this repository is written in arm lengths precisely so that a
movement authored on one body carries to another. That claim has never been
exercised. Every drill, every measurement and every coaching band has only ever
been produced by the one reference body the model ships with, which is 172.8 cm
tall with a 52.7 cm arm.

A coach's squad is not one body. This module makes the others.

MHR carries the size of a body in its scale parameters, separately from its
pose. Seven of the sixty-eight change the athlete's height or her reach:

    scale_spine_length  scale_neck_length  scale_uplegs  scale_lowlegs
    scale_foot_length   scale_uparms       scale_lowarms

They are lengths, near enough linear, at about ten centimetres per unit. The
solver must never touch them, and does not: they are in FORBIDDEN, so an
athlete keeps her proportions however hard a target pulls.

Arm span is set separately from height on purpose. Two players of the same
height with different reach is the case that tells you whether a drill written
in arm lengths really travels, and it is common: reach varies by about a tenth
either side of height across a squad.

The model has its own opinion about what bodies exist. Each scale parameter has
a range, and together they cover roughly 158 cm to 201 cm. That is a real limit
on who this tool can be pointed at: it does not reach a junior squad, where 145
to 160 cm is normal. Asking for a body outside it says so rather than quietly
building the nearest one it can.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# The parameters that make a body bigger, and how much of the height each one
# carries. Arms are held out because reach is set on its own.
STATURE = (
    "scale_spine_length",
    "scale_neck_length",
    "scale_uplegs",
    "scale_lowlegs",
    "scale_foot_length",
)
# The hands go with the arms. Leaving them out gave a 158 cm athlete the
# reference athlete's hands, which is both wrong and quietly changes the grip:
# the palm meets the ball at a fixed 3.5 cm of skin whatever the body.
REACH = ("scale_uparms", "scale_lowarms")
HANDS = ("scale_l_hands", "scale_r_hands")

# How close the built athlete has to come to the height that was asked for.
# A millimetre, which is finer than anyone measures a person.
TOLERANCE_CM = 0.1
MAXIMUM_PASSES = 12


class AthleteError(ValueError):
    pass


@dataclass(frozen=True)
class Athlete:
    """One body, as a set of model parameters the solver will not move."""

    name: str
    identity: np.ndarray
    height_cm: float
    arm_cm: float

    def describe(self) -> str:
        return (
            f"{self.name}: {self.height_cm:.1f} cm tall, {self.arm_cm:.2f} cm arm, "
            f"reach {self.arm_cm / self.height_cm:.4f} of height"
        )


def measure(character, identity: np.ndarray) -> tuple[float, float]:
    """Return this body's height and arm length, in centimetres."""
    from motion_track import arm_length
    from movement_engine import joint_positions

    names = list(character.skeleton.joint_names)
    index = {name: number for number, name in enumerate(names)}
    points = joint_positions(character, np.asarray(identity, dtype=np.float32))
    height = float(points[:, 1].max() - points[:, 1].min())
    return height, arm_length(points, index)


def minmax_limits(character) -> dict[str, tuple[float, float]]:
    """Return each parameter's own range, by name.

    This lives here rather than with the solver because it is a fact about the
    body, and because the solver cannot be imported without the solver.
    """
    names = list(character.parameter_transform.names)
    found: dict[str, tuple[float, float]] = {}
    for limit in character.parameter_limits:
        if str(limit.type) != "LimitType.MinMax":
            continue
        data = limit.data.minmax
        number = int(data.model_parameter_index)
        if 0 <= number < len(names):
            found[names[number]] = (float(data.min), float(data.max))
    return found


def hand_length(character, identity: np.ndarray) -> float:
    """Wrist to middle knuckle, which is what sets the palm and the grip."""
    from movement_engine import joint_positions

    names = list(character.skeleton.joint_names)
    index = {name: number for number, name in enumerate(names)}
    points = joint_positions(character, np.asarray(identity, dtype=np.float32))
    return float(
        np.linalg.norm(points[index["l_middle1"]] - points[index["l_wrist"]])
    )


def reference(character) -> Athlete:
    """The body the model ships with, and everything so far was authored on."""
    identity = np.zeros(character.parameter_transform.size, dtype=np.float32)
    height, arm = measure(character, identity)
    return Athlete("reference", identity, height, arm)


def _set(character, identity: np.ndarray, names, value: float) -> float:
    """Set these parameters, held inside the ranges the model allows.

    Without the clamp the foot length, whose range is only a tenth either way,
    goes 55 units past its limit while the spine is still comfortable, and the
    result is a body the model does not support wearing a pose that looks fine.
    """
    order = list(character.parameter_transform.names)
    limits = minmax_limits(character)
    for name in names:
        if name not in order:
            continue
        low, high = limits.get(name, (-1e9, 1e9))
        identity[order.index(name)] = max(low, min(high, value))
    # The requested value, not the clamped one. These are set in groups whose
    # limits differ, so there is no single applied value to report: the foot
    # saturates at a tenth while the spine is still going. Saturation is for
    # the solver to notice, which it does when two different requests give the
    # same measurement.
    return value


def supported_heights(character) -> tuple[float, float]:
    """The shortest and tallest body this model will make, in centimetres."""
    smallest = np.zeros(character.parameter_transform.size, dtype=np.float32)
    largest = smallest.copy()
    _set(character, smallest, STATURE + REACH, -1e9)
    _set(character, largest, STATURE + REACH, 1e9)
    return measure(character, smallest)[0], measure(character, largest)[0]


def _solve(apply, read, target_cm: float, label: str, strict: bool = True) -> float:
    """Return the parameter value that hits this measurement.

    A secant, because the scale parameters are near enough linear but not
    exactly, and because guessing the slope got it wrong: five stature
    parameters moving together are worth about 28 cm per unit, not the 10 that
    one of them is worth on its own, so a Newton step sized by the wrong slope
    oscillated and never arrived.
    """
    lo, hi = 0.0, 0.5
    lo = apply(lo)
    at_lo = read() - target_cm
    best, at_best = lo, abs(at_lo)
    for _ in range(MAXIMUM_PASSES):
        hi = apply(hi)
        at_hi = read() - target_cm
        if abs(at_hi) < at_best:
            best, at_best = hi, abs(at_hi)
        if abs(at_hi) <= TOLERANCE_CM:
            return hi
        if abs(at_hi - at_lo) < 1e-9:
            break
        lo, at_lo, hi = hi, at_hi, hi - at_hi * (hi - lo) / (at_hi - at_lo)
    if strict:
        raise AthleteError(
            f"{label}: could not reach {target_cm:.1f} cm, closest was "
            f"{target_cm + at_best:.1f}"
        )
    # A hand that cannot grow all the way is worth reporting, not refusing.
    apply(best)
    return best


def build(
    character,
    name: str,
    height_cm: float,
    reach_ratio: float = 1.0,
) -> Athlete:
    """Return an athlete of this height, with reach scaled by this ratio.

    ``reach_ratio`` is relative to the reference body's own proportions, so 1.0
    is a normally proportioned player of that height, 1.10 is a long armed one
    and 0.90 is short armed.

    Height and reach are solved separately because they are independent: not
    one of the seven length parameters changes both.
    """
    # Checked before anything is measured, so refusing a nonsense height does
    # not need a body loaded first.
    if height_cm <= 0.0:
        raise AthleteError(f"{name}: a height of {height_cm} cm is not a person")
    base = reference(character)
    base_hand = hand_length(character, base.identity)
    shortest, tallest = supported_heights(character)
    if not shortest - TOLERANCE_CM <= height_cm <= tallest + TOLERANCE_CM:
        raise AthleteError(
            f"{name}: {height_cm:.1f} cm is outside the {shortest:.1f} to "
            f"{tallest:.1f} cm this model makes. It does not reach a junior "
            "squad."
        )

    identity = np.zeros(character.parameter_transform.size, dtype=np.float32)
    _solve(
        lambda v: _set(character, identity, STATURE, v),
        lambda: measure(character, identity)[0],
        height_cm,
        f"{name} height",
    )
    wanted_arm = base.arm_cm * (height_cm / base.height_cm) * reach_ratio
    _solve(
        lambda v: _set(character, identity, REACH, v),
        lambda: measure(character, identity)[1],
        wanted_arm,
        f"{name} reach",
    )
    _solve(
        lambda v: _set(character, identity, HANDS, v),
        lambda: hand_length(character, identity),
        base_hand * (wanted_arm / base.arm_cm),
        f"{name} hand",
        strict=False,
    )

    height, arm = measure(character, identity)
    return Athlete(name, identity, height, arm)


def squad(character) -> list[Athlete]:
    """A range wide enough to break anything that does not scale.

    Under-13 through senior, and two players of the same height whose reach
    differs by a tenth either way, because that is the pair that tells you
    whether a drill written in arm lengths really travels.
    """
    shortest, tallest = supported_heights(character)
    return [
        reference(character),
        build(character, "smallest", shortest),
        build(character, "senior", 190.0),
        build(character, "short arms", 172.8, reach_ratio=0.90),
        build(character, "long arms", 172.8, reach_ratio=1.10),
    ]
