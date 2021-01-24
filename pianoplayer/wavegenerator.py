import numpy as np
import music21


try:
    import simpleaudio
    has_simpleaudio=True
except:
    print("Cannot find simpleaudio package. Not installed?")
    print('Try:\n(sudo) pip install --upgrade simpleaudio')
    has_simpleaudio=False



#####################################################################
def soundof(notes, duration=1, volume=0.75, fading=750, wait=True):
    """
    Play a group of notes (chord) for the prescribed duration.

    Parameters
    ----------
    notes : list
        list of notes to be played (as strings or music21.Note).
    duration : float
        duration in seconds.
    volume : float, optional
        Output volume. The default is 0.75.
    fading : int, optional
        linear ramp up and down of volume. The default is 750.
    wait : bool, optional
        wait for the sound to end before continuing
    """
    if not has_simpleaudio:
        return

    sample_rate = 44100
    fade_in  = np.arange(0, 1,  1/fading)
    fade_out = np.arange(1, 0, -1/fading)
    timepoints = int(duration*sample_rate)

    intensity = np.zeros(timepoints)
    for n in notes:
        if isinstance(n, (int,float)): # user gives n in Hz
            freq = n
        else:
            if isinstance(n, str):
                n = music21.note.Note(n)
            if isinstance(n, music21.note.Note):
                n21 = n
            else:
                n21 = n.note21
            if hasattr(n21, 'pitch'):
                freq = n21.pitch.frequency
            else:
                freq = n21.frequency

        # get timesteps for each sample, duration is note duration in seconds
        t = np.linspace(0, duration, timepoints, False)

        # generate sine wave notes
        note_intensity = np.sin(freq * 2*np.pi * t )
        if len(intensity) > fading:
            note_intensity[:fading]  *= fade_in
            note_intensity[-fading:] *= fade_out
        intensity += note_intensity

    # normalize to 16-bit range
    audio = intensity * (32767 / np.max(np.abs(intensity)) * float(volume))

    # start playback
    play_obj = simpleaudio.play_buffer(audio.astype(np.int16), 1, 2, sample_rate)

    # wait for playback to finish before exiting
    if wait:
        play_obj.wait_done()
    return play_obj


#######################################################
def playSound(n, speedfactor=1.0, wait=True):
    """Play a single chord and or a sequence of notes and chords"""
    if has_simpleaudio:
        soundof([n], n.duration/speedfactor, wait)
    else:
        try:
            s = music21.stream.Stream()
            if n.isChord:
                n = n.chord21
            else:
                s.append(n.note21)
            sp = music21.midi.realtime.StreamPlayer(s)
            sp.play()
        except:
            print('Unable to play sounds, add -z option')
            print('pygame not installed?')
        return

