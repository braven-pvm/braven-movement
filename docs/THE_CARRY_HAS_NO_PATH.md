# The carry has no path, and the ball is pinned to her

Measured on 2026-09-09 against `13148a7`, for the release-timing unit Marius
ruled mechanical on 2026-09-08. **Nothing is built and nothing is proposed.**
`spikes/movements/` is gate 4 and untouched. The instrument is
`scripts/carry_path.py`, committed beside this document.

This exists because **three lanes now depend on the answer**: it reshapes gate 4
for Marius, it corrects a reading in the contract lane's section 8, and it is
the mechanical explanation of the movement lane's own wrist figures.

## The two readings that were offered

Both were plausible, both were held by someone, and they cannot both be true.

1. **"The pre-release hand follows the AUTHORED CARRY PATH in each drill's
   `.ball.json` keys."** Held by the orchestrator and repeated by this lane.
2. **"The wrist is constrained to a STATIONARY authored point for the entire
   carry."** Read by the contract lane from `ball_track.offset_at` and
   `contact_solve.py:530`.

**Neither is right, and the truth is the third thing.**

## The population, stated before the result

| | |
|---|---|
| drills | the four passes: `chest_pass`, `overhead_pass`, `bounce_pass`, `one_hand_high_pass` |
| frames | every held frame of each, **76 per drill** |
| the offset | read from **`ball.offset_at(phase)`**, the engine's own call, at each held frame's own phase |
| the world position | `possession.frames[n].centre`, the engine's own |
| rebuilt | **nothing.** No parabola, no frame, no offset is reconstructed here |

## The result

**THE AUTHORED OFFSET IS ONE TRIPLE, HELD FOR THE WHOLE CARRY.** Counting the
distinct values of `ball.offset_at` across all 76 held frames:

| drill | held frames | distinct authored offsets | world motion, mean | max |
|---|---|---|---|---|
| `chest_pass` | 76 | **1** | 0.36 cm/frame | 0.71 |
| `overhead_pass` | 76 | **1** | 0.98 | 2.14 |
| `bounce_pass` | 76 | **1** | 0.56 | 0.70 |
| `one_hand_high_pass` | 76 | **1** | 1.60 | 2.82 |

The triple is `across 0.0, up 0.12, ahead 0.55` on all four.

**So reading 1 is wrong: there is no path.** Every pass authors two keys, both
before phase 0.02, at the same point, and `offset_at` clamps to the nearest end
of the flight for every later phase.

**And reading 2 is wrong: the point is not stationary.** The ball moves through
the carry on every drill. The engine places that constant offset in the
**athlete's frame**, and she moves.

**THE BALL IS PINNED TO HER. Every centimetre it travels before the release is
her own motion.**

That is why the wrist turns only 1.07 to 5.55 degrees through contact: the hand
grips a ball that has no motion of its own to follow.

## The FUNCTION the claim was traced in is not on the library path. The module is.

**A first version of this section was headed "the module ... is not on the
library path", and its own body said `solve_contact`.** The heading overstated
the text under it, which is the fault this repository records most often, and
two lanes were within one sentence of generalising it. It is corrected here and
the distinction is the point.

**The function is not reached.** `solve_contact`, which contains the
`contact_solve.py:530` fallback the contract lane read, has exactly one caller in
the repository and it is that module's own `main()`. It is a spike entry point.
The path the library build uses is `possession.py`'s frames into
`possession_solve.py:245`, which takes `frame.centre` for a holding side.

**The MODULE is reached, and its constants are load-bearing.**
`possession_solve.py` imports `elbow_poles` and `upper_arm_aim` from
`contact_solve` at lines 35 and 36 and calls them at 304 and 308. Both sit
outside `solve_contact`. So `ELBOW_POLE_ANGLE_DEGREES` at line 127 —
**the 31.3 a coach is being asked to move to 37.3** — is reached by every solve
the library performs. Found by the movement-science lane and verified here.

So the contract lane's reading was **right about the code it read and wrong about
which code runs**, and "`contact_solve` is a spike" would be wrong in the other
direction. **A file is not on or off the path. Its functions are.**

## The wrong origin, kept rather than deleted

**The first version of the instrument measured the ball against the SHOULDER
MIDPOINT** and reported it moving 0.28 cm per frame relative to the body. That
reads as a refutation of a body-fixed offset. **It is not, and it was nearly
published as one.**

The engine's frame is anchored at the **chest** and carries the athlete's
orientation. The shoulder midpoint is a different origin, and it moves
differently when the trunk turns. A constant offset in one frame is a changing
offset in the other. **One phrase, two origins**, which is the fault this
repository records more often than any other.

The wrong proxy is named in the instrument's own docstring rather than removed,
because the next person will reach for the same one.

## What it does to the unit

**Gate 4 changes shape.** "Retime the carry" is not a retune of existing keys,
because there are no keys to retune: there is one triple.

**The question is no longer how many numbers change. It is how many must be
CREATED, and from what.** A mechanical release needs a carry that accelerates
into the release. That is a path authored where none exists, and **its shape has
no source**: not the manual, not the footage, not a coach. It is a coaching
judgment nobody has made.

**No path is authored until Marius has scoped it.**

## What is now cheap to test, and was not before

The orchestrator's hypothesis is well posed in these terms: today the hand's
incoming speed at the release is her trunk's, the ease-out
`out = 1 - (1 - t)^2` begins at full speed and therefore assumes a matching
incoming speed, and **the mismatch is the release seam**. If a carry that
accelerates supplies that speed, the seam may close without any change to the
easing, and one decision replaces two.

That is the carry-side half of the sweep, and this measurement is what makes it
a defined experiment rather than a guess.
