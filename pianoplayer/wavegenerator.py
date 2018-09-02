from __future__ import division, print_function

import numpy as np

has_simpleaudio=True
try:
    import simpleaudio
except:
    print("Cannot find simpleaudio package. Not installed?")
    print('Try:\n(sudo) pip install --upgrade simpleaudio')
    has_simpleaudio=False



def soundof(notes, duration, volume=1):

    sample_rate = 44100

    # calculate note frequencies
    intensities = []
    for n in notes:
        # freq = frequency(n)
        n21 = n.note21
        if hasattr(n21, 'pitch'):
            freq = n21.pitch.frequency
        else:
            freq = n21.frequency
    
        # get timesteps for each sample, duration is note duration in seconds
        t = np.linspace(0, duration, duration * sample_rate, False)

        # generate sine wave notes
        intensity = np.sin((freq*2*np.pi) * t )
        intensities.append(intensity)
    
    for i in range(1, len(intensities)):
        intensity = intensity + intensities[i]

    if not 0<volume<=1: volume=1

    audio = intensity/(len(intensities)/float(volume))

    # concatenate notes
    # audio = np.hstack((intensity1, intensity2))
    # normalize to 16-bit range
    audio *= 32767 / np.max(np.abs(audio))
    # convert to 16-bit data
    audio = audio.astype(np.int16)

    # start playback
    play_obj = simpleaudio.play_buffer(audio, 1, 2, sample_rate)

    # wait for playback to finish before exiting
    play_obj.wait_done()

    
def pitch(freq):
    from math import log2, pow

    A4 = 440
    C0 = A4*pow(2, -4.75)
    name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    h = round(12*log2(freq/C0))
    octave = h // 12
    n = h % 12
    return name[n] + str(octave)
    

####################################################### 
from music21.midi.realtime import StreamPlayer
from music21.stream import Stream

def playSound(n, speedfactor):
    if has_simpleaudio:
        soundof([n], n.duration/speedfactor)
    else:
        try:
            s = Stream() 
            if n.isChord: n = n.chord21
            else: s.append(n.note21)
            sp = StreamPlayer(s)
            sp.play()            
            # if n.isChord: 
            #     s.append(n)
            # else: 
            #     nn = Note(n.nameWithOctave)
            #     s.append(nn)
            # sp = StreamPlayer(s)
            # sp.play()        
        except:
            print('Unable to play sounds, add -z option')
        return
    