"""Readers to convert score inputs to internal INote sequences."""

from __future__ import annotations

import logging
from operator import attrgetter
from typing import Any

from pianoplayer.models import INote, keypos_midi
from pianoplayer.musicxml_io import PartInfo, noteseq_from_part

logger = logging.getLogger(__name__)


def reader(
    score: Any,
    beam: int = 0,
    chord_note_stagger_s: float = 0.05,
) -> list[INote]:
    """Read a parsed score object and return an ``INote`` sequence for one part."""
    parts = getattr(score, "parts", None)
    if parts is None or len(parts) <= beam:
        return []
    part = parts[beam]
    if isinstance(part, PartInfo):
        return noteseq_from_part(part, chord_note_stagger_s=chord_note_stagger_s)
    return []


def reader_pretty_midi(
    pm: Any,
    beam: int = 0,
    chord_note_stagger_s: float = 0.05,
) -> list[INote]:
    """Convert a ``pretty_midi.Instrument`` object to ``INote`` entries."""
    noteseq: list[INote] = []
    pm_notes = sorted(pm.notes, key=attrgetter("start"))

    logger.info("Reading beam %s with %s objects in stream.", beam, len(pm_notes))

    chord_id = 0
    note_id = 0
    chord_note_stagger_s = max(0.0, float(chord_note_stagger_s))

    ii = 0
    while ii < len(pm_notes):
        onset = pm_notes[ii].start
        jj = ii + 1
        while jj < len(pm_notes) and pm_notes[jj].start == onset:
            jj += 1

        group = pm_notes[ii:jj]
        group_size = len(group)

        if group_size == 1:
            n = group[0]
            n_duration = n.end - n.start
            if n_duration > 0:
                an = INote()
                an.noteID = note_id
                note_id += 1
                an.pitch = n.pitch
                an.isChord = False
                an.octave = n.pitch // 12
                an.x = keypos_midi(n)
                an.time = n.start
                an.duration = n_duration
                pc = n.pitch % 12
                an.isBlack = pc in [1, 3, 6, 8, 10]
                noteseq.append(an)
            ii = jj
            continue

        valid_group = [n for n in group if (n.end - n.start) > 0]
        if not valid_group:
            ii = jj
            continue

        for k, cn in enumerate(valid_group):
            cn_duration = cn.end - cn.start
            an = INote()
            an.chordID = chord_id
            an.noteID = note_id
            note_id += 1
            an.isChord = True
            an.pitch = cn.pitch
            an.chordnr = k
            an.NinChord = len(valid_group)
            an.octave = cn.pitch // 12
            an.x = keypos_midi(cn)
            an.time = onset - chord_note_stagger_s * (len(valid_group) - k - 1)
            an.duration = cn_duration + chord_note_stagger_s * (len(valid_group) - 1)
            pc = cn.pitch % 12
            an.isBlack = pc in [1, 3, 6, 8, 10]
            noteseq.append(an)

        chord_id += 1
        ii = jj

    if len(noteseq) < 2:
        logger.info("Beam is empty.")
        return []
    return noteseq


def reader_PIG(fname: str, beam: int = 0) -> list[INote]:
    """Read a PIG text file and build ``INote`` values for one channel (beam)."""
    noteseq: list[INote] = []
    chord_id = 0
    note_id = 0

    rows: list[tuple[float, float, str, str]] = []
    with open(fname, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("//") or not line.strip():
                continue
            cols = line.split()
            if len(cols) < 8:
                continue
            _idx, onset, offset, name, _onv, _offv, channel, finger = cols[:8]
            if int(channel) != beam:
                continue
            rows.append((float(onset), float(offset), name.replace("b", "-"), finger))

    rows.sort(key=lambda r: (r[0], r[2]))
    i = 0
    while i < len(rows):
        onset = rows[i][0]
        j = i
        group: list[tuple[float, float, str, str]] = []
        while j < len(rows) and rows[j][0] == onset:
            group.append(rows[j])
            j += 1

        if len(group) == 1:
            _, off, name, finger = group[0]
            an = INote()
            an.noteID = note_id
            note_id += 1
            an.time = onset
            an.duration = max(0.0, off - onset)
            an.name = name[:-1]
            an.octave = int(name[-1])
            an.fingering = 0 if finger == "_" else int(finger)
            an.is_anchor = an.fingering in {1, 2, 3, 4, 5}
            pc_map = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
            step = an.name[0]
            alter = an.name.count("#") - an.name.count("-")
            an.pitch = (an.octave + 1) * 12 + pc_map[step] + alter
            an.isBlack = (an.pitch % 12) in [1, 3, 6, 8, 10]
            noteseq.append(an)
        else:
            for k, (_on, off, name, _finger) in enumerate(group):
                an = INote()
                an.chordID = chord_id
                an.noteID = note_id
                note_id += 1
                an.isChord = True
                an.chordnr = k
                an.NinChord = len(group)
                an.time = onset
                an.duration = max(0.0, off - onset)
                an.name = name[:-1]
                an.octave = int(name[-1])
                an.is_anchor = False
                pc_map = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
                step = an.name[0]
                alter = an.name.count("#") - an.name.count("-")
                an.pitch = (an.octave + 1) * 12 + pc_map[step] + alter
                an.isBlack = (an.pitch % 12) in [1, 3, 6, 8, 10]
                noteseq.append(an)
            chord_id += 1

        i = j

    if len(noteseq) < 2:
        logger.info("Beam is empty.")
        return []
    return noteseq
