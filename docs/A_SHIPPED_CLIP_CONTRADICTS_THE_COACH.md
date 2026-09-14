# A shipped clip contradicts the coach, and has for fifteen days

Written 2026-09-14. Measured on movement main `1624678` and tactics main
`9e77f25`.

**A coach graded a drill blind, wrote down what was wrong with it, the engine
was corrected to agree with her, and the file every board draws from still
carries the verdict she rejected.**

This is not a defect report. Nothing is broken. A correct, coach-driven, fully
documented fix landed on 2026-08-30 and the artefact in the other repository
never heard about it.

## The finding

`public/figures/clips.json` in Braven Tactics ships
`catch.netball.one-hand-snatch` with `graded: true`.

Braven Movement grades that same drill **false** today, and has since
2026-08-30. It fails one of its nine checkpoints:

    phase    contact
    measure  leftElbowFlexionDegrees
    measured 146.01
    band     [30.0, 120.0]
    verdict  ABOVE, by 26 degrees on a 90-degree band
    cue      "Other hand stays ready, close to the ball, not chasing it."

**The band has not moved.** `spikes/movements/netball_one_hand_snatch_to_other_hand.json`
was last changed on 2026-08-18, before the clip was exported. The measured pose
changed, not the rule it is judged against.

## The consequence, which is worse than a wrong field

`graded` is what lets a board **refuse to draw a technique that failed its own
definition**. That is its only purpose.

Since 2026-08-30 the shipped file has told every board that this technique met
its coaching definition. **The refusal has not been able to fire.** A board that
would have declined to draw this drill has had no way to know it should.

## The cause, named by a bisect and convicted by a revert

**`56fbb6c4726ea5f5b1ef194b99ead6ea8ed78c55`, 2026-08-30, "fix(spikes): the free
hand waits at the chest, not out at the passer".** Two files,
`spikes/possession.py` and `spikes/possession_solve.py`.

Bisected over the **563** commits between `f0172cf`, the build the Tactics commit
message names as the source of the shipped clips, and main. Ten steps, no skips.
The criterion was that one checkpoint, not the suite and not the clip bytes.

**The readings are strictly bimodal**: every commit reads either **89.64 within**
or about **146 above**, and nothing lies between them. A quantity drifting under
an accumulation of changes gives a spread. Two values and a step means one cause,
and that is known before anything is reverted.

Every commit probed, in date order:

    f0172cf  2026-08-27   89.64  within   the build the shipped clips came from
    346441a  2026-08-28   89.64  within
    b8d68fa  2026-08-28   89.64  within
    8e05507  2026-08-28   89.64  within
    56fbb6c  2026-08-30  146.13  above    <- FIRST BAD
    60b1795  2026-08-30  146.13  above
    d2abb99  2026-08-30  146.13  above
    ac3b400  2026-08-31  146.13  above
    1df5e52  2026-08-31  146.01  above
    2b55bcd  2026-09-02  146.01  above
    42abc11  2026-09-07  146.01  above
    1624678  2026-09-14  146.01  above    main today

**Then reverted rather than merely suspected.** At `56fbb6c`, with that one
commit reverted in place and nothing else changed, the value returns to exactly
**89.64** and the verdict to **within**. A bisect names a suspect; a revert
convicts it.

### Two hypotheses were offered before the bisect, and both were wrong

`a78a05f` and `d973cc1`, the 2026-09-07 commits touching `build_library.py`, one
of them a units fix. A units fix moving a measurement in degrees is plausible,
and plausible is exactly what a bisect exists to replace. **The cause is eight
days earlier and is not a units fix at all.** This is recorded because a
write-up that quietly drops its disproved hypotheses teaches nobody.

## Why the change was right

From the convicted commit's own message:

> Erin Burger graded the library blind on 2026-08-30 and marked the two
> one-handed drills down. Her notes say the same thing twice, unprompted: on the
> one-hand snatch, "Don't want other hand to go away from centre of body towards
> ball."

The free hand's target had been `ready_point`, which is the **catching** hand's
ready position: aimed at the passer, at full waiting distance, because that hand
has to meet the ball. Spent on the free hand it asked the free hand to reach for
the ball as well. The fix parks it at the last carry key, in her own frame, so it
follows her turn instead of being crossed by it. The free hand's reach on this
drill moves from 0.69 to 0.23 of reach.

And the commit predicted this exact flip, in these words:

