# Where the authored 600 came from, and what it produces

Step 1 of the release-timing unit, which Marius ruled mechanical on 2026-09-08.
Read on 2026-09-09 against `13148a7`. **Nothing is built here and no value is
proposed.** No engine file is changed and `spikes/movements/` is gate 4 and
untouched. Every figure comes from `scripts/launch_provenance.py`, committed
beside this document, or from git.

## 1. The provenance, traced through git

`author_flight.DEFAULT_SPEED_CM = 600.0` entered the repository in one commit.

| | |
|---|---|
| commit | `d1c89d1085620f3d5ae27e8511cc7fea77682379` |
| date | 2026-08-18 |
| author | Marius Bloemhof |
| subject | `feat(spikes): four balls, one technique, no hand authoring` |

**The comment beside it has never changed since that commit:**

    # A drill feed. A game pass is faster, and the flight gets shorter with it.
    DEFAULT_SPEED_CM = 600.0

**The commit message does not mention speed, 600, or any unit of velocity.** It
is a long message about milestone 4, the turn derivation and the snapping check.
The constant arrived with three others in the same block and none of them is
justified there.

So the provenance is complete and it is short. **The number is the author's own
working figure for a drill feed, stated as such, with no coach, no measurement
and no citation.** It is not anonymous, which matters: Marius can say what he
based it on, and no one else can.

The bounce pass's own ball file already records the same thing in
`launchSpeedNote`, and adds the point section 2 makes.

## 2. It is a HORIZONTAL speed, and this is easy to get wrong

`ball_track.solve_launch` takes the horizontal component and derives the
vertical from the span and the rise:

    seconds = span / horizontal_speed_cm
    vertical = (rise + 0.5 * GRAVITY_CM * seconds * seconds) / seconds

**So the launch speed is never 600. It is always larger, and how much larger
depends on the span.** Any sentence comparing 600 with a measured ball speed is
comparing a component with a magnitude.

## 3. What the manual says about pass speed

**No number and no unit.** The manual states no speed anywhere: a search for
`m/s`, `km/h` and the spelled-out forms returns nothing. Every apparent match is
the letters `mph` inside `lymphatic` and `emphasizes`.

**It does name pass speed as a coachable objective**, twice, which is the more
useful fact:

- `Category: Unit - Passing (Timing) Name of drill: Around the world` —
  `Objective: Speeding up the speed of the pass`
- `Category: Unit - Passing (Timing&Target) Name of drill: T-drill with runner
  in middle` — `Objective: To teach player pass accurately and with speed`

**A drill whose objective is to increase pass speed cannot be graded by an
engine whose pass speed is one constant.** That is the manual's own argument for
the ruling, and it is stronger than any figure in this document.

**AND THE MANUAL DOES STATE A DISTANCE.** `Area: Court (5-7m)` appears **37
times**, and it is the only distance the manual states in that form anywhere.
Every passing drill in the passing block uses it.

## 4. What 600 produces at the distance the manual states

Released and caught at the same height, which is the flattest a pass can be and
therefore the kindest case for the constant:

| span | flight | vertical | launch speed | angle | apex above release |
|---|---|---|---|---|---|
| **4.0 m**, the engine's own | 0.667 s | 327.0 | 683.3 cm/s | 28.6 deg | 54.5 cm |
| 5.0 m | 0.833 s | 408.8 | 726.0 | 34.3 deg | 85.2 cm |
| 6.0 m | 1.000 s | 490.5 | 775.0 | 39.3 deg | 122.6 cm |
| 7.0 m | 1.167 s | 572.2 | 829.1 | 43.6 deg | 166.9 cm |

**At the manual's own drill distance the authored constant produces a lob.** A
pass thrown at 43.6 degrees, rising 1.67 m above the release, is not a netball
pass. **And the engine feeds from 4.0 m, which is below the manual's entire
stated range**, so even the 28.6 degrees in the first row is measured at a
distance no drill in the manual uses.

**A level pass's apex depends only on its flight time**, because the vertical
must cancel gravity exactly: `apex = g * t * t / 8`. A flatter pass over the
same span is therefore a faster pass, and the horizontal speed is the only
lever:

| span | apex 20 cm | apex 40 cm | apex 80 cm |
|---|---|---|---|
| 5.0 m | 1238 cm/s | 875 cm/s | 619 cm/s |
| 6.0 m | 1486 cm/s | 1051 cm/s | 743 cm/s |
| 7.0 m | 1733 cm/s | 1226 cm/s | 867 cm/s |

To throw 6 m and rise no more than 40 cm above the release, the ball must leave
at **1051 cm/s horizontally, 1.75 times the authored constant**.

## 5. What depends on it today

**Fifteen ball files, and every one of them.** Four carry the constant directly
and eleven carry a value derived from it:

| field | files | value |
|---|---|---|
| `launch.speedCmPerSecond` | the 4 passes | 600.0, the constant itself |
| `flight.launchSpeedMetresPerSecond` | the 11 others | 6.11 to 6.64 |

**The eleven are not independent, and this was verified rather than assumed.**
Taking `netball_two_hand_catch_chest` and its own recorded inputs — a release at
135.0 cm, a catch at 145.4 cm and a flight of 0.276 s — a horizontal 600 cm/s
reproduces three further fields that the file records:

| field | recorded | reproduced from 600 |
|---|---|---|
| `launchSpeedMetresPerSecond` | 6.24 | 6.245 |
| `launchAngleDegrees` | 16.1 | 16.1 |
| `peakHeightCm` | 150.2 | 150.3 |

**They vary from 6.11 to 6.64 only because their geometry varies.** The spread
looks like eleven measurements agreeing and it is one constant seen eleven
times. This ledger already records that shape: a shared-source agreement
confirms its source rather than testing it.

## 6. What a derived launch would replace it with

**This document does not propose a value, and the slot for one is named and
empty.**

The video lane is measuring the athlete's ball speed at release from the
footage. **That would be the first real source this constant has ever had**, and
it belongs here when it lands. This step does not wait on it.

Two constraints are already available for whatever value arrives:

1. **It must be stated as a horizontal component or converted to one**, because
   that is what `solve_launch` consumes. A measured ball speed is a magnitude.
2. **It must be checked at the manual's 5 to 7 m and not only at the engine's
   4.0 m**, because the flight's shape changes with the span and the current
   constant is defensible at neither.

**And `DEFAULT_PASSER_AHEAD = 4.0` is a second unsourced number on the same
line.** It is below every distance the manual states. Changing the speed without
it would derive a launch for a drill the manual does not describe.
