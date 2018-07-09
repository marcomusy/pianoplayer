# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         PianoFing
# Purpose:      Find optimal fingering for piano scores
# Author:       Marco Musy
#-------------------------------------------------------------------------------
from __future__ import division, print_function

#####################################################
class Hand:
    def __init__(self, left_or_right="right", size='M'):
        
        self.LR        = left_or_right
        self.handspan  = None # thumb to pinkie distance in cm
        self.usable_fingers = (1, 2, 3, 4, 5)
        self.fpos      = [None,  -7.0,-2.8, 0.0, 2.8, 5.8] #first is dummy, (cm)
        self.weights   = [None,   1.1, 1.0, 1.1, 0.9, 0.8] #finger rel strenght
        self.bfactor   = [None,   0.5, 1.0, 1.1, 0.8, 0.6] #hit of black key bias
        self.noteseq   = []
        self.fingerseq = []
        self.depth     = 8
        self.autodepth = True  
        self.fstep     = 2 #recalculate fingering at each fstep
        
        self.setHandSize(size)
        if self.LR is not "right" and self.LR is not "left":
            print('Error: Hand must be left or right. Abort.', left_or_right)
            quit()

    #####################################################
    def setHandSize(self, s):
        self.size = s
        if    s=='M'  : f = 1.0
        elif  s=='XXS': f = 0.46
        elif  s=='XS' : f = 0.64
        elif  s=='S'  : f = 0.82
        elif  s=='L'  : f = 1.1
        elif  s=='XL' : f = 1.2
        elif  s=='XXL': f = 1.3
        else:
            print("Unknown hand size", s, "... Abort.")
            quit()
        
        for i in range(1,6): 
            if self.fpos[i]: self.fpos[i] *= f
        self.handspan = 21.0*f
        print('\nYour hand span set to size-'+s, 'which is',self.handspan,'cm')
        print('(max relaxed distance btw thumb and pinkie)\n')

    
    #####################################################
    def skiprules(self, fa,fb, na,nb): #two consecutive notes movement
        # fa is fingering for note na
        xba = nb.x - na.x #physical distance, cm

        #skip if repeat different note nb w/ same finger
        if fb==fa and xba!=0 and na.duration<4: return True 
    
        if fa>1 : ##if not thumb
            if fb>1  and (fb-fa)*xba<0:        
                return True #skip if non-thumb fingers are crossings
            if fb==1 and nb.isBlack and xba>0: 
                return True #crossing thumb goes to black key, skip.
        if na.isChord and nb.isChord and nb.time-na.time<4:
            if   fa >2 and abs(fb-fa)==1 and abs(xba)>4.5: 
                return True #dist max btw 2 consecutive fingers
            elif fa==1 and fb==2 and abs(xba)>12.: return True
            elif fa==2 and fb==1 and abs(xba)>12.: return True
            elif fa==2 and fb==3 and abs(xba)> 6.: return True
            elif fa==3 and fb==2 and abs(xba)> 6.: return True
