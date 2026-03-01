from types import SimpleNamespace

import pianoplayer.wavegenerator as wg


def test_soundof_smoke() -> None:
    calls = []

    def _fake_play(samples, sample_rate, wait):
        calls.append((len(samples), sample_rate, wait))
        return object()

    old = wg._play_with_pygame
    try:
        wg._play_with_pygame = _fake_play
        # MIDI pitches for C5, E5, G5 and A4
        obj = wg.soundof([72, 76, 79], duration=0.02, wait=True)
        assert obj is not None
        assert calls
        assert calls[0][1] == 44100
        assert calls[0][2] is True

        # Single note path
        note = SimpleNamespace(pitch=69, duration=0.1)
        assert wg.play_sound(note, speedfactor=2.0, wait=False) is not None
    finally:
        wg._play_with_pygame = old


def test_play_sound_invalid_speedfactor() -> None:
    note = SimpleNamespace(pitch=69, duration=1.0)
    assert wg.play_sound(note, speedfactor=0) is None
