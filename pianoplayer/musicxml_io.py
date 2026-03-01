"""Minimal MusicXML I/O helpers used by pianoplayer.

This module intentionally implements only the subset needed by the project:
parts, measures, notes/chords/rests, ties, duration/divisions, and fingering output.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

from pianoplayer.models import INote, keypos

logger = logging.getLogger(__name__)


_STEP_TO_SEMITONE = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

_CIRCLED_FINGER = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}
_CIRCLED_TO_FINGER = {v: k for k, v in _CIRCLED_FINGER.items()}


@dataclass(slots=True)
class PitchInfo:
    name: str
    octave: int
    midi: int


@dataclass(slots=True)
class EventInfo:
    kind: str  # note | chord | rest
    measure: int
    offset: float
    duration: float
    tie_types: set[str]
    notes: list[ET.Element] = field(default_factory=list)
    pitches: list[PitchInfo] = field(default_factory=list)


@dataclass(slots=True)
class PartInfo:
    part_id: str
    events: list[EventInfo]


@dataclass(slots=True)
class ScoreInfo:
    tree: ET.ElementTree
    parts: list[PartInfo]

    def write(self, filename: str) -> None:
        self.tree.write(filename, encoding="utf-8", xml_declaration=True)


def _note_name(step: str, alter: int) -> str:
    if alter == 0:
        return step
    if alter > 0:
        return step + ("#" * alter)
    return step + ("-" * abs(alter))


def _pitch_from_note(note_el: ET.Element) -> PitchInfo | None:
    pitch_el = note_el.find("pitch")
    if pitch_el is None:
        return None

    step_el = pitch_el.find("step")
    octave_el = pitch_el.find("octave")
    if step_el is None or octave_el is None or step_el.text is None or octave_el.text is None:
        return None

    step = step_el.text.strip().upper()
    alter_el = pitch_el.find("alter")
    alter = int(alter_el.text) if alter_el is not None and alter_el.text is not None else 0
    octave = int(octave_el.text)

    semitone = _STEP_TO_SEMITONE[step] + alter
    midi = (octave + 1) * 12 + semitone
    return PitchInfo(name=_note_name(step, alter), octave=octave, midi=midi)


def _extract_note_fingering(note_el: ET.Element) -> int:
    """Return a pre-existing fingering annotation from one note element, if present."""
    for fing_el in note_el.findall("./notations/technical/fingering"):
        if fing_el.text is None:
            continue
        value = fing_el.text.strip()
        if value in _CIRCLED_TO_FINGER:
            return _CIRCLED_TO_FINGER[value]
        if value.lstrip("+-").isdigit():
            finger = abs(int(value))
            if 1 <= finger <= 5:
                return finger

    for txt_el in note_el.findall("./lyric/text"):
        if txt_el.text is None:
            continue
        value = txt_el.text.strip()
        if value in _CIRCLED_TO_FINGER:
            return _CIRCLED_TO_FINGER[value]
        if value.lstrip("+-").isdigit():
            finger = abs(int(value))
            if 1 <= finger <= 5:
                return finger

    return 0


def _parse_mxl_tree(filename: str) -> ET.ElementTree:
    """Parse a compressed MusicXML (.mxl) archive and return the score tree."""
    with ZipFile(filename, "r") as archive:
        members = set(archive.namelist())

        # Standard MXL entry point via container descriptor.
        if "META-INF/container.xml" in members:
            container_root = ET.fromstring(archive.read("META-INF/container.xml"))
            for rootfile in container_root.findall(".//{*}rootfile"):
                full_path = rootfile.attrib.get("full-path", "").strip()
                if not full_path or full_path not in members:
                    continue
                return ET.parse(BytesIO(archive.read(full_path)))

        # Fallback for non-standard archives: first XML score payload.
        for name in archive.namelist():
            lname = name.lower()
            if lname.endswith(".xml") and not lname.startswith("meta-inf/"):
                return ET.parse(BytesIO(archive.read(name)))

    raise ValueError(f"No MusicXML document found inside archive: {filename}")


def parse_musicxml(filename: str) -> ScoreInfo:
    ext = Path(filename).suffix.lower()
    if ext == ".mxl":
        tree = _parse_mxl_tree(filename)
    else:
        tree = ET.parse(filename)
    root = tree.getroot()
    parts: list[PartInfo] = []

    for part_el in root.findall("part"):
        part_id = part_el.attrib.get("id", "")
        events: list[EventInfo] = []

        divisions = 1
        current_offset = 0.0

        for measure_el in part_el.findall("measure"):
            measure_no = int(measure_el.attrib.get("number", "0") or 0)

            for child in measure_el:
                if child.tag == "attributes":
                    div_el = child.find("divisions")
                    if div_el is not None and div_el.text is not None:
                        divisions = max(1, int(div_el.text))
                    continue

                if child.tag != "note":
                    continue

                note_el = child
                if note_el.find("grace") is not None:
                    continue

                duration_el = note_el.find("duration")
                duration_raw = (
                    int(duration_el.text)
                    if duration_el is not None and duration_el.text
                    else 0
                )
                duration = duration_raw / divisions if duration_raw else 0.0

                tie_types = {
                    t.attrib.get("type", "")
                    for t in note_el.findall("tie")
                    if t.attrib.get("type")
                }

                is_rest = note_el.find("rest") is not None
                is_chord_member = note_el.find("chord") is not None
                pitch = _pitch_from_note(note_el)

                if is_rest:
                    events.append(
                        EventInfo(
                            kind="rest",
                            measure=measure_no,
                            offset=current_offset,
                            duration=duration,
                            tie_types=tie_types,
                            notes=[note_el],
                            pitches=[],
                        )
                    )
                    current_offset += duration
                    continue

                if is_chord_member and events and events[-1].kind in {"note", "chord"}:
                    events[-1].kind = "chord"
                    events[-1].notes.append(note_el)
                    if pitch is not None:
                        events[-1].pitches.append(pitch)
                    events[-1].tie_types.update(tie_types)
                    continue

                evt = EventInfo(
                    kind="note",
                    measure=measure_no,
                    offset=current_offset,
                    duration=duration,
                    tie_types=tie_types,
                    notes=[note_el],
                    pitches=[pitch] if pitch is not None else [],
                )
                events.append(evt)
                current_offset += duration

        parts.append(PartInfo(part_id=part_id, events=events))

    return ScoreInfo(tree=tree, parts=parts)


def noteseq_from_part(part: PartInfo) -> list[INote]:
    noteseq: list[INote] = []
    chord_id = 0
    note_id = 0
    sfasam = 0.05

    for evt in part.events:
        if evt.duration == 0:
            continue
        if evt.tie_types.intersection({"continue", "stop"}):
            continue

        if evt.kind == "note" and evt.pitches:
            p = evt.pitches[0]
            an = INote()
            an.noteID = note_id
            an.note21 = evt
            an.isChord = False
            an.name = p.name
            an.octave = p.octave
            an.measure = evt.measure
            an.x = keypos(an)
            an.pitch = p.midi
            an.time = evt.offset
            an.duration = evt.duration
            an.isBlack = (p.midi % 12) in [1, 3, 6, 8, 10]
            an.fingering = _extract_note_fingering(evt.notes[0])
            an.is_anchor = an.fingering in {1, 2, 3, 4, 5}
            noteseq.append(an)
            note_id += 1
            continue

        if evt.kind == "chord" and evt.pitches:
            count = len(evt.pitches)
            for j, p in enumerate(evt.pitches):
                an = INote()
                an.chordID = chord_id
                an.noteID = note_id
                an.isChord = True
                an.note21 = evt
                an.name = p.name
                an.pitch = p.midi
                an.octave = p.octave
                an.chordnr = j
                an.NinChord = count
                an.measure = evt.measure
                an.x = keypos(an)
                an.time = evt.offset - sfasam * (count - j - 1)
                an.duration = evt.duration + sfasam * (count - 1)
                an.isBlack = (p.midi % 12) in [1, 3, 6, 8, 10]
                if j < len(evt.notes):
                    an.fingering = _extract_note_fingering(evt.notes[j])
                    an.is_anchor = an.fingering in {1, 2, 3, 4, 5}
                noteseq.append(an)
                note_id += 1
            chord_id += 1

    if len(noteseq) < 2:
        return []
    return noteseq


def _is_fingering_text(text: str) -> bool:
    value = text.strip()
    return value in _CIRCLED_TO_FINGER or value.lstrip("+-").isdigit()


def _valid_output_finger(value: int | str) -> int | None:
    """Normalize a generated finger to 1..5; return None when it should be skipped."""
    if isinstance(value, str):
        text = value.strip()
        if text in _CIRCLED_TO_FINGER:
            return _CIRCLED_TO_FINGER[text]
        if not text.lstrip("+-").isdigit():
            return None
        value = int(text)
    finger = abs(int(value))
    if 1 <= finger <= 5:
        return finger
    return None


def _clear_note_fingering(note_el: ET.Element, lyrics: bool) -> None:
    """Remove existing fingering markup so we write a single annotation per note."""
    for technical_el in note_el.findall("./notations/technical"):
        for fing_el in list(technical_el.findall("fingering")):
            technical_el.remove(fing_el)
        if len(technical_el) == 0:
            parent = note_el.find("./notations")
            if parent is not None:
                parent.remove(technical_el)
    for notations_el in list(note_el.findall("./notations")):
        if len(notations_el) == 0:
            note_el.remove(notations_el)

    if not lyrics:
        return
    for lyric_el in list(note_el.findall("lyric")):
        text_el = lyric_el.find("text")
        if text_el is not None and text_el.text and _is_fingering_text(text_el.text):
            note_el.remove(lyric_el)


def _set_note_fingering(
    note_el: ET.Element,
    fingering: int | str,
    lyrics: bool,
    *,
    anchored: bool,
) -> None:
    text = str(fingering)
    if anchored and isinstance(fingering, int) and fingering in _CIRCLED_FINGER:
        text = _CIRCLED_FINGER[fingering]

    _clear_note_fingering(note_el, lyrics)

    if lyrics:
        lyric_el = ET.SubElement(note_el, "lyric")
        text_el = ET.SubElement(lyric_el, "text")
        text_el.text = text
        return

    notations_el = note_el.find("notations")
    if notations_el is None:
        notations_el = ET.SubElement(note_el, "notations")
    technical_el = notations_el.find("technical")
    if technical_el is None:
        technical_el = ET.SubElement(notations_el, "technical")
    fingering_el = ET.SubElement(technical_el, "fingering")
    fingering_el.text = text


def annotate_part_with_fingering(
    part: PartInfo,
    hand_noteseq: Iterable[INote],
    *,
    lyrics: bool,
    skip_chords_with: int = 4,
) -> None:
    seq = list(hand_noteseq)
    idx = 0

    for evt in part.events:
        if evt.duration == 0:
            continue
        if evt.tie_types.intersection({"continue", "stop"}):
            continue

        if evt.kind == "note" and evt.notes:
            if idx >= len(seq):
                logger.warning("Not enough generated notes to annotate note at idx=%s", idx)
                return
            finger = _valid_output_finger(seq[idx].fingering)
            if finger is not None:
                _set_note_fingering(
                    evt.notes[0],
                    finger,
                    lyrics,
                    anchored=bool(getattr(seq[idx], "is_anchor", False)),
                )
            idx += 1
            continue

        if evt.kind == "chord" and evt.notes:
            chord_len = len(evt.notes)
            for note_el in evt.notes:
                if idx >= len(seq):
                    logger.warning("Not enough generated notes to annotate chord at idx=%s", idx)
                    return
                if chord_len < skip_chords_with:
                    finger = _valid_output_finger(seq[idx].fingering)
                    if finger is not None:
                        _set_note_fingering(
                            note_el,
                            finger,
                            lyrics,
                            anchored=bool(getattr(seq[idx], "is_anchor", False)),
                        )
                idx += 1
