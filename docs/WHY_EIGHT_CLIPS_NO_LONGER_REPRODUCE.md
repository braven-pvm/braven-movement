# Why eight shipped clips no longer reproduce, and why nothing is broken

Written 2026-09-14. Measured on movement main `0353b76` and the shipped arrays
in tactics `6e01e82`.

Eight technique clips shipped to Braven Tactics on 2026-08-27, exported from
movement `f0172cf`. **The engine no longer produces them.** All eight differ,
by 0.28 to 1.24 degrees in the drawn channels, and one of them carries a
coaching verdict the engine has since reversed.

**Two commits account for it. Both are correct fixes, both landed on the evening
of 2026-08-30, and they are ninety-six minutes apart.** Neither is a regression.
This is a record of the library's history, not a defect report.

The verdict flip has its own document,
`docs/A_SHIPPED_CLIP_CONTRADICTS_THE_COACH.md`. This one is about the pose.

## The method: measure the shape before bisecting

**A bisect assumes ONE transition.** Eight clips moving by a fraction of a
degree is as consistent with an accumulation of many small changes as with a
step, and a bisect run over an accumulation converges on whichever commit is
merely the largest. It then hands the next reader an authoritative-looking hash
that means nothing.

So the range was SAMPLED first, at nine points across the eighteen days, on the
clip that had drifted furthest. Four probes:

    f0172cf  2026-08-27   0.0000   exact
    25457b5  2026-08-27   0.0000   exact
    1df5e52  2026-08-31   1.2390
    a69730e  2026-09-02   1.3110
    b0f762d  2026-09-02   1.2410
    2f1a4f8  2026-09-07   1.2410
    4e189f3  2026-09-08   1.2410
    d8f62c3  2026-09-09   1.2410
    575d244  2026-09-09   1.2410
    718023e  2026-09-14   1.2410

Two values and a flat run: a step. **A drift gives a spread; a step gives two
values.** That is known before anything is reverted, and it is what licenses the
bisect that follows.

It cost four probes. Had the readings come back as a spread, it would have saved
ten bisect steps converging on nothing.

## Cause one: `56fbb6c`, 2026-08-30 17:45

**"fix(spikes): the free hand waits at the chest, not out at the passer".**

Six bisect steps over the 69 commits between `25457b5` and `1df5e52`, readings
bimodal at 0.0000 or 1.2420, no skips.

**The decisive test is not the bisect.** At `56fbb6c`, with that one commit
reverted in place and nothing else changed, **all eight clips reproduce what
shipped EXACTLY** — 8 of 8 at 0.0000, with every `graded` flag restored. So at
that moment in the history it is the only cause of any difference in any of
them.

Why it was right is in
`docs/A_SHIPPED_CLIP_CONTRADICTS_THE_COACH.md`: Erin Burger graded the library
blind that day and marked the two one-handed drills down, and the free hand had
been spending the *catching* hand's ready point.

**It explains the two one-handed drills entirely.** At that commit they read
1.2420 and 0.9930; at main today they read 1.2410 and 0.9910.

### A claim of mine that this disproved

A first version of this finding said the residual drift was **"not explained
by"** `56fbb6c`, reasoning from that commit's own statement that six other
drills move by "at most 0.01 cm" of hand step per frame.

**That was an overreach and the measurement refuted it.** 0.01 cm is small and
it is not zero, a hand step is not a joint angle, and nothing had established
that the two figures were inconsistent. The narrow claim in the commit message
was true; the wider claim built on it was mine and was wrong.

## Cause two: `0a99fbe`, 2026-08-30 19:21

**"fix(spikes): frame zero gets a neighbour to start from".** Seven commits and
ninety-six minutes after the first.

The six clips that are not one-handed read only 0.028 to 0.108 at `56fbb6c`,
against 0.285 to 0.659 at main. A second bisect, six steps over the 46 commits
between `56fbb6c` and `1df5e52`, found this one, with readings bimodal at 0.1080
or 0.7460.

Reverted in place: **0.7460 returns to 0.1080.**

### The corroboration nobody arranged

Under this cause the worst reading sits at **frame 0, channel 2 — the trunk
twist.** The commit's own explanation:

> Frame zero was the only frame solved without one. Every other frame is seeded
> with the previous frame's answer, so a joint the constraints do not determine
> carries on from where it already was. Frame zero had nothing to carry on from,
> so such a joint resolved however the rest pose left it.

**And reverting it moves the worst reading OFF frame 0, back to frame 74.**

The fix is about frame zero, the drift it causes is at frame zero, and removing
the fix moves the drift away from frame zero. Three independent facts agreeing,
none of them set up to agree.

## The threshold in the second bisect, and why it is not invented

Cause one had a clean criterion: does the clip reproduce exactly. **That
criterion cannot separate the commits in the second range**, because every
commit after `56fbb6c` already differs for the first reason.

So the second bisect used a band edge of **0.2**. The readings on either side of
the transition are ~0.1 and ~0.75, and 0.2 sits in the empty space between them.
**It is a band edge read off the measured distribution, not a tolerance chosen
to make the test pass**, and every reading is printed so the choice can be
checked against the numbers it was drawn from.

## A third change, smaller, unidentified

Between 2026-08-31 and 2026-09-02 something **reduces** two readings:
`deflect-high` from 0.746 to 0.659, and `two-hand-chest` from 0.550 to 0.285. It
is a step like the other two.

**It has not been bisected.** It moves no verdict and changes nothing in the
account above, and an hour of bisect for a 0.09 movement was judged not worth it
against eight re-exports waiting. It is recorded as unidentified rather than as
absent.

## A trap in the method, which cost a whole bisect

The second probe read its reference array with `git show
6e01e82:public/figures/clips.json` in the **tactics** repository, passing `cwd`.
It returned 125 with an empty reading for every commit it probed, until the
bisect exhausted the range and exited 2.

**`git bisect run` exports `GIT_DIR`.** A nested git command inherits it and
runs against the repository being bisected, whatever `cwd` says. That commit
does not exist in this repository, the output was empty, and the probe died
parsing it. **A correct command, aimed at the wrong repository, silently.**

That is the same shape as a test reading another worktree's path, one layer
further out. **Lift any cross-repository reference into a FILE before the bisect
starts.**

**And the thing that found it was logging.** The first attempt recorded only a
grepped summary line per commit, which came back empty forty-five times. An
empty column says a grep missed; it does not say why. Logging the probe's whole
output named the cause on the first run afterwards.

## What this means for the eight clips

They are not wrong. They are **stale against two correct fixes**, and have been
since the evening of 2026-08-30 — three days after they shipped.

**Nothing connected the two.** None of the eight can say which build made it;
the field that answers that was added on 2026-09-14. Dating them at all required
reading a commit message in the other repository, which is the reconstruction
that field exists to abolish.

A re-export is what makes them current. It is not a correction of an error.
