"""
Created on Thu Nov 26 19:22:20 2015

@author: marco musy
"""
import csv
from dataclasses import dataclass

import music21
from music21.articulations import Fingering

from pianoplayer.utils import keypos, keypos_midi
from operator import attrgetter


####################### ##############################
class INote:
    def __init__(self):
        self.name = None
        self.isChord = False
        self.previous_note = None
        self.isBlack = False
        self.chordNotes = None
        self.pitch = 0
        self.octave = 0
        self.x = 0.0
        self.time = 0.0
        self.duration = 0.0
        self.fingering = 0
        self.measure = 0
        self.chordnr = 0
        self.NinChord = 0
        self.chordID = 0
        self.noteID = 0


#####################################################
def get_finger_music21(n, j=0):
    fingers = []
    for art in n.articulations:
        if type(art) == Fingering and art.fingerNumber == ['1', '2', '3', '4', '5']:
            fingers.append(art.fingerNumber)
    finger = 0
    if len(fingers) > j and fingers[j] == ['1', '2', '3', '4', '5']:
        finger = fingers[j]
    return finger


def strm2map(strm):
    converted = []
    om = []
    for o in strm.flat.secondsMap:
        if o['element'].isClassOrSubclass(('Note',)):
            om.append(o)
        elif o['element'].isClassOrSubclass(('Chord',)):
            om_chord = [{'element': oc,
                         'offsetSeconds': o['offsetSeconds'],
                         'endTimeSeconds': o['endTimeSeconds'],
                         'chord': o['element']} for oc in sorted(o['element'].notes, key=lambda a: a.pitch)]
            om.extend(om_chord)
    om_filtered = []
    for o in om:
        offset = o['offsetSeconds']
        duration = o['endTimeSeconds']
        pitch = o['element'].pitch
        simultaneous_notes = [o2 for o2 in om if o2['offsetSeconds'] == offset and o2['element'].pitch.midi == pitch.midi]
        max_duration = max([float(x['endTimeSeconds']) for x in simultaneous_notes])
        if len(simultaneous_notes) > 1 and duration < max_duration and str(offset) + ':' + str(pitch) not in converted:
            continue
        else:
            converted.append(str(offset) + ':' + str(pitch))

        if not (o['element'].tie and (o['element'].tie.type == 'continue' or o['element'].tie.type == 'stop')) and \
                not ((hasattr(o['element'], 'tie') and o['element'].tie
                      and (o['element'].tie.type == 'continue' or o['element'].tie.type == 'stop'))) and \
                not (o['element'].duration.quarterLength == 0):
            om_filtered.append(o)

    return sorted(om_filtered, key=lambda a: (a['offsetSeconds'], a['element'].pitch))


def find_parent(el, class_type):
    """
    Returns the first parent of el of type class_type. Both el and class_type must be valid music21 objects
    If class_type does not exist in the parent chain of el, the outermost object will be returned
    """
    temp = el
    while not isinstance(temp, class_type) and temp.activeSite:
        temp = temp.activeSite
    return temp


def propagate_metronome_mark_to_parts(m21_stream):
    """
    Inserts the Metronome Marks in every part so that .seconds attribute can work correctly
    """
    metronome_marks = {}
    for mm in m21_stream.recurse().getElementsByClass(music21.tempo.MetronomeMark):
        measure = find_parent(mm, music21.stream.Measure)
        metronome_marks[measure.number] = mm

    for measure_number, mm in metronome_marks.items():
        measure_stream = m21_stream.measures(measure_number, measure_number)
        for measure in measure_stream.recurse().getElementsByClass(music21.stream.Measure):
            if mm not in measure:
                measure.insert(0, mm)
    return m21_stream


def sf2strm(sf, beam):
    sf = propagate_metronome_mark_to_parts(sf)
    if hasattr(sf, 'parts'):
        if len(sf.parts) < beam:
            return []
        elif len(sf.parts) == 1 and beam == 1:
            strm = sf.parts
        else:
            strm = sf.parts[beam]
    elif hasattr(sf, 'elements'):
        if len(sf.elements) == 1 and beam == 1:
            strm = sf[0]
        else:
            if len(sf) <= beam:
                return []
            strm = sf[beam]
    else:
        strm = sf
    return strm


