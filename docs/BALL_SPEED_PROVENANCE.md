# Every ball in the library travels at one undocumented constant

The athlete's return pass takes its speed from the pass thrown at her. That
reuse is real, and this document measures what it costs today.

**No solve was run.** Every number below comes from the JSON in
`spikes/movements/` and from reading `spikes/possession.py` and
`spikes/author_flight.py`. The shared MHR assets are still down, and none of
this needed them.

## The mechanism

`possession.return_velocity` sends the ball back to the passer. Where a ball
file does not author its own launch, the speed comes from
`possession.incoming_speed_cm`, which measures the passer's flight. So the
athlete throws at the speed she was thrown at.

The docstring already states the failure mode: a drill that holds the ball
from phase 0 needs a short fictional flight to satisfy `arrival`, and that
flight sets her throwing speed, so the earlier she holds it the harder she
throws. **That failure does not fire in the library today.** Every drill has a
real parabola with a flight of 0.219 to 0.315 seconds.

## What the library actually throws at

`arm_length_cm` is 52.675 cm. It is recovered from each ball file, and every
file agrees. `netball_two_hand_snatch_pull_in.ball.json` states the same
figure in prose as "this 52.7 cm arm", which is a second instrument on the
same quantity.

| drill | flight s | horizontal cm | derived cm/s | authored cm/s |
|---|---|---|---|---|
| `deflect_high` | 0.315 | 189.2 | 600.0 | 600.4 |
| `double_foot_landing` | 0.219 | 131.7 | 600.1 | 600.4 |
| `hooks_jump_pull_in` | 0.305 | 183.3 | 600.1 | 599.3 |
| `hooks_outside_hand` | 0.268 | 161.0 | 599.8 | 600.3 |
| `one_hand_snatch_to_other_hand` | 0.282 | 169.3 | 599.8 | 599.9 |
| `two_hand_catch_chest` | 0.276 | 165.4 | 600.1 | 599.5 |
| `two_hand_snatch_pull_in` | 0.278 | 167.5 | 603.1 | 600.2 |
| `two_hand_snatch_straight_back` | 0.277 | 166.5 | 600.0 | 600.2 |

"Derived" is what `incoming_speed_cm` computes. "Authored" is the flight
block's own launch speed, reduced to its horizontal component. The two agree
everywhere.

**Eight drills, one speed.** The flights differ in length and duration, and
the speed does not move.

## Where the constant comes from

`author_flight.DEFAULT_SPEED_CM` is `600.0`, and it authored all of them. Its
comment is honest about what it is:

    # A drill feed. A game pass is faster, and the flight gets shorter with it.

**That comment is the whole provenance.** A search of the repository finds no
coach, no measurement and no source for 600 cm/s. Nothing grades it. No band
reads it. It sets the feed she catches and the pass she returns, for every
drill in the library.

## The agreement above proves the arithmetic and not the value

`incoming_speed_cm` recovers 600 from a flight that was authored at 600. The
round trip is a tautology. It is a good check that the derivation is correct,
and it is no check at all that 600 is right.

This is the shape the project keeps finding: two things agree, and the
agreement is an artefact of their sharing a source rather than evidence about
the world. **No test asserts this round trip**, which was checked rather than
assumed. `test_authored_launch.py` builds synthetic tracks and each of its
probes carries an anti-hollow twin.

## What is not settled

- **Whether 6.00 m/s is a netball drill feed.** This is a coaching question
  and it belongs at the coach morning. The constant's own comment says a game
  pass is faster, so the engine already claims to be below match pace, and no
  coach has agreed to that.
- **Whether she should return the ball at the pace it arrived.** The
  `return_velocity` docstring marks this PROVISIONAL: it reads the manual's
  cues and no coach has confirmed it.
- **The three variant files** `high`, `low` and `wide` have no motion track,
  so they are not in the table. They were not measured, and they are not
  claimed to be clean.
- **`two_hand_snatch_pull_in` derives 603.1 against an authored 600.2.** That
  gap is 0.5 per cent and it comes from rounding in the authored phases. It is
  recorded because it is the one row that does not match to a tenth. It is not
  a defect.

## Provenance

Read from the working tree at `816fc08`. The tables are file-level facts and
need no solver. The claim that no test asserts the round trip comes from
reading `test_authored_launch.py`, not from a search alone.
