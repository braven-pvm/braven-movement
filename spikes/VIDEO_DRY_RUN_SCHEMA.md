# The alignment and dry-run files, version 1

What `video_phase_align.py` and `video_dry_run.py` write, and what a consumer
may assume. Two files in one document because the dry run is the alignment's
only consumer, and a contract written beside its consumer beats one written
ahead of it.

The third of the video contracts, after `VIDEO_KEYPOINT_SCHEMA.md` and
`VIDEO_CALIBRATION_SCHEMA.md`. It inherits their rules rather than restating
them: every field names its space and its units, and a direction travels as an
assertion a consumer can run rather than as a sentence.

## The decisions behind them

**Nothing is averaged into anything.** Two alignment instruments, two library
scorings, two elbow readings. Where they disagree, the disagreement travels and
neither is corrected toward the other. Averaging two instruments that fail
differently produces one number that fails in a way nobody has measured.

**A threshold says where it came from, in a field of its own.** `measured`,
`derived` or `chosen`. A bar somebody picked and a bar something measured are
not the same kind of claim, and a reader may disagree with a chosen bar without
disagreeing with any measurement. A first version packed the kind into the
prose that explained it, and the report then recovered the kind by splitting on
the first colon — which turned a sentence containing two colons into a table
cell containing half a sentence.

**Unmeasured is not a near-miss.** A condition nothing could read carries
`passes: null` and blocks exactly as hard as one that failed. Nothing read it,
so nothing can say whether it would have passed.

**Every number carries its uncertainty or names what is missing.**
`uncertainty: null` never means "small". It means no second instrument read
this, and `instrument` then has to name the instrument that does not exist.

**More than one build meets in every result**, and that is a property of the
answer rather than a footnote. The video half comes from the keypoint files and
the engine half from whichever build wrote the reference curves. Both stamps
travel.

## `phase-alignment-<set>.json`

```json
{
  "schemaVersion": "video-phase-alignment-1",
  "set": "0.1",
  "instrument": "fromLiftDegrees",
  "sourceCurve": "elbow-curve-0.1.json",
  "engineReferenceStamp": {"commit": "…", "treeWasClean": true, "utcTimestamp": "…"},
  "stampNote": "TWO BUILDS MEET HERE…",

  "repetitionsAccepted": 12,
  "repetitionsRefused": [
    {"peakSeconds": 4.33, "catchSeconds": null, "peakToNoise": 16.33,
     "stepNoiseDegrees": 2.62, "reason": "…"}
  ],

  "alignments": [
    {
      "movement": "netball_two_hand_snatch_pull_in",
      "measure": "leftElbowFlexionDegrees",
      "window": {"startSeconds": 6.7667, "catchSeconds": 8.7667,
                 "peakSeconds": 9.3667, "endSeconds": 9.3667,
                 "samples": 79, "peakToNoise": 25.5},
      "anchored": {"contactPhase": 0.5361, "note": "…"},
      "warped": {"distance": 0.0886, "bandShare": 0.25, "note": "…"},
      "agreementPhase": {"median": 0.13, "p90": 0.28, "worst": 0.331, "note": "…"},
      "handColumns": {"…": "the findings report's three columns, computed"},
      "libraryRanking": [
        {"movement": "…", "warpDistance": 0.0886,
         "informativeWarpDistance": 0.0886, "featurelessSharePhase": 0.4845}
      ],
      "rankOfAskedDrill": 1,
      "rankOfAskedDrillWholeCurve": 1,
      "rankNote": "Two scorings, and neither is called correct…",
      "featurelessSharePhase": 0.4845,
      "videoStillSharePhase": 0.05,
      "bothFeaturelessSharePhase": 0.05,
      "medianLevelGapDegrees": -50.3,
      "levelNote": "…kept OUT of the match…",
      "catchProxyNote": "…",
      "phasePerSample": [
        {"ptsSeconds": 6.7667, "degrees": 36.5,
         "anchoredPhase": 0.0, "warpedPhase": 0.0}
      ]
    }
  ],

  "askedDrillRanksFirstOn": 9,
  "askedDrillRanksFirstOnWholeCurve": 5,
  "askedDrillRanks": [1, 1, 4, 1, 1, 3, 1, 1, 4, 1, 1, 1],
  "askedDrillRanksWholeCurve": [1, 1, 2, 2, 2, 4, 2, 4, 5, 1, 1, 1],
  "rankingNote": "…a warp fits anything to anything…",
  "generatedFrom": {"…": "…"}
}
```