def reader(sf, beam=0, fingers=True):
    noteseq = []

    strm = sf2strm(sf, beam)

    om = strm2map(strm)

    print('Reading beam', beam, 'with', len(strm), 'objects in stream.')

    chordID = 0
    noteID = 0
    last_note = None
    idx = 0
    while idx < len(om):
        om_element = om[idx]
        n, onset, end_time = om_element['element'], om_element['offsetSeconds'], om_element['endTimeSeconds']
        duration = end_time - onset
        if type(n) in [music21.chord.Chord, music21.note.Note]:

            simultaneous_notes = [o for o in om[idx:] if o['offsetSeconds'] == onset]

            if len(simultaneous_notes) == 1:

                an = INote()
                an.noteID = noteID
                an.chordID = chordID
                an.isChord = False
                an.name = n.name
                an.octave = n.octave
                an.measure = n.measureNumber
                an.x = keypos(n)
                an.pitch = n.pitch.midi
                an.time = onset
                an.duration = duration
                an.isBlack = False
                pc = n.pitch.pitchClass
                an.isBlack = False
                if pc in [1, 3, 6, 8, 10]:
                    an.isBlack = True
                an.fingering = 0
                if fingers:
                    if n.lyrics:
                        an.fingering = n.lyric
                    else:
                        an.fingering = get_finger_music21(n)
                an.previous_note = last_note
                noteseq.append(an)
                noteID += 1
                last_note = an
                chordID += 1
                idx += 1

            elif len(simultaneous_notes) > 1:

                sfasam = 0.00  # sfasa leggermente le note dell'accordo
                chord_notes = []

                for j, (cn, onset, duration) in enumerate([(cns['element'], cns['offsetSeconds'], cns['endTimeSeconds']) for cns in simultaneous_notes]):
                    an = INote()
                    an.chordID = chordID
                    an.noteID = noteID
                    an.isChord = True
                    an.pitch = cn.pitch.midi
                    an.name = cn.name
                    an.chordnr = j
                    an.NinChord = len(simultaneous_notes)
                    an.octave = cn.octave
                    an.measure = cn.measureNumber
                    an.x = keypos(cn)
                    an.time = onset - sfasam * j
                    an.duration = duration
                    if hasattr(cn, 'pitch'):
                        pc = cn.pitch.pitchClass
                    else:
                        pc = cn.pitchClass
                    if pc in [1, 3, 6, 8, 10]:
                        an.isBlack = True
                    else:
                        an.isBlack = False

                    an.fingering = 0
                    if fingers:
                        an.fingering = get_finger_music21(n, j)

                    noteID += 1
                    an.previous_note = last_note
                    chord_notes.append(an)

                for an in chord_notes:
                    an.chordNotes = chord_notes
                    noteseq.append(an)

                last_note = chord_notes[-1] if chord_notes[0].time != 0 else None
                chordID += 1
                idx += len(simultaneous_notes)
        else:
            idx += 1

    if len(noteseq) < 2:
        print("Beam is empty.")
        return []
    return noteseq


def reader_pretty_midi(pm, beam=0):

    noteseq = []
    pm_notes = sorted(pm.notes, key=attrgetter('start'))
    pm_onsets = [onset.start for onset in pm_notes]

    print('Reading beam', beam, 'with', len(pm_notes), 'objects in stream.')

    chordID = 0

    ii = 0
    while ii < len(pm_notes):
        n = pm_notes[ii]
        n_duration = n.end - n.start
        chord_notes = pm_onsets.count(n.start)
        if chord_notes != 1:
            if n_duration == 0: continue
            an        = INote()
            an.noteID += 1
            an.note21 = n
            an.pitch = n.pitch
            an.isChord= False
            an.octave = n.pitch // 12
            an.x      = keypos_midi(n)
            an.time   = n.start
            an.duration = n_duration
            an.isBlack= False
            pc = n.pitch % 12
            if pc in [1, 3, 6, 8, 10]: an.isBlack = True
            noteseq.append(an)
            ii += 1

        else:
            if n_duration == 0: continue
            sfasam = 0.05 # sfasa leggermente le note dell'accordo

            for jj in range(chord_notes):
                cn = pm_notes[ii]
                cn_duration = cn.end - cn.start
                an = INote()
                an.chordID = chordID
                an.noteID += 1
                an.isChord = True
                an.chord21 = n
                an.pitch   = cn.pitch
                an.note21  = cn
                an.chordnr = jj
                an.NinChord = chord_notes
                an.octave  = cn.pitch // 2
                an.x       = keypos_midi(cn)
                an.time    = cn.start-sfasam*jj
                an.duration = cn_duration + sfasam * (jj - 1)
                pc = n.pitch % 12
                if pc in [1, 3, 6, 8, 10]: an.isBlack = True
                else: an.isBlack = False
                noteseq.append(an)
                ii += 1

            chordID += 1

    if len(noteseq)<2:
        print("Beam is empty.")
        return []
    return noteseq




KEY_TO_SEMITONE = {'c': 0, 'c#': 1, 'db': 1, 'd-': 1, 'c##': 2, 'd': 2, 'e--': 2, 'd#': 3, 'eb': 3, 'e-': 3, 'd##': 4,
                   'e': 4, 'f-': 4, 'e#': 5, 'f': 5, 'g--': 5, 'e##': 6, 'f#': 6, 'gb': 6, 'g-': 6, 'f##': 7, 'g': 7,
                   'a--': 7, 'g#': 8, 'ab': 8, 'a-': 8, 'g##': 9, 'a': 9, 'b--': 9, 'a#': 10, 'bb': 10, 'b-': 10,
                   'a##': 11, 'b': 11, 'b#': 12, 'c-': -1, 'x': None}


