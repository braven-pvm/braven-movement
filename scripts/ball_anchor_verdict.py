"""Per-figure pass or fail for the ball's anchor, against the 1 cm rule.

The renderer places the ball at `shoulders + fromShouldersInArms * arm`, and
every term but the midpoint is transmitted and identical. So the ball's error
is the shoulder midpoint's error, one for one.

DO NOT SUBTRACT THE TWO COLUMNS. This rig's midpoint sits 6.06 to 13.52 cm
below the engine's, and almost all of that is body shape: the arms are 48.547
against 52.680, and this rig is not a uniform scale of that athlete. A
shoulder-to-pelvis distance that differs between two bodies is not a defect.

THE ERROR IS THE ENGINE'S VARIATION, because this rig's is zero. It is a
subtraction WITHIN the engine's column, from the phase this rig is calibrated
to. That phase is the engine's neutral, and the evidence for it is below.
"""

# Shoulder midpoint above the pelvis, cm, per phase. These are the MOVEMENT
# LANE'S measured values, reported 2026-09-04: pelvis is the rig joint `root`,
# vertical only, from the solved pose, at frame round(atPhase * (frames - 1)).
# They are a snapshot of another lane's instrument, not a reading taken here.
ENGINE = {
    "overhead_pass": [("ready", 48.8260), ("lift", 56.2307), ("step", 56.1890),
                      ("release", 55.3906), ("follow_through", 52.2055)],
    "deflect_high": [("ready", 56.2844), ("contact", 54.5192),
                     ("control", 54.4526), ("send_on", 52.4786)],
    "hooks_jump_pull_in": [("gather", 50.2751), ("contact", 54.1299),
                           ("pull_in", 49.9148), ("release", 50.9044)],
    "chest_pass": [("ready", 48.8246), ("step", 48.8356), ("drive", 50.2703),
                   ("release", 50.7816), ("follow_through", 50.2727)],
}

# This rig: 42.7681 on all 18, range 0.0000. Ball to head, cm, measured.
BALL_TO_HEAD = {
    ("overhead_pass", "ready"): 27.090, ("overhead_pass", "lift"): 24.549,
    ("overhead_pass", "step"): 25.177, ("overhead_pass", "release"): 31.610,
    ("overhead_pass", "follow_through"): 202.001,
    ("deflect_high", "ready"): 189.302, ("deflect_high", "contact"): 35.398,
    ("deflect_high", "control"): 29.209, ("deflect_high", "send_on"): 178.550,
    ("hooks_jump_pull_in", "gather"): 186.656,
    ("hooks_jump_pull_in", "contact"): 37.608,
    ("hooks_jump_pull_in", "pull_in"): 26.892,
    ("hooks_jump_pull_in", "release"): 83.842,
    ("chest_pass", "ready"): 27.085, ("chest_pass", "step"): 27.432,
    ("chest_pass", "drive"): 34.392, ("chest_pass", "release"): 40.596,
    ("chest_pass", "follow_through"): 216.584,
}

RADIUS = 11.00
ARM_HERE, ARM_ENGINE = 48.547, 52.680
SCALE = ARM_HERE / ARM_ENGINE
THRESHOLD = 1.0
# Past this the ball has left the hands, so the anchor error is a fraction of
# a flight distance and no coach reads a cue from it.
IN_FLIGHT_CM = 100.0


def main():
    rest = [v for drill in ("overhead_pass", "chest_pass")
            for name, v in ENGINE[drill] if name == "ready"]
    reference = sum(rest) / len(rest)
    print("THE CALIBRATION POINT IS NOT ASSUMED, IT IS EVIDENCED.")
    print(f"  overhead_pass/ready {rest[0]:.4f} and chest_pass/ready "
          f"{rest[1]:.4f} agree to {abs(rest[0]-rest[1]):.4f} cm,")
    print("  from two independent drills. That is the engine's neutral girdle,")
    print("  and this rig's one fixed girdle is calibrated to it.")
    print("  The other two frame-0 phases do NOT agree with them "
          "(deflect ready 56.28, hooks gather 50.28)")
    print("  because those drills begin with the arms already up. The "
          "agreement of the two 48.82s is the signal.")
    print()
    print(f"{'drill / phase':<38}{'engine':>9}{'error':>9}{'scaled':>9}"
          f"{'of radius':>11}{'ball-head':>11}  verdict")
    fails = held = 0
    for drill, phases in ENGINE.items():
        for name, value in phases:
            error = value - reference
            scaled = error * SCALE
            reach = BALL_TO_HEAD[(drill, name)]
            flight = reach > IN_FLIGHT_CM
            bad = abs(error) > THRESHOLD
            if bad:
                fails += 1
                if not flight:
                    held += 1
            verdict = ("PASS" if not bad else
                       "fail (ball in flight)" if flight else "FAIL")
            print(f"{drill + '/' + name:<38}{value:>9.4f}{error:>9.4f}"
                  f"{scaled:>9.4f}{abs(error) / RADIUS * 100:>10.1f}%"
                  f"{reach:>11.2f}  {verdict}")
    total = sum(len(p) for p in ENGINE.values())
    print()
    print(f"{total - fails} of {total} phases pass the {THRESHOLD:.0f} cm rule. "
          f"{fails} fail, and {held} of those are held phases,")
    print("where the ball is in her hands and the error is what a coach looks "
          "at.")
    print()
    print(f"`scaled` divides the error by this rig's smaller body "
          f"({ARM_HERE} / {ARM_ENGINE} = {SCALE:.4f}).")
    print("Read the pair as a range. No verdict changes between the two "
          "columns.")
    print()
    print("UNMEASURED: the engine's column is VERTICAL ONLY. A fore-and-aft "
          "shift of the")
    print("midpoint would move the ball too and nothing here would see it. "
          "The numbers above")
    print("are a LOWER BOUND on the error, not the whole of it.")


if __name__ == "__main__":
    main()