### What a consumer may and may not assume

**May assume.** `ptsSeconds` are the container's own timestamps, the same
numbers `video_keypoints.py` writes. `anchoredPhase` and `warpedPhase` are both
monotone and both run 0 to 1 across the repetition. `degrees` are the ENGINE's
elbow convention, where a straight arm is zero — never the included angle.

**May NOT assume.**

- **That `warpDistance` is in degrees.** It is a mean squared distance between
  z-normalised curves. Z-normalising threw the level away on purpose, so no
  warp number is evidence about degrees. `medianLevelGapDegrees` is where the
  level lives, and it is never folded into the match.
- **That a low warp distance identifies the drill.** A warp fits anything to
  anything. `libraryRanking` against ALL eight drills is the only reading that
  bears on identity, and on session 1.0 the two scorings disagree on four of
  the twelve repetitions.
- **That `rankOfAskedDrill` is the right answer and the whole-curve rank is
  the wrong one.** Neither is called correct. The filmed drill is none of the
  eight, so there is no right answer here to be closer to, and a score that
  ranks the expected drill higher is what a biased score would also do.
- **That the alignment means anything over the featureless share.** Where
  `featurelessSharePhase` is 0.48, no alignment over that first 48 percent is
  better than any other, because warping onto a flat stretch costs nothing.
- **That `catchSeconds` is the catch.** It is the ONSET of the pull-in rise.
  The engine's `contactPhase` is its possession model holding the ball; the
  findings report's 9.13 s is an eye on a contact sheet; this is 8.767 s.
  Three definitions of one word, 363 ms — eleven frames — apart.
- **That one repetition's numbers are the clip's numbers.** On session 1.0 the
  level gap runs from -50.3 to +11.5 degrees across twelve repetitions of the
  same clip.

**Must check before use.** `repetitionsRefused`, which carries the reading that
caused each refusal. `featurelessSharePhase` before quoting anything from the
early part of a repetition.

## `dry-run-<set>.json` and `dry-run-<set>.md`

The JSON is the record. The Markdown is the same content rendered for a person,
and it leads with the verdict rather than burying it under evidence.

```json
{
  "schemaVersion": "video-dry-run-1",
  "set": "0.1",
  "movement": "netball_two_hand_snatch_pull_in",

  "verdict": {
    "mayShowNumbers": false,
    "blockedBy": ["calibration", "camera separation", "sync", "…"],
    "unmeasured": ["calibration", "camera separation"],
    "failed": ["sync", "two instruments agree", "…"],
    "reason": "Figures may NOT be presented as measurements…",
    "unmeasuredNote": "An unmeasured condition is not a near-miss…"
  },

  "capture": [
    {
      "name": "sync",
      "question": "Are the two views on one clock to within a frame?",
      "reading": 0.15, "units": "seconds", "threshold": 0.0333,
      "thresholdKind": "chosen",
      "thresholdWhy": "one frame, because that is the finest this material can resolve…",
      "passes": false,
      "why": "A hand at 2 m/s is displaced 30 cm between the views at 150 ms…",
      "instrument": "the sync block in the keypoint file"
    }
  ],

  "measures": {
    "leftKneeFlexionDegrees": {
      "unit": "degrees",
      "carriable": true,
      "verdict": {"mayShowNumbers": false, "…": "…"},
      "conditions": [
        {
          "name": "the engine half exists",
          "question": "Is there an engine reference curve for this measure?",
          "reading": false, "units": "", "threshold": true,
          "thresholdKind": "measured",
          "thresholdWhy": "the measure is either a key in reference-curves.json or it is not",
          "passes": false,
          "why": "…export_reference_curves writes five measures; the library grades nine.",
          "instrument": "reference-curves.json, per docs/REFERENCE_CURVE_WIDENING.md"
        }
      ]
    }
  },
  "measuresNote": "…taken from MovementDefinition.graded_measures()…",

  "shape": {
    "status": "ILLUSTRATIVE, NEVER A MEASUREMENT AT THIS CALIBRATION…",
    "repetitions": 12,
    "namedRepetition": {"why": "…", "startSeconds": 6.7667, "…": "…"},
    "columns": {"note": "…the 'before' column is the weakest of the three…",
                "before": {"video": 17.1, "engine": 88.9},
                "atContact": {"video": 43.1, "engine": 74.7},
                "pullingIn": {"video": 109.8, "engine": 145.5}},
    "levelGapDegrees": {"value": -11.9, "uncertainty": 30.9, "units": "degrees",
                        "instrument": "…", "note": "…"},
    "featurelessSharePhase": {"value": 0.4845, "uncertainty": null,
                              "instrument": "no second instrument: …"}
  },

  "provenance": {"front": "b8d68fa7, clean=False, …", "calibration": null},
  "provenanceNote": "MORE THAN ONE BUILD MEETS HERE…",
  "generatedFrom": {"…": "…"}
}
```

