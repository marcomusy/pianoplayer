from pianoplayer.wavegenerator import soundof


def test_soundof_smoke() -> None:
    # MIDI pitches for C5, E5, G5 and A4
    soundof([72, 76, 79], duration=0.1)
    soundof([69], duration=0.1)
