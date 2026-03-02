import xml.etree.ElementTree as ET
from types import SimpleNamespace

from pianoplayer.musicxml_io import (
    EventInfo,
    PartInfo,
    PitchInfo,
    annotate_part_with_fingering,
    noteseq_from_part,
    parse_musicxml,
    strip_layout_breaks,
)
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


def test_reader_does_not_treat_plain_numeric_lyrics_as_fingering(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <lyric><text>1</text></lyric>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
      </note>
    </measure>
  </part>
</score-partwise>
"""
    score_path = tmp_path / "lyrics_numbers.xml"
    score_path.write_text(xml, encoding="utf-8")
    score = parse_musicxml(str(score_path))
    seq = reader(score, beam=0)
    assert seq
    assert seq[0].fingering == 0


def test_annotate_below_beam_preserves_non_fingering_lyrics(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <lyric><text>1</text></lyric>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
      </note>
    </measure>
  </part>
</score-partwise>
"""
    score_path = tmp_path / "lyrics_preserve.xml"
    score_path.write_text(xml, encoding="utf-8")
    score = parse_musicxml(str(score_path))
    part = score.parts[0]
    seq = reader(score, beam=0)
    assert len(seq) >= 2
    seq[0].fingering = 2
    seq[1].fingering = 3

    annotate_part_with_fingering(part, seq, lyrics=True)
    first_note = part.events[0].notes[0]
    lyrics = first_note.findall("lyric")
    texts = [ly.find("text").text for ly in lyrics if ly.find("text") is not None]
    assert "1" in texts
    assert "2" in texts
    assert any(ly.attrib.get("number") == "pianoplayer-fingering" for ly in lyrics)


def test_noteseq_from_part_uses_configurable_chord_stagger() -> None:
    part = PartInfo(
        part_id="P1",
        events=[
            EventInfo(
                kind="chord",
                measure=1,
                offset=10.0,
                duration=1.0,
                tie_types=set(),
                notes=[],
                pitches=[
                    PitchInfo(name="C", octave=4, midi=60),
                    PitchInfo(name="E", octave=4, midi=64),
                    PitchInfo(name="G", octave=4, midi=67),
                ],
            )
        ],
    )

    seq_default = noteseq_from_part(part)
    seq_zero = noteseq_from_part(part, chord_note_stagger_s=0.0)

    assert len(seq_default) == 3
    assert len(seq_zero) == 3
    assert seq_default[0].time < seq_default[1].time < seq_default[2].time
    assert seq_zero[0].time == seq_zero[1].time == seq_zero[2].time == 10.0


def test_annotate_applies_hand_color_to_note_and_fingering() -> None:
    score = parse_musicxml("scores/test_scales.xml")
    part = score.parts[0]
    seq = reader(score, beam=0)
    assert seq
    seq[0].fingering = 3

    annotate_part_with_fingering(part, seq[:1], lyrics=False, hand_color="#112233")

    first_note = part.events[0].notes[0]
    fingering = first_note.find("./notations/technical/fingering")
    assert fingering is not None
    assert first_note.attrib.get("color") == "#112233"
    assert fingering.attrib.get("color") == "#112233"


def test_annotate_accepts_named_hand_color() -> None:
    score = parse_musicxml("scores/test_scales.xml")
    part = score.parts[0]
    seq = reader(score, beam=0)
    assert seq
    seq[0].fingering = 2

    annotate_part_with_fingering(part, seq[:1], lyrics=False, hand_color="royalblue")

    first_note = part.events[0].notes[0]
    fingering = first_note.find("./notations/technical/fingering")
    assert fingering is not None
    assert first_note.attrib.get("color") == "royalblue"
    assert fingering.attrib.get("color") == "royalblue"


def test_annotate_colorize_by_cost_applies_gradient() -> None:
    score = parse_musicxml("scores/test_scales.xml")
    part = score.parts[0]
    seq = reader(score, beam=0)
    assert len(seq) >= 2

    seq[0].fingering = 2
    seq[1].fingering = 3
    seq[0].cost = 0.1
    seq[1].cost = 9.0

    annotate_part_with_fingering(part, seq[:2], lyrics=False, colorize_by_cost=True)

    first = part.events[0].notes[0]
    second = part.events[1].notes[0]
    assert first.attrib.get("color")
    assert second.attrib.get("color")
    assert first.attrib.get("color") != second.attrib.get("color")


def test_strip_layout_breaks_removes_page_break_only(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <print new-page="yes" new-system="yes"/>
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    </measure>
  </part>
</score-partwise>
"""
    path = tmp_path / "layout_breaks.xml"
    path.write_text(xml, encoding="utf-8")
    score = parse_musicxml(str(path))
    strip_layout_breaks(score)
    out = tmp_path / "layout_breaks_out.xml"
    score.write(str(out))

    root = ET.parse(out).getroot()
    assert not root.findall(".//print[@new-page='yes']")
    assert root.findall(".//print[@new-system='yes']")


def test_noteseq_marks_same_onset_same_staff_as_synthetic_chord() -> None:
    note_a = ET.Element("note")
    ET.SubElement(note_a, "staff").text = "1"
    note_b = ET.Element("note")
    ET.SubElement(note_b, "staff").text = "1"

    part = PartInfo(
        part_id="P1",
        events=[
            EventInfo(
                kind="note",
                measure=1,
                offset=4.0,
                duration=1.0,
                tie_types=set(),
                notes=[note_a],
                pitches=[PitchInfo(name="E", octave=4, midi=64)],
            ),
            EventInfo(
                kind="note",
                measure=1,
                offset=4.0,
                duration=1.0,
                tie_types=set(),
                notes=[note_b],
                pitches=[PitchInfo(name="B", octave=4, midi=71)],
            ),
        ],
    )

    seq = noteseq_from_part(part, chord_note_stagger_s=0.05)
    assert len(seq) == 2
    assert seq[0].isChord and seq[1].isChord
    assert seq[0].chordID == seq[1].chordID
    assert seq[0].NinChord == 2 and seq[1].NinChord == 2
    assert seq[0].time < seq[1].time