### The twelve grading conditions, in two groups

**Six belong to the CAPTURE**, asked once. A second camera, a clap and a ball
in the picture are not properties of an elbow.

| condition | bar | kind |
|---|---|---|
| two views | 2 cameras | measured |
| calibration | 10 mm worked residual | chosen |
| camera separation | 45 degrees | measured |
| sync | one frame | chosen |
| the drill is in the library | first place on every repetition | chosen |
| a ball is in the picture | every repetition | chosen |

**Six belong to a MEASURE**, asked of every measure a checkpoint reads. The
right elbow being invisible says nothing about the left knee.

| condition | bar | kind |
|---|---|---|
| the modality carries it | a reader exists at all | measured |
| the graded joint was seen | 100 readings of its scarcest landmark | chosen |
| the engine half exists | a curve for this measure | measured |
| the units agree | the registry's unit | measured |
| two instruments agree | 5 degrees | measured |
| alignment agrees | clinical threshold ÷ reference slope | **derived** |

**Which measures** comes from `MovementDefinition.graded_measures()`, never
from a list written in the gate.

`passes` takes three values and they are not two: `true`, `false`, and `null`
for a condition nothing could read. **`null` blocks.**

**A measure's own verdict includes the capture-wide conditions**, because no
measure can be shown on a capture that cannot carry a number at all. The
movement's verdict is every condition at once: a drill is not gradeable on
three checkpoints of four.

**Blockers are deduplicated and counted.** The same condition is now asked of
every measure, so `blockedBy` reads `the units agree (x4)` rather than naming
it four times in the one sentence a reader is most likely to read.

### The three open questions, in a group of their own

**THEY DO NOT GATE GRADING, and the separation is the point.** The twelve above
decide whether a number may be put in front of a coach. These decide whether
the footage can settle something the ENGINE has not settled. A capture can grade
every checkpoint cleanly and answer none of these, and that is not a
contradiction: grading reads angles at named phases, and these read a rate of
change across a few frames. Folding them into one verdict would fail gradeable
footage for missing a measurement nobody was grading.

They carry their own answer in `openQuestions.canAnswer`. `assemble()` exists so
that a test can prove the grading verdict is built from the capture conditions
and the measure conditions and from nothing else.

| condition | bar | kind | on session 1.0 |
|---|---|---|---|
| the release is resolved | 120 fps | derived | **FAILS**, it is 30 |
| the release moment is addressable | 1 second | chosen | UNMEASURED, nothing writes it |
| the floor is in view | none | unavailable | UNMEASURED, the engine has no floor |

**BOTH VIEWS, and the worse of the two.** The frame rate takes the SLOWER
camera, because a hand speed read in one image is a projection and therefore a
lower bound, so the measurement needs the pair. The keyframe interval takes the
LONGER, because one unreachable view is enough to lose the frame. Session 1.0 is
exactly a case where they differ: the front keyframes every second and the side
every ten, and the fault was on the side, so a condition reading only the front
would have missed the reading it exists for. If either view fails to record the
field, the condition is UNMEASURED rather than judged on one camera.

**Where the 120 comes from.** Measured on session 1.0: at the rep 7 toss the
athlete's wrist goes from 0.7 to 6.3 cm per frame in about 67 ms. Five samples
inside that ramp is a CHOSEN minimum and needs 75 fps, so the next standard rate
above it. The engine's own claim — 0.72 cm in the frame before release against
7.37 cm in the frame after — is a difference between two ADJACENT frames of a
60 fps track, so below 60 fps no frame pair corresponds to it at all.

**Why `the floor is in view` has no bar.** The engine has no floor. A released
ball is one unbroken parabola, so no drill can declare that its ball bounces and
the gate cannot ask the question of a capture. The threshold kind `unavailable`
says that out loud rather than letting silence pass for a pass. If the floor is
ruled in, the rebound ratio must be MEASURED from footage and never typed.

### What a consumer may and may not assume

