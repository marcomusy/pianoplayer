"""
Created on Thu Nov 26 19:22:20 2015

@author: marco musy
"""
import music21
from music21.articulations import Fingering

from pianoplayer.utils import keypos, keypos_midi
from operator import attrgetter


#####################################################
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
        if type(art) == Fingering:
            fingers.append(art.fingerNumber)
    finger = 0
    if len(fingers) > j:
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


def reader(sf, beam=0):
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
                if n.lyrics:
                    an.fingering = n.lyric

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
    pm_notes = sorted(pm.notes, key=lambda a: (a.start, a.pitch))

    print('Reading beam', beam, 'with', len(pm_notes), 'objects in stream.')

    chordID = 0
    noteID = 0
    last_note = None


    ii = 0
    while ii < len(pm_notes):
        n = pm_notes[ii]
        n_duration = n.end - n.start
        onset_n = n.start
        simultaneous = list([float(no.start) for no in pm_notes if no.start == onset_n])
        if len(simultaneous) == 1:
            if n_duration == 0: continue
            an = INote()
            an.noteID += noteID
            an.chordID = chordID
            an.pitch = n.pitch
            an.isChord = False
            an.octave = n.pitch // 12
            an.x = keypos_midi(n)
            an.time = n.start
            an.duration = n_duration
            an.isBlack = False
            pc = n.pitch % 12
            if pc in [1, 3, 6, 8, 10]: an.isBlack = True
            an.previous_note = last_note
            noteseq.append(an)
            ii += 1
            chordID += 1
            noteID += 1
            last_note = an
        else:
            if n_duration == 0: continue
            sfasam = 0.00  # sfasa leggermente le note dell'accordo
            chord_notes = []

            for jj in range(len(simultaneous)):
                cn = pm_notes[ii]
                cn_duration = cn.end - cn.start
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
                an.time = cn.start + sfasam * jj
                an.duration = cn_duration
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


def reader_PIG(fname, beam=0):
    """
    Convert a PIG text file to a noteseq of type INote.

    time_unit must be multiple of 2.
    beam = 0, right hand
    beam = 1, left hand.
    """
    # read

    return []

def is_midi(value):
  try:
    int(value)
    return True
  except ValueError:
    return False


def PIG2Stream(fname, beam=0, time_unit=.5, fixtempo=0):
    """
    Convert a PIG text file to a music21 Stream object.
    time_unit must be multiple of 2.
    beam = 0, right hand
    beam = 1, left hand.
    """
    from music21 import stream, note, chord
    from music21.articulations import Fingering
    import numpy as np

    f = open(fname, "r")
    lines = f.readlines()
    f.close()

    # work out note type from distribution of durations
    # triplets are squashed to the closest figure
    durations = []
    firstonset = 0
    blines = []
    for l in lines:
        if l.startswith('//'):
            continue
        pig_line = l.split()
        onset = pig_line[1]
        offset = pig_line[2]
        name = pig_line[3]
        channel = pig_line[6]

        onset, offset = float(onset), float(offset)
        if beam != int(channel):
            continue
        if not firstonset:
            firstonset = onset
        if offset - onset < 0.0001:
            continue
        durations.append(offset - onset)
        blines.append(l)

    durations = np.array(durations)
    logdurs = -np.log2(durations)

    mindur = np.min(logdurs)
    expos = (logdurs - mindur).astype(int)
    if np.max(expos) > 3:
        mindur = mindur + 1
    # print(durations, '\nexpos=',expos, '\nmindur=', mindur)

    sf = stream.Part()
    sf.id = beam

    # first rest
    if not fixtempo and firstonset:
        r = note.Rest()
        logdur = -np.log2(firstonset)
        r.duration.quarterLength = 1.0 / time_unit / pow(2, int(logdur - mindur))
        sf.append(r)

    n = len(blines)
    i = 0
    while i < n:
        if blines[i].startswith('//'):
            i += 1
            continue

        blines_i = blines[i].split()
        onset = blines_i[1]
        offset = blines_i[2]
        name = blines_i[3]
        finger = blines_i[7]
        onset, offset = float(onset), float(offset)
        name = name.replace('b', '-')

        chordnotes = [name]
        chordfingers = [finger]
        for j in range(1, 5):
            if i + j < n:
                blines_i_j = blines[i + j].split()
                noteid1 = blines_i_j[0]
                onset1 = blines_i_j[1]
                offset1 = blines_i_j[2]
                name1 = blines_i_j[3]
                finger1 = blines_i_j[7]
                onset1 = float(onset1)
                if onset1 == onset:
                    name1 = name1.replace('b', '-')
                    chordnotes.append(name1)
                    chordfingers.append(finger1)
                    i += 1

        if len(chordnotes) > 1:
            if is_midi(chordnotes[0]):
                an = chord.Chord([int(c) for c in chordnotes])
                for finger in chordfingers:
                    f = music21.articulations.Fingering(finger)
                    an.articulations = [f] + an.articulations
            else:
                an = chord.Chord(chordnotes)
        else:
            if is_midi(name):
                an = note.Note(int(name))
            else:
                an = note.Note(name)
            if '_' not in finger:
                x = Fingering(abs(int(finger)))
                x.style.absoluteY = 20
            else:  # TODO in the future handle better the note's changes
                x = Fingering(abs(int(finger.split('_')[0])))
            an.articulations.append(x)
            x.style.absoluteY = 20

        if fixtempo:
            an.duration.quarterLength = fixtempo
        else:
            logdur = -np.log2(offset - onset)
            an.duration.quarterLength = 1.0 / time_unit / pow(2, int(logdur - mindur))
        # print('note/chord:', an, an.duration.quarterLength, an.duration.type, 't=',onset)

        sf.append(an)
        # rest up to the next
        if i + 1 < n:
            onset1 = blines[i + 1].split()[1]
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
        i += 1
    return sf
