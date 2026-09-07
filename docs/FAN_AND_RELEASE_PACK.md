# Fan figures, release stills, and the wrist question

Measured on the shipped library `2413f9d`, archived at
`.assets/archives/coach-figures-2413f9d`. Every pose in this pack was checked
against that archive's own receipts before a number was read from it: a fan
measured on a pose that is not the shipped one is not a measurement of the
figures. All 48 phases matched.

## 1. The fan figures, and why the published number was wrong twice

**The worst fan gap where the job asks for a symmetric hold is 0.0559 cm, at
`one_hand_snatch_to_other_hand/pull_in`.** This lane previously published
0.095 cm at `deflect_high/contact`. Both the instrument and the population were
wrong.

### The instrument posed under the wrong limits

`scripts/fan_mirror_check.py` posed each phase with the CONFIG's anatomy limits
and `None` for the knuckle limits. `render_job` passes the JOB's own. So every
fan number this lane published was taken under different limits from the figures
a coach was going to see.

That is the same lever that produced a false non-reproduction on
`one_hand_high_pass` earlier the same day. The instrument now poses exactly as
`render_job` does, and proves it by comparing its own girdle report against the
archived receipt before reading a fan.

### "Both hands grip" was a label, not a measurement

The mirror claim was scoped to phases where both sides appear in `grip`. That is
a label. `bounce_pass/pull_to_side` carries a grip on both sides and asks for one
**44.5 degrees away from a mirror**, with reach fractions of 0.2674 against
0.5040. Pulling a ball to one side is asymmetric by design, and its 0.27 cm fan
gap is the drill.

`deflect_high/contact` — the phase whose 0.095 cm was published as the library's
worst mirror gap — is **27.3 degrees askew**. It should never have been in the
population.

Symmetry is now measured. `mirror_error_degrees` reads the angle between
`outward.r` and `outward.l` reflected across the body. On the 24 gripping phases
the spread is 0.0 degrees on eighteen of them, then 2.8, 4.7, 7.8, 16.2, 16.4,
27.3 and 44.5. The threshold is 5 degrees, taken from the widest gap in that
run, and **the answer does not depend on it**: at 10 degrees the phase at 7.8
joins the population and its gap is 0.001 cm, so the worst is unchanged.

### The drift claim is also corrected

This lane said moving the ball moved the fan by "nearly three times" the gap the
figures report. Measured on the shipped poses, raising the ball by the overhead
pass's own girdle travel of 7.40 cm moves the fan by up to **0.3757 cm**, which
is 6.7 times the 0.0559 cm gap, not three. The direction of the caution was
right and the size was wrong.

**The figures can now be published.** The reason they were held was that the
ball was about to move. It has moved, these are the poses it moved to, and the
instrument proves each one is the shipped pose.

Reproduce with
`blender -b -P scripts/fan_mirror_check.py -- --archive coach-figures-2413f9d`.

## 2. The release stills

**They are three, not two.** `bounce_pass` is new on main and carries the same
defect. From the archive's own receipts:

    drill / phase             holding   vertices inside   deepest
    chest_pass/release          False               190   -20.27 mm
    bounce_pass/release         False               120   -17.76 mm
    overhead_pass/release       False                78    -9.55 mm

    hooks_jump_pull_in/release  False                 0     clean
    two_hand_catch_chest/release False                0     clean

Every deep intersection in the whole library is a `holding: False` frame. The 16
other phases with any vertex inside are all HOLDING phases at 0.05 to 1.65 mm,
which is the fingers pressing on the ball surface and is what a grip looks like.

The stills are in the archive as
`netball_{chest,bounce,overhead}_pass.release.{front,quarter,side}.png`, nine
files.

**The girdle fix did not remove this and slightly worsened it.**
`chest_pass/release` was 150 vertices at −17.08 mm before the fix and is 190 at
−20.27 mm now. That follows: the fix moved the shoulders, and the non-holding
formula is measured from the shoulder.

## 3. The wrist question, with numbers beside each option

**This lane does not choose.** The encoding is a contract question.

The renderer picks between two formulae on `ball.holding`:

    not holding   shoulder + direction * (reachFraction * reach)
    holding       ballCentre + outward * (radius + wristFromSurfaceInArms * reach)

`holding` goes False AT the release frame, so the formula changes in one frame.
The two agree to 0.000 mm on the body the engine solves, because that is where
they were authored, and they do not agree on this one, because the ball's radius
is one absolute size and does not scale with the athlete.

    drill / phase          option          inside   deepest   the wrist moves
    bounce_pass/release    A pick             120   -17.76
                           B ball-relative      6    -0.59            49.4 mm
    chest_pass/release     A pick             190   -20.27
                           B ball-relative      0     0.00            41.7 mm
    overhead_pass/release  A pick              78    -9.55
                           B ball-relative     32    -2.62            34.0 mm

**Option A is what ships today.** The wrist leaves the ball in a single frame,
and the ball passes through the hand on the way out. A coach sees the ball
inside the fingers at the moment of release on three of the library's five
release phases.

**Option B keeps the ball deciding for that frame.** The intersection nearly
disappears, and on the chest pass it goes to zero. The cost is that the wrist
sits 34 to 49 mm from where `arms` asked for it, so the arm a coach reads is no
longer the arm the solve graded.

Neither is free. A coach reads a release for whether the hands leave the ball
together and where they point, and the two options damage different halves of
that. Option B was measured in its crudest form — the previous phase's grip
carried one frame forward — and is not a proposal for how a blend would be
written.

Reproduce with `blender -b -P scripts/wrist_release_options.py --`.

## 4. Not in this unit

- The clavicle normalisation stays the movement lane's, queued behind Pack B.
- The render-loop abort fix is queued and not started.
