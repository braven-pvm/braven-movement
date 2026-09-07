# Fan figures, release stills, and the wrist question

Measured on the shipped library `2413f9d`, archived at
`.assets/archives/coach-figures-2413f9d`. Before a number is read from a pose,
the instrument checks that pose against the archive's own receipt and RAISES if
it differs. It pins the job's digest, the girdle and the hands — not everything
a picture contains, and section 1 says exactly what. All 48 phases passed.

## 1. The fan figures, and what actually moved the number

**The worst fan gap where the job asks for a symmetric hold is 0.0559 cm, at
`one_hand_snatch_to_other_hand/pull_in`.** This lane previously published
0.095 cm at `deflect_high/contact`.

### What moved it was the POPULATION, not the limits

An earlier draft of this section said the fan instrument had been posing under
the wrong limits and that "every fan number this lane published was taken under
different limits from the figures a coach was going to see". **That is
withdrawn.** It was a claim about a cause, and nobody measured whether the cause
moved a number.

Posing all 48 shipped phases BOTH ways — the old call with the config's anatomy
limits and `None` knuckle limits, the new call with the job's own — gives a
largest fan difference of **0.000000 cm**. All twelve jobs carry anatomy limits
identical to the config, and no knuckle reaches its licence on these phases. The
fault is real and it is LATENT: it would bite the first job whose limits differ.
It is fixed, and it explains nothing here.

What did move the published number:

- **The population was wrong.** "Both hands grip" is a LABEL.
  `deflect_high/contact`, the phase that gave 0.095, is **27.3 degrees off a
  mirror**. `bounce_pass/pull_to_side` grips on both sides and asks for a hold
  **44.5 degrees** off a mirror, with reach fractions 0.2674 against 0.5040;
  pulling a ball to one side is asymmetric by design and its 0.27 cm gap is the
  drill.
- **The library moved.** `deflect_high/contact` itself reads 0.085 cm on this
  library against 0.095 on `aa3f244`, under EITHER call. That is the girdle fix
  moving the poses.

### Symmetry is measured, and the threshold is not load-bearing

`mirror_error_degrees` reads the angle between `outward.r` and `outward.l`
reflected across the body. On the **25** gripping phases the spread is 0.0
degrees on eighteen of them, then 2.8, 4.7, 7.8, 16.2, 16.4, 27.3 and 44.5.

The threshold is 5 degrees. **The answer holds from 5 to 20 degrees** — the
phases at 7.8, 16.2 and 16.4 have gaps of 0.001, 0.037 and 0.017 cm — and it
BREAKS at 30, which admits `deflect_high/contact` at 27.3 degrees and 0.085 cm.
An earlier draft said the widest gap in the run was 4.7 to 7.8; it is 27.3 to
44.5, and 4.7 to 7.8 is only the widest below 10.

### The drift, in one population

Raising the ball by the overhead pass's own girdle travel of 7.40 cm moves the
fan, on the SAME symmetric-hold population, by up to **0.0830 cm** at
`two_hand_snatch_pull_in/contact`, which is **1.48 times** the 0.0559 cm gap.

An earlier draft said 0.3757 cm and 6.7 times. That drift is real but it is at
`bounce_pass/release`, a NON-HOLDING frame whose fan no mirror claim covers, so
dividing it by a symmetric-hold gap crosses two populations. The original claim
of "nearly three times" is withdrawn in both directions: within one population
it is 1.48.

### The gate, and what it pins

`pose_girdle` runs before the limits, the ball, the arms and the hands are
touched, so a girdle comparison alone cannot see a change to any of them. An
earlier draft claimed this instrument "PROVES each pose is the shipped one". It
did not, and its result only fed a printed row, so a run with 48 mismatches
still exited 0.

It now RAISES, and it pins three things:

    the job's sha256 against the receipt's `jobSha256`   the INPUTS
    girdle ballAnchorErrorMm and worstOffsetMm            the girdle
    each hand's wrist bend, forearm roll, palm error      the HANDS

The third is the one a fan claim needs. Perturbing a phase's `palmNormal` moves
the forearm roll from 52.0 to 5.0 degrees and the gate raises on the wrist bend,
34.67 against the archive's 38.18. It still does not pin everything a picture
contains; it pins the inputs, the girdle and the hands.

**The figures can be published.** The reason they were held was that the ball
was about to move. It has moved, and these are the poses it moved to.

Reproduce with
`blender -b --python-exit-code 9 -P scripts/fan_mirror_check.py -- --archive coach-figures-2413f9d`.

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

**The girdle fix did not remove this and worsened BOTH phases it could.** From
the `coach-figures-aa3f244` archive's own receipts, against this library:

    chest_pass/release      150 at -17.08 mm  ->  190 at -20.27 mm
    overhead_pass/release    52 at  -6.72 mm  ->   78 at  -9.55 mm
    bounce_pass/release      not in that library, the drill is new

That follows: the fix moved the shoulders, and the non-holding formula is
measured from the shoulder. An earlier draft reported only the chest pass and
gave its prior figures without naming the archive they came from.

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
