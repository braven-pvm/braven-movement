# What the proper shoot must do differently

Findings from session 1.0, the four-clip feasibility sample. Written for
planning the real shoot.

## The answer

**Can we get from phone video what the engine needs?**

Not yet from footage like this — but the reason is specific, cheap to fix, and
none of it is about the phones.

The pipeline runs end to end. Two camera views became **3,439 tracked frames
out of 3,665** in about 160 seconds, lifted into 3D, and turned into a joint
angle against time. **It recovers the right movement.** Laid beside the engine's own
curve for the nearest drill, one catch cycle of left elbow flexion reads:

| | before the catch | at the catch | pulling in |
|---|---|---|---|
| measured from the video | 60 to 75° | 58° | 122 to 131° |
| the engine's snatch pull-in | 89° | 80° | 113 to 145° |

Both dip as she reaches to meet the ball, then fold sharply to bring it in.

The video row reads one catch cycle from `elbow-curve-0.1.json`: the catch is at
9.13 s, the pull-in window is 9.2 to 9.6 s, and 131° is the raw peak at 9.37 s
across all 13 frames in that window. An earlier draft said "122 to 126" from a
printout sampling every third frame, which understated the peak by 5 degrees.

**The shape is right. The numbers are not.** Two independent readings of that
same elbow, from the same footage, disagree by a median of 21 degrees. Nothing
in the analysis fixes that, because the information needed is not in the
footage.

**A shape cannot become a number without a calibration reference in frame.**
That, and a clap. Neither is sufficient on its own — nothing tested explains
the whole disagreement — but both are necessary, both cost nothing, and neither
was present.

## What to change, in order of consequence

### 1. A clap — audible AND visible in both frames

There is no clap in this material. In both views the athlete stands and talks
for the first eight seconds, hands at her sides. The first shared event of any
kind is her first ball catch.

Four audio methods were tried. All four failed, and the confidence measure is
what says so:

| method | set 0.1 | set 0.2 |
|---|---|---|
| raw waveform | −78.6 ms, p/s 1.08 | +633.7 ms, p/s 1.12 |
| energy envelope | −249.0 ms, p/s 1.08 | +184.0 ms, p/s 1.01 |
| spectral flux, first 12 s | −245.3 ms, p/s 1.35 | +3616.0 ms, p/s 1.27 |
| spectral flux, whole clip | +17962.7 ms, p/s 1.02 | +4325.3 ms, p/s 1.28 |

Peak-to-sidelobe near 1.0 means the best match is no better than the next best:
there is no peak, so the milliseconds beside it are not a measurement. Four
readings, four different answers.

Matching catches by eye instead gives an offset good to about **±150 ms**, which
is four to five frames.

**Instruction: after both cameras are rolling and before anyone speaks, clap
once, sharply, where both cameras can see the hands.** On any take longer than
about a minute, clap at **both ends** — the two phone clocks differ by 0.04
percent, which is 11 ms over 28 seconds and 120 ms over five minutes. Two
anchors measure the rate as well as the offset; one anchor cannot.

**And between the clap and the first repetition, nobody speaks.** The clap
makes the talking harmless, so this is insurance rather than a second rule: if
the clap is missed in one view, the fallback is correlation, and correlation is
what speech defeats. It costs a sentence of silence.

**A fourth reading of this offset landed at the EDGE of the documented band.**
Added 2026-09-02. Cutting the coach clips, the side view was placed against the
front using the documented 1.22 s offset with an uncertainty near 0.25 s, and
the effective offset that actually lined the two views up read **0.95 to
1.00 s** — the very bottom of that band. That is a fourth instrument on the
same quantity, and the four now spread wider than any one of them claims: four
audio methods with no peak at all, motion energy whose halves disagreed by
three seconds, an eye on contact sheets at 1.0 to 1.27 s, and this.

Nothing here narrows the offset and nothing should be read as narrowing it.
What it says is that **the ±0.25 s band is not conservative**, and that a
number sitting at the edge of its own uncertainty is the shape of a bias rather
than of noise. The clap is what settles it, which is why it is instruction 1.