**May assume.** `mayShowNumbers` is the whole verdict: it is true only when
every condition passes. `thresholdKind` is one of `measured`, `derived`,
`chosen` or `unavailable`, checked when the condition is built.

**May NOT assume.**

- **That the shape section is a measurement.** It carries `status` for exactly
  that reason, and the phrase is the findings report's own.
- **That `uncertainty: null` means small.** It means nothing read the quantity
  twice.
- **That a passing gate makes a figure correct.** It makes the figure
  presentable. The uncertainty on it is still the uncertainty on it.
- **That the "before" column is the strong one.** It is the weakest and it
  looks like the strongest, because it is where the two numbers are furthest
  apart: it is read inside the reference's featureless lead, where the engine's
  value is simply its rest pose.

## `video-annotations/ball-in-frame-<set>.json`

**COMMITTED, not in `poc-output`.** Everything else in the video chain is
regenerable — run the extractor again and the keypoints come back. An
annotation is a person watching footage, and it is the only artefact in this
pipeline a machine cannot rebuild. Left in a gitignored output directory it is
one worktree teardown from not existing.

```json
{
  "schemaVersion": "ball-in-frame-1",
  "set": "0.1",
  "annotatedBy": "…",
  "annotatedUtc": "2026-09-02",
  "method": "…what was actually looked at, and whether it was a fresh look…",
  "windowSource": {"file": "phase-alignment-0.1.json", "commit": "…", "treeWasClean": true},
  "repetitions": [
    {
      "index": 0,
      "startSeconds": 5.267,
      "endSeconds": 5.833,
      "ballVisible": false,
      "ballVisibleThroughout": false,
      "evidence": "a frame strip across the whole window shows the athlete standing and gesturing"
    }
  ]
}
```

### The decisions in it

**`ballVisible` is asked at the ANCHORED MOMENT** — the pull-in onset through
the peak, where a catch actually happens. That is the question "is this a catch
rather than a gesture", and it is the one that blocks.

**`ballVisibleThroughout` is optional** and asks about the whole window. It
exists because session 1.0 forced it: repetition 1 has the athlete standing
empty-handed for over two seconds before the ball drops in from off frame. One
boolean would have had to call that either a clean catch or a gesture, and it
is neither. Absent means not asked, which is not "no".

**Both are TRISTATE.** `true`, `false`, `null`. Null is "nobody looked" and it
blocks exactly as hard as false does — for the same reason every unmeasured
condition in this gate blocks. Four of session 1.0's twelve repetitions are
null because the clip lane rejected them on RANKING alone and recorded nothing
about the picture; inferring a ball from a rejection that never mentioned one
would be fabrication.

**Every row carries `evidence`.** An annotation without evidence is an opinion,
and loading refuses a row that has none.

**Every row carries the WINDOW it looked at, and a stale file is refused
whole.** Repetition indices are not stable: the alignment tooling changed twice
in one evening and one change — a lookback widened from 0.5 s to 1.0 s — moved
every window in the file. An annotation keyed on index alone would silently
reattach a person's judgement about one repetition to different footage. If any
window has moved by more than 0.1 s, **none of the file is used**, because a
half-stale annotation is one nobody can tell the halves apart in.

**A refusal shuts the condition and keeps the report.** `gather` catches the
error and carries its text, so a malformed annotation costs the reader that one
condition and not the whole dry run.

## THE BLIND SPOT THIS PACK CLOSED, AND WHAT IT SAYS ABOUT THE REST

The gate asked eleven questions and not one of them was **"is this a catch"**.

Cutting clips for the coach page, the repetition the whole-curve scoring ranked
BEST of twelve contained no ball at all. Rank 1 of 8 drills on both scorings.
The null test — the guard built precisely because a warp fits anything to
anything — ranked a gesture first, because a monotone warp does always exist.

**Every reading in this file is computed from a joint curve, and a joint curve
does not know what is in the picture.** That is not a defect in any one of
them; it is the shape of the whole instrument. The lesson generalises past the
ball:

- The alignment ranks a CURVE. It cannot tell you the curve came from the
  movement you think it did.
- The level gap, the phase agreement and the warp distance all inherit that.
- The one reading that was odd — 35 percent still, double the next highest —
  is a symptom of "nothing is happening", and it is deliberately NOT promoted
  into a proxy for "no ball". A proxy that happens to correlate on one clip is
  how a gate comes to believe it can see something it cannot.

**What a person looking at a frame strip found, no number in the pipeline
could.** That is worth stating plainly in a document full of numbers.

