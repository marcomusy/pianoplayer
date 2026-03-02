"""Minimal MusicXML I/O helpers used by pianoplayer.

This module intentionally implements only the subset needed by the project:
parts, measures, notes/chords/rests, ties, duration/divisions, and fingering output.
"""

from __future__ import annotations

import logging
import re
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
_FINGERING_LYRIC_NUMBER = "pianoplayer-fingering"


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


def _note_staff(note_el: ET.Element) -> int:
    """Return MusicXML staff number for one note element (0 when missing)."""
    staff_text = note_el.findtext("staff", "")
    if staff_text and staff_text.strip().isdigit():
        return int(staff_text.strip())
    return 0


def _drop_shorter_simultaneous_duplicates(events: list[EventInfo]) -> list[EventInfo]:
    """Drop duplicate notes sharing same onset+pitch+staff.

    This keeps voice-unison duplicates out of the optimizer while preserving
    duplicates that belong to different staves.
    """
    winner_by_key: dict[tuple[int, int], tuple[int, int, float, int]] = {}
    losers_by_event: dict[int, set[int]] = {}

    for event_idx, evt in enumerate(events):
        if evt.kind not in {"note", "chord"} or not evt.pitches:
            continue

        for note_idx, pitch in enumerate(evt.pitches):
            onset_key = int(round(evt.offset * 1_000_000))
            staff = _note_staff(evt.notes[note_idx]) if note_idx < len(evt.notes) else 0
            key = (onset_key, staff, pitch.midi)

            anchor_bonus = 0
            if note_idx < len(evt.notes):
                finger = _extract_note_fingering(evt.notes[note_idx])
                anchor_bonus = 1 if 1 <= finger <= 5 else 0

            candidate = (event_idx, note_idx, evt.duration, anchor_bonus)
            previous = winner_by_key.get(key)
            if previous is None:
                winner_by_key[key] = candidate
                continue

            _, _, prev_duration, prev_anchor_bonus = previous
            should_replace = (
                evt.duration > prev_duration + 1e-9
                or (abs(evt.duration - prev_duration) <= 1e-9 and anchor_bonus > prev_anchor_bonus)
            )

            if should_replace:
                prev_event_idx, prev_note_idx, _, _ = previous
                losers_by_event.setdefault(prev_event_idx, set()).add(prev_note_idx)
                winner_by_key[key] = candidate
            else:
                losers_by_event.setdefault(event_idx, set()).add(note_idx)

    if not losers_by_event:
        return events

    cleaned_events: list[EventInfo] = []
    dropped = 0

    for event_idx, evt in enumerate(events):
        dropped_idx = losers_by_event.get(event_idx)
        if not dropped_idx or evt.kind not in {"note", "chord"} or not evt.pitches:
            cleaned_events.append(evt)
            continue

        kept_pitches: list[PitchInfo] = []
        kept_notes: list[ET.Element] = []
        for note_idx, pitch in enumerate(evt.pitches):
            if note_idx in dropped_idx:
                dropped += 1
                continue
            kept_pitches.append(pitch)
            if note_idx < len(evt.notes):
                kept_notes.append(evt.notes[note_idx])

        if not kept_pitches:
            continue

        evt.pitches = kept_pitches
        evt.notes = kept_notes
        evt.kind = "note" if len(kept_pitches) == 1 else "chord"
        cleaned_events.append(evt)

    logger.debug("Dropped %s duplicated simultaneous note(s) (kept longest duration).", dropped)
    return cleaned_events


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

    for lyric_el in note_el.findall("./lyric"):
        text_el = lyric_el.find("text")
        if text_el is None or text_el.text is None:
            continue
        value = text_el.text.strip()
        is_pianoplayer_lyric = lyric_el.attrib.get("number", "") == _FINGERING_LYRIC_NUMBER
        # Avoid mistaking ordinary numeric lyrics (verse numbers) for fingering.
        if not is_pianoplayer_lyric and value not in _CIRCLED_TO_FINGER:
            continue
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
    """Parse plain/compressed MusicXML and build lightweight score containers."""
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

        sequential_measure_no = 0
        for measure_el in part_el.findall("measure"):
            raw_measure = (measure_el.attrib.get("number", "0") or "0").strip()
            if raw_measure.isdigit():
                measure_no = int(raw_measure)
            else:
                digits = re.sub(r"\D", "", raw_measure)
                if digits.isdigit():
                    measure_no = int(digits)
                else:
                    sequential_measure_no += 1
                    measure_no = sequential_measure_no
            sequential_measure_no = max(sequential_measure_no, measure_no)

            for child in measure_el:
                # Divisions can change across measures; keep it updated.
                if child.tag == "attributes":
                    div_el = child.find("divisions")
                    if div_el is not None and div_el.text is not None:
                        divisions = max(1, int(div_el.text))
                    continue

                if child.tag == "backup":
                    duration_el = child.find("duration")
                    duration_raw = (
                        int(duration_el.text)
                        if duration_el is not None and duration_el.text
                        else 0
                    )
                    current_offset = max(0.0, current_offset - (duration_raw / divisions))
                    continue

                if child.tag == "forward":
                    duration_el = child.find("duration")
                    duration_raw = (
                        int(duration_el.text)
                        if duration_el is not None and duration_el.text
                        else 0
                    )
                    current_offset += duration_raw / divisions
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
                    # Rests advance timeline but do not create INote values.
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

                # Chord members share the same onset: append to previous note/chord event.
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

        events = _drop_shorter_simultaneous_duplicates(events)
        parts.append(PartInfo(part_id=part_id, events=events))

    return ScoreInfo(tree=tree, parts=parts)