### 2. A calibration reference in frame

Two independent readings of the same elbow disagree by a median of 21 degrees
(90th 63°). Four explanations were raised and all four were refuted — the table
is further down, under the elbow angle.

**So the case for a calibration reference is not that it fixes a known cause.**
Nothing tested explains that 21 degrees. The case is that without a known
object in shot, the depth axis has to be scaled by matching a body length
between two cameras at unknown distances with unknown lenses, and there is no
way to check that scale at all — not to confirm it, and not to rule it out.

The deeper reason is comparison. A calibration reference makes a future
measurement **like-for-like**, and the absence of one is why this disagreement
was so hard to read: every candidate had to be tested against correlations too
weak to exclude a minor contributor.

**Instruction: put a rigid object of known size in both cameras' view for the
whole take.** A printed checkerboard is ideal. A metre rule taped to the floor,
or a marked pole, will do. It must not move and it must be visible throughout,
not just at the start.

**Superseded in one detail, and extended in two.** Added 2026-08-31 by the
video-readiness lane, which built the code that reads the reference
(`spikes/video_calibration.py`). A metre rule gives two points and fits no lens
— **use a printed checkerboard**, and no known-object route is built. The
board's square size must be measured with a rule and supplied, because it is
the one quantity nothing in the footage can check: every angle stays correct
and every length scales with it. **Instructions 12 and 13 say what to do with
the board**, and they belong to this instruction rather than to the end of the
list.

### 3. Film the drills the library contains, with a passer

Both sets show the same thing: she stands still, **tosses the ball upward
herself**, catches it at head height, brings it in, and tosses again. She begins
holding the ball, and no passer appears in either view.

Every one of the engine's eight drills is fed by a passer. The ball's flight is
authored from a passer position and a catch point, and the whole model turns on
a ball arriving with a speed and direction the athlete must answer. A ball
tossed straight up arrives slowly, vertically, and at a moment she chose.

**A perfect two-camera capture of a self-toss still grades nothing.**

**Instruction: film the drills by name, with a passer feeding the ball as the
manual describes.**

**"No passer" is not "no other person present."** Added 2026-09-02 from the
frame strips read while cutting the coach-page clips. The strips show the ball
entering and leaving frame between repetitions: she hands or lobs it to someone
off camera while she talks, and it is fed back in from above to start a cycle.
Repetition 1 of set 0.1 is exactly that — she stands empty-handed for over two
seconds, then the ball drops in from off frame, and she catches it.

The drill structure is still self-toss, because the toss-away, the flight and
the catch inside each repetition are all her own. But an off-camera helper was
present and handling the ball throughout, which matters twice: a second person
is a tracking hazard under instruction 7, and a repetition whose ball arrives
from off frame is not the self-toss the rest of this section describes.

### 4. One drill per clip

Set 0.1 runs a single drill for 28 seconds, eight of them spent talking before
any movement.

The engine's reference curves are indexed by PHASE, running 0 to 1 across ONE
movement — that is stated in `reference-curves.json`'s own note. A clip holding
two drills cannot be phase-matched to either curve, because there is no single
movement for the phase to run across. This is not a tidiness preference: it is
what makes a comparison against the engine possible at all.

**Instruction: start a clip, clap, do one drill, stop. Then start the next
clip.**

### 5. A 90-degree camera pair cannot see one side of the body

Usable readings from the two views together, set 0.1:

| landmark | left | right |
|---|---|---|
| wrist | 731 | **28** |
| ankle | 199 | **14** |

The side camera sees her in profile, so the far limb is occluded almost
entirely. No analysis recovers a joint the cameras never saw.

**Instruction: pick one.** A third camera on the far side; or two takes with the
athlete turned around between them; or choose drills where the near arm is the
working one, and say which arm each clip is for.

