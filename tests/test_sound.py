import pytest


def test_soundof_smoke() -> None:
    pytest.importorskip("music21")

    from music21.note import Note

    from pianoplayer.wavegenerator import soundof

    soundof([Note("C5"), "E-5", Note("G5")], duration=1)
    soundof([Note("A4")], duration=1)
