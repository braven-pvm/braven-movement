# The calibration file, version 1

What two cameras and a checkerboard produce, and what a consumer may assume.

The companion to `VIDEO_KEYPOINT_SCHEMA.md`, and it inherits that file's rules
rather than restating them: every coordinate field names its space and its
units in its own name, and direction travels as an assertion a consumer runs
rather than as a sentence. Both rules exist because a version of them was got
wrong once, and the second one cost a 2.1 second error that landed inside real
footage and threw nothing.

`docs/VIDEO_CAPTURE_FINDINGS.md` instruction 2 asks for a calibration reference
in frame. This file is what reading that reference produces.

## The decisions behind it

**Two passes, and they answer different questions.** Intrinsics belong to a
phone, its lens and its capture resolution, and they need the board at many
angles and distances, so one person waves the board in front of ONE camera.
The pair pose belongs to the take, because a nudged tripod ends it, and it
needs both cameras to see the board at ONE instant.

**The pair pose needs no clap, if the board does not move.** A still board is
in the same place in every frame, so any frame of one camera pairs with any
frame of the other. That is why `--pairing static` exists and why the file
carries `pairing.boardMovement`: the assumption is MEASURED on the footage that
used it, not asserted by whoever ran the tool.

**The square size is required and has no default.** A wrong board size
announces itself — the detector finds nothing and the run stops. A wrong square
size does not: every angle stays correct and every length is wrong by that
ratio, in a file that looks finished. So `--square-metres` is a required
argument and `--board` is not.

**Three error readings travel, and they are not interchangeable.** One is the
objective the optimiser minimised. One is weak where people expect it to be
strong. One is the reading to judge a lens by. Each says which it is, in the
file, next to its own number.

**Held-out frames are strided, never a tail.** A board waved in front of a
camera drifts through its poses, so the last quarter of the frames is the last
quarter of the poses, and a fit tested only there is tested on one corner of
its own range.

## Shape

```json
{
  "schemaVersion": "video-calibration-1",
  "sessionId": "1.0",

  "board": {
    "kind": "checkerboard",
    "innerCornersAcross": 9,
    "innerCornersDown": 6,
    "squareSizeMetres": 0.040,
    "note": "INNER corners, one fewer than the squares in each direction…"
  },

  "cameras": [
    {
      "view": "front",
      "videoFile": "board-front.mp4",
      "videoSha256": "…",
      "containerWidthPixels": 1024,
      "containerHeightPixels": 576,
      "rotationMetadataDegrees": -90,
      "intrinsics": {
        "focalXPixels": 900.12,
        "focalYPixels": 899.63,
        "principalXPixel": 288.44,
        "principalYPixel": 511.02,
        "imageWidthPixels": 576,
        "imageHeightPixels": 1024,
        "distortion": {"k1": -0.081, "k2": 0.021, "p1": 0.0004, "p2": -0.0005, "k3": 0.0},
        "distortionModel": "OpenCV five-coefficient plumb bob, in the order k1 k2 p1 p2 k3…",
        "imageSizeNote": "The DECODED frame size, read off a real frame…"
      },
      "boardViewsFitted": 27,
      "boardViewsHeldOut": 9,
      "ptsSecondsFitted": [1.2, 1.367, "…"],
      "ptsSecondsHeldOut": [1.533, "…"],
      "fitReprojectionErrorPixels": 0.201,
      "heldOutReprojectionErrorPixels": 0.216,
      "splitHalfAgreement": {
        "focalXPixelsFirstHalf": 901.4,
        "focalXPixelsSecondHalf": 898.1,
        "focalDisagreementPercent": 0.367,
        "principalDisagreementPixels": 2.9,
        "note": "…read it as an estimate of the error and NOT as a ceiling…"
      },
      "errorNote": "THREE READINGS, AND THEY ARE NOT INTERCHANGEABLE…"
    }
  ],

  "extrinsics": {
    "fromView": "front",
    "toView": "side",
    "rotationRowMajorFromViewToView": [9 numbers],
    "translationMetresFromViewToView": [2.819, 0.0, 1.974],
    "directionNote": "These carry a point from the front camera's own 3D frame into the side camera's…",
    "baselineMetres": 3.441,
    "separationDegrees": 69.8,
    "minimumSeparationDegrees": 45.0,
    "separationSufficient": true,
    "separationNote": "…multi_camera_fit's MINIMUM_SEPARATION_DEGREES…",
    "boardViewsFitted": 6,
    "boardViewsHeldOut": 3,
    "fitReprojectionErrorPixels": 0.31,
    "heldOutReprojectionErrorPixels": 0.44,
    "worked": {
      "note": "The board's origin corner, located in each camera's own 3D frame by a separate solvePnP…",
      "landmark": "board inner corner index 0",
      "pointInFromViewMetres": [-0.121, 0.038, 2.914],
      "pointInToViewMetres": [0.402, 0.041, 2.733],
      "assertion": "rotationRowMajorFromViewToView @ pointInFromViewMetres + translationMetresFromViewToView == pointInToViewMetres",
      "residualMetres": 0.0021
    },
    "triangulatedSquare": {
      "medianMetres": 0.0401, "p90Metres": 0.0404,
      "knownMetres": 0.040, "medianErrorMetres": 0.0001
    }
  },

  "pairing": {
    "method": "static",
    "note": "The board did not move, so any frame of one camera pairs with any frame of the other…",
    "boardMovement": {
      "front": {
        "worstPairTranslationMetres": 0.0021,
        "worstPairRotationDegrees": 0.14,
        "toleranceTranslationMetres": 0.010,
        "toleranceRotationDegrees": 1.0,
        "heldStill": true
      },
      "side": {"…": "…"}
    }
  },

  "accuracyIsSetByTheFootage": {"note": "…", "rows": ["…"], "whatItMeansForTheShoot": "…"},
  "preconditions": ["…"],
  "tool": {"name": "video_calibration.py", "library": "OpenCV", "libraryVersion": "5.0.0", "…": "…"},
  "generatedFrom": {"commit": "…", "treeWasClean": true, "utcTimestamp": "…"}
}
```

