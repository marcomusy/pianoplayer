#
# 
#-------------------------------------------------------------------------------
# Name:         PianoPlayer
# Purpose:      Find optimal fingering for piano scores
# Author:       Marco Musy
#-------------------------------------------------------------------------------
from __future__ import division, print_function
from music21.articulations import Fingering
import pianoplayer.utils as utils


#####################################################
class Hand:
    def __init__(self, side="right", size='M'):
        
        self.LR        = side
        self.frest     = [None,  -7.0,-2.8, 0.0, 2.8, 5.8] # first is dummy, (cm)
        self.weights   = [None,   1.1, 1.0, 1.1, 0.9, 0.8] # finger rel strength
        self.bfactor   = [None,   0.3, 1.0, 1.1, 0.8, 0.7] # hit of black key bias
        self.noteseq   = []
        self.fingerseq = []
        self.depth     = 9
        self.autodepth = True  
        self.verbose   = True
        self.lyrics    = False  # show fingering numbers as lyrics in musescore
        self.size      = size

        self.hf = utils.handSizeFactor(size)
        for i in (1,2,3,4,5): 
            if self.frest[i]: self.frest[i] *= self.hf
        print('Your hand span set to size-'+size, 'which is',21*self.hf,'cm')
        print('(max relaxed distance btw thumb and pinkie)')
        self.cfps = list(self.frest) # current finger positions


    def set_fingers_positions(self, fings, notes, i): 
        # allow whole hand stretching from -20% to +40%, 
        # based on the distribution of the future 3 notes

        tfac, fac, minfac, maxfac = 1, 1, 0.8, 1.4
        n = min(len(fings), len(notes), 2)

        fi = fings[i]
        ni = notes[i]
        if not ni.isChord:
            xs = [n.x for n in notes[i:i+n]]
            if xs:
                handspread = max(xs) - min(xs)
                if handspread>0: 
                    tfac = handspread/(self.frest[5]-self.frest[1])*self.hf/0.8
                    if   tfac < minfac: fac = minfac 
                    elif tfac > maxfac: fac = maxfac
                    else: fac = tfac

        ifx = self.frest[fi]
        if ifx is not None:
            for j in (1,2,3,4,5): 
                self.cfps[j] = (self.frest[j]-ifx) *fac + ni.x
         
        
    #####################################################
    def ave_velocity(self, fingering, notes):
        ###calculate v for playing for notes in a given fingering combination
        
        self.set_fingers_positions(fingering, notes, 0)

        vmean = 0.
        for i in range(1, self.depth):
            na = notes[i-1]
            nb = notes[i]
            fb = fingering[i]
                        
            dx = nb.x - self.cfps[fb]     # space travelled by finger fb
            dt = nb.time - na.time +0.01  # available time +smoothing term
            v  = abs(dx/dt)               # velocity
            
            if nb.isBlack: bfac = self.bfactor[fb]
            else: bfac=1
            v /= self.weights[fb] * bfac  # penalty (increase speed)
            vmean += v
            
            #update all fingers positions
            self.set_fingers_positions(fingering, notes, i)

        return vmean / (self.depth-1)
        
        
    #####################################################
    def optimize_seq(self, nseq, istart):
        '''Generate meaningful fingerings for a note sequence of size depth'''
    
        if self.autodepth:
            for i in (4,5,6,7,8):
                self.depth = i+1
                if nseq[i].time - nseq[0].time > 4: 
                    break #depth limit in secs
        depth = self.depth
    
        n1, n2, n3, n4, n5 = nseq[0:5] 
        n6, n7, n8, n9 = [None]*4
        if depth>5: n6 = nseq[5]
        if depth>6: n7 = nseq[6]
        if depth>7: n8 = nseq[7]
        if depth>8: n9 = nseq[8]
        if istart == 0: u1 = (1,2,3,4,5)
        else: u1 = [istart]
        fingers = (1,2,3,4,5)

        def skiprules(fa,fb, na,nb): ### two-consecutive-notes movement ###
            # fa is fingering for note na
            xba = nb.x - na.x  # physical distance, cm

            if fb==fa and xba!=0 and na.duration<4 and not nb.isChord: 
                return True # play normal notes w/ same finger, skip
        
            if fa>1 : # if a is not thumb
                if fb>1  and (fb-fa)*xba<0: return True # non-thumb fingers are crossings, skip
                if fb==1 and nb.isBlack and xba>0: return True # crossing thumb goes to black, skip
                
            if na.isChord and nb.isChord and nb.time-na.time<0.1: # na and nb are in the same chord
                axba = abs(xba)*self.hf/0.8 # max normalizd distance in cm btw 2 consecutive fingers
                if abs(fb-fa)==0 and axba>0: return True # play different chord notes w/ same finger, skip
                elif fa==1 and fb==4 and axba>16: return True
                elif fa==4 and fb==1 and axba>16: return True
                elif fa==1 and fb==3 and axba>14: return True
                elif fa==3 and fb==1 and axba>14: return True
                elif fa==1 and fb==2 and axba>12: return True
                elif fa==2 and fb==1 and axba>12: return True
                elif fa==2 and fb==3 and axba> 6: return True
                elif fa==3 and fb==2 and axba> 6: return True
                
                if fa>1  and fb==1 and xba>0: return True # no thumb cross inside chord, skip
                if fa==1 and fb>1  and xba<0: return True
            return False             #######################################

        out = ([0]*depth, -1)
        minvel = 1.e+10
        for f1 in u1:
            for f2 in fingers:
                if skiprules(f1,f2, n1,n2): continue
                for f3 in fingers:
                    if skiprules(f2,f3, n2,n3): continue
                    for f4 in fingers:
                        if skiprules(f3,f4, n3,n4): continue
                        for f5 in fingers:
                            if skiprules(f4,f5, n4,n5): continue
                            if depth<6: u=[False]
                            else: u=fingers
                            for f6 in u:
                                if f6 and skiprules(f5,f6, n5,n6): continue
                                if depth<7: u=[False]
                                else: u=fingers
                                for f7 in u:
                                    if f7 and skiprules(f6,f7, n6,n7): continue
                                    if depth<8: u=[False]
                                    else: u=fingers
                                    for f8 in u:
                                        if f8 and skiprules(f7,f8, n7,n8): continue
                                        if depth<9: u=[False]
                                        else: u=fingers
                                        for f9 in u:
                                            if f9 and skiprules(f8,f9, n8,n9): continue
                                            c = [f1,f2,f3,f4,f5,f6,f7,f8,f9]
                                            v = self.ave_velocity(c, nseq)
                                            if v < minvel: 
                                                out = (c, v)
                                                minvel  = v
        return out

    
    ###########################################################################################
    def generate(self, start_measure=0, nmeasures=1000):

        if start_measure == 1: start_measure=0 # avoid confusion with python numbering
        if self.LR == "left":
            for anote in self.noteseq:
                anote.x = -anote.x  #play left hand as a right on a mirrored keyboard

        start_finger, out, vel = 0, [0]*9, 0
        N = len(self.noteseq)
        
        for i in range(N):##############

            an = self.noteseq[i]
            if an.measure:
                if an.measure < start_measure : continue
                if an.measure > start_measure + nmeasures : break

            if i > N-11:
                self.autodepth = False
                self.depth = 9

            best_finger = 0
            if i > N-10:
                if len(out)>1: best_finger = out.pop(1)
            else:
                ninenotes = self.noteseq[i : i+9]
                out, vel  = self.optimize_seq(ninenotes, start_finger)
                best_finger  = out[0]
                start_finger = out[1]

            an.fingering = best_finger
            self.set_fingers_positions(out, ninenotes, 0)
            self.fingerseq.append(list(self.cfps))

            if best_finger>0:
                fng = Fingering(best_finger)
                if an.isChord:
                    if self.lyrics:
                         npitches = len(an.chord21.pitches)
                         if (self.LR=='right' and npitches<4) or (self.LR=='left' and npitches<4):
                             # dont show fingering for >3 note-chords
                             nl = len(an.chord21.pitches) - an.chordnr
                             an.chord21.addLyric(best_finger, nl)
                    else:
                        an.chord21.articulations.append(fng)
                else:
                    if self.lyrics: 
                        an.note21.addLyric(best_finger)
                    else:           
                        an.note21.articulations.append(fng)


            #-----------------------------
            if self.verbose:
                print("meas."+str(an.measure), end=' ')
                print("  finger:"+str(best_finger) + " on " + an.name+str(an.octave), end=' ')
                if i < N-10:
                    print("\tv=" + str(round(vel,1)), end='')
                    if self.autodepth:
                        print("\t"+"   "+str(out[0:self.depth]) + " d:" + str(self.depth))
                    else:
                        print("\t"+("   "*(i%self.depth))+str(out[0:self.depth]))
                else:
                    print()
            else:
                if i and not i%100:
                    print('scanned',i,'notes in', an.measure+1, 'measures for', self.LR ,'hand..')