**THE THIRD OPTION IS ALMOST NEVER AVAILABLE, and the counts are worse than the
table above.** Added 2026-09-02 by the video-readiness lane, counted from the
lift's own rows and from `MovementDefinition.graded_measures()`:

| landmark | left | right |
|---|---|---|
| elbow | 734 | **0** |
| knee | 442 | **0** |
| wrist | 731 | 28 |
| ankle | 199 | 14 |

**The right elbow and the right knee appear in ZERO of 735 frame pairs.** The
wrist's 28 was the number this section already carried; the joints the library
actually grades are worse, and they are nothing at all.

**Seven of the eight drills grade at least one RIGHT-side measure** —
`rightElbowFlexionDegrees` in six of them, `rightShoulderElevationDegrees` in
two, `rightKneeFlexionDegrees` in one. So "choose drills where the near arm is
the working one" leaves exactly ONE drill in the library, and the option should
not be read as a general escape from the first two.

**A 90-degree pair costs three of the nine graded measures outright.** The
dry-run gate reports those three as having no evidence at all, per measure,
which is where this shows up if it is not fixed at the shoot.

### 6. Cameras within about four metres

The pose model's own card puts people further than about 4 metres out of scope.

**Instruction: keep both cameras inside 4 metres of the athlete.**

### 7. Nobody else in frame

The model tracks one person. A second person entering frame is a tracking
hazard, and one enters the right edge of `side 0.2` late in the clip.

**Instruction: clear the background. One person in shot.**

### 8. Whole body in frame, throughout

`front 0.1` crops her feet for part of the clip. Ankle readings drop to 199 of
the 735 usable frame pairs as a result.

**Instruction: frame for the whole body including the feet, and check it after
the first repetition rather than at the end.**

### 9. Do not stop a camera while the drill is still running

`front 0.1` is camera handling from 26.0 s and dark from 26.267 s. Its usable
content ends at **25.7 s**, measured per frame.

The pose model does not save you here: it detects a body through **26.133 s**,
past the usable end, because a smeared body is still body-shaped.

**Instruction: let the camera run for three seconds after the last repetition,
then stop it.**

### 10. Constant frame rate, or document it

The front cameras run at exactly 30.000 fps. The side cameras run at 30.012,
which is variable and drifts 11 to 13 ms over a clip — about a third of a frame.
Small here, free to avoid.

**Instruction: lock the frame rate if the phone allows it. 60 fps is better than
30 for a fast catch, if both phones can hold it. If a phone cannot lock its
rate, write down the phone model and the camera setting used, per take** — the
analysis can measure the drift afterwards, but only if it knows which clip came
from which camera and at what setting.

### 11. Camera originals, not messaging transcodes

These files are 1.4 to 1.8 Mbps and 576p-class. They have been through a
messaging app.

**Instruction: transfer the original files off the phones — cable, AirDrop, or a
file-sharing link, not a chat app.**

**This buys calibration accuracy as well as sharpness, which is more than this
instruction originally claimed for itself.** Added 2026-08-31 by the
video-readiness lane, from `spikes/video_calibration.py` and its tests. The
calibration fit has no bias of its own — at zero detector noise it recovers
every camera parameter exactly — so everything a real calibration gets wrong is
the footage's noise coming out the other end. Measured on a synthetic 36-view
rig, five seeds a row, with the corner detector's noise as the only variable:

| detector noise | focal error | pair rotation error | pair translation error |
|---|---|---|---|
| 0.30 px | 0.25 % | 1.23 deg | 42.1 mm |
| 0.15 px | 0.12 % | 0.61 deg | 21.0 mm |
| 0.05 px | 0.04 % | 0.20 deg | 7.0 mm |

**One degree of pair rotation error puts about 50 mm into a point triangulated
at three metres** — the size of the elbow residual this report could not
explain. Sub-pixel corner detection on a 576p messaging transcode is not
0.05 pixels.

### 12. Shoot a separate board clip per camera, and vary the board through it

