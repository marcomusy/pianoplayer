"""Readers to convert scores and MIDI to internal INote sequences."""

from __future__ import annotations

import logging
from operator import attrgetter
from typing import Any

from music21.articulations import Fingering

from pianoplayer.models import INote
from pianoplayer.utils import keypos, keypos_midi

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
            if n.lyrics:
                an.fingering = n.lyric
            an.fingering = get_finger_music21(n)
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
    pm_onsets = [onset.start for onset in pm_notes]

    logger.info("Reading beam %s with %s objects in stream.", beam, len(pm_notes))
    chord_id = 0

    ii = 0
    while ii < len(pm_notes):
        n = pm_notes[ii]
        n_duration = n.end - n.start
        chord_notes = pm_onsets.count(n.start)

        if chord_notes != 1:
            if n_duration == 0:
                ii += 1
                continue

            an = INote()
            an.noteID += 1
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
            ii += 1
            continue

        if n_duration == 0:
            ii += 1
            continue

        sfasam = 0.05
        for jj in range(chord_notes):
            cn = pm_notes[ii]
            cn_duration = cn.end - cn.start
            an = INote()
            an.chordID = chord_id
            an.noteID += 1
            an.isChord = True
            an.chord21 = n
            an.pitch = cn.pitch
            an.note21 = cn
            an.chordnr = jj
            an.NinChord = chord_notes
            an.octave = cn.pitch // 2
            an.x = keypos_midi(cn)
            an.time = cn.start - sfasam * jj
            an.duration = cn_duration + sfasam * (jj - 1)
            pc = n.pitch % 12
            an.isBlack = pc in [1, 3, 6, 8, 10]
            noteseq.append(an)
            ii += 1

        chord_id += 1

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
    del fname, beam
    return []


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

    durations_arr = np.array(durations)
    logdurs = -np.log2(durations_arr)
    mindur = np.min(logdurs)
    expos = (logdurs - mindur).astype(int)
    if np.max(expos) > 3:
        mindur = mindur + 1

    sf = stream.Part()
    sf.id = beam

    if not fixtempo and firstonset:
        r = note.Rest()
        logdur = -np.log2(firstonset)
        r.duration.quarterLength = 1.0 / time_unit / pow(2, int(logdur - mindur))
        sf.append(r)

    n_lines = len(blines)
    for i in range(n_lines):
        if blines[i].startswith("//"):
            continue

        _, onset, offset, name, _, _, _, finger = blines[i].split()
        onset, offset = float(onset), float(offset)
        name = name.replace("b", "-")

        chordnotes = [name]
        for j in range(1, 5):
            if i + j >= n_lines:
                continue
            _, onset1, _, name1, _, _, _, _ = blines[i + j].split()
            onset1 = float(onset1)
            if onset1 == onset:
                name1 = name1.replace("b", "-")
                chordnotes.append(name1)

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

        if i + 1 < n_lines:
            _, onset1, _, _, _, _, _, _ = blines[i + 1].split()
            onset1 = float(onset1)
            if onset1 - offset > 0:
                r = note.Rest()
                if fixtempo:
                    r.duration.quarterLength = fixtempo
                logdur = -np.log2(onset1 - offset)
                d = int(logdur - mindur)
                if d < 4:
                    r.duration.quarterLength = 1.0 / time_unit / pow(2, d)
                    sf.append(r)

    return sf
