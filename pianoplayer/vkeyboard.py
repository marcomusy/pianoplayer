#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         VirtualKeyboard
# Purpose:      Find optimal fingering for piano scores
#
# Author:       Marco Musy
# Copyright:    Copyright 2017-2022
#-------------------------------------------------------------------------------

from music21.midi.realtime import StreamPlayer
from music21.stream import Stream
try:
    import visual as vp
    from visual.text import text
except:
    # import vpython as vp
    # from vpython.text import text
    print "VirtualKeyboard: cannot find some package."
    print 'python visual not installed?'
    quit()


version = 'PIANOFING V4.2'


###########################################################
class VirtualKeyboard:

    def __init__(self):
                  
        self.rate = 100
        
        self.KB = dict()
        self.scene = None
        
        self.rightHand = None
        self.leftHand  = None
                
        self.playsounds = False

        self.build_keyboard()
        self.vpRH=None
        self.vpLH=None

    
    #######################################################
    def build_RH(self, hand):
    
        print 'Building Right Hand..'
        self.rightHand = hand
        sz = (0.8, 1, 5)
        f1 = vp.ellipsoid(pos=(-2.,1.5,6.2),size=sz, opacity=0.9, color=(.7,0.3,0.3))
        f2 = vp.ellipsoid(pos=(-1.,1.5,4.2),size=sz, opacity=0.9, color=(.7,0.3,0.3))
        f3 = vp.ellipsoid(pos=( 0.,1.5,4),  size=sz, opacity=0.9, color=(.7,0.3,0.3))
        f4 = vp.ellipsoid(pos=( 1.,1.5,4.1),size=sz, opacity=0.9, color=(.7,0.3,0.3))
        f5 = vp.ellipsoid(pos=( 2.,1.5,4.5),size=sz, opacity=0.9, color=(.7,0.3,0.3))

        palm = vp.ellipsoid(pos=(0,1.6,10), size=(9.6,2.,6),  opacity=0.3, color=(.5,0,0))
        palm.rotate(angle=0.1)
        palm.rotate(angle=0.1, axis=(0,1,0))

        self.vpRH = [palm, f1,f2,f3,f4,f5]
        for limb in self.vpRH: 
            limb.x   *= 2.5
            limb.pos += (16.5*5.+1, 0, 0)
    
    #######################################################
    def build_LH(self, hand):
    
        print 'Building Left Hand..'
        self.leftHand = hand
        sz = (0.8, 1, 5)
        f1 = vp.ellipsoid(pos=(-2.,1.5,6.2),size=sz, opacity=0.9, color=(.7,0.3,0.3))
        f2 = vp.ellipsoid(pos=(-1.,1.5,4.2),size=sz, opacity=0.9, color=(.7,0.3,0.3))
        f3 = vp.ellipsoid(pos=( 0.,1.5,4),  size=sz, opacity=0.9, color=(.7,0.3,0.3))
        f4 = vp.ellipsoid(pos=( 1.,1.5,4.1),size=sz, opacity=0.9, color=(.7,0.3,0.3))
        f5 = vp.ellipsoid(pos=( 2.,1.5,4.5),size=sz, opacity=0.9, color=(.7,0.3,0.3))

        palm = vp.ellipsoid(pos=(0,1.6,10), size=(9.6,2.,6),  opacity=0.3, color=(.5,0,0))
        palm.rotate(angle=-0.1)
        palm.rotate(angle=-0.1, axis=(0,1,0))

        self.vpLH = [palm, f1,f2,f3,f4,f5]
        for limb in self.vpLH: 
            limb.x   *= -2.5
            limb.pos += (16.5*3.+1, 0, 0)
            

    #######################################################
    def build_keyboard(self):
        
        print 'Building Keyboard..'
        nts = ("C","D","E","F","G","A","B")
        tol = 0.12
        keybsize = 16.5 #cm, span of one octave
        wb = keybsize/7.
        nr_octaves = 7
        span = nr_octaves*wb*7.
    
        self.scene = vp.display(title='Piano Keyboard', x=0, y=0, width=1400./1., height=600./1.,  
                                center=(75,0,0), forward=(0.,-2,-1.), background=(0., 0.25, 0.0))
        #wooden top and base
        vp.box(pos=(span/2+keybsize,-1.,-3),length=span+1, height=1, width=17, material=vp.materials.wood)
        vp.box(pos=(span/2+keybsize, 1, -8),length=span+1, height=3, width=7,  material=vp.materials.wood)
        text(pos=(28,2.2,-8), string=version, width=2, height=2, up=(0,0,-1),
             color=vp.color.orange, depth=0.3, justify='center')
        #leggio
        leggio = vp.box(pos=(75, 8., -12.), length=span/2, height=span/8, width=0.08, color=(1,1,0.9))
        leggio.rotate(angle=-0.4)

        for ioct in range(nr_octaves):
            for ik in range(7):#white keys
                x  = ik * wb + (ioct+1.)*keybsize +wb/2.
                tb = vp.box(pos=(x,0.,0), length=wb-tol, height=1, width=10, up=(0,1,0), color=(1,1,1))
                self.KB.update({nts[ik]+str(ioct+1) : tb})
                if not nts[ik] in ("E","B"): #black keys
                    tn=vp.box(pos=(x+wb/2,wb/2,-2), length=wb*.6, height=1, width=6, up=(0,1,0), color=(0,0,0))
                    self.KB.update({nts[ik]+"#"+str(ioct+1) : tn})

        self.scene.lights = []
        vp.local_light(pos=(  0, 100,  0), color=vp.color.white) #source1
        vp.local_light(pos=(-10, -40, 20), color=vp.color.white) #source2


    ####################################################### 
    def playsound(self, n):
        s = Stream() 
        if n.isChord: n = n.chord21
        else: s.append(n.note21)
        sp = StreamPlayer(s)
        sp.play()