Added 2026-08-31 by the video-readiness lane. Intrinsics belong to a phone, a
lens and a capture resolution — not to a take — and recovering them needs the
board at many angles and distances. One person waves the board in front of ONE
camera for about twenty seconds. The other camera is not involved and no clock
is shared, so this pass needs no clap.

**On a synthetic rig of 16 board views at 0.15 pixels of detector noise, one
seed, a board kept at one distance and one small tilt fit the focal length 1.93
percent wrong where a varied sequence fit it 0.85 percent wrong on the same
number of frames.** An earlier version of this line gave those two figures
without naming the rig they came from, which made a single seed read like a
property of boards.

The more useful statement comes from a different rig — 36 views at 0.05 pixels
— where **the narrow sequence was worse on 12 of 12 seeds measured**, median
0.145 percent against 0.066 percent, a ratio of medians of 2.19. The direction
is robust across every seed tried. The ratio is not, running from 1.29 to 193
per seed, so do not quote a single factor.

**Twelve seeds is what was measured. Six is what a test enforces.**
`VarietyTest` in `spikes/test_video_calibration.py` sweeps the first six of
those twelve and requires the narrow sequence to be worse on every one of them,
and requires the per-seed ratio to be visibly unstable. An earlier version of
this line said the test "holds" the twelve-seed figure, which claimed more
enforcement than exists.

**Instruction: per camera, record twenty seconds of the board moving through
the frame — near and far, tilted left and right, in the corners as well as the
middle. One camera at a time.**

### 13. For the pair clip, put the board on a stand and leave it

Added 2026-08-31 by the video-readiness lane. The two cameras' relative pose
belongs to the take, and recovering it needs both cameras to see the board at
the SAME INSTANT — which normally demands the sync this material never had. It
does not demand sync if the board does not move: a still board is in the same
place in every frame, so any frame of one camera pairs with any frame of the
other.

`video_calibration.py --pairing static` takes that route and then MEASURES
whether the board really held still, refusing the run with the measured
movement if it did not. An assumption nobody checks is how a wrong number gets
a provenance stamp.

**Instruction: place the board where both cameras see it, on a stand or against
a wall, and record a few seconds on both cameras without touching it. Then
shoot the drills.**

**Note on ordering.** Instructions 12 and 13 are additions to instruction 2 and
not replacements for it: 2 says a rigid object of known size must be in shot,
and these two say what to do with it. A printed checkerboard is what the code
reads. A metre rule gives two points and fits no lens, and no known-object
route is built.

### 14. The ball visibly in frame through every graded repetition, and a slate between them

Added 2026-09-02 by the video-readiness lane. **This one was found by looking,
after every number said the opposite.**

Cutting clips for the coach page, the repetition the alignment scored BEST in
the whole sample was rejected on sight: **it contains no ball.** A frame strip
across its whole window shows the athlete standing and gesturing. Measured, on
build `bb7dc4c`, repetition 0 of set 0.1 over 5.267 to 5.833 s:

| reading | value | where it placed |
|---|---|---|
| whole-curve warp distance | 0.02369 | **best of twelve**, against 0.06093 next |
| informative warp distance | 0.02213 | fifth of twelve |
| rank against all eight drills | 1 | **first, on both scorings** |

**An elbow curve fits a gesture as happily as a catch.** Every reading the dry
run had — warp distance, library rank, phase agreement, level gap — is computed
from that curve, so not one of them could see it. The null test could not see
it either: a gesture ranks first of eight drills because a monotone warp always
exists. One reading was odd and nothing acted on it: that repetition is still
for 35 percent of its window, more than double the next highest.

**Instruction: the ball must be visibly in frame for every repetition that is
to be graded.** Frame for it. If a repetition's ball leaves the picture, that
repetition is not gradeable, whatever its numbers look like.

**Instruction: frame high enough that the ball stays in shot through its
flight.** Added 2026-09-02 after watching all twelve repetitions frame by
frame. **This is a second and separate cause of a missing ball, and it is not
the athlete's doing.** Repetition 2 is a real catch — the ball is plainly in
her hands at 11.200 to 11.400 — and the ball then leaves the TOP of the frame
at 11.633, before the anchored moment at 11.733. Repetition 7 is the same
shape with a tighter margin: the ball is in frame at the anchor of 17.200 and
half out of it by 17.233, one frame later.

