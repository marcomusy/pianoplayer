from types import SimpleNamespace

import pianoplayer.wavegenerator as wg


def test_soundof_smoke() -> None:
    class _FakePlayObj:
        def __init__(self) -> None:
            self.wait_done_called = False

        def wait_done(self) -> None:
            self.wait_done_called = True

    class _FakeSimpleAudio:
        def __init__(self) -> None:
            self.calls = []
            self.last_obj = _FakePlayObj()

        def play_buffer(self, data, channels, bytes_per_sample, sample_rate):
            self.calls.append((data, channels, bytes_per_sample, sample_rate))
            self.last_obj = _FakePlayObj()
            return self.last_obj

    fake = _FakeSimpleAudio()
    old = wg._simpleaudio
    old_flag = wg.has_simpleaudio
    try:
        wg._simpleaudio = fake
        wg.has_simpleaudio = True
        # MIDI pitches for C5, E5, G5 and A4
        obj = wg.soundof([72, 76, 79], duration=0.02, wait=True)
        assert obj is not None
        assert fake.calls
        assert fake.calls[0][1:] == (1, 2, 44100)
        assert fake.last_obj.wait_done_called is True

        # Single note path
        note = SimpleNamespace(pitch=69, duration=0.1)
        assert wg.play_sound(note, speedfactor=2.0, wait=False) is not None
    finally:
        wg._simpleaudio = old
        wg.has_simpleaudio = old_flag


def test_play_sound_invalid_speedfactor() -> None:
    note = SimpleNamespace(pitch=69, duration=1.0)
    assert wg.play_sound(note, speedfactor=0) is None