## The extrinsics block, and the assertion that guards it

`rotationRowMajorFromViewToView` and `translationMetresFromViewToView` carry a
point from `fromView`'s own 3D camera frame into `toView`'s. On load, assert:

    rotation @ pointInFromViewMetres + translation == pointInToViewMetres

with the values in `worked`, to a tolerance of ten millimetres.
`load_calibration` runs it for you, and `check_worked_example` is the function
if you load the file yourself.

**This assertion can genuinely fail, and the keypoint schema's sync assertion
cannot.** The sync worked example is derived from the offset it guards, so it
only ever catches a later edit. Both points here come from a separate
`solvePnP` run in each camera and neither is computed from the pair pose, so
the assertion asks whether the pair fit agrees with two independent
single-camera fits. `residualMetres` is that disagreement and it is never zero.

Four mutations fire it, each held by a test: a transposed rotation, a negated
translation, the whole pose stored in reverse, and the two worked points
written the wrong way round.

## Which reading judges what

| reading | what it is | what it judges |
|---|---|---|
| `fitReprojectionErrorPixels` | the objective the optimiser minimised | nothing on its own |
| `heldOutReprojectionErrorPixels` (camera) | the lens, on frames the fit never saw | gross faults only |
| `splitHalfAgreement.focalDisagreementPercent` | two fits of one lens on disjoint halves | **the lens** |
| `heldOutReprojectionErrorPixels` (extrinsics) | the pair pose, on frames the pair fit never saw | **the pair pose** |
| `triangulatedSquare.medianErrorMetres` | the board rebuilt in 3D | a scale slip, and not direction |

**Why the camera held-out reading is weak.** `solvePnP` re-solves six degrees
of freedom per held-out frame and absorbs most of a focal error into the
board's distance. A 5 percent focal error leaves under a third of a pixel
behind, which is inside the noise real footage already carries. It stays a
strong reading of a gross fault — a bent line, a board size entered wrong, a
view mixed up between cameras — because no rigid pose can absorb those.

**Why the split-half reading is the one for the lens.** Two independent fits of
one fixed quantity have nothing to absorb a disagreement into. Measured on a
synthetic 36-view rig, ten seeds a row:

| detector noise | true focal error | split-half gap | ratio |
|---|---|---|---|
| 0.50 px | 0.864 % | 1.187 % | 1.37 |
| 0.30 px | 0.523 % | 0.712 % | 1.36 |
| 0.15 px | 0.263 % | 0.359 % | 1.36 |
| 0.05 px | 0.088 % | 0.120 % | 1.37 |