So a repetition can be a genuine catch, correctly found, and still carry no
ball at the moment the gate asks about — because the camera does not frame the
ball's flight. Of the three repetitions in session 1.0 with no ball at the
anchor, two are gesture stretches and ONE IS THIS.

**Instruction: put enough pixels on the hands to measure a wrist.** Added
2026-09-02 after Marius watched the engine's catch beside the real clips and
said the wrist action was missing. **The footage cannot answer him**, and the
reason is arithmetic rather than opinion.

The wrist angle has to be measured on the lever from the wrist to the knuckles.
On this material that lever is **30 pixels** — against a 90 pixel forearm — so
**one pixel of landmark jitter is 1.9 degrees, and at 30 fps that is 58 degrees
per second.**

Measured on the two stretches the frame strips prove she is standing still, the
noise floor of that reading is a median of **40**, a 90th percentile of **104**
and a maximum of **197 degrees per second**. At the two ball releases verified
by eye it reads **142.6** and **78.9 degrees per second** — **both inside the
still maximum, one below the still 90th.** A wrist flick at release cannot be
told from landmark jitter here, so no figure from this footage may be compared
against a solve.

**The motion is detectable in principle**: peaks of **502 degrees per second**
occur elsewhere in the same clip, nearly five times the still 90th. What is
missing is resolution at the instant that matters, not the movement.

**What would fix it, as pixel arithmetic and NOT as a promise.** The floor
scales with the lever, and the lever scales with linear resolution. These files
are 576p-class with a 30 pixel hand. Roughly: 1080p puts the lever near 60
pixels and the floor near 50 degrees per second; 4K puts it near 120 pixels and
near 25. **Both estimates assume the landmark jitter stays about one pixel, and
nothing here measures that assumption.** A closer camera buys the same thing as
more pixels.

So: **shoot so the hands carry at least about a hundred pixels from wrist to
knuckles** — by resolution, by lens, or by standing the camera closer — and
say which. The other instructions here are about seeing the movement; this one
is about being able to measure the part of it a coach can see and an engine
cannot yet reproduce.

**Instruction: put a slate between repetitions** — a clap of the hands, a
raised marker, anything that appears in both views and cannot be confused with
the drill. Two things follow from it. Repetitions stop having to be inferred
from the shape of a joint curve, which is what let a gesture become a
repetition in the first place. And a stretch of talking or gesturing between
takes is separated from the drill by something a person can point at rather
than by a threshold somebody chose.

**What answers this today, and what does not.** No ball detector is built, and
one could not gate anything until it had been validated — a detector that fires
on a bright patch of floor answers the question wrongly and confidently, which
is the failure the whole gate exists to prevent. The only instrument that has
ever answered it is **a person reading frame strips, one repetition at a
time**, and that is what caught this. The dry-run gate now carries the
condition, reads UNMEASURED until an annotation exists, and accepts one in
`spikes/video-annotations/ball-in-frame-<set>.json`.

### 15. Enough frames in the release to see the hand accelerate

**The engine does not drive the ball.** Its hands move **0.72 cm in the frame
before release and 7.37 cm in the frame after** — a factor of 10.2 across one
frame boundary. Nothing accelerates the ball at the moment it leaves. That is
the mechanism behind what Marius saw when he said the wrist action was missing,
and whether the carry should accelerate before release is decided by measuring
a real athlete and by nothing else available.

**Session 1.0 cannot answer it, and the reason is the frame rate rather than
the pixels.** Measured on this footage, at the rep 7 toss her wrist goes from
**0.7 to 6.3 cm per frame in about 67 ms**. At 30 fps that ramp holds **two
samples**. Two samples give a start and an end and say nothing about the shape
between them. Worse, one 30 fps frame spans both of the engine's 60 fps frames,
so the 0.72 and the 7.37 are averaged together and the step cannot be seen even
in principle.

