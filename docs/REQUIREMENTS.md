# Requirements, and the POC work still outstanding

Written 2026-08-19. This document comes before `DESIGN.md`, which was written
first and is therefore a candidate to be checked against this, not an answer.

## 1. The four answers this rests on

| Question | Answer |
|---|---|
| Who operates the first version, and where | A sport scientist, in the laboratory |
| Which decision must it support first | Producing the manual content |
| What makes a number fit to show a client | Agreement with expert coaches |
| What is driving the timing | Nothing. Build it properly |

Two consequences follow immediately, and both change what gets built.

**Physics is not on the critical path.** The trust bar is agreement with
coaches, and a joint moment says nothing about whether a coach agrees. Inverse
dynamics stays in the design so that it is not blocked later. It is not built
now.

**Capture is not on the critical path either.** Manual content has no camera in
it. Every risk about detectors, calibration and camera geometry is deferred,
including the field footage already filmed.

What remains on the critical path is small and sharp: **is the content we
produce coaching-correct?**

## 2. Who it is for

**The operator** is a sport scientist. Competent, in a laboratory, with time to
set things up and check results. This is a generous assumption and it should be
used: no courtside constraints, no tolerance for rough handling, no interface
polish needed yet.

**The reader** is a coach or an athlete looking at a training manual.

**The reviewer** is a skills coach who approves content before it is published.
This role does not exist today and it must, because it is where the trust bar
is met.

## 3. What the first version does

Produces the figures and sequences for a training manual, from movements that
have been graded against the coaches manual.

## 4. What it must not claim

Written down so it cannot drift.

- It does not measure a real athlete.
- It does not report forces, joint moments or ground reaction.
- It does not report any quantity derived from acceleration.
- A figure is an illustration of a technique. It is not evidence about a
  person.

## 5. Requirements

Each is written to be testable. An untestable requirement is an opinion.

### Functional

- **R1** Given a drill in the coaches manual, produce a figure at each phase
  the coaching definition names.
- **R2** Every figure states whether its movement met every coaching
  checkpoint. A figure from a movement that failed a checkpoint is either
  excluded or marked.
- **R3** A sport scientist can add a new drill without changing code, using
  only the movement, definition and technique files.
- **R4** The same drill can be produced for more than one body, without
  rewriting the movement.
- **R5** Producing the same drill twice from the same inputs gives the same
  output, and a receipt records the inputs, the versions and the hashes.
- **R6** Every published figure can be traced back to the movement, the
  definition and the athlete body that produced it.
- **R7** A coach can review the figures for a drill and record approval or
  rejection, with a reason, before publication.

### Non-functional

- **N1** One person can produce a full drill, all phases and views, in under
  fifteen minutes of their own time. Machine time may be longer.
- **N2** No component in the published path carries a licence we cannot use
  commercially. This currently fails: refer to section 8.
- **N3** The system runs on one workstation. No cluster, no service.
- **N4** Anyone new to the repository can produce one drill by following
  written instructions, without asking the author.

### Acceptance

- **V1** On a set of drills, coaches grading blind agree with the engine's
  assessment at least as often as the coaches agree with one another.

V1 is the trust bar in a testable form. It is deliberately not "the engine is
right". A grading system cannot be more consistent than the humans it is
imitating, and asking for that would be dishonest.

## 6. The POC work still outstanding

Each experiment has a pass mark, and the pass mark is set here, before running
it. That is the point of writing it down first.

### P1 — Do coaches agree with the engine?

The one that can invalidate the concept.

Take the eight drills. Render the phases. Ask at least three skills coaches to
grade each phase blind against the manual's own cues, with no sight of the
engine's assessment. Measure how often coaches agree with each other, then how
often the engine agrees with a coach.

**Pass:** engine-to-coach agreement is within the range of coach-to-coach
agreement.
**Fail:** the bands are wrong, or measuring the wrong thing, and that must be
fixed before any content is published.

### P2 — Do the authored drills match how the drill is really done?

