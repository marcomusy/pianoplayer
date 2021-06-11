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
    for o in strm.secondsMap:
        if o['element'].isNote:
            om.append(o)
        elif o['element'].isChord:
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


def reader(sf, beam=0):
    noteseq = []

    if hasattr(sf, 'parts'):
        if len(sf.parts) <= beam:
            return []
        strm = sf.parts[beam].flat.getElementsByClass("GeneralNote")
    elif hasattr(sf, 'elements'):
        if len(sf.elements) == 1 and beam == 1:
            strm = sf[0].flat.getElementsByClass("GeneralNote")
        else:
            if len(sf) <= beam:
                return []
            strm = sf[beam].flat.getElementsByClass("GeneralNote")
    else:
        strm = sf.flat.getElementsByClass("GeneralNote")

    om = strm2map(strm)

    print('Reading beam', beam, 'with', len(strm), 'objects in stream.')

    chordID = 0
    noteID = 0
    last_note = None
    idx = 0
    while idx < len(om):
        om_element = om[idx]
        n, offset, duration = om_element['element'], om_element['offsetSeconds'], om_element['endTimeSeconds']

        if type(n) in [music21.chord.Chord, music21.note.Note]:

            simultaneous_notes = [o for o in om[idx:] if o['offsetSeconds'] == offset]

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
                an.time = n.offset
                an.duration = n.duration.quarterLength
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

                sfasam = 0.05  # sfasa leggermente le note dell'accordo
                chord_notes = []

                for j, cn in enumerate([cns['element'] for cns in simultaneous_notes]):
                    an = INote()
                    an.chordID = chordID
                    an.noteID = noteID
                    an.isChord = True
                    an.pitch = cn.pitch.midi
                    an.name = cn.name
                    an.chordnr = j
                    an.NinChord = len(simultaneous_notes)
                    an.octave = cn.octave
                    an.measure = n.measureNumber
                    an.x = keypos(cn)
                    an.time = n.offset - sfasam * (len(simultaneous_notes) - j - 1)
                    an.duration = n.duration.quarterLength + sfasam * (an.NinChord - 1)
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
    pm_notes = sorted(pm.notes, key=attrgetter('start'))
    pm_onsets = [float(onset.start) for onset in pm_notes]

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
            sfasam = 0.05  # sfasa leggermente le note dell'accordo
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
                an.NinChord = chord_notes
                an.octave = cn.pitch // 2
                an.x = keypos_midi(cn)
                an.time = cn.start - sfasam * jj
                an.duration = cn_duration + sfasam * (jj - 1)
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
        if l.startswith('//'): continue
        _, onset, offset, name, _, _, channel, _ = l.split()
        onset, offset = float(onset), float(offset)
        if beam != int(channel): continue
        if not firstonset:
            firstonset = onset
        if offset - onset < 0.0001: continue
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
    for i in range(n):
        if blines[i].startswith('//'): continue
        _, onset, offset, name, _, _, _, finger = blines[i].split()
        onset, offset = float(onset), float(offset)
        name = name.replace('b', '-')

        chordnotes = [name]
        for j in range(1, 5):
            if i + j < n:
                noteid1, onset1, offset1, name1, _, _, _, finger1 = blines[i + j].split()
                onset1 = float(onset1)
                if onset1 == onset:
                    name1 = name1.replace('b', '-')
                    chordnotes.append(name1)

        if len(chordnotes) > 1:
            an = chord.Chord(chordnotes)
        else:
            an = note.Note(name)
            if '_' not in finger:
                x = Fingering(abs(int(finger)))
                x.style.absoluteY = 20
            an.articulations.append(x)

        if fixtempo:
            an.duration.quarterLength = fixtempo
        else:
            logdur = -np.log2(offset - onset)
            an.duration.quarterLength = 1.0 / time_unit / pow(2, int(logdur - mindur))
        # print('note/chord:', an, an.duration.quarterLength, an.duration.type, 't=',onset)

        sf.append(an)

        # rest up to the next
        if i + 1 < n:
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
