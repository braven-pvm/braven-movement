"""Find the clap offset between the two cameras of a filmed set.

THIS INSTRUMENT FAILED ON SESSION 1.0 AND IS KEPT ANYWAY. There is no clap in
that material, and all four methods below returned peak-to-sidelobe between
1.01 and 1.35 — no peak, so no measurement. Its numbers are cited in
`docs/VIDEO_CAPTURE_FINDINGS.md` as the evidence for the clap instruction, and
a report citing a measurement nobody can rerun is worse than a failed script in
the tree. Nothing downstream reads its output.

Both phones record the same drill from 90 degrees apart, started by hand, so
the two files begin at different moments. A clap at the top of the take is the
shared event that ties them together.

Two instruments, because one is not evidence
--------------------------------------------

This file runs the AUDIO one: cross-correlate the two soundtracks and read the
lag at the peak. It runs it four times, in ways that fail differently:

- on the RAW waveform, which is sharp but assumes the two microphones agree
  about the shape of a transient;
- on the ENERGY ENVELOPE, which throws away the waveform and keeps only how
  loud things are, so two different microphones can still agree.

If those two disagree, the answer is not trustworthy and this says so rather
than picking one. The visual instrument is `video_motion_sync.py`, which reads
pixels instead of sound and fails differently — and on this material also
fails, for the reason recorded there.

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
# Spectral flux resolution. 256 samples at 48 kHz is 5.33 ms a step, fine
# enough that the peak is not quantised by the analysis.
FLUX_HOP = 256
FLUX_WINDOW = 1024


@dataclass
class Offset:
    """The lag the cross-correlation puts between the two files, in ms.

    THE SIGN, WORKED, BECAUSE PROSE ABOUT DIRECTION HAS FAILED TWICE HERE.

    Take the first catch of set 0.1: it is at 9.25 s in the front file and
    8.25 s in the side file. `correlate(front, side)` returns **+1000 ms**,
    verified against synthetic impulses at exactly those times.

        side 8.25 + 1.000 = 9.25 front      correct
        side 8.25 - 1.000 = 7.25            wrong by twice the offset

    So ADD this number to a timestamp in the SECOND file to reach the first
    file's clock. It is therefore identical to the schema's
    `offsetSecondsToReference` for the second view, in seconds rather than
    milliseconds, with the first file as the reference.

    An earlier version of this docstring said the opposite — subtract, and
    positive means later in the second file. Both halves were wrong, and
    applying the stated rule to the computed number lands 2.0 s away inside
    real footage, where nothing throws.
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


def spectral_flux(wave: np.ndarray, rate: int = WORK_RATE) -> tuple[np.ndarray, float]:
    """How much the spectrum BRIGHTENS frame to frame, and that series' rate.

    Sharper than loudness for a transient and largely immune to gym reverb,
    which raises the level without re-brightening the spectrum. The third
    method, committed because the report cites its numbers.
    """
    window = np.hanning(FLUX_WINDOW)
    count = 1 + (len(wave) - FLUX_WINDOW) // FLUX_HOP
    frames = np.lib.stride_tricks.sliding_window_view(wave, FLUX_WINDOW)[::FLUX_HOP][:count]
    spectrum = np.abs(np.fft.rfft(frames * window, axis=1))
    return np.maximum(np.diff(spectrum, axis=0), 0.0).sum(axis=1), rate / FLUX_HOP


def correlate(
    first: np.ndarray, second: np.ndarray, rate: float, method: str,
    seconds: float | None = SEARCH_SECONDS,
) -> Offset:
    """Lag of `second` behind `first`, by cross-correlation.

    Both signals are mean-removed and scaled to unit energy, so the peak is a
    correlation coefficient and comparable between methods rather than a number
    whose size depends on how loud the gym was.
    """
    window = len(first) if seconds is None else int(seconds * rate)
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
    # int() because a derived rate can be fractional: the spectral-flux series
    # runs at 48000/256 = 187.5 Hz, and a float here indexes nothing.
    guard = max(1, int(rate // 10))
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
    flux_front, flux_rate = spectral_flux(raw_front)
    flux_side, _ = spectral_flux(raw_side)
    on_flux = correlate(flux_front, flux_side, flux_rate, "spectral flux, 12 s")
    # The whole clip as well, because a repetitive drill correlates differently
    # over one cycle and over twenty, and the report cites both.
    on_flux_all = correlate(
        flux_front, flux_side, flux_rate, "spectral flux, whole clip",
        seconds=None,
    )
    gap = abs(on_wave.milliseconds - on_energy.milliseconds)
    return {
        "set": name,
        "front": front.name,
        "side": side.name,
        "measures": [asdict(on_wave), asdict(on_energy), asdict(on_flux),
                     asdict(on_flux_all)],
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
            f"  waveform against envelope: {entry['disagreementMs']:.2f} ms "
            f"apart  ->  "
            + ("they agree" if entry["methodsAgree"] else "THEY DISAGREE")
        )

    print(
        "\nADD this offset to a side-file timestamp to reach the front file's\n"
        "clock. Worked on set 0.1: the first catch is at 8.25 s in the side\n"
        "file and 9.25 in the front, and 8.25 + 1.000 = 9.25. It is the\n"
        "schema's offsetSecondsToReference for the side view, in milliseconds.\n"
        "\nEVERY ROW ABOVE FAILED on this material: peak-to-sidelobe near 1.0\n"
        "means the best match is no better than the next-best, so there is no\n"
        "peak and the milliseconds beside it are not a measurement."
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    where = OUTPUT / "clap-offsets.json"
    where.write_text(json.dumps(found, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
