import xml.etree.ElementTree as ET
from types import SimpleNamespace

from pianoplayer.musicxml_io import annotate_part_with_fingering, parse_musicxml
from pianoplayer.scorereader import reader


def test_annotate_handles_short_hand_sequence() -> None:
    score = parse_musicxml("scores/test_scales.xml")
    part = score.parts[0]

    # Deliberately shorter than the note stream to verify no IndexError is raised.
    short_hand = SimpleNamespace(
        noteseq=[SimpleNamespace(fingering=1)],
        lyrics=False,
    )

    annotate_part_with_fingering(part, short_hand.noteseq, lyrics=False)


def test_reader_preserves_existing_musicxml_fingering() -> None:
    score = parse_musicxml("scores/test_scales_all_keys.xml")
    seq = reader(score, beam=0)
    assert seq
    assert seq[0].fingering == 1


def test_annotate_replaces_existing_fingering_with_single_anchor_marker() -> None:
    score = parse_musicxml("scores/test_scales_all_keys.xml")
    part = score.parts[0]
    seq = reader(score, beam=0)

    annotate_part_with_fingering(part, seq, lyrics=False)

    first_note = part.events[0].notes[0]
    fingerings = first_note.findall("./notations/technical/fingering")
    assert len(fingerings) == 1
    assert fingerings[0].text in {"①", "1"}

    xml_text = ET.tostring(first_note, encoding="unicode")
    assert xml_text.count("<fingering>") == 1