#        if n.isChord: 
#            s.append(n)
#        else: 
#            nn = Note(n.nameWithOctave)
#            s.append(nn)
#        sp = StreamPlayer(s)
#        sp.play()

      
    ##############################################
    def nameof(self, n):
        a = n.name+str(n.octave)
        if "-" in a:
            b = a.replace("C-","B")
            b = b.replace("D-","C#")
            b = b.replace("E-","D#")
            b = b.replace("F-","E")
            b = b.replace("G-","F#")
            b = b.replace("A-","G#")
            b = b.replace("B-","A#")
            return b 
        elif "E#" in a:
            b = a.replace("E#","F")
            return b         
        elif "B#" in a:
            b = a.replace("B#","C")
            return b         
        else:
            return a
    
    
    #####################################################################
    def playKeyboard(self):
        
        print "\nPlaying now at speed:", self.rate
        print "Right-mouse click to move 3D scene."
        print "Press <esc> at any time to quit."

        tR,tL = 9999,9999

        if self.rightHand:
            handR   = self.rightHand
            vphandR = self.vpRH
             
            engagedkeysR    = [False]*len(handR.noteseq)
            engagedfingersR = [False]*6 # element 0 is dummy
        
            tR    = handR.noteseq[0].time #start time of first note
            fineR = handR.noteseq[-1].time #end time

        if self.leftHand:
            handL   = self.leftHand
            vphandL = self.vpLH
             
            engagedkeysL    = [False]*len(handL.noteseq)
            engagedfingersL = [False]*6 # element 0 is dummy
        
            tL    = handL.noteseq[0].time #start time of first note
            fineL = handL.noteseq[-1].time #end time

        t = min(tR,tL)
        dt = 0.01
        txs=[]
        
        while True:
            
            if self.rightHand:
                for i, n in enumerate(handR.noteseq):##################### RIGHT
                    start, stop, f = n.time, n.time+n.duration, n.fingering
                    if stop <= t <= stop+dt and engagedkeysR[i]:  ###release key
                        engagedkeysR[i]    = False
                        engagedfingersR[f] = False
    
                        name = self.nameof(n)
                        ts   = self.KB[name]
                        #print t, '\t..release', name
                        ts.rotate(angle=-0.15)
                        vphandR[f].rotate(angle= +0.2, origin=(vphandR[f].x, 3.5, 7.5))
                        if "#" in name: ts.color = vp.color.black
                        else: ts.color = vp.color.white
                
                if t>fineR+dt: break
                
                for i, n in enumerate(handR.noteseq):##################### RIGHT
                    start, stop, f = n.time, n.time+n.duration, n.fingering
    
                    ### press key n with finger f
                    if start <= t < stop and not engagedkeysR[i] and not engagedfingersR[f]: 
                        engagedkeysR[i]    = True
                        engagedfingersR[f] = True
    
                        name = self.nameof(n)
                        ts   = self.KB[name]
                        #print t, '\tpressing', name, start,'->', stop, ' \tfinger=', f
                        
                        if i>=len(handR.fingerseq): return                    
                        for g in [1,2,3,4,5]: vphandR[g].x = handR.fingerseq[i][g]
                        vphandR[f].rotate(angle= -0.2, origin=(vphandR[f].x, 3.5, 7.5))
                        vphandR[0].x = vphandR[3].x+0.2 # index 0 is palm
                        ts.rotate(angle= +0.15)                   ### press key
                        ts.color = (0.604,0.808,0.875)#154 206 223
                        tx=vp.label(pos=(vphandR[f].x, 3, -9),text=name, opacity=0,
                                    height=10, xoffset=86-vphandR[f].x, yoffset=85, box=0, border=8)
                        txs.append(tx)
                        
                        if self.playsounds: self.playsound(n)
            
            ##########################################################            
            if self.leftHand:
                for i, n in enumerate(handL.noteseq):##################### LEFT
                    start, stop, f = n.time, n.time+n.duration, n.fingering
                    if stop <= t <= stop+dt and engagedkeysL[i]:  ###release key
                        engagedkeysL[i]    = False
                        engagedfingersL[f] = False
    
                        name = self.nameof(n)
                        ts   = self.KB[name]
                        #print t, '\t..release', name
                        ts.rotate(angle=-0.15)
                        vphandL[f].rotate(angle= +0.2, origin=(vphandL[f].x, 1.5, 7.5))
                        if "#" in name: ts.color = vp.color.black
                        else: ts.color = vp.color.white
                
                if t>fineL+dt: break
                
                for i, n in enumerate(handL.noteseq):##################### LEFT
                    start, stop, f = n.time, n.time+n.duration, n.fingering
    
                    ### press key n with finger f
                    if start <= t < stop and not engagedkeysL[i] and not engagedfingersL[f]: 
                        engagedkeysL[i]    = True
                        engagedfingersL[f] = True
    
                        name = self.nameof(n)
                        ts   = self.KB[name]
                        #print t, '\tpressing', name, start,'->', stop, ' \tfinger=', f
                        
                        if i>=len(handL.fingerseq): return
                        for g in [5,4,3,2,1]: vphandL[g].x = -handL.fingerseq[i][g]
                        vphandL[f].rotate(angle= -0.2, origin=(vphandL[f].x, 1.5, 7.5))
                        vphandL[0].x = vphandL[3].x+0.2 # index 0 is palm
                        ts.rotate(angle= +0.15)                   ### press key
                        ts.color = (0.604,0.808,0.875)#154 206 223
                        tx=vp.label(pos=(vphandL[f].x, 3, -9),text=name, opacity=0,
                                    height=10, xoffset=86-vphandL[f].x, yoffset=85, box=0, border=8)
                        txs.append(tx)
                        
                        if self.playsounds and not self.rightHand: self.playsound(n)
            
            for i,tt in enumerate(txs):
                tt.xoffset -= 1.5
                if tt.xoffset < -200: 
                    tt.visible = False
                    del tt
                    del txs[i]
                
            t += dt #time flows
            vp.rate(self.rate)


#################################################################### test
if __name__ == "__main__":

        vk=VirtualKeyboard()
        vk.build_RH(None)
        vk.build_LH(None)
#        from music21.note import Note
#        n = Note('A-', quarterLength=1.5)
#        vk.playsound(n)




