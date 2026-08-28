# Video spike, session 1.0

What phone video can and cannot give the engine. Working notes, written as the
work happens rather than after it, so the failures stay in.

The material is a feasibility sample: two drills, each filmed from a front and
a side camera about 90 degrees apart. `F:\Repositories\braven-movement\.assets\video-samples\session-1.0`.

## Facts, re-verified rather than taken on trust

| | front 0.1 | front 0.2 | side 0.1 | side 0.2 |
|---|---|---|---|---|
| container | 1024x576 | 1024x576 | 478x850 | 478x850 |
| rotation metadata | −90 | −90 | none | none |
| decoded | 576x1024 | 576x1024 | 478x850 | 478x850 |
| frames | 866 | 946 | 863 | 990 |
| measured rate | **30.0000** | **30.0000** | 30.0120 | 30.0121 |
| audio | 44100 stereo | 44100 stereo | 48000 stereo | 48000 stereo |

Two of the four traps are confirmed and sized:

- **The side cameras are variable rate**, but only just. Steps run 33.222 to
  33.422 ms across five distinct values. Against a 30 fps assumption the
  end-of-clip error is **−11.5 ms and −13.3 ms**, about a third of a frame over
  half a minute. Real, and an order of magnitude smaller than the other
  problems here.
- **ffmpeg applies the rotation on decode.** The front files decode portrait,
  576x1024, verified by reading the dimensions off a decoded PNG rather than
  reasoning about the metadata. Any tool that goes through ffmpeg inherits
  this; one that reads the stream itself does not.

## The sync, which is the part that failed

### There is no clap

Not "the correlation could not find one" — there is no clap. In both views of
set 0.1 the athlete stands and TALKS for the first eight seconds, hands at her
sides or gesturing while she speaks. The first shared event of any kind is her
first ball catch.

That was established by looking at the frames, after the audio route failed
four times:

| method | set 0.1 | set 0.2 |
|---|---|---|
| raw waveform | −78.6 ms, p/s 1.08 | +633.7 ms, p/s 1.12 |
| energy envelope | −249.0 ms, p/s 1.08 | +184.0 ms, p/s 1.01 |
| spectral flux, first 12 s | −245.3 ms, p/s 1.35 | +3616.0 ms, p/s 1.27 |
| spectral flux, whole clip | +17962.7 ms, p/s 1.02 | +4325.3 ms, p/s 1.28 |

`p/s` is peak-to-sidelobe: how far the best match stands above the next best.
**A value near 1.0 means there is no peak**, so the milliseconds beside it are
not a measurement. Four readings, four different answers, none with a peak.

Reporting only the first line would have looked like a −78.6 ms offset with a
plausible sign, and it would have been fiction.

### Motion energy fails too, and for a reason worth keeping

`video_motion_sync.py` correlates total frame-to-frame pixel change instead of
sound. It fails differently and it still fails:

| | offset | peak/sidelobe |
|---|---|---|
| set 0.1 whole clip | −1325 ms | 1.32 |
| set 0.1 first half | −4310 ms | 1.01 |
| set 0.1 second half | −1321 ms | 1.37 |
| set 0.2 whole clip | −700 ms | 1.22 |
| set 0.2 first half | +220 ms | 1.26 |
| set 0.2 second half | −727 ms | 1.27 |

The halves disagree by 2989 ms and 947 ms, against a measured clock drift of
about 12 ms. That is not drift, it is ambiguity.

**A repetitive drill defeats whole-signal correlation.** The athlete throws and
catches on a cycle of a second or two, so the signal is nearly periodic and the
correlation has many near-equal peaks. This holds whatever the signal is —
sound or pixels — which is why both routes failed the same way.

### Matching events by eye: about ±150 ms

Two catches, located by reading frame contact sheets:

| event | front | side | offset |
|---|---|---|---|
| A, first catch | 9.133 s | 8.133 s | **−1.000 s** |
| B, a catch 15 s later | 24.067 s | 22.800 s | **−1.267 s** |

The two disagree by **267 ms**, which is eight frames. That is how precisely a
catch can be located by eye on a small tile, and nothing more.

**No drift figure may be derived from these two events.** A single frame is
33 ms, so an event pair cannot resolve a clock difference of 11 ms however far
apart the events are. Event B's role is a gross-error check on the offset — it
confirms there is no whole-cycle mismatch — and it is not a drift measurement.
The drift number comes from the frame timestamps, below.

So the honest answer for this material is an offset of about **−1.1 s with an
uncertainty near ±150 ms**. For a feasibility spike that is enough to pair
frames for a look. For reading joint angles off two views it is not.

**What ±150 ms costs downstream.** A hand travelling at 2 m/s is displaced
about 30 cm between the two views at that sync error. Two-view 3D from this
sample therefore certifies that the pipeline runs; it yields usable numbers
only where the athlete is nearly still — stance, hold, ready — and in fast
phases it is illustrative and never a measurement. The clap is not a
convenience: it bounds the 3D accuracy of everything downstream.

