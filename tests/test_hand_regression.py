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


def _mk_note(idx: int, measure: int, fingering: int = 0) -> INote:
    return INote(
        name="C",
        pitch=60 + idx,
        octave=4,
        x=float(idx),
        time=float(idx),
        duration=1.0,
        measure=measure,
        isBlack=False,
        fingering=fingering,
    )


def test_generate_respects_exact_measure_count() -> None:
    notes = [_mk_note(i, measure=i + 1) for i in range(8)]
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.generate(start_measure=2, nmeasures=2)

    touched = [n.measure for n in hand.noteseq if n.fingering]
    assert touched == [2, 3]


def test_tail_reuse_keeps_fingerseq_aligned_with_applied_finger() -> None:
    notes = [_mk_note(i, measure=1) for i in range(12)]
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.autodepth = False
    hand.depth = 9
    hand.frest = [None, -1.0, -2.0, -3.0, -4.0, -5.0]
    hand.cfps = list(hand.frest)

    seq = [1, 2, 3, 4, 5, 1, 2, 3, 4]

    def fake_optimize_seq(_nseq, _istart):
        return list(seq), 0.0

    hand.optimize_seq = fake_optimize_seq  # type: ignore[method-assign]
    hand.generate(start_measure=1, nmeasures=10)

    # At i=3 we enter tail-reuse path and apply finger=2; fingerseq must reflect finger 2 geometry.
    i = 3
    expected = (hand.frest[1] - hand.frest[2]) + hand.noteseq[i].x
    assert hand.noteseq[i].fingering == 2
    assert hand.fingerseq[i][1] == expected


def test_manual_depth_not_overridden_near_tail() -> None:
    notes = [_mk_note(i, measure=1) for i in range(12)]
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.autodepth = False
    hand.depth = 5
    hand.generate(start_measure=1, nmeasures=10)
    assert hand.depth == 5