### What the rest of the looking then found

The four repetitions left null were watched on 2026-09-02, and the result was
not the expected one. **Three of the twelve have no ball at the anchored
moment, and for TWO different causes:**

- **Repetitions 0 and 8 are gesture stretches** — no ball anywhere in the
  window, the athlete standing and talking.
- **Repetition 2 is a REAL CATCH.** The ball is plainly in her hands at 11.200
  to 11.400 and leaves the TOP of the frame at 11.633, before the anchor at
  11.733. The camera does not frame the ball's flight.

Those need different instructions and the annotation records which is which.
Two more passed by margins worth knowing: repetition 5 by 25 ms, repetition 7
by a single frame.

**Two method notes came out of the looking, and both cost time to learn.**

*Magnify before calling a frame ambiguous.* At 230 pixels wide, repetition 7's
ball read as an indeterminate dark blur and was nearly recorded null. A
top-crop at full resolution showed it unambiguously in three consecutive
frames. The close look is part of the method, not an extra.

*Label with the true timestamp, and match the frame back before you rely on
it.* A first version of this note blamed FAST SEEK on the variable-rate side
camera, and **that blame was wrong.** Asked for a single frame at 17.030, fast
seek, an accurate `-copyts` seek and `select` by timestamp all return the
IDENTICAL source frame — matched at a difference of 0.663 against a next rival
of 3.324. Seeking is not the fault, and the clip lane's cutting method is
sound.

What is established is narrower and still worth having: a label computed as a
FIXED OFFSET plus the output timestamp, inside a filter chain that RESAMPLES
and TILES, can diverge from the frames it is printed on. One such chain asked
for 9.733 s produced frames whose true timestamps ran 12.000 to 14.200 —
**real footage under fictional labels**, which is the worst shape a
mislabelling can take, because nothing looks wrong.

So: label with the true container PTS and no offset, select by timestamp rather
than seeking when a window matters, and **match a consequential frame back
against the source rather than trusting any label.** Every reading in the
annotation was taken that way.

**And the caution that explains the original symptom.** The side file carries
only **THREE keyframes** — 0.000, 9.996 and 19.992, a ten-second GOP — where
the front has one every second. Any KEYFRAME-SNAPPING reader
(`-noaccurate_seek`, a stream copy, most players) asked for 16.93 on the side
lands at **9.996**, a +6.93 s error — and 9.996 is where repetition 2's catch
lives. That is precisely the symptom that started this: repetition 2's catch
appearing under a repetition-7 label. ffmpeg's default seek is accurate and
does not do it; a reader that snaps does, and a ten-second GOP is what makes
the error that large.

### Two fields the gate reads back out

**`cause`** on a blocking row — `gesture` or `framing`. The gate names it per
repetition: *"0 (gesture), 2 (framing), 8 (gesture)"*. The two need different
shoot instructions — a slate between repetitions, or framing for the ball's
flight — so collapsing them to a count would lose the only thing that decides
which fix applies.

**`marginFrames`** on a passing row — how many frames of the anchored span
actually carry the ball. Repetitions 5 and 7 each carry it in exactly ONE:
14.900 for rep 5, which is the peak itself, and 17.200 for rep 7, which is the
anchor itself. The anchor is located "to about one frame and no better" and the
two views are synchronised to no better than 0.25 s, **so a one-frame margin is
inside the uncertainty of the question being asked.** The gate reports those as
NARROW rather than as plain passes, and it quotes each row's own margin rather
than the threshold it fell under. `null` means nobody counted, which is not the
same as wide.

## Open, and deliberately so

- **The gate has never opened on real footage.** It opens on a synthetic
  evidence bundle in `test_video_dry_run.py`, and eight single-fault mutations
  of that bundle each shut it and name their own condition. That is what
  separates a working gate from one hard-wired to refuse, and it is not the
  same as a shoot that passes.
- **The `sync` bar is chosen at one frame, and the derived bar is far
  tighter.** The lift's own 15 mm residual over a hand at 2 m/s allows 8 ms.
  The looser bar is used because a sub-frame claim cannot be verified on this
  material at all, and a bar nothing can check is not a bar. When a clap
  exists, re-derive it.
- **Only the left elbow is gated.** The measure is one joint on one arm.
  Grading a whole drill needs the same treatment for every measure the
  checkpoint reads, and the eighth condition already shows why: the right elbow
  appears in zero of 735 frame pairs.
