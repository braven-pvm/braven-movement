# The keypoint file, version 1

What one camera view of one clip produces, and what a consumer may assume.

Agreed between the movement lane and the rendering lane for the video spike,
and ratified by the orchestrator. Version 1 of this file had a sign error in
the sync block that the rendering lane found before any data crossed the
boundary. That review is the reason several things below are DATA rather than
sentences.

## The decisions behind it

**Time is a PTS timestamp, never a frame index.** The side cameras in
session 1.0 are variable rate: 30.012 fps against the front's exact 30.000, so
the two views' frame N are not the same moment and the error grows through the
clip. Every record carries the timestamp the container gives it.

**Every coordinate field names its space and its units in its own name.** The
pose tool emits more than one space, and they differ by a factor of the image
size and by an origin. There is no field called `x`. There is
`xNormalizedImage` and `xPixel` and `xWorldMetres`, so a reader who does not
know which one they want cannot silently pick the wrong one.

**Visibility travels per landmark.** A foot cropped out of frame and a foot
seen clearly must be distinguishable, or no finding about framing can be
measured.

**The decoded frame size is mandatory.** It anchors both image spaces, and it
is not the container size: the front cameras carry −90 rotation metadata, so
their containers say 1024x576 and their decoded frames are 576x1024.

**Direction is carried as a worked example, not as a sentence.** Version 1 said
"add this offset to place it on the reference clock" and then gave a number
with the opposite sign. Applying it moved a timestamp 2.1 s the wrong way and
landed inside real footage, so nothing would have thrown. Prose about direction
is what failed; the fix is an assertion a consumer can run.

**The skeleton's edges live in the file.** A consumer that supplies its own
edges hardcodes one model's topology, and the day the model changes or the
landmarks reorder it draws a limb through a chest — confidently, with nothing
failing. Edges are pairs of NAMES so a reordering cannot silently rewire them.

**Frame quality sits beside `detected`.** The pose tool will emit landmarks for
a smeared frame with high visibility, because a smeared body is still
body-shaped. `detected: true` at 0.9 visibility on a frame that is not footage
is worse than a missing frame.

## Shape

```json
{
  "schemaVersion": "video-keypoints-1",

  "source": {
    "videoFile": "side 0.1.mp4",
    "videoSha256": "…",
    "view": "side",
    "setId": "0.1",
    "decodedWidthPixels": 478,
    "decodedHeightPixels": 850,
    "containerWidthPixels": 478,
    "containerHeightPixels": 850,
    "rotationMetadataDegrees": 0,
    "framesPerSecondMeasured": 30.0120,
    "constantFrameRate": false,
    "usableToSeconds": null
  },

  "model": {
    "tool": "mediapipe",
    "toolVersion": "1.0.1",
    "toolLicence": "Apache 2.0",
    "modelFile": "pose_landmarker_heavy.task",
    "modelSha256": "64437AF838A65D18E5BA7A0D39B465540069BC8AAE8308DE3E318AAD31FCBC7B",
    "modelSourceUrl": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
    "modelFetchedUtc": "2026-08-28",
    "modelLicence": "…as read from the model card, not assumed from the tool…",
    "modelLicenceSource": "…url or file the licence was read from…",
    "landmarkNames": ["nose", "left_eye_inner", "…"],
    "landmarkEdges": [["left_shoulder", "left_elbow"], ["left_elbow", "left_wrist"], "…"]
  },

  "athlete": {
    "heightMetres": 1.77,
    "wingspanMetres": 1.82,
    "oneArmReachMetres": 0.77,
    "ballDiameterMetres": 0.223,
    "source": "supplied by Marius, 2026-08-28; ball is netball size 5, 220 to 226 mm"
  },

  "sync": {
    "referenceView": "front",
    "file": "side 0.2.mp4",
    "measured": true,
    "pairedWith": "front 0.1.mp4",
    "pairKey": "front 0.1 + side 0.2",
    "frameOffsetToReference": -5,
    "framePeriodSeconds": 0.033322,
    "methodKind": "shared-event",
    "method": "the frame in which a ball first meets her hands, read in both files by index from the container's own timestamp list",
    "anchors": [
      {"event": "first catch, ball into hands",
       "referenceIndex": 274, "referenceSeconds": 9.1333,
       "otherIndex": 269, "otherSeconds": 8.9630,
       "derivedSecondsOffset": -0.1704},
      {"event": "overhead catch, ball into hands",
       "referenceIndex": 605, "referenceSeconds": 20.1667,
       "otherIndex": 600, "otherSeconds": 19.9920,
       "derivedSecondsOffset": -0.1746}
    ],
    "checks": [{"event": "second clap, hands meet", "referenceIndex": 534, "otherIndex": 529, "…": "…"}],
    "setAside": [{"event": "first clap, hands meet", "frameDifference": 4, "why": "a clasp is soft; …"}],
    "offsetUncertaintySeconds": 0.0333,
    "derivedNote": "The seconds above are DERIVED from each file's own pts and are not the measurement. …",
    "methodNote": "…"
  },

  "generatedFrom": {
    "commit": "…",
    "treeWasClean": true,
    "utcTimestamp": "…"
  },

  "frames": [
    {
      "ptsSeconds": 8.1333,
      "frameIndex": 244,
      "detected": true,
      "frame_quality": 0.98,
      "degraded": false,
      "landmarks": [
        {
          "name": "left_wrist",
          "xNormalizedImage": 0.5123,
          "yNormalizedImage": 0.3310,
          "zNormalizedImageRelative": -0.0412,
          "xPixel": 244.9,
          "yPixel": 281.4,
          "visibility": 0.981,
          "presence": 0.994
        }
      ],
      "worldLandmarks": [
        {
          "name": "left_wrist",
          "xWorldMetres": 0.183,
          "yWorldMetres": -0.402,
          "zWorldMetres": 0.061
        }
      ]
    }
  ]
}
```

