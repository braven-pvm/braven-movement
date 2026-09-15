"""The sweep `docs/KNOWN_ISSUES.md` asked for: can the landing's cue fail?

    "whether those three checkpoints can fail under any lever is a sweep
     nobody has run"

`netball_double_foot_landing` grades `footHeightGapCm` at three phases, with
bands 0-14, 0-6 and 0-6. The measure is `abs(left_up - right_up)`, a DIFFERENCE
between the two feet. `leftFootHeightCm` and `rightFootHeightCm` are measured on
the same line of `possession_solve.py` and neither is graded.

This answers the question in both directions, because "I could not make it fail"
and "it cannot fail" are different sentences.

    can it fail      YES. Each checkpoint fails when an asymmetry is authored
                     at its own graded phase, and the solve carries the
                     authored size through faithfully.
    what can it not  THE FLIGHT. Take the drill's flight away entirely and all
    see              three still read `within`.

**NOT A SWEEP ALONG ONE AXIS, DELIBERATELY, DESPITE THE NAME THE ROW GAVE IT.**
This repository has measured that the lower body is discontinuous in its
inputs: equal increments of a planted asymmetry gave 4.44, 3.49, 5.85, 2.24,
7.05 and 1.80 cm, so a sweep characterises nothing and a single crossing would
be a basin change rather than a threshold. Built cases ask an answerable
question instead: with a LARGE asymmetry authored at a graded phase, does the
measurement follow it past the band, and with the flight removed, does anything
notice.

THE LEVER IS THE MOTION FILE'S AUTHORED FOOT HEIGHT, `footLeft.up` and
`footRight.up`, in arm lengths from the ground. **At all three graded phases the
two feet are authored IDENTICAL** -- flight 0.18807 and 0.18807, land 0.0 and
0.0, absorb 0.0 and 0.0. The drill's only authored asymmetry is at `take_off`,
which is not graded.

SCALE. At flight, `up` 0.18807 measures 15.80 cm, so one arm length is about
84 cm: a 14 cm gap needs about 0.167 and a 6 cm gap about 0.071.

**NOTHING UNDER `spikes/movements/` IS COMMITTED BY THIS SCRIPT.** It is gate-4
territory. The motion file is edited in place, solved, and restored from the
bytes read before the first edit. The restore is confirmed by sha256 AND by
`git status`, and it runs in a `finally`, so an exception still puts the file
back.

    pixi run --frozen python -B ../scripts/landing_cue_sweep.py <repo>

Measured 2026-09-15 on movement main `dc50dfc`, after the feet fix that places
her feet from the job, so the flight below is the one the picture now draws.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

MOVEMENT = "netball_double_foot_landing"
BANDS = {"flight": 14.0, "land": 6.0, "absorb": 6.0}


def main(argv: list[str]) -> int:
    repo = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / "spikes"))
    motion = repo / "spikes" / "movements" / f"{MOVEMENT}.motion.json"

    from movement_definition import load as load_definition
    from movement_engine import definition_path, load_character
    from possession_solve import solve_movement

    original = motion.read_bytes()
    before = hashlib.sha256(original).hexdigest()
    base = json.loads(original.decode("utf-8"))
    character = load_character()
    definition = load_definition(definition_path(MOVEMENT))

    def read() -> tuple[dict, float]:
        rows = solve_movement(character, MOVEMENT)["measurements"]
        last = len(rows) - 1
        peak = max(max(r.get("leftFootHeightCm", 0.0),
                       r.get("rightFootHeightCm", 0.0)) for r in rows)
        out = {}
        for phase in definition.phases:
            if phase.name in BANDS:
                out[phase.name] = rows[round(phase.at_phase * last)]
        return out, peak

    def show(label: str, data: dict) -> bool:
        motion.write_text(json.dumps(data, indent=2), encoding="utf-8")
        graded, peak = read()
        print(f"=== {label} ===")
        print(f"    highest foot anywhere: {peak:.2f} cm")
        every = True
        for name, row in graded.items():
            gap, ceiling = row["footHeightGapCm"], BANDS[name]
            ok = gap <= ceiling
            every = every and ok
            print(f"    {name:9s} gap {gap:6.2f}  feet "
                  f"{row['leftFootHeightCm']:6.2f} /{row['rightFootHeightCm']:6.2f}"
                  f"   band 0-{ceiling:.0f}   {'within' if ok else '*** FAILS ***'}")
        print(f"    -> all three within: {every}\n")
        return every

    try:
        show("control: the drill as authored", copy.deepcopy(base))

        print("CAN THEY FAIL? One asymmetry, authored at each graded phase.\n")
        for name, lift in (("flight", 0.25), ("land", 0.15), ("absorb", 0.15)):
            data = copy.deepcopy(base)
            for key in data["keys"]:
                if key["name"] == name:
                    key["footRight"]["up"] = round(key["footRight"]["up"] + lift, 5)
            show(f"right foot +{lift} arm lengths at {name}", data)

        print("WHAT CAN THEY NOT SEE? Both feet moved TOGETHER, so the "
              "difference never moves.\n")
        for label, scale in (("flight halved", 0.5),
                             ("NO FLIGHT AT ALL, both feet flat", 0.0)):
            data = copy.deepcopy(base)
            for key in data["keys"]:
                for side in ("footLeft", "footRight"):
                    key[side]["up"] = round(key[side]["up"] * scale, 5)
            show(label, data)
    finally:
        motion.write_bytes(original)
        after = hashlib.sha256(motion.read_bytes()).hexdigest()
        print("motion file restored:", "EXACT" if after == before else "*** FAILED ***")
        status = subprocess.run(
            ["git", "status", "--porcelain", "spikes/movements"],
            cwd=repo, capture_output=True, text=True)
        print("git status spikes/movements:", status.stdout.strip() or "clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
