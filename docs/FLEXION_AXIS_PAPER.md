# The twelfth drill: whose assumption is the flexion axis?

`netball_one_hand_high_pass` is absent from the `2413f9d` library. Its `ready`
phase cannot be posed:

    FLEXION_AXIS: r index is set to flex about axis 0, which carries only 0.44
    of the turn: x=18.5 y=-7.2 z=42.2 degrees.

This measures the question and does not answer it. **No change is proposed to
the posing path and the library is not re-rendered.**

## 1. What the job says, and what it does not

`knuckleLimitsDegrees` carries, per digit:

    flexion    {min: -44.7, max: 90.0}
    deviation  {min: -45.8, max: 45.8}
    visibleBendAtFlexionLimit  90.0

**The job never says WHICH component is flexion.** Searching the whole job file
for the string `axis` returns nothing, on any of the twelve.

The axis is `FLEXION_AXIS = {"index": 0, "middle": 0, "ring": 0, "pinky": 0,
"thumb": 2}`, a module constant at `blender_mpfb_reference_catch.py:437`. Its
own comment, four lines above the guard that reads it, says it is "an
assumption about the rig and nothing checked it".

**So the axis is this renderer's assumption, not a convention the job carries.**

## 2. What the hands actually turn about

Measured on all twelve drills, 216 asserted knuckle readings. The share is what
fraction of the LARGEST turned component the named axis carries, so 1.0 means
the named axis is the one that turned most.

    the eleven drills that pose      208 readings, share 1.0000 on every one
    the twelfth                        8 readings, four of them below 0.5

The four are all `one_hand_high_pass/ready`, RIGHT hand:

    digit    share    x        y        z       turned most about
    pinky    0.1912   +1.7     -0.1     +8.7    z
    middle   0.3527   +15.4    -6.2     +43.8   z
    ring     0.3671   +12.1    -3.6     +33.0   z
    index    0.4239    0.0      0.0      0.0    z

**The named axis disagrees with the turning axis on 4 of 216 readings, and all
four are one hand of one phase of one drill.** The assumption holds everywhere
else that has ever been measured.

The guard speaks 39 times over that one hand, because the flexion loop raises
the angle a degree at a time and re-checks. The share FALLS as the flexion
grows — index 0.44, 0.40, 0.37, 0.35 down to 0.34 at x=28.0 z=82.9 — which says
the flexion itself is being applied about z and not about x.

Reproduce the eleven with `python scripts/flexion_axis_survey.py`, which reads
the archived receipts and adds nothing.

## 3. Why that one hand, measured

The flexion does not turn about the bone's own axis. It turns the finger TOWARD
THE BALL, and `within_limits` says so: the aim axis "sits 8 to 16 degrees off
flexion on a finger". So the axis that carries the flexion is decided by where
the ball is relative to the hand.

    ball off the finger line, every gripping phase of the eleven   41.8 to 46.6 deg
    ball off the finger line, one_hand_high_pass/ready right hand       110.9 deg
    ball off the finger line, one_hand_high_pass/lift right hand         46.3 deg

**No overlap.** Every hold in the library asks the fingers to close on a ball
roughly 45 degrees ahead of where they point. This one asks them to close on a
ball more than a right angle BEHIND where they point, and the aim plane swings
round with it.

The job sends that hand as fingers 7.4 degrees off straight up, with the palm
facing across the body. It is a rolled wrist under a high ball, not an extreme
reach.

## 4. The options, and what each would cost the eleven

**Every option below leaves the eleven drills' receipts unchanged, and that is
measured rather than assumed: on 208 of 208 readings the axis the guard names is
already the axis that turned most, so any rule that chose the axis by what
turned would choose the same one.** Only the refused hand moves.

### A. The guard reads the axis from the job

**This one cannot be done alone.** The job carries no axis, so A requires B
first. Stating it as a separate option overstates the number of choices
available: there are two, not three.

### B. The job carries the axis

The engine would name which component is flexion. **A measured objection:** the
axis is a property of THIS rig's bone frame, and the engine solves on MHR. The
repository's own rule for this boundary is in `docs/HANDOFF_RENDERING.md`: "A
POSE crosses this boundary as geometry, because a rotation only means something
against the rest pose it was measured in and the two rigs do not share one. A
RANGE OF MOTION crosses as a rotation." An axis index is neither: it names a
component of a euler decomposition in a skeleton the engine has never seen.

### C. The limit is applied about the axis that turned

The guard stops naming an axis and measures one. On the eleven this is
identical, by the 208 of 208 above. On the refused hand it would let the flexion
proceed with the 90-degree flexion licence applied to the 82.9 degrees about z,
and the deviation licence to what is left.

**What this pack cannot tell you** is whether that motion IS flexion. The
finger is being turned through more than a right angle to reach a ball behind
it. Option C would draw the figure; it would not establish that the figure is
anatomically right, and the guard exists precisely because a wrongly named axis
lets a joint run past its licence without raising.

### A fourth possibility the brief did not list

**The pose may be the defect rather than the axis.** A grip that asks the
fingers to close on a ball 110.9 degrees behind where they point is 65 degrees
outside the range every other hold in the library occupies, and the guard may be
catching a target this rig cannot honestly hold rather than an axis wrongly
named. That is the movement lane's grip and this lane does not rule on it. It is
listed because a paper that offered only the three options would have implied
the pose was sound, and nothing here shows that.

## 5. What is not measured

- Whether the engine's own athlete turns that knuckle about the same axis. This
  lane cannot read MHR's knuckle frames.
- What the figure would LOOK like under option C. The pose exists only behind a
  neutralised guard in a probe, and no still has been rendered from it.
- Whether `MIN_AXIS_SHARE = 0.5` is the right threshold. Nothing in the library
  sits between 0.4239 and 1.0000, so the library cannot distinguish 0.5 from any
  value in that gap.

## 6. Instruments

    scripts/flexion_axis_survey.py   the eleven, from the archived receipts
    scripts/ball_off_finger_line.py  where the ball sits relative to each hand

Both read what the render already recorded or re-pose without changing the
posing path. The refused frame can only be measured with `axis_complaint`
neutralised, which the probe does for itself and never on disk.