### Drift is real, ignorable here, and not ignorable on a long take

The side clock runs about 0.04 percent fast. Over a 28 second clip that is
11 ms, a third of a frame, and it can be ignored. Over a **five minute** take
it is **120 ms, four frames**, which cannot.

So a long take needs **a clap at both ends**, not only at the start: two
anchors measure the rate as well as the offset, and one anchor cannot.

## Mistakes made in this spike, kept deliberately

- **I read a camera being picked up as a jump.** The last two seconds of
  front 0.1 show heavy motion blur and a changing viewpoint, and at tile size
  it looked like the athlete leaving the ground. The side view showed her
  standing throughout, which read as a contradiction in the sync until I
  looked at the whole clip and found the front camera simply stops.

  A third instrument settled it independently: frame strips from the
  orchestrator's own check put the overhead moment as her own toss, caught in
  the side view at 24.50 to 24.75 s and thrown in the front view at 25.50 to
  25.75 s — consistent with −1.0 s and inside the ±150 ms. **Nobody jumps.**
  Front 0.1 is camera handling from 26.0 s and dark from 26.267 s.

  **Treat front 0.1 as ending at 25.9 s for every downstream use.**

  The lesson is the one this project keeps meeting: a disagreement between two
  instruments is a question, not a verdict, and the answer was in neither
  instrument but in the framing.

## Licence position

`mediapipe` 1.0.1 is already installed and its metadata reads **Apache 2.0**,
with the OSI classifier confirming. That can enter the product path.

The package licence is not the model licence. The Tasks API needs a
`pose_landmarker.task` bundle which is **not** present in the environment, so a
download is required, and its terms have to be read before anything is built on
it. That download is not made in this spike.

Everything else needed is already present: numpy, scipy, OpenCV, PIL, torch.

## Which drill is it? None of the eight, and for one reason

Both sets show the same thing: the athlete stands still, tosses the ball
upward herself, catches it at head height with two hands, brings it in, and
tosses it again. Set 0.1 repeats that for about seventeen seconds. Set 0.2 is
the same pattern.

**The ball is self-fed.** She begins holding it — visible in the first frame of
side 0.1 — throws it up, and catches her own toss. No passer appears in either
view, and the ball rises out of frame and falls back rather than arriving
across the room.

Every one of the library's eight drills is fed by a PASSER. The ball's flight
is authored from a passer position and a catch point, and the whole possession
model turns on a ball that arrives with speed and direction the athlete has to
answer. A ball she has tossed straight up arrives slowly, vertically, and at a
moment she chose.

So the honest answer to "which of our eight is this" is **none of them**. The
closest in SHAPE is a two-hand catch at head height, which resembles
`netball_two_hand_snatch_pull_in` in what the arms do and resembles nothing in
the library in what the ball does.

That is not a criticism of the sample. It was shot to test whether phone video
can feed the engine, and it answers that. But it means deliverable (d)'s
comparison against a reference curve can only be qualitative in the weakest
sense: the same joint doing a similar thing, not the same drill.

**For the shoot: film the drills the library actually contains, with a passer.**
Self-fed repetitions test the camera rig and nothing about the movement the
engine models. A perfect two-camera capture of a self-toss still grades
nothing, which is why this outranks most of the rig findings below.

## Angle references are recorded

`export_reference_curves.py` writes the engine's own curves for all eight
drills to `poc-output/video/reference-curves.json`: elbow flexion, shoulder
elevation and trunk lean per frame, with contact and release marked, indexed by
PHASE from 0 to 1 rather than by seconds so a clip of any tempo can be laid
over them. Left elbow flexion ranges from 35.8 to 145.9 degrees across the
library.

They come from the same measurements `build_library` grades, so a video curve
is compared against the engine's own definition of the angle rather than a
second definition invented for the comparison.

## What the proper shoot must change

Confirmed from this material rather than assumed:

1. **A clap, audible and visible in both frames**, performed after both cameras
   are rolling and before anyone speaks. This is the cheapest thing on the list
   and the whole two-camera method rests on it. The sample has none.
2. **Constant frame rate on every camera**, or the VFR documented. The
   measured cost here is small, about a third of a frame, but it is free to
   avoid.
2b. **A clap at BOTH ENDS of any take longer than about a minute.** The side
   clock runs 0.04 percent fast, which is 11 ms over 28 seconds and 120 ms —
   four frames — over five minutes. Two anchors measure the rate as well as the
   offset; one anchor cannot.
3. **Do not stop a camera while the drill is still running.** front 0.1's last
   two seconds are the phone being picked up.
4. **One drill per clip.** Set 0.1 contains eight seconds of talking before any
   movement, and the talking is what made the first sync attempts hunt.
5. **Camera originals, not messaging transcodes.** These are 1.4 to 1.8 Mbps
   and 576p-class.

Still to confirm or refute from the pipeline: 60 fps, feet in frame at all
times, a scale reference in view, and no bystanders.
