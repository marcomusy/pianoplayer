import logging
import math
from array import array

logger = logging.getLogger(__name__)

try:
    import simpleaudio

    has_simpleaudio = True
except ImportError:
    logger.info("simpleaudio not available; sound playback disabled")
    has_simpleaudio = False


def _pitch_to_frequency(value):
    if isinstance(value, (int, float)):
        midi = float(value)
        return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))
    return None


def soundof(notes, duration=1, volume=0.75, fading=750, wait=True):
    """Play a group of notes (chord) for the prescribed duration."""
    if not has_simpleaudio:
        return None

    sample_rate = 44100
    timepoints = max(1, int(duration * sample_rate))
    fade_n = min(fading, timepoints // 2)

    freqs = []
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

        amp = int(max(-1.0, min(1.0, val * float(volume))) * 32767)
        samples.append(amp)

    play_obj = simpleaudio.play_buffer(samples.tobytes(), 1, 2, sample_rate)
    if wait:
        play_obj.wait_done()
    return play_obj


def playSound(n, speedfactor=1.0, wait=True):
    """Play a single note or chord-like item."""
    if not has_simpleaudio:
        return
    soundof([n], duration=n.duration / speedfactor, wait=wait)
