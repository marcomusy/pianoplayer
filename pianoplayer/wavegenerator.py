"""Minimal sine-wave playback helpers used by the 3D keyboard view."""

from __future__ import annotations

import logging
import math
from array import array
from typing import Any, Iterable

logger = logging.getLogger(__name__)

try:
    import simpleaudio as _simpleaudio
except ImportError:
    _simpleaudio = None

has_simpleaudio = _simpleaudio is not None
_warned_missing_backend = False


def _warn_missing_backend_once() -> None:
    global _warned_missing_backend
    if _warned_missing_backend:
        return
    logger.debug("simpleaudio not available; sound playback disabled")
    _warned_missing_backend = True


def _pitch_to_frequency(value: Any) -> float | None:
    """Convert MIDI pitch to frequency in Hz."""
    if isinstance(value, (int, float)):
        midi = float(value)
        return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))
    return None


def soundof(
    notes: Iterable[Any],
    duration: float = 1.0,
    volume: float = 0.75,
    fading: float = 17.0,
    wait: bool = True,
):
    """Play a group of notes (chord) for the prescribed duration.

    Parameters
    ----------
    fading:
        Fade-in/out length in milliseconds.
    """
    if _simpleaudio is None:
        _warn_missing_backend_once()
        return None

    try:
        duration_s = float(duration)
    except (TypeError, ValueError):
        logger.warning("Invalid duration %r; skipping sound.", duration)
        return None
    if duration_s <= 0:
        return None

    try:
        volume_f = max(0.0, min(1.0, float(volume)))
    except (TypeError, ValueError):
        logger.warning("Invalid volume %r; using 0.75.", volume)
        volume_f = 0.75

    try:
        fading_ms = max(0.0, float(fading))
    except (TypeError, ValueError):
        fading_ms = 17.0

    sample_rate = 44100
    timepoints = int(duration_s * sample_rate)
    if timepoints <= 0:
        return None
    fading_n = int(sample_rate * (fading_ms / 1000.0))
    fade_n = min(fading_n, timepoints // 2)

    freqs: list[float] = []
    for n in notes:
        freq = None
        if hasattr(n, "pitch"):
            freq = _pitch_to_frequency(getattr(n, "pitch"))
        if freq is None:
            freq = _pitch_to_frequency(n)
        if freq is not None:
            freqs.append(freq)

    if not freqs:
        return None

    samples = array("h")
    for i in range(timepoints):
        t = i / sample_rate
        val = 0.0
        for freq in freqs:
            val += math.sin(freq * 2.0 * math.pi * t)
        val /= len(freqs)

        if fade_n > 0:
            if i < fade_n:
                val *= i / fade_n
            elif i >= (timepoints - fade_n):
                val *= (timepoints - i - 1) / fade_n

        amp = int(max(-1.0, min(1.0, val * volume_f)) * 32767)
        samples.append(amp)

    play_obj = _simpleaudio.play_buffer(samples.tobytes(), 1, 2, sample_rate)
    if wait:
        play_obj.wait_done()
    return play_obj


def play_sound(n: Any, speedfactor: float = 1.0, wait: bool = True):
    """Play a single note or chord-like item."""
    if _simpleaudio is None:
        _warn_missing_backend_once()
        return None

    try:
        speed = float(speedfactor)
    except (TypeError, ValueError):
        logger.warning("Invalid speedfactor %r; skipping sound.", speedfactor)
        return None
    if speed <= 0:
        logger.warning("Invalid speedfactor %r; expected > 0.", speedfactor)
        return None

    duration = getattr(n, "duration", None)
    if duration is None:
        logger.warning("Note object has no duration; skipping sound.")
        return None
    return soundof([n], duration=float(duration) / speed, wait=wait)


def playSound(n: Any, speedfactor: float = 1.0, wait: bool = True):
    """Backward-compatible wrapper for ``play_sound``."""
    return play_sound(n, speedfactor=speedfactor, wait=wait)