## The sync block, and the assertion that guards it

## The sync block: a FRAME COUNT between two named FILES

**THE PAIRING IS BETWEEN FILES, NOT BETWEEN SETS, AND THE FILE NAMES ARE
WRONG.** `front 0.1.mp4` and `side 0.2.mp4` are the same run, established
2026-09-07. `front 0.2.mp4` and `side 0.1.mp4` are not shown to be a pair by
anything measured. The source files are NOT renamed — they are Marius's assets
and every path in the tree points at them — so `sync.pairedWith` carries the
mapping and every consumer reads that rather than a name.

**THE MEASUREMENT IS `frameOffsetToReference`.** It is added to a frame INDEX in
this file to reach the reference file's index, and the consumer assertion is an
index one:

```
other_pts[reference_index + frameOffsetToReference]   is the other view's time
```

**SECONDS ARE DERIVED AND NEVER STORED AS THE MEASUREMENT.** The two cameras'
frame periods differ — 33.3330 ms on the front against 33.3220 ms on the side —
so a constant frame offset shows as a time offset that DRIFTS, from −0.1704 s at
the first anchor to −0.1746 s eleven seconds later. That is an eighth of a frame
and it is real. Two offsets in seconds have been published from this material
and both were withdrawn; the field that carried them, `offsetSecondsToReference`,
is gone so that nothing reads one by habit.

| field | what it is |
|---|---|
| `pairedWith` | the other file's name, or `null` |
| `frameOffsetToReference` | the measurement; `0` in the reference file |
| `framePeriodSeconds` | this file's own median interval, for deriving seconds |
| `anchors` | two ball-into-hands events, at least ten seconds apart |
| `checks` | events that agree but add no span |
| `setAside` | events that DISAGREE, with the reason |
| `offsetUncertaintySeconds` | one frame — which frame the contact was called in |

**AN ANCHOR IS A BALL MEETING HANDS. A CLAP IS A CHECK.** A ball arriving is a
one-frame transition with no judgement in it; a clasp is soft, and "nearly
together" against "together" is a frame either way. The first clap of the run
gives a frame difference of **4** where everything else gives 5, and it is
recorded in `setAside` rather than resolved by picking the frame that agrees.

**TWO ANCHORS, AT LEAST TEN SECONDS APART, OR NO SYNC IS WRITTEN.** One anchor
is always satisfiable. The athlete's toss cycle is 1.90 s, so a wrong offset
lands on a catch exactly as a right one does — which is how −0.7295 s survived
its own check for three days.

**`methodKind` DECLARES THE GRADE, and its vocabulary is closed.** A consumer
deciding whether to trust a pairing needs the grade, and a grade it has to parse
out of a sentence is not a field. `METHOD_KINDS` in `spikes/video_keypoints.py`
holds the list:

| kind | what it means |
|---|---|
| `clap` | a sharp shared sound, located in both tracks |
| `shared-event` | one physical event, read in both views — and it must be UNIQUE in the clip, which a catch is not |
| `eye` | two moments judged to correspond by a person |
| `correlation` | a signal correlation with a stated confidence |
| `unknown` | nothing has measured it |

**Session 0.1 is `unknown`.** Two offsets have been withdrawn from it, the
second graded `shared-event` on a catch — and a catch recurs every 1.866 s, so
it was not unique and the pairing was one cycle out. Refer to
`spikes/video-annotations/event-ledger-0.1.json`.

**`offsetSecondsToReference` NO LONGER EXISTS.** It carried two offsets that
were both withdrawn, and it is removed so that nothing reads one by habit.