#            if fa>1 and fb==1 and xba>0: return True #no thumb cross (not working?)
#            if fa==1 and fb>1 and xba<0: return True
        return False
    
    
    ##################################################### rigid hand
    def set_fingers_positions(self, fings, notes, i):
        fi = fings[i]
        ni = notes[i]
        newfpos = [0]*6
        ifx = self.fpos[fi]
        for j in self.usable_fingers:
            newfpos[j]= self.fpos[j] + ni.x - ifx
        return newfpos


    ##################################################### proportional stretching
    def set_fingers_positions_hide(self, fings, notes, i):
        fi = fings[i]
        nix = notes[i].x
        newfpos = [0]*6

        fac, minfac, maxfac = 1., 0.8, 1.4
        if i<len(notes)-1:
            fj = fings[i+1] #next note
            if fj :
                nj = notes[i+1]
                restd = self.fpos[fi]-self.fpos[fj] #rest distance btw 2 fings
                actud = nix - nj.x                  #actual distance btw 2 notes
                if restd: 
                    tfac  = abs(actud/restd)
                    if    tfac < minfac: fac = minfac   #allow whole hand stretching
                    elif  tfac > maxfac: fac = maxfac
                    else: fac = tfac 

        for j in self.usable_fingers:
            newfpos[j] = (self.fpos[j]-self.fpos[fi]) *fac + nix

        return newfpos


    #####################################################
    def ave_velocity(self, fingering, notes):
        ###calculate v for playing notes in fingering combination

        #initial position of first note played with finger fing[0]
        newfpos = self.set_fingers_positions(fingering, notes, 0)
        
        val = 0.
        for i in range(1, self.depth):
            na = notes[i-1]
            nb = notes[i]
            fb = fingering[i]
                        
            dx = nb.x - newfpos[fb]      #spazio percorso dal dito
            dt = nb.time - na.time +0.01 #tempo disponibile
            v  = dx/dt                   #velocita
            
            if nb.isBlack: bfac = self.bfactor[fb]
            else: bfac=1.
            v /= self.weights[fb] * bfac #penalty (increase speed)
            val += abs(v)
            
            #update all fingers positions
            newfpos = self.set_fingers_positions(fingering, notes, i)

        return val / (self.depth-1)*10.
        
        
    #####################################################
    #generate meaningful fingerings for note sequence 
    def optimize_seq(self, n, istart):
    
        if self.autodepth:
            for i in range(4,9):
                self.depth = i+1
                if n[i].time - n[0].time > 4: break #depth limit in secs
    
        n1, n2, n3, n4, n5 = n[0], n[1], n[2], n[3], n[4] 
        n6, n7, n8, n9 = [None]*4
        if self.depth>5: n6 = n[5]
        if self.depth>6: n7 = n[6]
        if self.depth>7: n8 = n[7]
        if self.depth>8: n9 = n[8]
        if istart == 0: u1 = self.usable_fingers
        else: u1 = [istart]
    
        bestval = 1.e+10
        bestcomb = None
        for f1 in u1:
            for f2 in self.usable_fingers:
                if self.skiprules(f1,f2,n1,n2): continue
                for f3 in self.usable_fingers:
                    if self.skiprules(f2,f3,n2,n3): continue
                    for f4 in self.usable_fingers:
                        if self.skiprules(f3,f4,n3,n4): continue
                        for f5 in self.usable_fingers:
                            if self.skiprules(f4,f5,n4,n5): continue
                            if self.depth<6: u=[False]
                            else: u=self.usable_fingers
                            for f6 in u:
                                if f6 and self.skiprules(f5,f6,n5,n6): continue
                                if self.depth<7: u=[False]
                                else: u=self.usable_fingers
                                for f7 in u:
                                    if f7 and self.skiprules(f6,f7,n6,n7): continue
                                    if self.depth<8: u=[False]
                                    else: u=self.usable_fingers
                                    for f8 in u:
                                        if f8 and self.skiprules(f7,f8,n7,n8): continue
                                        if self.depth<9: u=[False]
                                        else: u=self.usable_fingers
                                        for f9 in u:
                                            if f9 and self.skiprules(f8,f9,n8,n9): continue
                                            c = [f1,f2,f3,f4,f5,f6,f7,f8,f9]
                                            val = self.ave_velocity(c, n)
                                            if val < bestval: 
                                                bestcomb = c
                                                bestval  = val
        
        if bestcomb is None: return ([0]*self.depth, -1)       
        return (bestcomb, bestval)

    
    ###########################################################################################
    def generateFingering(self, nmeasures=1000):
    
        if self.LR == "left":
            #play left hand on a mirrored keyboard
            for anote in self.noteseq:
                anote.x = -anote.x 

        start_finger, out, costf = 0, [0]*9, 0

        for inote in range(len(self.noteseq)):
            an = self.noteseq[inote]
            i  = inote%self.fstep # position inside the group of step notes
            if an.measure > nmeasures : break
            
            if i==0:
                if inote <= len(self.noteseq)-9: 
                    ninenotes  = self.noteseq[inote : inote+9] 
                    out, costf = self.optimize_seq(ninenotes, start_finger)
                    best_finger= out[i]
                else: #close to the end of score
                    best_finger= out[9-len(self.noteseq) + inote]
            else:
                best_finger = out[i] 
            start_finger = out[i+1]
            
            bestfpos = self.set_fingers_positions(out, ninenotes, i)
            self.fingerseq.append(bestfpos)
            
            an.fingering = best_finger
            if best_finger>0:
                if an.isChord:
                    if not an.chord21.hasLyrics():
                        for li in range(len(an.chord21.pitches)): an.chord21.addLyric('0')
                    #an.chord21.addLyric(best_finger)
                    nl = len(an.chord21.pitches)-an.chordnr
                    an.chord21.addLyric(best_finger, nl)
                else:
                    an.note21.addLyric(best_finger)

            
            #-----------------------------

            print("meas."+str(an.measure), end='')
            print("  finger:"+str(best_finger) + " on " + an.name+str(an.octave), end='')
            if i==0:
                print("\tv=" + str(int(costf*10.)/10.), end='')
                if self.autodepth:
                    print("\t"+"   "+str(out[0:self.depth]) + " d =",self.depth)
                else:
                    print("\t"+("   "*(inote%self.depth))+str(out[0:self.depth]))
            else:
                print()