**Instruction: shoot the release at 120 fps or faster.** Five samples inside a
67 ms ramp is a chosen minimum and needs 75 fps, so the next standard rate above
it. 240 fps is better and costs nothing but light. Below 60 fps there is no
frame pair that corresponds to the engine's claim at all.

**The pixels are not the limit here, and this is measured rather than assumed.**
The landmark jitter on this footage, taken as each sample's departure from a
smooth track through its neighbours, is **0.05 cm per axis typically and 0.36 cm
at the 90th percentile** — that is **0.24 and 1.79 pixels**. A one-frame
displacement carries two samples of it, so about 0.10 cm typically. The engine's
0.72 cm step is **7.2 times that**, and the 1.44 cm it becomes across a 30 fps
frame is 14.6 times it. There are enough pixels; there are not enough frames.

**This also settles an assumption instruction 14 had to leave open.** That
instruction estimated the wrist floor "assuming the landmark jitter stays about
one pixel" and said plainly that nothing measured that assumption. It is now
measured: **0.24 px typical, 1.79 px at the 90th**. The assumption was
reasonable and slightly optimistic at the tail. The wrist figures do not change.

**Where these readings come from.** `keypoints-front-0.1.json`, whose source
block names `front 0.1.mp4` at sha256 `f7faf38b…`. The scale is the athlete's
own measurement — 0.280 m across the shoulders — which reads 139.5 pixels
median across 785 frames, so one pixel is 0.2007 cm. The file carries a −90
rotation, so the decoded frame is 576 by 1024 and the landmark pixels are in
that frame, not in the 1024 by 576 the container reports.

**Its dry-run condition** is `the release is resolved`. It reads
`framesPerSecondMeasured` from BOTH keypoint files and takes the SLOWER, because
a hand speed read in one image is a projection and therefore a lower bound, so
the measurement needs the pair. Session 1.0 reads 30 and FAILS it.

### 16. A keyframe interval that keeps the important frame reachable

**A separate fault from the frame rate, and it has already cost this project a
reading.** The side file of session 1.0 carries **three keyframes, at 0.000,
9.996 and 19.992 seconds** — a ten-second interval, where the front camera has
one per second. Any reader that snaps to a keyframe, asked for 16.93 on that
file, lands at 9.996. That is where repetition 2's catch lives, which is exactly
how repetition 2's catch came to appear under a repetition 7 label.

A capture can run at 240 fps and still put the one frame that matters out of
reach. The two properties are independent and the instructions must be too.

**Instruction: keep the keyframe interval at about one second.** That is what
the front camera did, and nothing about it caused trouble. If the camera cannot
be told, record what it produced so a reader knows before trusting a timestamp.

**Its dry-run condition** is `the release moment is addressable`. It reads both
files and takes the LONGER interval, because one unreachable view is enough to
lose the frame — and on session 1.0 the fault is on the SIDE file while the
front is fine, so a condition reading only the front would miss the very reading
it exists for. No tool in this repository records the interval yet, so it reads
UNMEASURED on every set until `video_keypoints.py` writes it.

### 17. A bounce pass, filmed so the rebound can be measured

**The engine has no floor.** A released ball is one unbroken parabola, so a
bounce pass cannot be represented today. It cannot be graded and it cannot be
authored either. If Marius rules the floor in, the model needs a rebound ratio,
and that ratio must be **MEASURED from footage and never typed**. A typed ratio
is a number with no instrument behind it, which is the shape of every figure
this lane has had to withdraw.

**Instruction: film a bounce pass with the floor contact in view in both
cameras.** Record what the measurement needs:

- The ball's height before the floor contact and after it.
- A known distance in the same frames, so both heights carry a scale.
- The contact itself in both views, not inferred from the ball leaving one.

The side camera is the one that sees the height. The front camera is what makes
the reading two instruments rather than one.

