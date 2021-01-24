"""
Created on Thu Nov 26 19:22:20 2015

@author: marco musy
"""
from pianoplayer.utils import keypos

#####################################################
class INote:
    def __init__(self):
        self.note21   = None
        self.name     = None
        self.isChord  = False
        self.isBlack  = False
        self.octave   = 0
        self.x        = 0.0
        self.time     = 0.0
        self.duration = 0.0
        self.fingering= 0
        self.measure  = 0
        self.chordnr  = 0
        self.NinChord = 0
        self.chordID  = 0
        self.noteID   = 0


#####################################################
def reader(sf, beam=0):

    noteseq = []

    if hasattr(sf, 'parts'):
        if len(sf.parts) <= beam:
            return []
        strm = sf.parts[beam].flat
    elif hasattr(sf, 'elements'):
        if len(sf.elements)==1 and beam==1:
            strm = sf[0]
        else:
            if len(sf) <= beam:
                return []
            strm = sf[beam]
    else:
        strm = sf.flat

    print('Reading beam', beam, 'with', len(strm), 'objects in stream.')

    chordID = 0

    for n in strm:

        if n.duration.quarterLength==0 : continue

        if hasattr(n, 'tie'): # address bug https://github.com/marcomusy/pianoplayer/issues/29
            if n.tie and (n.tie.type=='continue' or n.tie.type=='stop'): continue

        if n.isNote:
            if len(noteseq) and n.offset == noteseq[-1].time:
                # print "doppia nota", n.name
                continue
            an        = INote()
            an.noteID += 1
            an.note21 = n
            an.isChord= False
            an.name   = n.name
            an.octave = n.octave
            an.measure= n.measureNumber
            an.x      = keypos(n)
            an.time   = n.offset
            an.duration = n.duration.quarterLength
            an.isBlack= False
            if hasattr(n, 'pitch'):
                pc = n.pitch.pitchClass
            else:
                pc = n.pitchClass
                an.isBlack = False
            if pc in [1, 3, 6, 8, 10]: an.isBlack = True
            if n.lyrics: an.fingering = n.lyric
            noteseq.append(an)

        elif n.isChord:

            if n.tie and (n.tie.type=='continue' or n.tie.type=='stop'): continue
            sfasam = 0.05 # sfasa leggermente le note dell'accordo
            for j, cn in enumerate(n.pitches):
                an = INote()
                an.chordID  = chordID
                an.noteID += 1
                an.isChord = True
                an.chord21 = n
                an.note21  = cn
                an.name    = cn.name
                an.chordnr = j
                an.NinChord = len(n.pitches)
                an.octave  = cn.octave
                an.measure = n.measureNumber
                an.x       = keypos(cn)
                an.time    = n.offset                 -sfasam*j
                an.duration= n.duration.quarterLength +sfasam*(an.NinChord-1)
                if hasattr(cn, 'pitch'):
                    pc = cn.pitch.pitchClass
                else:
                    pc = cn.pitchClass
                if pc in [1, 3, 6, 8, 10]: an.isBlack = True
                else: an.isBlack = False
                noteseq.append(an)

            chordID += 1

    if len(noteseq)<2:
        print("Beam is empty.")
        return []
    return noteseq


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

    #work out note type from distribution of durations
    # triplets are squashed to the closest figure
    durations = []
    firstonset = 0
    blines=[]
    for l in lines:
        if l.startswith('//'): continue
        _, onset, offset, name, _, _, channel, _ = l.split()
        onset, offset = float(onset), float(offset)
        if beam != int(channel): continue
        if not firstonset:
            firstonset = onset
        if offset-onset<0.0001: continue
        durations.append(offset-onset)
        blines.append(l)
    durations = np.array(durations)
    logdurs = -np.log2(durations)
    mindur = np.min(logdurs)
    expos = (logdurs-mindur).astype(int)
    if np.max(expos) > 3:
        mindur = mindur + 1
    #print(durations, '\nexpos=',expos, '\nmindur=', mindur)

    sf = stream.Part()
    sf.id = beam

    # first rest
    if not fixtempo and firstonset:
        r = note.Rest()
        logdur = -np.log2(firstonset)
        r.duration.quarterLength = 1.0/time_unit/pow(2, int(logdur-mindur))
        sf.append(r)

    n = len(blines)
    for i in range(n):
        if blines[i].startswith('//'): continue
        _, onset, offset, name, _, _, _, finger = blines[i].split()
        onset, offset = float(onset), float(offset)
        name = name.replace('b', '-')

        chordnotes = [name]
        for j in range(1, 5):
            if i+j<n:
                noteid1, onset1, offset1, name1, _, _, _, finger1 = blines[i+j].split()
                onset1 = float(onset1)
                if onset1 == onset:
                    name1 = name1.replace('b', '-')
                    chordnotes.append(name1)

        if len(chordnotes)>1:
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
            an.duration.quarterLength = 1.0/time_unit/pow(2, int(logdur-mindur))
        #print('note/chord:', an, an.duration.quarterLength, an.duration.type, 't=',onset)

        sf.append(an)

        # rest up to the next
        if i+1<n:
            _, onset1, _, _, _, _, _, _ = blines[i+1].split()
            onset1 = float(onset1)
            if onset1 - offset > 0:
                r = note.Rest()
                if fixtempo:
                    r.duration.quarterLength = fixtempo
                logdur = -np.log2(onset1 - offset)
                d = int(logdur-mindur)
                if d<4:
                    r.duration.quarterLength = 1.0/time_unit/pow(2, d)
                    sf.append(r)

    return sf








































