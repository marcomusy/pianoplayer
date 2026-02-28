from types import SimpleNamespace

from pianoplayer.musicxml_io import annotate_part_with_fingering, parse_musicxml


def test_annotate_handles_short_hand_sequence() -> None:
    score = parse_musicxml("scores/test_scales.xml")
    part = score.parts[0]

    # Deliberately shorter than the note stream to verify no IndexError is raised.
    short_hand = SimpleNamespace(
        noteseq=[SimpleNamespace(fingering=1)],
        lyrics=False,
    )

    annotate_part_with_fingering(part, short_hand.noteseq, lyrics=False)