**Its dry-run condition** is `the floor is in view`, and its threshold kind is
`unavailable` — **there is no bar to set**. No drill in the library can declare
that its ball bounces, because the engine has no floor, so the gate cannot ask
the question of a capture at all. The condition exists to say so out loud rather
than to let the silence pass for a pass.

## What was measured, and how well

### Two-view agreement

On 735 frame pairs and 5,088 landmark readings, comparing the height of each
landmark as the front camera sees it against the side camera's answer for the
same landmark:

| landmark | readings | median | 90th |
|---|---|---|---|
| left shoulder | 735 | 14.2 mm | 39.8 mm |
| right shoulder | 735 | 17.3 mm | 46.0 mm |
| left knee | 442 | 13.4 mm | 27.2 mm |
| left elbow | 734 | 65.8 mm | 193.7 mm |
| left ankle | 199 | 90.2 mm | 125.5 mm |
| left wrist | 731 | 140.9 mm | 336.4 mm |
| both hips | 735 | 3.7 mm | 8.5 mm |

**The hips are the vertical origin of both views, so their 3.7 mm is nearly
circular and is not a measure of accuracy.** It is the most quotable number here
and it means the least. Read the shoulders and the knees.

### The elbow angle: nothing tested explains the disagreement

Two independent readings of the same left elbow — one from the 3D lift, one
from the side view alone — differ by a **median of 21.2 degrees**, 90th 63.1.
This is measured on 730 frames, five fewer than the residual table's 735,
because it additionally requires shoulder, elbow and wrist all visible in
**both** views rather than one landmark at a time.

**It is a symmetric spread, not a constant offset.** The signed median is
+1.6 degrees, taking the lift's angle minus the side view's. Those two point at different causes and only the second would
suggest a fixable bias.

**About 5.0 degrees of it is geometry rather than error.** A 3D angle and a
side-view 2D angle are not the same quantity: the side camera cannot see the
across axis, so it reads the arm projected into its own plane. That floor was
isolated by taking the same 3D and dropping `across` — no second instrument
enters, so nothing else can be blamed. It is about a quarter of the 21.

**Four explanations were raised and all four were refuted**, two by each lane,
and each lane killed one of its own:

| candidate | test | verdict |
|---|---|---|
| sync uncertainty | does not grow with speed above 1 m/s | refuted |
| projection alignment | correlation +0.088, flat across every band | refuted |
| depth scale error | banding is U-shaped, not monotonic rising | refuted |
| camera foreshortening | banding also U-shaped | refuted |

**Nothing tested explains the 21 degrees.** No fifth candidate is offered here:
a report that ends on an untested hypothesis reads as an explanation, and there
is not one.

**What that refutation is worth, stated honestly.** These are correlations
against a quantity whose median is 21 degrees with a wide spread. That gives
good power to refute an effect that DOMINATES and poor power to exclude one
contributing a few degrees. None of the four is ruled out as a minor
contributor, and this data cannot distinguish "small effect" from "none". The
case is bounded, not closed.

**A correlation quoted without the exact definition of both quantities is not a
measurement.** The two lanes computed the same refutation on identical frames
and got +0.023 and +0.140 — a six-fold difference, caused by one taking the
larger across-extent of the two arm SEGMENTS and the other the shoulder-to-wrist
span. Neither wrote the choice down. The refutation survives all four readings
taken, and the discrepancy is the sharper lesson: it is the same fault as a
number quoted without its instrument.

**One unexplained fact, recorded without a story.** Every banding either lane
has tried is U-shaped — worst at both extremes of the range, best in the
middle. Nobody can say why.

### Where the sync uncertainty bites

Agreement was measured, not predicted. On trunk landmarks in slow phases the two
cameras agree to **13 to 17 mm**. On the hands in fast phases they disagree by
**100 to 340 mm**, and that disagreement stops growing with speed above about
1 m/s — sync uncertainty bounds it rather than explaining it. The lift is usable
in stance, hold and ready; in fast phases it is illustrative and never a
measurement.