The gap runs about 1.4 times the true error and holds that ratio across a
tenfold range of noise. **It is not a ceiling**: it exceeded the true error in
only seven runs of ten, so a reader who treats it as a bound will sometimes be
optimistic.

**What the triangulated square does NOT do.** It is not the direction guard,
and a first draft of the code said it was. Reversing the pair pose moved the
recovered square by 2.8 mm on a 16-view rig — inside the band an honest fit
occupies. A reversed pose still triangulates to roughly board-sized geometry.
Direction is guarded by the worked assertion, which fails a reversed pose by a
factor of a hundred.

## What a consumer may and may not assume

**May assume.** `focalXPixels` and the rest are in PIXELS of the DECODED frame,
whose size is in the same block. `ptsSecondsFitted` are the container's own
timestamps, the same numbers `video_keypoints.py` writes, so a calibration can
be tied to the take it was shot in. The distortion coefficients are in OpenCV's
own order and may be passed to `cv2.undistortPoints` unchanged.

**May NOT assume.**

- **That the calibration still describes the rig.** It describes the rig at the
  moment the board was shot. Nothing in this file can detect a nudged tripod,
  and `preconditions` says so in words because there is nowhere else to put it.
- **That the intrinsics apply at another capture resolution.** They do not.
  `imageWidthPixels` and `imageHeightPixels` are how a consumer notices.
- **That `squareSizeMetres` was verified.** A person measured it with a rule.
  Every length this calibration yields is proportional to it, and no reading in
  the file can check it.
- **That `separationSufficient` being true makes a capture measurable.** It is
  one of the conditions in `multi_camera_fit.judge`, not the verdict.
- **That `k3` was fitted.** It is fixed at zero unless `--free-k3` was passed,
  because twenty handheld frames do not identify a third radial term.
  `distortionModel` says which happened.
- **That the pair pose is exact.** Refer to `accuracyIsSetByTheFootage`. The
  fit has no bias of its own — at zero detector noise it recovers every
  parameter exactly — so everything it gets wrong is the footage's noise coming
  out the other end.

**Must check before use.** `worked`, by running the assertion, which
`load_calibration` does. `pairing.boardMovement[*].heldStill` on any file whose
pairing method is `static`. `separationSufficient` before any triangulated
number reaches a coach.

## What this buys the shoot, beyond instruction 2

Measured on a synthetic 36-view rig, five seeds a row, with the corner
detector's noise as the only variable:

| detector noise | focal error | pair rotation error | pair translation error |
|---|---|---|---|
| 0.30 px | 0.25 % | 1.23 deg | 42.1 mm |
| 0.15 px | 0.12 % | 0.61 deg | 21.0 mm |
| 0.05 px | 0.04 % | 0.20 deg | 7.0 mm |

A pair rotation error of one degree puts about 50 mm into a point triangulated
at three metres, which is the size of the elbow residual the findings report
could not explain. **Sub-pixel corner detection on a 576p messaging transcode is
not 0.05 pixels.** So instruction 11 — camera originals, not messaging
transcodes — buys calibration accuracy as well as sharpness, which is more than
that instruction claimed for itself.

Two instructions this work adds, both from measurement rather than preference:

1. **Shoot a separate board clip per camera, and vary the board's distance and
   tilt through it.** A board kept at one distance and one small tilt fit the
   focal length 1.9 percent wrong where a varied sequence fit it 0.85 percent
   wrong on the same number of frames. `VarietyTest` holds the measurement.
2. **For the pair clip, put the board on a stand and leave it.** Then the pair
   pose needs no sync at all, and `pairing.boardMovement` proves the board held
   still rather than assuming it.

## Open, and deliberately so

- **A known-object route is not built.** A checkerboard gives hundreds of
  sub-pixel correspondences per frame across the whole image, which is what
  fits a lens. Two ends of a metre rule give two points and fit nothing. The
  shoot instruction should ask for a printed board rather than leave the choice
  open, and `--pairing synced` is the only concession to a rig that cannot.
- **`--pairing synced` has never run on real footage**, because no material
  with a clap exists yet. Its pairing is a timestamp match within half a frame
  and it is written, tested against the static route's structure, and unproven
  on video.
- **No radial-tangential model beyond five coefficients.** A phone ultra-wide
  may need the rational model. That is a change to `fit_intrinsics` and to
  `distortionModel`, and it should wait until a lens is measured that needs it.
