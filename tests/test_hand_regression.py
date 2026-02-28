from pianoplayer.hand import Hand
from pianoplayer.models import INote
from pianoplayer.musicxml_io import parse_musicxml
from pianoplayer.scorereader import reader


def test_hand_generates_fingering_for_sample_score() -> None:
    score = parse_musicxml("scores/test_scales.xml")
    noteseq = reader(score, beam=0)

    hand = Hand(side="right", noteseq=noteseq, size="M")
    hand.verbose = False
    hand.generate(start_measure=1, nmeasures=2)

    assert any(getattr(n, "fingering", 0) for n in hand.noteseq[:10])


def test_hand_respects_existing_fingering_anchor() -> None:
    notes = [
        INote(
            name="C",
            pitch=60 + i,
            octave=4,
            x=float(i),
            time=float(i),
            duration=1.0,
            measure=1,
            isBlack=False,
            fingering=0,
        )
        for i in range(12)
    ]
    notes[1].fingering = 5

    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False

    starts: list[int] = []

    def fake_optimize_seq(nseq, istart):
        starts.append(istart)
        return [1, 2, 3, 4, 5, 1, 2, 3, 4], 0.0

    hand.optimize_seq = fake_optimize_seq  # type: ignore[method-assign]
    hand.generate(start_measure=1, nmeasures=2)

    assert hand.noteseq[1].fingering == 5
    assert 5 in starts
    idx = starts.index(5)
    assert idx + 1 < len(starts)
    assert starts[idx + 1] == 2