### Scale

Recovered from the athlete's own measurements rather than an anthropometric
table. Wingspan 1.82 m minus twice the 0.77 m one-arm reach leaves **0.280 m
across the shoulders**, visible in the front view every frame. The side view's
scale is tied to the front's by requiring the torso to be the same length in
both — one length seen twice, needing no assumptions about body proportions.

## Method notes for whoever runs this next

**Repetitive drills defeat whole-signal correlation, in any modality.** The
athlete throws and catches on a cycle of a second or two, so the signal is
nearly periodic and the correlation has many near-equal peaks. This held for
audio and for pixel motion alike. A unique event is not a convenience for this
method — it is a requirement, and that is what a clap is.

**"Detected" does not mean "usable".** The pose model finds a body in smeared
frames with high confidence. Detection answers *did the model find a body*;
frame quality answers *is this frame footage*. A consumer trusting detection
alone measures a blur with confidence.

**The elbow angle has two conventions and they are opposites.** The engine's
`elbow_flexion_degrees` in `spikes/segment_measures.py` is `180 − included
angle`, so a straight arm is **zero**. A video curve carrying the included angle
would be the opposite convention, and laying the two side by side compares
different quantities that both read in degrees. This was caught before it
published a number, by reading the definition rather than assuming it.

**Two readings of the same joint disagreed by 21.2 degrees and neither was
averaged into the other.** Four candidates were raised and all four refuted —
the table is above, under the elbow angle — and the cause remains unidentified.
The honest statement is that neither reading is a measurement of that joint on
this material.

Every correlation in that table carries a definition, and they are not
interchangeable. The projection-alignment figure of +0.088 is the FOREARM's
share along the side camera's viewing axis against the absolute gap, computed
on the front-only `up`. Quoting it without that clause would be the same fault
the paragraph above it describes.

## Artifacts

Computed at the time of writing. Any regeneration supersedes these.

| file | size | sha256, first 32 |
|---|---|---|
| `keypoints-front-0.1.json` | 10.0 MB | `e1ded2a18569095ed53feb9e77c88dc7` |
| `keypoints-side-0.1.json` | 10.9 MB | `c05b9f545326c81ea73cdda5c5a35cc1` |
| `keypoints-front-0.2.json` | 11.5 MB | `3d57d4930cdce7d04e227ec8264ca918` |
| `keypoints-side-0.2.json` | 11.4 MB | `7768feeeecfc9e8819dd1d9ced4a261a` |
| `lift-3d-0.1.json` | 1.0 MB | `209f878249bd26714f5fe87aa35d61dd` |
| `elbow-curve-0.1.json` | 0.1 MB | `e4f7bcfa057aa3e438149d0fda8f5c5c` |
| `reference-curves.json` | 0.1 MB | `4f779c6ea4f5965ae11b27cde2bd4622` |

All under `spikes/poc-output/video/`. **The four keypoint files and
`reference-curves.json` carry `generatedFrom` stamps**; the lift and
elbow-curve files carry none, so their provenance is the keypoint files they
were derived from.

**Those stamps read commit `b8d68fa` with `treeWasClean: false`** — the code
was uncommitted when it ran and was committed immediately afterwards. An
earlier draft of this report said "generated at commit e4f0983", a commit that
did not exist when the files were written. The stamps are the authority; quote
them rather than a commit chosen later. Set 0.2's
two views carry `"measured": false` in their sync block: only set 0.1 has a
measured offset between the cameras.

The tooling is `mediapipe` 1.0.1, Apache 2.0, with the
`pose_landmarker_heavy.task` bundle. The bundle itself carries no licence text
of any kind; its model card states Apache License, Version 2.0, and that is the
authority. The card also names 3D pose measurement in scope, and puts people
beyond 4 metres and multi-person scenes out of it.

## Working notes

The full working record, including the failures and two mistakes made and
corrected during the spike, is in `spikes/VIDEO_SPIKE_NOTES.md`.
