from pianoplayer.wavegenerator import soundof
from music21.note import Note

soundof([Note("C5"), "E-5", Note("G5")], duration=1)
soundof([Note("A4")], duration=1)

## OR (needs pygame)
# from music21.midi.realtime import StreamPlayer
# from music21.stream import Stream
# s = Stream()
# s.append(Note("C5"))
# s.append(Note("E5"))
# s.append(Note("G5"))
# sp = StreamPlayer(s)
# sp.play()

