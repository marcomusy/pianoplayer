from pianoplayer.hand import Hand
from pianoplayer.musicxml_io import parse_musicxml
from pianoplayer.scorereader import reader


def test_hand_generates_fingering_for_sample_score() -> None:
    score = parse_musicxml("scores/test_scales.xml")
    noteseq = reader(score, beam=0)

    hand = Hand(side="right", noteseq=noteseq, size="M")
    hand.verbose = False
    hand.generate(start_measure=1, nmeasures=2)

    assert any(getattr(n, "fingering", 0) for n in hand.noteseq[:10])
