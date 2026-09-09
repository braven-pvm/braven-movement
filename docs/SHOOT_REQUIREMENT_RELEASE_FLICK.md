# What a camera would need to see a release flick

Written 2026-09-09 under principle 7, which closes the question on the footage
we have, and principle 3, which asks that what we learn ends as an instrument or
a written procedure rather than only as a result.

**This is a capability document, not a result.** It says what CAN be measured at
a given rate, scale and shutter. It says nothing about what this athlete did.
Refer to principle 4.

**The existing filming brief says "slow motion" and gives no numbers.** This
supplies them.

## Why the current footage cannot answer it

Cited from the video lane, not re-derived here:

| | |
|---|---|
| rate | 30.012 fps measured, not nominal |
| the hand | **15 to 30 pixels** |
| angular resolution | **one pixel is 2 to 3 degrees** |
| landmark scatter, still arm | **11 degrees raised, 22 hanging** |
| at the release frame | the index landmark slid **45 px** on a motion-blurred hand while the wrist moved 35 |

**A 5 degree band cannot be graded by an instrument whose pixel is worth 2 to 3
degrees**, and a one-frame event at 30 fps cannot be separated from a landmark
sliding across a blurred hand. That is the whole of it.

## The four requirements, with their derivations

**Every number below states its inputs. Two inputs are assumptions and are marked
as such.**

### 1. Rate: at least 240 frames per second

A flick must span enough frames that it cannot be confused with a single-frame
landmark artefact, which is exactly the confusion the video lane's null
produced. **Five frames is the minimum to see that an event has a shape; ten to
see the shape itself.**

**ASSUMPTION, and it is the largest gap here: nobody has measured how long a
release flick takes.** Taking 40 to 60 ms as a working figure, five frames needs
100 fps and ten needs **170 to 250 fps**. 240 fps is the nearest common camera
setting and gives ten to fourteen samples.

**The duration is itself a research question**, and a shoot at 240 fps would
answer it for the first time. That is the honest reason for the rate: not that
240 is known to be enough, but that it is the first rate at which the question
can be asked.

### 2. Scale: the hand at 100 pixels, preferably 150

Angular resolution scales with the pixels across the hand. At 15 to 30 px the
video lane measures 2 to 3 degrees per pixel, so:

| hand, pixels | degrees per pixel | against a 5 degree band |
|---|---|---|
| 20, today | 2.5 | **half a band in one pixel** |
| 100 | 0.5 | a tenth of a band |
| 150 | 0.33 | a fifteenth |

**100 px is the floor and 150 gives margin.** That is a tighter framing or a
longer lens, and it trades against keeping the whole body in shot. **A second
camera framed on the hand alone is the cheaper answer than compromising the
body view**, and the two-camera synchronisation this project already built is
what makes that affordable.

### 3. Shutter: 1/2000 s or shorter

The hand travels **2.5 to 5.4 m/s** through the release, measured by the video
lane.

**ASSUMPTION: a hand is about 19 cm across.** At 150 px that is 0.127 cm per
pixel. At 4 m/s the hand covers one pixel in 0.32 ms, so:

| shutter | blur at 4 m/s |
|---|---|
| 1/1000 s | 3.2 px |
| **1/2000 s** | **1.6 px** |
| 1/4000 s | 0.8 px |

**Blur of 3 px on a 150 px hand is worth a degree of angle. Blur of 3 px on
today's 20 px hand is worth eight.** The requirement is not that blur be zero: it
is that blur be small against the feature being measured, which is why it cannot
be stated without the framing.

**This is a lighting requirement more than a camera one.** 1/2000 s at 240 fps
needs substantially more light than the current recordings had.

### 4. A stationary null in the SAME shoot, at the SAME framing

**This is the requirement most likely to be dropped and it is the one that makes
the rest usable.**

Film the athlete **holding the release pose still**, at the same distance, lens,
rate and shutter, for several seconds. That measures the landmark scatter in the
regime of the claim.

**The alternative is the fault this project has recorded sixteen times: a noise
floor measured in one regime and spent in another.** The current null was
measured on a still arm and the claim it was spent on was a fast, blurred one.
A null filmed at the same framing as the event costs ten seconds of recording
and makes every angle in the shoot defensible.

### 5. A known length in the plane of motion

Not about the flick, and it removes a disagreement that already cost two lanes a
day.

**The video lane's two scales disagree by about 30 per cent at the median**, with
a per-frame ratio running 0.21 to 3.05, because both are inferred rather than
measured. **A rigid object of known length, in the plane the athlete moves in and
visible in the same frames, converts pixels to metres without inference.**

## What a shoot meeting these would settle

- **Whether a release flick exists at all**, and how long it takes, which nobody
  has measured.
- **The wrist and finger angles through contact**, which are the two parameters
  the release model has no source for.
- **The ball's speed at release from the hand**, which would be the first real
  source for `author_flight.DEFAULT_SPEED_CM = 600`.

## What it would still not settle

**How a level-1 netball player SHOULD release.** That is a coach's statement, not
a measurement, and no camera supplies it. The manual asks for pass speed as an
objective in two drills and gives no number for it.