class note:
    idx: int
    onset: float
    offset: float
    pitch: int
    v1: float
    v2: float
    channel: int
    finger: int

    def __init__(self, n):
        if len(n) == 9:
            idx, onset, offset, pitch, v1, v2, channel, finger, _ = n
        elif len(n) == 8:
            idx, onset, offset, pitch, v1, v2, channel, finger = n

        self.idx = int(idx)
        self.onset = float(onset)
        self.offset = float(offset)
        self.pitch = int(pitch)
        self.channel = int(channel)
        self.finger = abs(int(finger.split('_')[0]))


def reader_PIG(filename, beam=0, fingers=True):
    """
        Convert a PIG text file to a noteseq of type INote.

        time_unit must be multiple of 2.
        beam = 0, right hand
        beam = 1, left hand.
    """
    noteseq = []

    with open(filename, mode='r') as csvfile:
        r = list(csv.reader(csvfile, delimiter='\t'))

    if len(r[0]) == 1:
        r = r[1:]

    for idx in range(len(r)):
        r[idx][3] = KEY_TO_SEMITONE[r[idx][3][:-1].lower()] + int(r[idx][3][-1]) * 12

    pm_notes = [row for row in r if row[6] == str(beam)]

    print('Reading beam', beam, 'with', len(pm_notes), 'objects in stream.')

    chordID = 0
    noteID = 0
    last_note = None

    ii = 0
    while ii < len(pm_notes):
        n = note(pm_notes[ii])
        n_duration = n.offset - n.onset
        onset_n = n.onset
        simultaneous = list([note(no).onset for no in pm_notes if note(no).onset == onset_n])
        if len(simultaneous) == 1:
            if n_duration == 0:
                ii += 1
                continue
            an = INote()
            an.noteID += noteID
            an.chordID = chordID
            an.pitch = n.pitch
            an.isChord = False
            an.octave = n.pitch // 12
            an.x = keypos_midi(n)
            an.time = n.onset
            an.duration = n_duration
            an.isBlack = False
            if fingers:
                an.fingering = n.finger
            pc = n.pitch % 12
            if pc in [1, 3, 6, 8, 10]: an.isBlack = True
            an.previous_note = last_note
            noteseq.append(an)
            ii += 1
            chordID += 1
            noteID += 1
            last_note = an
        else:
            if n_duration == 0:
                ii += 1
                continue
            sfasam = 0.00  # sfasa leggermente le note dell'accordo
            chord_notes = []

            for jj in range(len(simultaneous)):
                cn = note(pm_notes[ii])
                cn_duration = cn.offset - cn.onset
                an = INote()
                an.chordID = chordID
                an.noteID = noteID
                an.isChord = True
                an.chord21 = n
                an.pitch = cn.pitch
                an.note21 = cn
                an.chordnr = jj
                an.NinChord = len(simultaneous)
                an.octave = cn.pitch // 2
                an.x = keypos_midi(cn)
                an.time = cn.onset + sfasam * jj
                an.duration = cn_duration
                if fingers:
                    an.fingering = cn.finger
                pc = n.pitch % 12
                if pc in [1, 3, 6, 8, 10]:
                    an.isBlack = True
                else:
                    an.isBlack = False
                an.previous_note = last_note
                noteID += 1
                ii += 1
                chord_notes.append(an)

            for an in chord_notes:
                an.chordNotes = chord_notes
                noteseq.append(an)

            last_note = chord_notes[-1] if chord_notes[0].time != 0 else None
            chordID += 1

    if len(noteseq) < 2:
        print("Beam is empty.")
        return []
    return noteseq


def is_midi(value):
  try:
    int(value)
    return True
  except ValueError:
    return False


def PIG2Stream(filename, beam, fingers=True):
    sc = music21.stream.Part()

    with open(filename, mode='r') as csvfile:
        r = list(csv.reader(csvfile, delimiter='\t'))

    if len(r[0]) == 1:
        r = r[1:]

    is_int = True
    try:
        check = int(r[0][3])
    except:
        is_int = False

    if not is_int:
        for idx in range(len(r)):
            r[idx][3] = KEY_TO_SEMITONE[r[idx][3][:-1].lower()] + int(r[idx][3][-1]) * 12

    pm_notes = [row for row in r if row[6] == str(beam)]

    print('Reading beam', beam, 'with', len(pm_notes), 'objects in stream.')

    ii = 0
    while ii < len(pm_notes):
        n = note(pm_notes[ii])
        simultaneous = list([note(no).onset for no in pm_notes if note(no).onset == n.onset])
        if len(simultaneous) == 1:
            note1 = music21.note.Note(n.pitch + 12)
            note1.duration.type = 'quarter'
            if fingers:
                note1.articulations = [music21.articulations.Fingering(n.finger)]
            sc.append(note1)
            ii += 1
        else:
            ch = music21.chord.Chord([note(pm_notes[ii + jj]).pitch + 12 for jj in range(len(simultaneous))])
            ch.duration.type = 'quarter'
            if fingers:
                ch.articulations = [music21.articulations.Fingering(note(pm_notes[ii + jj]).finger)
                                    for jj in range(len(simultaneous))]
            sc.append(ch)
            ii += len(simultaneous)
    return sc