def noteseq_from_part(part: PartInfo, chord_note_stagger_s: float = 0.05) -> list[INote]:
    """Convert a parsed part to INote sequence.

    Parameters
    ----------
    chord_note_stagger_s:
        Small onset/duration offset (seconds) used to turn a simultanous chord into
        a very short top-to-bottom note sequence for the optimizer.
    """
    noteseq: list[INote] = []
    chord_id = 0
    note_id = 0
    chord_note_stagger_s = max(0.0, float(chord_note_stagger_s))

    for evt in part.events:
        if evt.duration == 0:
            continue
        # Skip continuation/stop tie events: onset is already represented by the tie start.
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
            an.staff = _note_staff(evt.notes[0]) if evt.notes else 0
            an.isBlack = (p.midi % 12) in [1, 3, 6, 8, 10]
            an.fingering = _extract_note_fingering(evt.notes[0])
            an.is_anchor = an.fingering in {1, 2, 3, 4, 5}
            noteseq.append(an)
            note_id += 1
            continue

        if evt.kind == "chord" and evt.pitches:
            count = len(evt.pitches)
            # Expand one chord event into multiple INote entries.
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
                an.time = evt.offset - chord_note_stagger_s * (count - j - 1)
                an.duration = evt.duration + chord_note_stagger_s * (count - 1)
                an.staff = _note_staff(evt.notes[j]) if j < len(evt.notes) else 0
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
    return value in _CIRCLED_TO_FINGER


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
        if lyric_el.attrib.get("number", "") == _FINGERING_LYRIC_NUMBER:
            note_el.remove(lyric_el)
            continue
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
        lyric_el = ET.SubElement(note_el, "lyric", {"number": _FINGERING_LYRIC_NUMBER})
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
    target_staff: int | None = None,
) -> None:
    """Write generated fingering values back into one MusicXML part.

    When `target_staff` is set, only notes on that staff are consumed and annotated.
    """
    seq = list(hand_noteseq)
    idx = 0

    for evt in part.events:
        if evt.duration == 0:
            continue
        if evt.tie_types.intersection({"continue", "stop"}):
            continue

        if evt.kind == "note" and evt.notes:
            if target_staff is not None and _note_staff(evt.notes[0]) != target_staff:
                continue
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
            # In single-part piano scores, this lets RH/LH annotate only staff 1/2.
            notes_to_annotate = (
                [n for n in evt.notes if _note_staff(n) == target_staff]
                if target_staff is not None
                else list(evt.notes)
            )
            chord_len = len(notes_to_annotate)
            for note_el in notes_to_annotate:
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


def clear_part_fingering(part: PartInfo, *, lyrics: bool, target_staff: int | None = None) -> None:
    """Remove existing fingering markup from one part (optionally one staff only)."""
    for evt in part.events:
        if evt.kind not in {"note", "chord"}:
            continue
        for note_el in evt.notes:
            if target_staff is not None and _note_staff(note_el) != target_staff:
                continue
            _clear_note_fingering(note_el, lyrics)
