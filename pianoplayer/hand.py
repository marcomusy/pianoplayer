# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         PianoPlayer
# Purpose:      Find optimal fingering for piano scores
# Author:       Marco Musy
#-------------------------------------------------------------------------------
from __future__ import division, print_function
from music21.articulations import Fingering, Articulation
from music21.style import Style


#####################################################
class Hand:
    def __init__(self, side="right", size='M'):
        
        self.LR        = side
        self.handspan  = None # thumb to pinkie distance in cm
        self.fpos      = [None,  -7.0,-2.8, 0.0, 2.8, 5.8] #first is dummy, (cm)
        self.weights   = [None,   1.1, 1.0, 1.1, 0.9, 0.8] #finger rel strength
        self.bfactor   = [None,   0.5, 1.0, 1.1, 0.8, 0.6] #hit of black key bias
        self.noteseq   = []
        self.fingerseq = []
        self.depth     = 8
        self.autodepth = True  
        self.verbose   = True
        self.currentFpositions = list(self.fpos) 
        self.fstep     = 2    # recalculate fingering at each fstep
        
        self.setHandSize(size)
        if self.LR is not "right" and self.LR is not "left":
            print('Error: Hand must be left or right. Abort.', side)
            quit()

    #####################################################
    def setHandSize(self, s):
        if    s=='XXS': f = 0.46
        elif  s=='XS' : f = 0.64
        elif  s=='M'  : f = 1.0
        elif  s=='L'  : f = 1.1
        elif  s=='XL' : f = 1.2
        elif  s=='XXL': f = 1.3
        else:
            s = 'S'
            f = 0.82
        self.size = s
        
        for i in range(1,6): 
            if self.fpos[i]: self.fpos[i] *= f
        self.handspan = 21.0*f
        if self.verbose:
            print('\nYour hand span set to size-'+s, 'which is',self.handspan,'cm')
            print('(max relaxed distance btw thumb and pinkie)\n')
    
    
    ##################################################### rigid hand
    def set_fingers_positions(self, fings, notes, inote):
        ni = notes[inote]
        fi = fings[inote]
        newfpos = [0, 0,0,0,0,0]
        ifx = self.fpos[fi] #position of fingers with hand at (0,0,0)
        for j in (1,2,3,4,5):
            if ifx:
                newfpos[j]= ni.x + self.fpos[j] - ifx
            else:
                newfpos[j]= ni.x + self.fpos[j]
        return newfpos


    #####################################################
    def ave_velocity(self, fingering, notes):
        ###calculate v for playing given notes in given fingering combination

        #initial position of note nr0 played with finger fingering[0]
        newfpos = self.set_fingers_positions(fingering, notes, 0)
        
        val = 0.
        for i in range(1, self.depth):
            na = notes[i-1]
            nb = notes[i]
            fb = fingering[i]
                        
            dx = nb.x - newfpos[fb]      #space travelled by finger
            dt = nb.time - na.time +0.01 #available time
            v  = dx/dt                   #velocity
            
            if nb.isBlack: bfac = self.bfactor[fb]
            else: bfac=1
            v /= self.weights[fb] * bfac #penalty (increase speed)
            val += abs(v)
            
            #update all fingers positions
            newfpos = self.set_fingers_positions(fingering, notes, i)

        return val / (self.depth-1)*10
        
        
    #####################################################
    def optimize_seq(self, nseq, istart):
        '''Generate meaningful fingerings for a note sequence of size depth'''
    
        if self.autodepth:
            for i in range(4,9):
                self.depth = i+1
                if nseq[i].time - nseq[0].time > 4: 
                    break #depth limit in secs
        depth = self.depth
    
        n1, n2, n3, n4, n5 = nseq[0], nseq[1], nseq[2], nseq[3], nseq[4] 
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
            xba = nb.x - na.x #physical distance, cm

            #repeat different note nb w/ same finger, skip.
            if fb==fa and xba!=0 and na.duration<4: return True 
        
            if fa>1 : ##if not thumb
                if fb>1  and (fb-fa)*xba<0:        
                    return True #non-thumb fingers are crossings, skip.
                if fb==1 and nb.isBlack and xba>0: 
                    return True #crossing thumb goes to black key, skip.
            if na.isChord and nb.isChord and nb.time-na.time<4: #chords
                if   fa >2 and abs(fb-fa)==1 and abs(xba)>4.5: return True #max dist btw 2 consecutive fingers
                elif fa==1 and fb==2 and abs(xba)>12: return True
                elif fa==2 and fb==1 and abs(xba)>12: return True
                elif fa==2 and fb==3 and abs(xba)> 6: return True
                elif fa==3 and fb==2 and abs(xba)> 6: return True
                #if fa>1 and fb==1 and xba>0: return True #no thumb cross (not working?)
                #if fa==1 and fb>1 and xba<0: return True
            return False


        bestcomb = None
        bestval = 1.e+10
        for f1 in u1:
            for f2 in fingers:
                if skiprules(f1,f2,n1,n2): continue
                for f3 in fingers:
                    if skiprules(f2,f3,n2,n3): continue
                    for f4 in fingers:
                        if skiprules(f3,f4,n3,n4): continue
                        for f5 in fingers:
                            if skiprules(f4,f5,n4,n5): continue
                            if depth<6: u=[False]
                            else: u=fingers
                            for f6 in u:
                                if f6 and skiprules(f5,f6,n5,n6): continue
                                if depth<7: u=[False]
                                else: u=fingers
                                for f7 in u:
                                    if f7 and skiprules(f6,f7,n6,n7): continue
                                    if depth<8: u=[False]
                                    else: u=fingers
                                    for f8 in u:
                                        if f8 and skiprules(f7,f8,n7,n8): continue
                                        if depth<9: u=[False]
                                        else: u=fingers
                                        for f9 in u:
                                            if f9 and skiprules(f8,f9,n8,n9): continue
                                            c = [f1,f2,f3,f4,f5,f6,f7,f8,f9]
                                            val = self.ave_velocity(c, nseq)
                                            if val < bestval: 
                                                bestcomb = c
                                                bestval  = val
        if bestcomb is None: 
            return ([0]*depth, -1)   
        else:    
            return (bestcomb, bestval)

    
    ###########################################################################################
    def generate(self, start_measure=0, nmeasures=1000):

        if start_measure == 1: start_measure=0 # avoid confusion with python numbering
        if start_measure>1: 
            if self.fstep>1: print('Warning: --skip mode disabled by --start-measure option')
            self.fstep=1
        if self.LR == "left":
            for anote in self.noteseq:
                anote.x = -anote.x  #play left hand as a right on a mirrored keyboard

        start_finger, out, costf, ninenotes  = 0, [0]*9, 0, [0]*9
        N = len(self.noteseq)

        for inote in range(start_measure, N):

            best_finger = 0
            an = self.noteseq[inote]
            if an.measure:
                if an.measure < start_measure : continue
                if an.measure > start_measure + nmeasures : break
            if inote > N-11:
                self.autodepth = False
                self.depth = 9
                self.fstep = 1

            if inote > N-10:
                if len(out)>1: best_finger = out.pop(1)
            else:
                i  = inote%self.fstep # position inside the group of step notes   
                if i==0: #beginning of group
                    ninenotes  = self.noteseq[inote : inote+9] 
                    out, costf = self.optimize_seq(ninenotes, start_finger)
                    best_finger= out[0]
                else:
                    best_finger = out[i]

                start_finger = out[i+1]
                bestfpos = self.set_fingers_positions(out, ninenotes, i)

            self.fingerseq.append(bestfpos)
           
            an.fingering = best_finger
            if best_finger>0:
                if an.isChord:
                    npitches = len(an.chord21.pitches)
                    # dont show fingering for >3 note-chords
                    if (self.LR=='right' and npitches<4) or (self.LR=='left' and npitches<3):
                        nl = len(an.chord21.pitches) - an.chordnr
                        an.chord21.addLyric(best_finger, nl)
                else:
                    an.note21.addLyric(best_finger)
                    # muf = Fingering(best_finger) # cannot shift them to make them visible
                    # sty = Style()
                    # sty.placement = 'below'
                    # sty.offset = .90
                    # sty.absoluteY = 30
                    # muf.style = sty
                    # an.note21.articulations.append(muf)
                    

            #-----------------------------
            if self.verbose:
                print("meas."+str(an.measure), end=' ')
                print("  finger:"+str(best_finger) + " on " + an.name+str(an.octave), end=' ')
                if i==0 and inote < N-10:
                    print("\tv=" + str(round(costf,1)), end='')
                    if self.autodepth:
                        print("\t"+"   "+str(out[0:self.depth]) + " d =",self.depth)
                    else:
                        print("\t"+("   "*(inote%self.depth))+str(out[0:self.depth]))
                else:
                    print()







    ##################################################### proportional stretching
    # def set_fingers_positions(self, fings, notes, i):
    #     fi = fings[i]
    #     nix = notes[i].x
    #     newfpos = [0]*6
    #     fac, minfac, maxfac = 1., 0.8, 1.4
    #     if i<len(notes)-1:
    #         fj = fings[i+1] #next note
    #         if fj :
    #             nj = notes[i+1]
    #             restd = self.fpos[fi]-self.fpos[fj] #rest distance btw 2 fings
    #             actud = nix - nj.x                  #actual distance btw 2 notes
    #             if restd: 
    #                 tfac  = abs(actud/restd)
    #                 if    tfac < minfac: fac = minfac   #allow whole hand stretching
    #                 elif  tfac > maxfac: fac = maxfac
    #                 else: fac = tfac 

    #     for j in (1,2,3,4,5):
    #         newfpos[j] = (self.fpos[j]-self.fpos[fi]) *fac + nix

    #     return newfpos
