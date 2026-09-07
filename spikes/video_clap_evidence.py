"""The two measurements behind the sync-clap identification, as runnable code.

WHY THIS FILE EXISTS. The identification of session 1.0's repetitions 0 and 8 as
Erin's sync claps was published with numbers that lived only in one session's
scratchpad: spike heights, counts, a gap. An independent reviewer could not
re-measure any of them, reconstructed the detector by hand, and got different
figures — 25.4 against 26.5, counts varying from zero to twenty-seven depending
on the rule chosen. A NUMBER NOBODY ELSE CAN REGENERATE IS NOT A MEASUREMENT,
whatever it happens to be. So the detector is here, its parameters are named
constants with reasons, and every figure quoted in the documents comes from
`python video_clap_evidence.py`.

WHAT IT MEASURES. Two independent things that happen to coincide, which is the
whole argument:

1. THE HANDS. Wrist-to-wrist separation in shoulder widths, per frame, from the
   front keypoint file. A clap brings them together.
2. THE SOUND. Energy above 4 kHz in 5 ms blocks, against a trailing local floor.
   A clap is broadband and quick; a voice is neither.

Neither alone identifies a clap. Her hands come together often — she talks with
them — and the recording has many loud moments. What is rare is the two at once,
and this file reports both so that the coincidence can be counted rather than
asserted.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
OUTPUT = SPIKE_DIR / "poc-output" / "video"
SAMPLES = Path("F:/Repositories/braven-movement/.assets/video-samples/session-1.0")

# --- the sound -------------------------------------------------------------

# A clap is BROADBAND. Speech carries little energy above 4 kHz and a hand clap
# carries a lot, so the band is what separates the two; an amplitude envelope
# finds a talking woman instead.
BAND_HERTZ = 4000.0

# 5 ms blocks. A clap's attack is under 10 ms, so the block has to be shorter
# than the thing being measured or the attack is averaged into its own floor.
BLOCK_SECONDS = 0.005

# The floor is the MEDIAN of the preceding half second, stopping 10 ms short of
# the block being judged so the attack cannot raise its own floor. Median rather
# than mean because a second loud event nearby should not hide this one.
FLOOR_SECONDS = 0.5
FLOOR_GUARD_BLOCKS = 2

# An ATTACK, not merely a loud moment: the block 10 ms earlier must be under
# half its height. Sustained speech fails this and a clap passes it.
ATTACK_RATIO = 0.5

# Reported spikes are separated by at least this much, keeping the loudest of a
# cluster rather than every block of one event.
SEPARATION_SECONDS = 0.15

# The bar. CHOSEN, and the reason it is not tighter is that the side recording's
# strongest event reaches only x24 while the front's reaches x44: a bar set from
# the front alone would refuse everything in the side and prove nothing.
SPIKE_RISE = 8.0

# --- the hands -------------------------------------------------------------

# Below this, in shoulder widths, the wrists count as together. CHOSEN: her
# whole-clip median is about 0.94, so half of that is comfortably closed hands
# without requiring the landmarks to coincide.
TOGETHER_WIDTHS = 0.5

# A landmark under this visibility is not read. The wrists get the looser bar
# because the far hand is often partly hidden even when it is plainly there.
WRIST_VISIBILITY = 0.4
BODY_VISIBILITY = 0.4


def audio_path(view: str, set_id: str) -> Path:
    """The mono 48 kHz track, extracted once and cached beside the outputs.

    BOTH VIEWS ARE RESAMPLED TO ONE RATE. The front records at 44.1 kHz and the
    side at 48 kHz; correlating or comparing them on sample indices would put
    their time axes 8.8 per cent apart. ffmpeg resamples, so the clocks agree.
    """
    out = OUTPUT / f"audio-{view}-{set_id}.wav"
    if out.exists():
        return out
    source = SAMPLES / f"{view} {set_id}.mp4"
    if not source.exists():
        raise FileNotFoundError(source)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(source),
         "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(out)],
        check=True)
    return out


def read_wave(path: Path) -> tuple[np.ndarray, int]:
    import wave
    with wave.open(str(path)) as handle:
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(float) / 32768.0, rate


def high_band_energy(samples: np.ndarray, rate: int) -> tuple[np.ndarray, np.ndarray]:
    block = int(BLOCK_SECONDS * rate)
    count = len(samples) // block
    freqs = np.fft.rfftfreq(block, 1.0 / rate)
    keep = freqs >= BAND_HERTZ
    window = np.hanning(block)
    energy = np.array([
        np.abs(np.fft.rfft(samples[i * block:(i + 1) * block] * window))[keep].sum()
        for i in range(count)])
    return np.arange(count) * BLOCK_SECONDS, energy


def spikes(times: np.ndarray, energy: np.ndarray, rise: float = SPIKE_RISE) -> list[dict]:
    """Broadband attacks, loudest-first within each cluster."""
    back = int(FLOOR_SECONDS / BLOCK_SECONDS)
    found: list[dict] = []
    for i in range(back, len(energy) - 1):
        floor = float(np.median(energy[i - back:i - FLOOR_GUARD_BLOCKS]))
        if floor <= 0:
            continue
        ratio = float(energy[i] / floor)
        if ratio < rise:
            continue
        if energy[i] < energy[i - 1] or energy[i] < energy[i + 1]:
            continue
        if energy[i - FLOOR_GUARD_BLOCKS] > ATTACK_RATIO * energy[i]:
            continue
        if found and times[i] - found[-1]["seconds"] < SEPARATION_SECONDS:
            if ratio > found[-1]["rise"]:
                found[-1] = {"seconds": float(times[i]), "rise": ratio}
            continue
        found.append({"seconds": float(times[i]), "rise": ratio})
    return found


def wrist_separation(frames: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    times, widths = [], []
    for frame in frames:
        points = {p["name"]: p for p in (frame.get("landmarks") or [])}

        def seen(name: str, floor: float) -> bool:
            return name in points and points[name].get("visibility", 0) >= floor

        if not all(seen(n, WRIST_VISIBILITY) for n in ("left_wrist", "right_wrist")):
            continue
        if not all(seen(n, BODY_VISIBILITY) for n in ("left_shoulder", "right_shoulder")):
            continue
        shoulder = max(1.0, float(np.hypot(
            points["left_shoulder"]["xPixel"] - points["right_shoulder"]["xPixel"],
            points["left_shoulder"]["yPixel"] - points["right_shoulder"]["yPixel"])))
        apart = float(np.hypot(
            points["left_wrist"]["xPixel"] - points["right_wrist"]["xPixel"],
            points["left_wrist"]["yPixel"] - points["right_wrist"]["yPixel"]))
        times.append(frame["ptsSeconds"])
        widths.append(apart / shoulder)
    return np.asarray(times), np.asarray(widths)


def together(times: np.ndarray, widths: np.ndarray) -> dict:
    """Three counts, because they are three different numbers.

    A published sentence once said "only seven frames in 785 fall under 0.5".
    FIFTY-FIVE FRAMES DO. Seven was a count of local minima after a separation
    rule, reported as a count of frames, and the deepest frame in the clip was
    not among them. The three counts are kept apart here so that no summary can
    quietly swap one for another again.
    """
    under = widths < TOGETHER_WIDTHS
    stretches: list[dict] = []
    start = None
    for i, low in enumerate(under):
        if low and start is None:
            start = i
        elif not low and start is not None:
            stretches.append({"fromSeconds": float(times[start]),
                              "toSeconds": float(times[i - 1]),
                              "frames": i - start})
            start = None
    if start is not None:
        stretches.append({"fromSeconds": float(times[start]),
                          "toSeconds": float(times[-1]),
                          "frames": len(under) - start})
    minima = []
    for i in range(1, len(widths) - 1):
        if under[i] and widths[i] <= widths[i - 1] and widths[i] <= widths[i + 1]:
            minima.append({"seconds": float(times[i]), "widths": float(widths[i])})
    return {
        "framesRead": int(len(widths)),
        "medianWidths": float(np.median(widths)),
        "framesUnder": int(under.sum()),
        "stretches": stretches,
        "minima": minima,
        "deepest": {"seconds": float(times[int(widths.argmin())]),
                    "widths": float(widths.min())},
    }


def coincidences(minima: list[dict], sound: list[dict], window: float = 0.10) -> list[dict]:
    """The whole argument: a hands-together minimum WITH a broadband attack.

    Neither reading identifies a clap by itself. She talks with her hands and
    the room is noisy. The claim is about the two coinciding, so the coincidence
    is what gets counted.
    """
    out = []
    for low in minima:
        near = [s for s in sound if abs(s["seconds"] - low["seconds"]) <= window]
        out.append({
            "handsSeconds": low["seconds"],
            "widths": low["widths"],
            "soundSeconds": near[0]["seconds"] if near else None,
            "rise": max((s["rise"] for s in near), default=None),
        })
    return out


def main(argv: list[str]) -> int:
    set_id = argv[1] if len(argv) > 1 else "0.1"
    keypoints = OUTPUT / f"keypoints-front-{set_id}.json"
    if not keypoints.exists():
        raise SystemExit(f"{keypoints} is missing; run video_keypoints.py first")
    frames = json.loads(keypoints.read_text(encoding="utf-8"))["frames"]
    hands = together(*wrist_separation(frames))

    sound = {}
    for view in ("front", "side"):
        samples, rate = read_wave(audio_path(view, set_id))
        sound[view] = spikes(*high_band_energy(samples, rate))

    report = {
        "set": set_id,
        "parameters": {
            "bandHertz": BAND_HERTZ, "blockSeconds": BLOCK_SECONDS,
            "floorSeconds": FLOOR_SECONDS, "attackRatio": ATTACK_RATIO,
            "separationSeconds": SEPARATION_SECONDS, "spikeRise": SPIKE_RISE,
            "togetherWidths": TOGETHER_WIDTHS,
            "wristVisibility": WRIST_VISIBILITY, "bodyVisibility": BODY_VISIBILITY,
        },
        "hands": hands,
        "sound": sound,
        "coincidences": coincidences(hands["minima"], sound["front"]),
    }
    where = OUTPUT / f"clap-evidence-{set_id}.json"
    where.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")

    print(f"session {set_id}\n")
    print(f"  HANDS, front view: {hands['framesRead']} frames read, "
          f"median separation {hands['medianWidths']:.2f} shoulder widths")
    print(f"    under {TOGETHER_WIDTHS}: {hands['framesUnder']} FRAMES in "
          f"{len(hands['stretches'])} stretches, {len(hands['minima'])} local minima")
    print(f"    deepest {hands['deepest']['widths']:.3f} at "
          f"{hands['deepest']['seconds']:.3f} s")
    for s in hands["stretches"]:
        print(f"      {s['fromSeconds']:7.3f}-{s['toSeconds']:7.3f} s  {s['frames']} frames")
    for view in ("front", "side"):
        print(f"\n  SOUND, {view}: {len(sound[view])} spikes at x{SPIKE_RISE:.0f}+")
        for s in sound[view]:
            print(f"      {s['seconds']:7.3f} s   x{s['rise']:6.1f}")
    print("\n  COINCIDENCE — a hands-together minimum with a broadband attack "
          "within 100 ms:")
    for c in report["coincidences"]:
        mark = f"x{c['rise']:.1f} at {c['soundSeconds']:.3f}" if c["rise"] else "nothing"
        print(f"      hands {c['handsSeconds']:7.3f} ({c['widths']:.3f})  ->  {mark}")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
