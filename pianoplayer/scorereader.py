"""Readers to convert scores and MIDI to internal INote sequences."""

from __future__ import annotations

import logging
from operator import attrgetter
from typing import Any

from music21.articulations import Fingering

from pianoplayer.models import INote, keypos, keypos_midi

logger = logging.getLogger(__name__)


def get_finger_music21(n: Any, j: int = 0) -> int | str:
    fingers = [art.fingerNumber for art in n.articulations if isinstance(art, Fingering)]
    return fingers[j] if len(fingers) > j else 0


def reader(sf: Any, beam: int = 0) -> list[INote]:
    noteseq: list[INote] = []

    if hasattr(sf, "parts"):
        if len(sf.parts) <= beam:
            return []
        strm = sf.parts[beam].flat
    elif hasattr(sf, "elements"):
        if len(sf.elements) == 1 and beam == 1:
            strm = sf[0]
        else:
            if len(sf) <= beam:
                return []
            strm = sf[beam]
    else:
        strm = sf.flat

    logger.info("Reading beam %s with %s objects in stream.", beam, len(strm))

    chord_id = 0
    note_id = 0
    for n in strm.getElementsByClass("GeneralNote"):
        if n.duration.quarterLength == 0:
            continue

        if hasattr(n, "tie") and n.tie and n.tie.type in {"continue", "stop"}:
            continue

        if n.isNote:
            if len(noteseq) and n.offset == noteseq[-1].time:
                continue

            an = INote()
            an.noteID = note_id
            an.note21 = n
            an.isChord = False
            an.name = n.name
            an.octave = n.octave
            an.measure = n.measureNumber
            an.x = keypos(n)
            an.pitch = n.pitch.midi
            an.time = n.offset
            an.duration = n.duration.quarterLength
            pc = n.pitch.pitchClass
            an.isBlack = pc in [1, 3, 6, 8, 10]

            # Prefer explicit articulation fingering; fallback to lyric fingering.
            art_finger = get_finger_music21(n)
            if art_finger:
                an.fingering = art_finger
            elif n.lyrics:
                an.fingering = n.lyric

            noteseq.append(an)
            note_id += 1
            continue

        if n.isChord:
            if n.tie and n.tie.type in {"continue", "stop"}:
                continue

            sfasam = 0.05
            for j, cn in enumerate(n.pitches):
                an = INote()
                an.chordID = chord_id
                an.noteID = note_id
                an.isChord = True
                an.pitch = cn.midi
                an.note21 = cn
                an.name = cn.name
                an.chordnr = j
                an.NinChord = len(n.pitches)
                an.octave = cn.octave
                an.measure = n.measureNumber
                an.x = keypos(cn)
                an.time = n.offset - sfasam * (len(n.pitches) - j - 1)
                an.duration = n.duration.quarterLength + sfasam * (an.NinChord - 1)
                pc = cn.pitch.pitchClass if hasattr(cn, "pitch") else cn.pitchClass
                an.isBlack = pc in [1, 3, 6, 8, 10]
                an.fingering = get_finger_music21(n, j)
                note_id += 1
                noteseq.append(an)
            chord_id += 1

    if len(noteseq) < 2:
        logger.info("Beam is empty.")
        return []
    return noteseq


def reader_pretty_midi(pm: Any, beam: int = 0) -> list[INote]:
    noteseq: list[INote] = []
    pm_notes = sorted(pm.notes, key=attrgetter("start"))

    logger.info("Reading beam %s with %s objects in stream.", beam, len(pm_notes))

    chord_id = 0
    note_id = 0
    sfasam = 0.05

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
                an.note21 = n
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
            an.chord21 = group[0]
            an.pitch = cn.pitch
            an.note21 = cn
            an.chordnr = k
            an.NinChord = len(valid_group)
            an.octave = cn.pitch // 12
            an.x = keypos_midi(cn)
            an.time = onset - sfasam * (len(valid_group) - k - 1)
            an.duration = cn_duration + sfasam * (len(valid_group) - 1)
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
    """
    Convert a PIG text file to a noteseq of type INote.

    time_unit must be multiple of 2.
    beam = 0, right hand
    beam = 1, left hand.
    """
    sf = PIG2Stream(fname, beam=beam)
    return reader(sf, beam=0)


def PIG2Stream(fname: str, beam: int = 0, time_unit: float = 0.5, fixtempo: float = 0) -> Any:
    """
    Convert a PIG text file to a music21 Stream object.
    time_unit must be multiple of 2.
    beam = 0, right hand
    beam = 1, left hand.
    """
    import numpy as np
    from music21 import chord, note, stream
    from music21.articulations import Fingering

    with open(fname, "r", encoding="utf-8") as f:
        lines = f.readlines()

    durations = []
    firstonset = 0.0
    blines = []
    for line in lines:
        if line.startswith("//"):
            continue
        _, onset, offset, _name, _, _, channel, _ = line.split()
        onset, offset = float(onset), float(offset)
        if beam != int(channel):
            continue
        if not firstonset:
            firstonset = onset
        if offset - onset < 0.0001:
            continue
        durations.append(offset - onset)
        blines.append(line)

    sf = stream.Part()
    sf.id = beam

    if not blines:
        return sf

    durations_arr = np.array(durations)
    logdurs = -np.log2(durations_arr)
    mindur = np.min(logdurs)
    expos = (logdurs - mindur).astype(int)
    if np.max(expos) > 3:
        mindur = mindur + 1

    if not fixtempo and firstonset:
        r = note.Rest()
        logdur = -np.log2(firstonset)
        r.duration.quarterLength = 1.0 / time_unit / pow(2, int(logdur - mindur))
        sf.append(r)

    i = 0
    n_lines = len(blines)
    while i < n_lines:
        line = blines[i]
        if line.startswith("//"):
            i += 1
            continue

        _, onset, offset, name, _, _, _, finger = line.split()
        onset, offset = float(onset), float(offset)
        name = name.replace("b", "-")

        chordnotes = [name]
        next_i = i + 1
        while next_i < n_lines:
            _, onset1, _, name1, _, _, _, _ = blines[next_i].split()
            onset1 = float(onset1)
            if onset1 != onset:
                break
            name1 = name1.replace("b", "-")
            chordnotes.append(name1)
            next_i += 1

        if len(chordnotes) > 1:
            an = chord.Chord(chordnotes)
        else:
            an = note.Note(name)
            if "_" not in finger:
                fingering = Fingering(abs(int(finger)))
                fingering.style.absoluteY = 20
                an.articulations.append(fingering)

        if fixtempo:
            an.duration.quarterLength = fixtempo
        else:
            logdur = -np.log2(offset - onset)
            an.duration.quarterLength = 1.0 / time_unit / pow(2, int(logdur - mindur))

        sf.append(an)

        if next_i < n_lines:
            _, onset_next, _, _, _, _, _, _ = blines[next_i].split()
            onset_next = float(onset_next)
            if onset_next - offset > 0:
                r = note.Rest()
                if fixtempo:
                    r.duration.quarterLength = fixtempo
                logdur = -np.log2(onset_next - offset)
                d = int(logdur - mindur)
                if d < 4:
                    r.duration.quarterLength = 1.0 / time_unit / pow(2, d)
                    sf.append(r)

        i = next_i

    return sf
