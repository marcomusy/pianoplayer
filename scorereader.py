#
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 19:22:20 2015

@author: marco musy
"""
from __future__ import division, print_function

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
def keypos(n): #position of notes on keyboard
    step = 0.0
    keybsize = 16.5 #cm
    k = keybsize/7.0
    if   n.name == 'C'  : step = k *0.5
    elif n.name == 'D'  : step = k *1.5
    elif n.name == 'E'  : step = k *2.5
    elif n.name == 'F'  : step = k *3.5
    elif n.name == 'G'  : step = k *4.5
    elif n.name == 'A'  : step = k *5.5
    elif n.name == 'B'  : step = k *6.5
    elif n.name == 'B#' : step = k *0.5
    elif n.name == 'C#' : step = k
    elif n.name == 'D#' : step = k *2.
    elif n.name == 'E#' : step = k *3.5
    elif n.name == 'F#' : step = k *4.
    elif n.name == 'G#' : step = k *5.
    elif n.name == 'A#' : step = k *6.
    elif n.name == 'C-' : step = k *6.5
    elif n.name == 'D-' : step = k 
    elif n.name == 'E-' : step = k *2.
    elif n.name == 'F-' : step = k *2.5
    elif n.name == 'G-' : step = k *4.
    elif n.name == 'A-' : step = k *5.
    elif n.name == 'B-' : step = k *6.
    else: 
        print("ERROR note not found", n.name)
    return keybsize * n.octave + step
    

#####################################################
def reader(sf, beam=0):
    
    try:
        strm = sf.parts[beam].flat
    except AttributeError: 
        strm = sf.flat
    except IndexError:
        print('Beam nr.', beam, 'not found. Skip.')
        return []
    print('Reading beam', beam, 'made of', len(strm), 'objects...')

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
            try:
                pc = n.pitch.pitchClass
            except AttributeError:
                pc = n.pitchClass
                an.isBlack = False
            if pc in [1, 3, 6, 8, 10]: an.isBlack = True
            if n.hasLyrics(): an.fingering = n.lyric
            noteseq.append(an)

        if n.isChord:
            if n.tie and (n.tie.type=='continue' or n.tie.type=='stop'): continue
            sfasam = 0.01 # sfasa leggermente le note dell'accordo
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
                try:
                    pc = cn.pitch.pitchClass
                except AttributeError:
                    pc = cn.pitchClass
                if pc in [1, 3, 6, 8, 10]: an.isBlack = True
                else: an.isBlack = False
                noteseq.append(an)

    print("Total nr of notes read:", len(noteseq))
    if len(noteseq)<2: 
        print("Beam is empty.")
        quit()    
    
    return noteseq

