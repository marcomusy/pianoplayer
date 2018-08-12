#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         VirtualKeyboard
# Purpose:      Find optimal fingering for piano scores
# URL:          https://github.com/marcomusy/pianoplayer
# Author:       Marco Musy
#-------------------------------------------------------------------------------
from __future__ import division, print_function
from music21.midi.realtime import StreamPlayer
from music21.stream import Stream
try:
    import vtk
    import vtkplotter
except:
    print("VirtualKeyboard: cannot find vtk or vtkplotter packages. Not installed?")
    print('Try: (sudo) pip install --upgrade vtkplotter')
    quit()


version = 'PianoPlayer 1.0.0'


###########################################################
class VirtualKeyboard:

    def __init__(self):
                  
        self.rate = 100
        
        self.KB = dict()
        self.vp = None
        
        self.rightHand = None
        self.leftHand  = None
                
        self.playsounds = False

        self.vpRH=None
        self.vpLH=None
        self.build_keyboard() 

    #######################################################
    def build_RH(self, hand):
    
        print('Building Right Hand..')
        self.rightHand = hand
        a1, a2, a3 = (0.8, 0, 0), (0, 1, 0), (0, 0, 5)
        f1 = self.vp.ellipsoid(pos=(-2.,1.5,6.2), axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
        f2 = self.vp.ellipsoid(pos=(-1.,1.5,4.2), axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
        f3 = self.vp.ellipsoid(pos=( 0.,1.5,4),   axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
        f4 = self.vp.ellipsoid(pos=( 1.,1.5,4.1), axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
        f5 = self.vp.ellipsoid(pos=( 2.,1.5,4.5), axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))

        a1, a2, a3 = (9.6, 0, 0), (0, 2, 0), (0, 0, 6)
        palm = self.vp.ellipsoid(pos=(0,1.6,10), axis1=a1, axis2=a2, axis3=a3,  alpha=0.3, c=(.5, 0, 0))

        self.vpRH = [palm, f1,f2,f3,f4,f5]
        for limb in self.vpRH: 
            limb.rotateX(90)
            limb.x( limb.x()* 2.5 )
            limb.pos(limb.pos() + [16.5*5.+1, 0, 0] )
    
    #######################################################
    def build_LH(self, hand):
    
        print('Building Left Hand..')
        self.leftHand = hand
        a1, a2, a3 = (0.8, 0, 0), (0, 1, 0), (0, 0, 5)
        f1 = self.vp.ellipsoid(pos=(-2.,1.5,6.2), axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
        f2 = self.vp.ellipsoid(pos=(-1.,1.5,4.2), axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
        f3 = self.vp.ellipsoid(pos=( 0.,1.5,4),   axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
        f4 = self.vp.ellipsoid(pos=( 1.,1.5,4.1), axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
        f5 = self.vp.ellipsoid(pos=( 2.,1.5,4.5), axis1=a1, axis2=a2, axis3=a3, alpha=0.9, c=(.7,0.3,0.3))
 
        a1, a2, a3 = (9.6, 0, 0), (0, 2, 0), (0, 0, 6)
        palm = self.vp.ellipsoid(pos=(0,1.6,10), axis1=a1, axis2=a2, axis3=a3,  alpha=0.3, c=(.5, 0, 0))

        self.vpLH = [palm, f1,f2,f3,f4,f5]
        for limb in self.vpLH: 
            limb.rotateX(90)
            limb.rotateY(180)
            limb.x( limb.x()* 2.5 )
            limb.pos(limb.pos() + [16.5*3.+1, 0, 3] )
                

    #######################################################
    def build_keyboard(self):
        
        print('Building Keyboard..')
        nts = ("C","D","E","F","G","A","B")
        tol = 0.12
        keybsize = 16.5 #cm, span of one octave
        wb = keybsize/7.
        nr_octaves = 7
        span = nr_octaves*wb*7.
    
        self.vp = vtkplotter.Plotter(title='Piano Keyboard', axes=0, size=(1200,600), bg='lb', verbose=0)

        #wooden top and base
        self.vp.box(pos=(span/2+keybsize, 6,  1), length=span+1, height=3, width= 5, texture='wood5') #top
        self.vp.box(pos=(span/2+keybsize, 0, -1), length=span+1, height=1, width=17, texture='wood5')
        self.vp.text(version, pos=(18,5.5,2.), depth=.7)
        #leggio
        leggio = self.vp.box(pos=(span/1.6,8,10), length=span/2, height=span/8, width=0.08, c=(1,1,0.9))
        leggio.rotateX(angle=-20)

        for ioct in range(nr_octaves):
            for ik in range(7): #white keys
                x  = ik * wb + (ioct+1.)*keybsize +wb/2.
                tb = self.vp.box(pos=(x,-2,0), length=wb-tol, height=1, width=12, c=(1,1,1))
                self.KB.update({nts[ik]+str(ioct+1) : tb})
                if not nts[ik] in ("E","B"): #black keys
                    tn=self.vp.box(pos=(x+wb/2,-0, 1), length=wb*.6, height=1, width=8, c=(0,0,0))
                    self.KB.update({nts[ik]+"#"+str(ioct+1) : tn})


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
    
    
    #####################################################################
    def playKeyboard(self):
        
        print("\nPlaying now at speed:", self.rate)
        print("Right-mouse click to move 3D scene.")
        print("Press <esc> at any time to quit.")

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
        
        while True:
            
            if self.rightHand:
                for i, n in enumerate(handR.noteseq):##################### RIGHT
                    start, stop, f = n.time, n.time+n.duration, n.fingering
                    if stop <= t <= stop+dt and engagedkeysR[i]:  ###release key
                        engagedkeysR[i]    = False
                        engagedfingersR[f] = False
    
                        name = nameof(n)
                        ts   = self.KB[name]
                        #print t, '\t..release', name
                        ts.rotateX(angle=-0.15)
                        vphandR[f].rotateX(angle= +0.2, origin=(vphandR[f].x, 3.5, 7.5))
                        #if "#" in name: ts.color = vp.color.black
                        #else: ts.color = vp.color.white
                
                if t>fineR+dt: break
                
                for i, n in enumerate(handR.noteseq):##################### RIGHT
                    start, stop, f = n.time, n.time+n.duration, n.fingering
    
                    ### press key n with finger f
                    if start <= t < stop and not engagedkeysR[i] and not engagedfingersR[f]: 
                        engagedkeysR[i]    = True
                        engagedfingersR[f] = True
    
                        name = nameof(n)
                        ts   = self.KB[name]
                        #print t, '\tpressing', name, start,'->', stop, ' \tfinger=', f
                        
                        if i>=len(handR.fingerseq): return                    
                        for g in [1,2,3,4,5]: vphandR[g].x = handR.fingerseq[i][g]
                        vphandR[f].rotateX(angle= -0.2, origin=(vphandR[f].x, 3.5, 7.5))
                        vphandR[0].x = vphandR[3].x+0.2 # index 0 is palm
                        ts.rotateX(angle= +0.15)                   ### press key
                        #ts.color = (0.604,0.808,0.875)#154 206 223
                        
                        if self.playsounds: self.playsound(n)
            
            ##########################################################            
            if self.leftHand:
                for i, n in enumerate(handL.noteseq):##################### LEFT
                    start, stop, f = n.time, n.time+n.duration, n.fingering
                    if stop <= t <= stop+dt and engagedkeysL[i]:  ###release key
                        engagedkeysL[i]    = False
                        engagedfingersL[f] = False
    
                        name = nameof(n)
                        ts   = self.KB[name]
                        #print t, '\t..release', name
                        ts.rotateX(angle=-0.15)
                        vphandL[f].rotateX(angle= +0.2, origin=(vphandL[f].x, 1.5, 7.5))
                        #if "#" in name: ts.color = vp.color.black
                        #else: ts.color = vp.color.white
                
                if t>fineL+dt: break
                
                for i, n in enumerate(handL.noteseq):##################### LEFT
                    start, stop, f = n.time, n.time+n.duration, n.fingering
    
                    ### press key n with finger f
                    if start <= t < stop and not engagedkeysL[i] and not engagedfingersL[f]: 
                        engagedkeysL[i]    = True
                        engagedfingersL[f] = True
    
                        name = nameof(n)
                        ts   = self.KB[name]
                        #print t, '\tpressing', name, start,'->', stop, ' \tfinger=', f
                        
                        if i>=len(handL.fingerseq): return
                        for g in [5,4,3,2,1]: vphandL[g].x = -handL.fingerseq[i][g]
                        vphandL[f].rotateX(angle= -0.2, origin=(vphandL[f].x, 1.5, 7.5))
                        vphandL[0].x = vphandL[3].x+0.2 # index 0 is palm
                        ts.rotateX(angle= +0.15)                   ### press key
                        #ts.color = (0.604,0.808,0.875)#154 206 223
                        
                        if self.playsounds and not self.rightHand: self.playsound(n)
                            
            t += dt #time flows

   
##############################################
def nameof(n):
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


#################################################################### test
if __name__ == "__main__":

    vk = VirtualKeyboard()
    vk.build_RH(None)
    vk.build_LH(None)

    vk.vp.show(zoom=2)

    # from music21.note import Note
    # n = Note('A-', quarterLength=1.5)
    # vk.playsound(n)




