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

**The job never says WHICH COMPONENT is flexion.** Searching the whole job file
for the string `axis` returns nothing, on any of the twelve.

**It does name the axis ANATOMICALLY, and that distinction is the whole
question.** `docs/HANDOFF_RENDERING.md` documents the field as

    flexion    {min, max}   about the knuckle's own curl axis
    deviation  {min, max}   about the knuckle's own deviation axis, side to side

So the job says which MOTION the licence bounds. It does not say which euler
component of this rig's bone carries that motion, and it should not: the same
document states the boundary rule, that "a RANGE OF MOTION crosses as a rotation
about the anatomical axis, because it is a fact about the joint rather than a
configuration".

The mapping from "the knuckle's own curl axis" to a component index is therefore
the CONSUMER's, and it is `FLEXION_AXIS = {"index": 0, "middle": 0, "ring": 0,
"pinky": 0, "thumb": 2}`, a module constant at
`blender_mpfb_reference_catch.py:437`. The line that reads it is
`axis = FLEXION_AXIS[digit]`, and the comment DIRECTLY BELOW that line says it
is "an assumption about the rig and nothing checked it". The guard it feeds
raises seventeen lines further down.

**So the axis is this renderer's assumption, correctly so, and the defect is
that the assumption is fixed rather than measured.**

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

**This one cannot be done alone.** The job names the axis anatomically and
carries no component index, so there is nothing for the guard to read and A
requires B first. Stating it as a separate option overstates the number of
choices available: there are two, not three.

### B. The job carries the axis

The engine would name which component is flexion. **This is refuted by a rule
the repository already carries, not by an opinion.**
`docs/HANDOFF_RENDERING.md` states that a range of motion crosses the boundary
"as a rotation about the anatomical axis, because it is a fact about the joint
rather than a configuration", and the field already does that: it bounds the
motion about the knuckle's own curl axis.

A component index is a different kind of thing. It names a coordinate of a euler
decomposition of a bone in a skeleton the engine has never loaded. Sending it
would put a fact about the CONSUMER's rig into the producer, which is the same
error, in the other direction, as the shoulder positions this lane asked for in
metres on 4 September and had to withdraw.

The first version of this field already broke that rule once, by exporting a
range of motion as visible bend. It never shipped.

### C. The limit is applied about the axis that turned

**RULED ON 2026-09-09 BY THE ORCHESTRATOR. This is the option.** Recorded here
rather than in a message, because a ruling that lives in a message is a ruling
nobody can find.

**THE LIMITATION OF THE RULING, WHICH IS NOT A CAVEAT ON THE OPTION.** C would
draw the figure. It would not show the figure is anatomically right. The guard
exists because a wrongly named axis lets a joint run past its licence silently,
and **C does not restore that protection for this drill. It moves the question**
to whether that grip is a pose this engine should hold, which is the fourth
possibility below and is the movement lane's.

**NOT IMPLEMENTED, and deliberately.** The fourth possibility is open with that
lane, and implementing C first would draw a figure whose pose may be the actual
defect. The ruling settles which option, not when.

This is the only option that keeps the boundary rule intact, because it changes
nothing about what crosses it: the job keeps bounding the motion about the
knuckle's own curl axis, and the consumer stops ASSUMING which component that is
and measures it instead.

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

## 5. The consequence for the coach morning, which nobody has connected

**THE REFUSAL IS NOT A LIBRARY GAP. IT IS A MORNING ITEM WITH NO PICTURE.**

`netball_one_hand_high_pass` is item 13 of `docs/COACH_MORNING_2026-09.md`, and
that item opens: "**What she can see.** The ball taken up on one arm to the top
of its reach, a step, the release, and the arm coming through."

**There is no render of that drill anywhere.** Two searches agree, one by file
name and one by content:

    .assets/archives, all three sets              absent
    every worktree's out/, 940 stills and 16 clips absent
    spikes/movements/, the authored definition     PRESENT
    spikes/poc-output/, the job file               PRESENT

**THE ARCHIVES ARE THE AUTHORITY AND THE WORKTREE SWEEP IS NOT.** Nine worktrees
were swept at their current tips and none was fetched first, so that row is an
absence in those trees as they stood. The archives decide the question, and they
sit at `.assets/archives`, outside every checkout.

So the drill is authored and jobbed and never drawn, and the cause is the
refusal this paper measures. The archive's own `PROVENANCE.md` records the
absence correctly. **What no document connects is the agenda item on the other
side of it.**

**AND THE RUNNING ORDER PLACES IT IN A BLOCK IT BELIEVES IS SAFE.**
`docs/COACH_MORNING_RUNNING_ORDER.md` puts item 13 in block 3 and says of that
block: "none needs a render, so none can be blocked by a missing artefact". Its
artefact table marks item 13 **ready**, needing "the drill's own figures".

**Three of that block's four items are fine and the fourth is not.** Item 12's
`bounce_pass` has 15 stills in the archive, and item 16's `double_foot_landing`
has 12. Item 13's drill has none.

**AND ITEM 10 DEPENDS ON IT.** The running order's own reason for placing item 10
last is that it "needs her answer to item 13". So a question in block 4 waits on
a question in block 3 that has nothing to show.

This lane states the fact and proposes no change to the running order. **What it
does say is that the option chosen in section 4 decides whether item 13 has a
picture at all**, which makes this a morning decision rather than a library
tidy-up.

## 6. What is not measured

- Whether the engine's own athlete turns that knuckle about the same axis. This
  lane cannot read MHR's knuckle frames.
- What the figure would LOOK like under option C. The pose exists only behind a
  neutralised guard in a probe, and no still has been rendered from it.
- Whether `MIN_AXIS_SHARE = 0.5`, at `finger_curl.py:147`, is the right threshold. Nothing in the library
  sits between 0.4239 and 1.0000, so the library cannot distinguish 0.5 from any
  value in that gap.

## 7. Instruments

    scripts/flexion_axis_survey.py   the eleven, from the archived receipts
    scripts/ball_off_finger_line.py  where the ball sits relative to each hand

Both read what the render already recorded or re-pose without changing the
posing path. The refused frame can only be measured with `axis_complaint`
neutralised, which the probe does for itself and never on disk.
