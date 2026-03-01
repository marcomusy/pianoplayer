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
    hand.finger_positions = list(hand.frest)

    seq = [1, 2, 3, 4, 5, 1, 2, 3, 4]

    def fake_optimize_seq(_nseq, _istart):
        return list(seq), 0.0

    hand.optimize_seq = fake_optimize_seq  # type: ignore[method-assign]
    hand.generate(start_measure=1, nmeasures=10)

    # At i=3 we enter tail-reuse path and apply finger=2.
    # The pressed finger must land exactly on the played note.
    i = 3
    assert hand.noteseq[i].fingering == 2
    assert hand.fingerseq[i][2] == hand.noteseq[i].x


def test_manual_depth_not_overridden_near_tail() -> None:
    notes = [_mk_note(i, measure=1) for i in range(12)]
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.autodepth = False
    hand.depth = 5
    hand.generate(start_measure=1, nmeasures=10)
    assert hand.depth == 5


def test_set_fingers_positions_preserves_posture_memory() -> None:
    notes = [_mk_note(i, measure=1) for i in range(2)]
    notes[0].x = 0.0
    notes[1].x = 10.0
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.preserve_posture_memory = True
    hand.relocation_alpha = 0.35

    # First placement defines initial posture around finger 2 at x=0.
    hand.set_fingers_positions([2, 3], notes, 0)
    prev_finger4 = hand.finger_positions[4]
    assert prev_finger4 is not None

    # Second placement lands finger 3 at x=10 and blends the rest.
    hand.set_fingers_positions([2, 3], notes, 1)
    assert hand.finger_positions[3] == notes[1].x

    if3 = hand.frest[3]
    i4 = hand.frest[4]
    assert if3 is not None and i4 is not None
    target_finger4 = (i4 - if3) + notes[1].x

    # Memory means finger 4 moves toward target but does not jump exactly to target.
    assert hand.finger_positions[4] is not None
    assert hand.finger_positions[4] != target_finger4
    assert hand.finger_positions[4] != prev_finger4


def test_set_fingers_positions_alpha_zero_matches_default_relocation() -> None:
    notes = [_mk_note(i, measure=1) for i in range(2)]
    notes[0].x = 0.0
    notes[1].x = 10.0
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.preserve_posture_memory = True
    hand.relocation_alpha = 0.0

    hand.set_fingers_positions([2, 3], notes, 0)
    hand.set_fingers_positions([2, 3], notes, 1)

    if3 = hand.frest[3]
    i4 = hand.frest[4]
    assert if3 is not None and i4 is not None
    expected = (i4 - if3) + notes[1].x
    assert hand.finger_positions[4] == expected


def test_ave_velocity_does_not_mutate_shared_hand_state() -> None:
    notes = [_mk_note(i, measure=1) for i in range(9)]
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.preserve_posture_memory = True
    hand.relocation_alpha = 0.8
    before = list(hand.finger_positions)

    _ = hand.ave_velocity([1, 2, 3, 4, 5, 1, 2, 3, 4], notes)
    after = list(hand.finger_positions)
    assert after == before


def test_first_placement_uses_relaxed_default_not_residual_state() -> None:
    notes = [_mk_note(i, measure=1) for i in range(2)]
    notes[0].x = 2.0
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.preserve_posture_memory = True
    hand.relocation_alpha = 1.0

    # Simulate stale state from a previous run.
    hand.finger_positions = [None, 100.0, 100.0, 100.0, 100.0, 100.0]
    hand.set_fingers_positions([2, 3], notes, 0)

    assert hand.finger_positions[2] == notes[0].x
    if2 = hand.frest[2]
    if1 = hand.frest[1]
    assert if2 is not None and if1 is not None
    assert hand.finger_positions[1] == (if1 - if2) + notes[0].x


def test_consecutive_window_local_i0_calls_do_not_always_reset_relaxed_geometry() -> None:
    notes = [_mk_note(i, measure=1) for i in range(2)]
    notes[0].x = 0.0
    notes[1].x = 10.0
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.preserve_posture_memory = True
    hand.relocation_alpha = 1.0
    hand.max_follow_lag_cm = 1e9

    # Emulate generate(): each call updates current note at local index 0 of a sliding window.
    hand.set_fingers_positions([2], [notes[0]], 0)
    hand.set_fingers_positions([3], [notes[1]], 0)

    if3 = hand.frest[3]
    i4 = hand.frest[4]
    assert if3 is not None and i4 is not None
    relaxed_target_second = (i4 - if3) + notes[1].x
    assert hand.finger_positions[4] != relaxed_target_second


def test_memory_mode_clamps_follow_lag_to_target() -> None:
    notes = [_mk_note(i, measure=1) for i in range(2)]
    notes[0].x = 0.0
    notes[1].x = 10.0
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.preserve_posture_memory = True
    hand.relocation_alpha = 1.0

    hand.set_fingers_positions([2], [notes[0]], 0)
    hand.finger_positions[4] = -100.0  # intentionally leave finger far behind
    hand.set_fingers_positions([3], [notes[1]], 0)

    if3 = hand.frest[3]
    i4 = hand.frest[4]
    assert if3 is not None and i4 is not None
    target_f4 = (i4 - if3) + notes[1].x
    assert hand.finger_positions[4] is not None
    assert abs(hand.finger_positions[4] - target_f4) <= hand.max_follow_lag_cm + 1e-9


def test_memory_mode_enforces_max_thumb_pinky_span() -> None:
    notes = [_mk_note(i, measure=1) for i in range(2)]
    notes[0].x = 0.0
    notes[1].x = 10.0
    hand = Hand(side="right", noteseq=notes, size="M")
    hand.verbose = False
    hand.preserve_posture_memory = True
    hand.relocation_alpha = 1.0

    hand.set_fingers_positions([3], [notes[0]], 0)
    hand.finger_positions[1] = -100.0
    hand.finger_positions[5] = 100.0
    hand.set_fingers_positions([3], [notes[1]], 0)

    assert hand.finger_positions[1] is not None and hand.finger_positions[5] is not None
    assert (hand.finger_positions[5] - hand.finger_positions[1]) <= hand.max_span_cm + 1e-9
