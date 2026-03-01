"""Minimal sine-wave playback helpers used by the 3D keyboard view."""

from __future__ import annotations

import logging
import math
import os
import tempfile
import wave
from array import array
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

try:
    import pygame
except ImportError:
    pygame = None

try:
    import winsound as _winsound
except ImportError:
    _winsound = None

_warned_missing_backend = False
_temp_audio_dir = Path(tempfile.gettempdir()) / "pianoplayer_audio"
_temp_audio_dir.mkdir(parents=True, exist_ok=True)


def _warn_missing_backend_once() -> None:
    global _warned_missing_backend
    if _warned_missing_backend:
        return
    logger.warning("Audio playback unavailable (install pygame).")
    _warned_missing_backend = True


def _init_pygame_mixer() -> bool:
    if pygame is None:
        return False
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.mixer.init()
        return True
    except Exception as exc:
        logger.debug("pygame mixer init failed: %s", exc)
        return False


def has_audio_backend() -> bool:
    """Return True when at least one audio backend is available."""
    return _init_pygame_mixer() or (_winsound is not None)


def _pitch_to_frequency(value: Any) -> float | None:
    """Convert MIDI pitch to frequency in Hz."""
    if isinstance(value, (int, float)):
        midi = float(value)
        return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))
    return None


def _render_samples(
    notes: Iterable[Any],
    duration: float,
    volume: float,
    fading: float,
) -> tuple[array, int] | None:
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

    return samples, sample_rate


def _play_with_pygame(samples: array, sample_rate: int, wait: bool):
    """Play raw samples using pygame mixer."""
    if not _init_pygame_mixer():
        return None

    pid = os.getpid()
    wav_path = _temp_audio_dir / f"pp_{pid}_{id(samples)}.wav"
    try:
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(samples.tobytes())

        snd = pygame.mixer.Sound(str(wav_path))
        ch = snd.play()
        if wait and ch is not None:
            while ch.get_busy():
                pygame.time.delay(1)
        return ch
    except Exception as exc:
        logger.debug("pygame playback failed: %s", exc)
        return None
    finally:
        try:
            wav_path.unlink(missing_ok=True)
        except Exception:
            pass


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
    rendered = _render_samples(notes, duration=duration, volume=volume, fading=fading)
    if rendered is None:
        return None
    samples, sample_rate = rendered

    ch = _play_with_pygame(samples, sample_rate, wait)
    if ch is not None:
        return ch

    # Last-resort fallback: Windows beep for single-note usage.
    if _winsound is not None:
        freqs = []
        for n in notes:
            freq = _pitch_to_frequency(getattr(n, "pitch", n))
            if freq is not None:
                freqs.append(freq)
        if freqs:
            try:
                hz = int(max(37, min(32767, round(freqs[0]))))
                msec = max(20, int(float(duration) * 1000))
                if wait:
                    _winsound.Beep(hz, msec)
                else:
                    _winsound.MessageBeep()
                return True
            except Exception:
                pass

    _warn_missing_backend_once()
    return None


def play_sound(n: Any, speedfactor: float = 1.0, wait: bool = True):
    """Play a single note or chord-like item."""
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
