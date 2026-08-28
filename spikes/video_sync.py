"""Find the clap offset between the two cameras of a filmed set.

Both phones record the same drill from 90 degrees apart, started by hand, so
the two files begin at different moments. A clap at the top of the take is the
shared event that ties them together.

Two instruments, because one is not evidence
--------------------------------------------

This file runs the AUDIO one: cross-correlate the two soundtracks and read the
lag at the peak. It runs it twice, in two ways that fail differently:

- on the RAW waveform, which is sharp but assumes the two microphones agree
  about the shape of a transient;
- on the ENERGY ENVELOPE, which throws away the waveform and keeps only how
  loud things are, so two different microphones can still agree.

If those two disagree, the answer is not trustworthy and this says so rather
than picking one. The VISUAL instrument lives in `video_clap_frames.py` and is
the one that matters: audio and pixels fail in genuinely unrelated ways.

Sample rates differ between the cameras, 44100 against 48000, so everything is
resampled to one rate before anything is compared. Comparing at two rates would
be the same units-across-a-boundary fault this project keeps finding.

    pixi run python video_sync.py
    pixi run python video_sync.py --set 0.1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
SAMPLES = Path("F:/Repositories/braven-movement/.assets/video-samples/session-1.0")
OUTPUT = SPIKE_DIR / "poc-output" / "video"

# One rate for both cameras. 48000 is the higher of the two present, so the
# 44100 side is upsampled rather than the 48000 side thrown away.
WORK_RATE = 48000
# The envelope is a loudness reading, not a waveform, so it needs far less
# resolution. 1000 Hz gives a millisecond of precision, which is a thirtieth of
# a frame and finer than anything downstream can use.
ENVELOPE_RATE = 1000
# A clap is at the start of a take. Searching the whole clip invites a match on
# a bounce or a footfall, and the two cameras were started within seconds of
# each other by hand.
SEARCH_SECONDS = 12.0


@dataclass
class Offset:
    """How far the second file lags the first, in milliseconds.

    Positive means the event happens LATER in the second file, so the second
    file's timestamps must have this subtracted to land on the first's clock.
    """

    milliseconds: float
    peak: float
    peakToSidelobe: float
    method: str


def audio(path: Path, rate: int = WORK_RATE) -> np.ndarray:
    """Mono, one rate, float. ffmpeg does the resampling and the downmix."""
    done = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path),
            "-map", "0:a:0", "-ac", "1", "-ar", str(rate),
            "-f", "f32le", "-",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(done.stdout, dtype="<f4").astype(np.float64)


def envelope(wave: np.ndarray, rate: int = WORK_RATE) -> np.ndarray:
    """Loudness against time, at ENVELOPE_RATE.

    Root mean square over a short window. This is what survives two different
    microphones: they disagree about a transient's shape and agree about when
    it was loud.
    """
    step = max(1, rate // ENVELOPE_RATE)
    usable = (len(wave) // step) * step
    blocks = wave[:usable].reshape(-1, step)
    return np.sqrt((blocks * blocks).mean(axis=1))


def correlate(first: np.ndarray, second: np.ndarray, rate: int, method: str) -> Offset:
    """Lag of `second` behind `first`, by cross-correlation.

    Both signals are mean-removed and scaled to unit energy, so the peak is a
    correlation coefficient and comparable between methods rather than a number
    whose size depends on how loud the gym was.
    """
    window = int(SEARCH_SECONDS * rate)
    a = first[:window].astype(np.float64)
    b = second[:window].astype(np.float64)
    a = a - a.mean()
    b = b - b.mean()
    a = a / (np.linalg.norm(a) or 1.0)
    b = b / (np.linalg.norm(b) or 1.0)

    size = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    spectrum = np.fft.rfft(a, size) * np.conj(np.fft.rfft(b, size))
    joined = np.fft.irfft(spectrum, size)
    # Lags from -len(b)+1 to +len(a)-1, rearranged so index 0 is the most
    # negative lag.
    joined = np.concatenate((joined[-(len(b) - 1):], joined[: len(a)]))
    lags = np.arange(-(len(b) - 1), len(a))

    best = int(np.argmax(joined))
    peak = float(joined[best])
    # How far the peak stands above everything else. A true clap match towers;
    # a room-tone match does not. The exclusion window is a tenth of a second,
    # wide enough to skip the peak's own shoulders.
    guard = max(1, rate // 10)
    masked = joined.copy()
    low = max(0, best - guard)
    masked[low : best + guard] = -np.inf
    sidelobe = float(np.max(masked)) if np.isfinite(np.max(masked)) else 0.0
    ratio = peak / sidelobe if sidelobe > 1e-12 else float("inf")

    return Offset(
        milliseconds=float(lags[best]) * 1000.0 / rate,
        peak=peak,
        peakToSidelobe=ratio,
        method=method,
    )


def measure(name: str, front: Path, side: Path) -> dict:
    raw_front, raw_side = audio(front), audio(side)
    on_wave = correlate(raw_front, raw_side, WORK_RATE, "raw waveform")
    on_energy = correlate(
        envelope(raw_front), envelope(raw_side), ENVELOPE_RATE, "energy envelope"
    )
    gap = abs(on_wave.milliseconds - on_energy.milliseconds)
    return {
        "set": name,
        "front": front.name,
        "side": side.name,
        "measures": [asdict(on_wave), asdict(on_energy)],
        "disagreementMs": round(gap, 3),
        # One frame at 30 fps is 33.3 ms. Two methods landing inside a third of
        # that are looking at the same event.
        "methodsAgree": gap <= 11.0,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", dest="only", default=None)
    arguments = parser.parse_args(argv[1:])

    found = []
    for name in ("0.1", "0.2"):
        if arguments.only and arguments.only != name:
            continue
        front, side = SAMPLES / f"front {name}.mp4", SAMPLES / f"side {name}.mp4"
        if not front.exists() or not side.exists():
            print(f"set {name}: files missing, skipped")
            continue
        found.append(measure(name, front, side))

    for entry in found:
        print(f"\nset {entry['set']}   {entry['front']} against {entry['side']}")
        for measure_entry in entry["measures"]:
            print(
                f"  {measure_entry['method']:16s} "
                f"offset {measure_entry['milliseconds']:+9.2f} ms   "
                f"peak {measure_entry["peak"]:.4f}   "
                f"peak/sidelobe {measure_entry['peakToSidelobe']:6.2f}"
            )
        print(
            f"  the two methods differ by {entry['disagreementMs']:.2f} ms  ->  "
            + ("they agree" if entry["methodsAgree"] else "THEY DISAGREE")
        )

    print(
        "\nPositive means the event happens LATER in the side file, so a side\n"
        "timestamp minus this offset lands on the front camera's clock.\n"
        "This is ONE instrument. `video_clap_frames.py` is the other, and a\n"
        "number that only audio believes is not yet a measurement."
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    where = OUTPUT / "clap-offsets.json"
    where.write_text(json.dumps(found, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
