# The keypoint file, version 1

What one camera view of one clip produces, and what a consumer may assume.

Proposed by the movement lane for the video spike. Nothing is written in this
format yet — the pose model is not in the environment and no keypoints exist.
The schema is settled first so that the rendering lane and the movement lane
agree before there is data to disagree about.

## The decisions behind it

Four of these are the reason the file looks the way it does.

**Time is a PTS timestamp, never a frame index.** The side cameras in
session 1.0 are variable rate: 30.012 fps against the front's exact 30.000, so
the two views' frame N are not the same moment and the error grows through the
clip. Every record carries the timestamp the container gives it. A consumer
that wants frame numbers can count records; a consumer that wants time must not
have to multiply.

**Every coordinate field names its space and its units in its own name.** The
pose tool emits more than one space, and they differ by a factor of the image
size and by an origin. A consumer that guesses reproduces the fault this
project has spent a week removing: a number measured in one frame of reference
and spent in another. So there is no field called `x`. There is
`xNormalizedImage` and `xPixel` and `xWorldMetres`, and a reader who does not
know which one they want cannot silently pick the wrong one.

**Visibility travels per landmark.** A foot cropped out of frame and a foot
seen clearly must be distinguishable, or no finding about framing can ever be
measured — and framing is one of the questions the proper shoot has to answer.
A single per-frame confidence cannot say which joint was lost.

**The decoded frame size is mandatory.** It is the anchor for both image
spaces, and it is not the container size: the front cameras carry −90 rotation
metadata, so their containers say 1024x576 and their decoded frames are
576x1024. A file that recorded only the container geometry would put every
normalised coordinate on the wrong axis, and nothing downstream would notice.

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
    "modelFile": "pose_landmarker_full.task",
    "modelSha256": "…",
    "modelLicence": "…as read from the model card, not assumed from the tool…",
    "modelLicenceSource": "…url or file the licence was read from…",
    "landmarkNames": ["nose", "left_eye_inner", "…"]
  },

  "sync": {
    "referenceView": "front",
    "offsetSecondsToReference": -1.1,
    "offsetUncertaintySeconds": 0.15,
    "method": "two visual events matched by eye; no clap exists in this material",
    "note": "Add this offset to a timestamp here to place it on the reference view's clock."
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

## What a consumer may and may not assume

**May assume.** `ptsSeconds` is the container's own timestamp for that frame,
in that file's clock. `xNormalizedImage` and `yNormalizedImage` run 0 to 1
across `decodedWidthPixels` and `decodedHeightPixels`. `xPixel` and `yPixel`
are the same points multiplied by those sizes, carried so that nobody has to
multiply and nobody multiplies by the container size instead.

**May NOT assume.** That `zNormalizedImageRelative` is a distance — it is the
tool's own relative depth and is not metric. That the world landmarks share an
origin with anything: their origin is the athlete's own hip centre, so they
describe a POSE and not a position in the gym. That `frames` are evenly
spaced — on a variable-rate view they are not. That a missing landmark is at
the origin — an undetected frame carries `"detected": false` and no landmarks
at all rather than zeros.

**Must check before use.** `visibility` on any landmark the consumer's question
depends on. A framing finding is only measurable because this field exists.

## Open, and deliberately so

- `offsetSecondsToReference` is stated with its uncertainty because on this
  material it is ±150 ms, which is larger than most consumers will expect. A
  file whose sync came from a real clap should carry a much smaller number, and
  the field is the same either way.
- `usableToSeconds` is null unless the clip has a known bad tail. For
  `front 0.1` it is **25.9**, because the camera is picked up after that.
- `modelLicence` is deliberately not pre-filled. It is read from the model card
  when the bundle arrives, and a file that says "Apache 2.0" because the
  package said so would be exactly the assumption this field exists to prevent.
