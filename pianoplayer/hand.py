# -------------------------------------------------------------------------------
# Name:         PianoPlayer
# Purpose:      Find optimal fingering for piano scores
# Author:       Marco Musy
# -------------------------------------------------------------------------------


import pianoplayer.utils as utils


#####################################################
class Hand:
    def __init__(self, noteseq, side="right", size='M'):

        self.LR = side
        self.hf = utils.handSizeFactor(size)
        # fingers pos at rest first is dummy, (cm), asymmetry helps with scales
        self.frest = [None, -7.0 * self.hf, -2.8 * self.hf, 0.0 * self.hf, 2.8 * self.hf, 5.6 * self.hf]
        self.weights = [None, 1.1, 1.0, 1.1, 0.9, 0.8]  # finger relative strength
        self.bfactor = [None, 0.3, 1.0, 1.1, 0.8, 0.7]  # hit of black key bias
        self.noteseq = noteseq
        self.fingerseq = []
        self.depth = 9
        self.autodepth = True
        self.verbose = True
        self.lyrics = False  # show fingering numbers as lyrics in musescore
        self.size = size

        print('Your hand span set to size-' + size, 'which is', 21 * self.hf, 'cm')
        print('(max relaxed distance between thumb and pinkie)')
        print('frest: ' + str(self.frest))
        self.cfps = list(self.frest)  # hold current finger positions
        self.cost = -1

    #####################################################

    def set_fingers_positions(self, fings, notes, i):
        fi = fings[i]
        ni = notes[i]
        ifx = self.frest[fi]
        if ifx is not None:
            for j in (1, 2, 3, 4, 5):
                jfx = self.frest[j]
                self.cfps[j] = (jfx - ifx) + ni.x

    #####################################################

    def ave_velocity(self, fingering, notes):
        ###calculate v for playing for notes in a given fingering combination

        self.set_fingers_positions(fingering, notes, 0)  # init fingers position
        # if fingering[0] == 1 and fingering[1] == 2 and notes[0].pitch == 76:
        #     print()
        vmean = 0.
        for i in range(1, self.depth):
            nb = notes[i]
            fb = fingering[i]
            dx = abs(nb.x - self.cfps[fb])  # space travelled by finger fb
            dt = abs(nb.time - nb.previous_note.time if nb.previous_note is not None else 0) + 0.1  # available time +smoothing term 0.1s
            v = dx / dt  # velocity
            if nb.isBlack:  # penalty (by increasing speed)
                v /= self.weights[fb] * self.bfactor[fb]
            else:
                v /= self.weights[fb]
            vmean += v
            self.set_fingers_positions(fingering, notes, i)  # update all fingers

        return vmean / (self.depth - 1)

        # ---------------------------------------------------------

    # NOT OPTIMIZED
    # def _skip(self, fa, fb, na, nb, level):
    #     ### two-consecutive-notes movement, skipping rules ###
    #     # fa is fingering for note na, level is passed only for debugging
    #
    #     xba = nb.x - na.x  # physical distance btw the second to first note, in cm
    #
    #     if not na.isChord and not nb.isChord:  # neither of the 2 notes live in a chord
    #         if fa == fb and xba and na.duration < 4:
    #             return True  # play different notes w/ same finger, skip
    #         if fa > 1:  # if a is not thumb
    #             if fb > 1 and (fb - fa) * xba < 0: return True  # non-thumb fingers are crossings, skip
    #             if fb == 1 and nb.isBlack and xba > 0: return True  # crossing thumb goes to black, skip
    #         else:  # a is played by thumb:
    #             # skip if  a is black  and  b is behind a  and  fb not thumb  and na.duration<2:
    #             if na.isBlack and xba < 0 and fb > 1 and na.duration < 2: return True
    #
    #     elif na.isChord and nb.isChord and na.chordID == nb.chordID:
    #         # na and nb are notes in the same chord
    #         if fa == fb: return True  # play different chord notes w/ same finger, skip
    #         if fa < fb and self.LR == 'left': return True
    #         if fa > fb and self.LR == 'right': return True
    #         axba = abs(xba) * self.hf / 0.8
    #         # max normalized distance in cm btw 2 consecutive fingers
    #         if axba > 5 and (fa == 3 and fb == 4 or fa == 4 and fb == 3): return True
    #         if axba > 5 and (fa == 4 and fb == 5 or fa == 5 and fb == 4): return True
    #         if axba > 6 and (fa == 2 and fb == 3 or fa == 3 and fb == 2): return True
    #         if axba > 7 and (fa == 2 and fb == 4 or fa == 4 and fb == 2): return True
    #         if axba > 8 and (fa == 3 and fb == 5 or fa == 5 and fb == 3): return True
    #         if axba > 11 and (fa == 2 and fb == 5 or fa == 5 and fb == 2): return True
    #         if axba > 12 and (fa == 1 and fb == 2 or fa == 2 and fb == 1): return True
    #         if axba > 14 and (fa == 1 and fb == 3 or fa == 3 and fb == 1): return True
    #         if axba > 16 and (fa == 1 and fb == 4 or fa == 4 and fb == 1): return True
    #
    #     return False
    def _skip(self, past_chord, current_chord, fa, fb, na, nb):
        # fa is fingering for note na, level is passed only for debugging
        skipped = False
        xba = abs(nb.x - na.x)  # physical distance btw the second to first note, in cm
        if self.LR == 'right':
            crossing = (na.pitch < nb.pitch and fa > fb) or (na.pitch > nb.pitch and fa < fb)
        else:  # left
            crossing = (na.pitch > nb.pitch and fa > fb) or (na.pitch < nb.pitch and fa < fb)

        # handle blocks
        if self.LR == 'right' and nb.isChord:
            if nb.chordnr == 0 and nb.NinChord == 2 and fb == 5:
                skipped = True
            elif nb.NinChord == 3 and fb > nb.chordnr + 3:
                skipped = True
            elif nb.NinChord == 4 and fb > nb.chordnr + 2:
                skipped = True
            elif nb.NinChord == 5 and fb != nb.chordnr + 1:
                skipped = True

        if self.LR == 'left' and nb.isChord:
            if nb.chordnr == 0 and nb.NinChord == 2 and fb == 1:
                skipped = True
            elif nb.NinChord == 3 and fb + nb.chordnr < 3:
                skipped = True
            elif nb.NinChord == 4 and fb + nb.chordnr < 4:
                skipped = True
            elif nb.NinChord == 5 and fb + nb.chordnr != 5:
                skipped = True

        if not skipped:
            if not na.isChord and not nb.isChord:  # neither of the 2 notes live in a chord
                if fa == fb and xba and na.duration < 4:
                    skipped = True  # play different notes w/ same finger, skip
                elif fa > 1:  # if a is not thumb
                    if fb > 1 and crossing:
                        skipped = True  # non-thumb fingers are crossings, skip
                    elif fb == 1 and nb.isBlack and crossing:
                        skipped = True  # crossing thumb goes to black, skip
                else:  # a is played by thumb:
                    # skip if  a is black  and  b is behind a and fb not thumb and na.duration<2:
                    if na.isBlack and xba < 0 and fb > 1 and na.duration < 2:
                        skipped = True
                    elif crossing and nb == 5:
                        skipped = True
            elif na.isChord and nb.isChord and na.chordID == nb.chordID:
                # if na.noteID == 5 and fa == 4 and fb == 5:
                #     print()
                # na and nb are notes in the same chord
                if fa == fb:
                    skipped = True  # play different chord notes w/ same finger, skip
                elif crossing:  # not crossing fingers in a chord
                    skipped = True
                elif xba > 9.5 and (fa == 3 and fb == 4 or fa == 4 and fb == 3):
                    skipped = True
                elif xba > 9.5 and (fa == 4 and fb == 5 or fa == 5 and fb == 4):
                    skipped = True
                elif xba > 10 and (fa == 2 and fb == 3 or fa == 3 and fb == 2):
                    skipped = True
                elif xba > 12.5 and (fa == 2 and fb == 4 or fa == 4 and fb == 2):
                    skipped = True
                elif xba > 15 and (fa == 3 and fb == 5 or fa == 5 and fb == 3):
                    skipped = True
                elif xba > 18 and (fa == 2 and fb == 5 or fa == 5 and fb == 2):
                    skipped = True
                elif xba > 18.5 and (fa == 1 and fb == 2 or fa == 2 and fb == 1):
                    skipped = True
                elif xba > 19 and (fa == 1 and fb == 3 or fa == 3 and fb == 1):
                    skipped = True
                elif xba > 21 and (fa == 1 and fb == 4 or fa == 4 and fb == 1):
                    skipped = True


            elif not na.isChord and nb.isChord:
                # respect previous onset
                if na.pitch != nb.pitch and fa == fb:  # not same fingers
                    skipped = True
                elif crossing:  # not crossing fingers
                    skipped = True

            elif na.isChord and not nb.isChord:
                # if na.noteID == 6 and fa == 4 and fb == 1:
                #     print()
                for fc, nc in zip(current_chord, na.chordNotes):
                    if self.LR == 'right':
                        nc_crossing = (nc.pitch < nb.pitch and fc > fb) or (nc.pitch > nb.pitch and fc < fb)
                    else:  # left
                        nc_crossing = (nc.pitch > nb.pitch and fc > fb) or (nc.pitch < nb.pitch and fc < fb)

                    if nc.pitch != nb.pitch and fc == fb:  # not same fingers
                        skipped = True
                    elif nc_crossing:  # not crossing fingers
                        skipped = True
        return skipped
        # ---------------------------------------------------------------------------

    def _exploit_fingers(self, past_chord, current_chord, f, na, nb, level):
        exploit = []

        for next_f in [1, 2, 3, 4, 5]:
            if not self._skip(past_chord, current_chord, f, next_f, na, nb):
                if na.chordID == nb.chordID:
                    p = past_chord
                    c = current_chord + [next_f]
                else:  # na.chord_id != nb.chordID:
                    p = current_chord
                    c = [next_f]
                exploit.append((next_f, p, c))

        return exploit

    #####################################################
    def optimize_seq(self, nseq, fingers_start):
        '''Generate meaningful fingering for a note sequence of size depth'''
        if self.autodepth:
            # choose depth based on time span of 3.5 seconds
            if nseq[0].isChord:
                self.depth = max(3, nseq[0].NinChord - nseq[0].chordnr + 1)
            else:
                tn0 = nseq[0].time
                for i in (4, 5, 6, 7, 8, 9):
                    self.depth = i
                    if nseq[i - 1].time - tn0 > 3.5:
                        break
        depth = self.depth

        n1, n2, n3, n4, n5, n6, n7, n8, n9 = nseq

        #####################################
        out = ([0 for _ in range(depth)], -1, [(ii, [], [ii]) for ii in range(1, 6)])

        minvel = 1.e+10
        for f1, past_chord1, current_chord1 in fingers_start:
            for f2, past_chord, current_chord in self._exploit_fingers(past_chord1, current_chord1, f1, n1, n2, 2):
                for f3, past_chord, current_chord in self._exploit_fingers(past_chord, current_chord, f2, n2, n3, 3):
                    for f4, past_chord, current_chord in self._exploit_fingers(past_chord, current_chord, f3, n3, n4, 4):
                        for f5, past_chord, current_chord in self._exploit_fingers(past_chord, current_chord, f4, n4, n5, 5):
                            for f6, past_chord, current_chord in self._exploit_fingers(past_chord, current_chord, f5, n5, n6, 6):
                                for f7, past_chord, current_chord in self._exploit_fingers(past_chord, current_chord, f6, n6, n7, 7):
                                    for f8, past_chord, current_chord in self._exploit_fingers(past_chord, current_chord, f7, n7, n8, 8):
                                        for f9, past_chord, current_chord in self._exploit_fingers(past_chord, current_chord, f8, n8, n9, 9):
                                            c = [f1, f2, f3, f4, f5, f6, f7, f8, f9]
                                            v = self.ave_velocity(c, nseq)
                                            if v < minvel:
                                                out = (c, v, self._exploit_fingers(past_chord1, current_chord1, f1, n1, n2, 2))
                                                minvel = v

        return out

    ###########################################################################################
    def generate(self, start_measure=0, nmeasures=1000):
        if start_measure == 1:
            start_measure = 0  # avoid confusion with python numbering

        if self.LR == "left":
            for anote in self.noteseq:
                anote.x = -anote.x  # play left as a right on a mirrored keyboard

        start_finger, out, vel = 0, [0 for _ in range(9)], 0
        N = len(self.noteseq)
        if self.depth < 3:
            self.depth = 3
        if self.depth > 9:
            self.depth = 9

        last_chord, current_chord = None, None

        for i in range(N):  ##############

            an = self.noteseq[i]
            if an.measure:
                if an.measure < start_measure: continue
                if an.measure > start_measure + nmeasures: break

            if i > N - 11:
                self.autodepth = False
                self.depth = 9

            best_finger = 0
            if i > N - 10:
                if len(out) > 1: best_finger = out.pop(1)
            else:
                if i == 0:
                    fingers_start = [(ii, [], [ii]) for ii in range(1, 6)]
                else:
                    fingers_start = possible_fingers

                ninenotes = self.noteseq[i:i + 9]
                out, vel, possible_fingers = self.optimize_seq(ninenotes, fingers_start)
                best_finger = out[0]

            an.fingering = best_finger
            self.set_fingers_positions(out, ninenotes, 0)
            self.fingerseq.append(list(self.cfps))

            an.cost = vel

            # print()
            # if i == 6:
            #     break

            # ---------------------------------------------------------------------------- print
            if self.verbose:
                if not best_finger:
                    best_finger = 0
                if an.measure:
                    print(f"meas.{an.measure: <3}", end=' ')
                print(f"finger_{best_finger}  plays  Pitch:{an.pitch} Octave:{an.octave}", end=' ')
                if i < N - 10:
                    print(f"  v={round(vel, 1)}", end='')
                    if self.autodepth:
                        print("\t " + str(out[0:self.depth]) + " d:" + str(self.depth))
                    else:
                        print("\t" + ("   " * (i % self.depth)) + str(out[0:self.depth]))
                else:
                    print()
            else:
                if i and not i % 100 and an.measure:
                    print('scanned', i, '/', N,
                          'notes, measure', an.measure + 1, ' for the', self.LR, 'hand...')

            # break
