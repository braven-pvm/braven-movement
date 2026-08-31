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

### The eleven conditions, in two groups

**Five belong to the CAPTURE**, asked once. A second camera and a clap are not
properties of an elbow.

| condition | bar | kind |
|---|---|---|
| two views | 2 cameras | measured |
| calibration | 10 mm worked residual | chosen |
| camera separation | 45 degrees | measured |
| sync | one frame | chosen |
| the drill is in the library | first place on every repetition | chosen |

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