`frameOffsetToReference` replaces it and is added to a frame INDEX in this file
to reach the paired file's index. On load, assert on the indices:

    other_pts[referenceIndex + frameOffsetToReference] == otherSeconds

for every row of `anchors` and `checks`. On this material that is
`side_pts[274 - 5] == 8.9630` and `side_pts[605 - 5] == 19.9920`. **The
assertion is on integers and cannot drift**, which is the point of moving it off
seconds.

### Mapping to the rendering lane's `--offset`

The two conventions agree on this material and carry OPPOSITE SIGNS, because
they are defined in opposite directions. The rendering lane's tool converts a
REFERENCE time into a THIS-VIEW time; this field converts a THIS-VIEW time into
a REFERENCE time.

    For the non-reference view, a consumer that still needs seconds derives
    them AT ITS OWN FRAME rather than from a stored constant:

        seconds = other_pts[reference_index + frameOffsetToReference]
        the rendering lane's --offset = -(seconds - reference_pts[reference_index])

    **The derived number is not constant across the clip** — it moves about
    4 ms across the 11 s between the two anchors, because the cameras' frame
    periods differ by 11 microseconds. A consumer that caches one and reuses it
    at the other end of the clip is out by an eighth of a frame; a consumer that
    stores one as THE offset repeats the fault this schema was rewritten for.

Neither is wrong, and either alone is unambiguous. Together and unwritten they
are a sign error waiting for whoever reads both, which is why the mapping is
here rather than in anyone's memory.

## Frame quality

`frame_quality` and `degraded` take their definitions from the rendering lane's
`frame_quality` and `degraded` in `scripts/video_sync_sheet.py`, so the
definition exists once rather than twice. Judge each clip against **its own**
median: one absolute threshold condemns the softer camera everywhere and
catches nothing on the sharper one.

**Whenever a quality figure is quoted, say which reference it is against.** The
same camera-handling frame in `front 0.1` reads 26 percent against the clip's
settled baseline and 21 percent against the median of a sampled sheet. Both are
correct and they are different references.

## What a consumer may and may not assume

**May assume.** `ptsSeconds` is the container's own timestamp for that frame,
in that file's clock. `xNormalizedImage` and `yNormalizedImage` run 0 to 1
across `decodedWidthPixels` and `decodedHeightPixels`. `xPixel` and `yPixel`
are the same points already multiplied by those sizes, carried so that nobody
multiplies by the container size instead.

**May NOT assume.**

- That `zNormalizedImageRelative` is a distance. It is the tool's own relative
  depth and is not metric.
- That the world landmarks share an origin with anything. Their origin is the
  athlete's own hip centre, so they describe a POSE and not a position in the
  gym. A consumer taking them as gym coordinates gets a plausible wrong answer.
- That `frames` are evenly spaced. On a variable-rate view they are not.
- That a missing landmark is at the origin. An undetected frame carries
  `"detected": false` and no landmarks at all rather than zeros.
- **That a sync offset in SECONDS is constant across the clip.** It is not, and
  that is why the measurement is a frame count. The two cameras' frame periods
  differ by 11 microseconds — 33.3330 ms against 33.3220 — so the derived
  offset moves about 4 ms across the 11 s between the anchors and would move
  240 ms, seven frames, over a ten minute shoot. **The FRAME offset does not
  drift.** Derive seconds at the frame you need them for.

- **That `detected` means the frame is usable.** It does not. `detected`
  answers "did the model find a body"; `usableToSeconds` and `degraded` answer
  "is this frame footage". They part company exactly where it matters: in
  `front 0.1` the model detects a body through **26.133 s**, past the 25.7 s
  usable end, because a smeared body is still body-shaped and it only loses her
  at darkness. A consumer trusting `detected` alone measures a blur with
  confidence.

**Must check before use.** `visibility` on any landmark the question depends
on, and `degraded` on any frame at all. `detected` is not a substitute for
either.

## Open, and deliberately so

- `offsetUncertaintySeconds` is ONE FRAME, 0.0333 s, on the one established pair; it was ±150 ms while the sync was matched by eye between two files that are not a pair. That older figure is larger than
  most consumers will expect. A file whose sync came from a real clap should
  carry a much smaller number; the field is the same either way.
- `usableToSeconds` is null unless the clip has a known bad tail. For
  `front 0.1` it is **25.7**, measured per frame by the rendering lane:
  sharpness holds to 25.6, is 87 percent of baseline at 25.700 with the
  inter-frame motion already tripled, and 39 percent at 25.900. An earlier
  reading of 25.9 came from an eye on quarter-second strips and is superseded.
  For a field that says "usable to", take the conservative end.
- `modelLicence` is deliberately not pre-filled. It is read from the model card
  when the bundle arrives, and a file that said "Apache 2.0" because the
  package said so would be exactly the assumption this field exists to prevent.
