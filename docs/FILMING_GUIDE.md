# Filming a drill for movement analysis

Written for coaches. The web version, which prints, is the same words:
https://claude.ai/code/artifact/c3a6b17c-2076-4eac-ae9c-161abc0c40ee

Two phones, two tripods, about twenty minutes.

## What you need

- Two phones that can record video.
- Two tripods, or two steady places to stand the phones.
- The player's height and weight, written down.

## Where to put the cameras

One camera in front of her. The second one round to her side, about a quarter
turn away. Both must see all of her, all the time.

**Why two.** With one camera we cannot tell how far away her arm is, only where
it is on the screen. One camera is out by about 50 degrees. Two is out by
almost nothing. This is measured, in `spikes/spike_h_roundtrip.py`.

## Filming, step by step

1. Stand both phones on tripods. Far enough back that she stays in the picture
   for the whole drill. Close enough that she fills most of the height.
2. Get some court lines in the shot. The lines are a ruler.
3. Start both phones recording, then leave them alone.
4. Clap once, where both cameras can see you. This lines the two videos up.
5. Ask her to stand still for five seconds, facing camera 1, arms slightly away
   from her sides. This is how we measure her.
6. Film the drill three times, with a reset between each one.
7. Stop both phones. Write down the drill and who was doing it.

## Please do not

- Do not hold the phone. It must not move at all.
- Do not follow her with the camera. No panning, no zooming.
- Do not let anyone walk between the camera and her.
- Do not use slow motion.
- Do not film straight into the sun.
- Do not stop one phone before the other.

## Things that help

- Fitted kit rather than baggy.
- Bare legs and arms if it is warm enough.
- A plain background rather than a busy fence.
- Sixty frames a second if the phone offers it.

## If the wrists and fingers matter, the current setup cannot see them

Marius watched the coach player on 2026-09-08 and said the athlete flicks her
wrist and fingers in the last moments of contact, and that the engine's hand
stays flat. **Neither run of the 2026-08-28 footage can measure that flick**,
and this section says what would.

**Why not.** The hand is about twenty pixels across in these recordings, so
the forearm-to-hand angle is taken from a vector a quarter the length of the
forearm it is measured against. One pixel of landmark error is then 2.0 to 3.3
degrees, and a still, well-tracked arm reads 11 degrees of swing where nothing
is moving. A slight flick is inside that.

**What a next shoot needs.** The two requirements are independent and failing
either makes the other pointless. The hand sizes below are the wrist-to-hand
vector in pixels; the fractions compare with the best side view we have, where
that vector is 22.1 px.

| if the flick is | and lasts | the hand must be | that is | and the camera | 
|---|---|---|---|---|
| 25 degrees | 100 ms | about 29 px | 1.3x today | about 40 fps |
| 15 degrees | 50 ms | about 49 px | 2.2x today | about 80 fps |

**The frame rate is the harder gate.** Both cameras ran at 30 fps, where one
frame is 33 ms, so a 50 ms movement gets one and a half samples: even a perfect
landmark could not show it rising and falling. The distance is a smaller
change than it looks — the athlete needs to be roughly a third to twice again
closer, or the lens longer.

**The fingers are a different problem, not a harder one.** The pose model
carries one point per finger — index, pinky and thumb tips — and no knuckles,
so finger flexion is not expressible in it AT ANY RESOLUTION or frame rate.
Measuring it needs the hand landmarker, twenty-one points per hand, which is a
separate model and wants the hand much larger in frame again. That is a
decision to take before the shoot, not after.

**What the current footage DOES measure well** is hand SPEED, because the
wrist travels 8 to 40 pixels between frames where the hand vector is only 20
pixels long. Her hand peaks at 3.3 to 5.4 m/s through a release against a
standing-still floor of 0.06 to 0.10 m/s. If speed is the question, this
footage answers it; if the angle is the question, it does not.

The numbers and the instruments are in
`.remember/extraction/wrist-at-release/`.

## What to send

- Both videos from each set. The pair, not one of them.
- The player's name, height and weight.
- Which drill it was.

If something goes wrong, film it anyway and say what happened.