> ONE verdict flips: one_hand_snatch_to_other_hand, contact,
> leftElbowFlexionDegrees, 89.64 to 146.13 against a band of 30 to 120, so
> "within" becomes "above". **Erin marked that same checkpoint NOT met. The
> engine now agrees with her. The band is untouched.**

**So the shipped `graded: true` is the error.** It is the reading from before the
coach was listened to.

## What this does NOT explain

**The bisect criterion was the verdict, so this explains the verdict and nothing
else.**

All nine technique clips were re-exported from main and compared field by field
against what is shipped. Eight of the nine have moved:

| clip | largest frames change | largest ball change | other |
|---|---|---|---|
| block.netball.deflect-high | 0.659 | 0.0116 | — |
| catch.netball.hooks-jump | 0.551 | 0.0022 | — |
| catch.netball.hooks-outside-hand | 1.241 | 0.0049 | `rootTravelM` |
| catch.netball.one-hand-snatch | 0.991 | 0.0107 | **`graded` true → false** |
| catch.netball.two-hand-chest | 0.285 | 0.0016 | — |
| catch.netball.two-hand-snatch | 0.594 | 0.0010 | — |
| catch.netball.two-hand-snatch-back | 0.594 | 0.0011 | — |
| land.netball.double-foot | 0.550 | 0.0013 | — |
| **pass.netball.chest-pass** | **0.000** | **0.0000** | — |

Degrees for frames, arm lengths for ball, so 0.0116 is about 0.7 cm. Frame counts
are unchanged everywhere and the eighteen capture clips are byte-identical.

**The chest pass at exactly zero is the positive control.** A clip exported this
morning reproduces bit for bit through the same tool, the same environment and
the same lock, so the method is not what is moving. Without that row every number
in the table would be a candidate artefact of the measuring pipeline.

**The residual pose drift on the other seven is open and unbisected.** The
convicted commit's own message claims "Six drills are unchanged. Their worst hand
step per frame moves by at most 0.01 cm", and the table above shows 0.28 to 1.24
degrees. Those are different quantities and they may be consistent, but nothing
here has established that. **One cause is named. The rest of the table is not
explained by it.**

## A thing that could not be reconciled, recorded rather than smoothed

**No drawn channel in that clip moved more than 0.99 degrees, yet the graded
elbow crossed a 90-degree band by 26.**

Elbow flexion is not one of the fifteen drawn channels. Those are bob, lean,
twist, limb swing and limb out. **So the pose a board draws and the pose a coach
grades are not the same reading, and nothing here bounds how far apart they can
drift.** That is a separate finding, it is bigger than this clip, and the bisect
does not answer it.

## Two loose ends

- The convicted commit predicted **146.13** and main measures **146.01**.
  Something moved the same value by 0.12 degrees afterwards. The bisect readings
  bound it without being aimed at it: `ac3b400` still reads 146.13 and `1df5e52`
  reads 146.01, **and both are dated 2026-08-31**. So the second change lies
  between those two commits. It has not been identified, and 0.12 degrees does
  not move this verdict either way.
- That commit recorded one failing test at the time, `test_elbow_pole`'s mean
  contact separation at **41.68 cm** against the manual's **38.6**, referred
  upward on 2026-08-30 rather than adjusted, because the angle it guards was
  calibrated on that mean. Whether that was ever resolved is not established
  here.

## Why nobody saw it

**Not one of the eight older clips can say which build made it.** The field that
answers that question was added to Movement on 2026-09-14 and crosses the
boundary from that date. To date these clips at all, the build had to be
reconstructed from a commit message in the *other* repository — the exact
reconstruction the field exists to abolish.

## The options, with their costs

**No recommendation is made here.** Whether a board should draw a technique the
coach failed is a coaching decision and not this lane's to take.

1. **Leave the shipped clip as it is.** No work. The file continues to state a
   verdict the coach rejected, and the refusal cannot fire.
2. **Re-export the clip from main.** Restores the true verdict. It also ships the
   pose drift in the same change, and that drift is unexplained — a behavioural
   change inside a correctness change is the kind nobody reads.
3. **Correct only the `graded` flag in `clips.json`, by hand.** Makes the verdict
   true without shipping the drift. It also makes the file a thing no build
   produces, so the stamp it will carry would name a build that did not write it.
4. **Re-export, after the residual drift is bisected and understood.** The
   slowest, and the only one where both the verdict and the pose are explained
   before they ship.

Options 2 and 3 both raise the same question: a clip whose `graded` is false is a
technique a board may decline to draw, so the drill may stop being drawn at all.
That consequence belongs with the decision.
