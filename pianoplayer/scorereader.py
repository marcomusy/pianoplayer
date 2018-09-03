#
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 19:22:20 2015

@author: marco musy
"""
from __future__ import division, print_function
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
    

#####################################################
def reader(sf, beam=0):
    
    try:
        strm = sf.parts[beam].flat
    except AttributeError: 
        strm = sf.flat
    except IndexError:
        print('Beam nr.', beam, 'not found. Skip.')
        return []
    print('Reading beam', beam, 'with', len(strm), 'objects in stream.')

    noteseq = []

    for n in strm:

        if n.duration.quarterLength==0 : continue
        
        if n.tie and (n.tie.type=='continue' or n.tie.type=='stop'): continue

        if n.isNote:
            if len(noteseq) and n.offset == noteseq[-1].time:
                # print "doppia nota", n.name
                continue
            an        = INote()
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

        if n.isChord:
            if n.tie and (n.tie.type=='continue' or n.tie.type=='stop'): continue
            sfasam = 0.005 # sfasa leggermente le note dell'accordo
            for j, cn in enumerate(n.pitches):
                an = INote()
                an.isChord = True
                an.chord21 = n
                an.note21  = cn
                an.name    = cn.name
                an.chordnr = j
                an.octave  = cn.octave
                an.measure = n.measureNumber
                an.x       = keypos(cn)
                an.time    = n.offset                 +sfasam*j
                an.duration= n.duration.quarterLength -sfasam*(len(n.pitches)-1)
                if hasattr(cn, 'pitch'):
                    pc = cn.pitch.pitchClass
                else:
                    pc = cn.pitchClass
                if pc in [1, 3, 6, 8, 10]: an.isBlack = True
                else: an.isBlack = False
                noteseq.append(an)

    if len(noteseq)<2: 
        print("Beam is empty. Exit.")
        quit()    
    
    return noteseq