The eight drills came from a manual, not from watching anybody. The sample
footage now exists.

Show a coach the authored movement beside the real footage of the same drill.
Ask what is wrong with ours.

**Pass:** no coach identifies a difference they would correct in a player.
**Fail:** we are illustrating a drill that nobody does.

### P3 — Can somebody else author a drill?

Give a sport scientist the manual, the tools and the written instructions. Ask
for one new drill.

**Pass:** it is done unaided in under a working day, and the result grades
clean.
**Fail:** the authoring model is ours alone, which makes it a prototype.

### P4 — Does a manual need more than one body?

A question before it is an experiment. If manuals show one athlete, the
retargeting shortfall does not matter. If they show a range, it does: 29 of 40
pairings currently retarget.

**Pass:** the answer is written down, and if more than one body is needed, the
shortfall is measured against that need.

### P5 — Reproducible with receipts

Produce a drill twice, on two days, and compare the outputs byte for byte.

**Pass:** identical, with a receipt naming every input.
**Fail:** we cannot say what produced a published figure.

P1 and P2 come first, and neither is an engineering task. Both need coaches and
a morning. Everything else can wait behind them, because if either fails the
work that follows changes.

## 7. Explicitly deferred

Recorded so that deferring is a decision and not an oversight.

| Deferred | Why | Revisit when |
|---|---|---|
| Capture from video | No camera in manual content | The first job is analysis |
| Detector accuracy against the pixel budget | Same | Capture starts |
| Inverse dynamics, ground reaction, joint moments | Trust bar is coach agreement, not instruments | An instrument claim is made |
| Athlete, Session and Capture records | Nothing to record yet | Capture starts |
| Courtside operation | Operator is in the laboratory | A coach operates it |

The design must not block these. It must not build them.

## 8. Known failures against these requirements

Honest list of where we stand today.

- **N2 fails.** The manual page draws an SMPL-X figure, which is research
  licence only and needs a commercial licence from the Max Planck Institute.
  Moving the manual page to the Blender path removes this. Refer to
  `LICENCE-RISK.md`.
- **R7 does not exist.** There is no review step and no record of approval.
- **R5 is partial.** The Blender path writes receipts. The engine does not.
- **N4 is untested.** Nobody outside this work has produced a drill.
- **R2 is partial.** The library reports checkpoint results, but a figure does
  not carry them.
- **Two anatomy defects remain open.** The elbows sit 27.3 cm apart against
  38.6 cm in the reference photographs. And `netball_hooks_outside_hand`
  exceeds a joint limit on one frame by 0.715 degrees.

## 9. Roadmap

Each phase has a decision point at the end. A decision point is a place where
stopping or changing direction is a permitted outcome.

### Phase 0 — Close the POC

P1 and P2. Coaches, a morning, no code.

**Decision:** do coaches agree with what we produce? If not, fix the bands or
the drills before building anything.

### Phase 1 — Make the manual content path fit to use

Requirements R1 to R7 and N1 to N4. Moves the manual page onto Blender, which
also closes N2. Adds the review step and the receipts. Then P3 and P5.

**Decision:** can somebody else run it, and would a coach sign the output?

### Phase 2 — Produce a manual

Real content, at volume, for a real manual. The first honest test of N1 and of
whether the library is big enough.

**Decision:** is this worth continuing to build, or is it already enough?

### Phase 3 — Analysis

Only now does capture matter. The field footage, the detector budget, the
two-camera geometry, and the Athlete and Session records.

**Decision:** does a real detector meet the pixel budget? If not, analysis
needs different equipment, and that is a commercial decision rather than an
engineering one.

### Phase 4 — Physics

Inverse dynamics, validated against the force plates. Only worth starting once
capture is trusted, because forces from untrusted motion are worse than no
forces.

## 10. What this document does not decide

- Whether the anatomy stays on MHR.
- What the manual actually needs, in content terms. Nobody has written the
  contents page.
- Who the coaches for P1 are, and when they are available.
