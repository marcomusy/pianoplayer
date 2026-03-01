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
