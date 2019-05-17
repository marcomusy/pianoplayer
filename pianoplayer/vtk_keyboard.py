#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         VirtualKeyboard
# Purpose:      Find optimal fingering for piano scores
# URL:          https://github.com/marcomusy/pianoplayer
# Author:       Marco Musy
#-------------------------------------------------------------------------------
from __future__ import division, print_function

try:
    import time
    from vtkplotter import Plotter, printc
    from vtkplotter.shapes import Ellipsoid, Box, Cylinder, Text
    from vtkplotter import Assembly
except:
    print("VirtualKeyboard: cannot find vtkplotter package. Not installed?")
    print('Try:\n(sudo) pip install --upgrade vtkplotter')
    quit()

from pianoplayer import __version__
from pianoplayer.utils import fpress, frelease, kpress, krelease, nameof
from pianoplayer.wavegenerator import playSound
import pianoplayer.utils as utils


###########################################################
class VirtualKeyboard:

    def __init__(self, songname=''):
                         
        self.KB = dict()
        self.vp = None
        self.rightHand = None
        self.leftHand  = None
        self.vpRH = None
        self.vpLH = None
        self.playsounds = True
        self.verbose = True
        self.songname = songname
        self.t0 = 0 # keep track of how many seconds to play
        self.dt = 0.1
        self.speedfactor = 1
        self.engagedfingersR = [False]*6 # element 0 is dummy
        self.engagedfingersL = [False]*6 
        self.engagedkeysR    = []
        self.engagedkeysL    = []

        self.build_keyboard() 

    #######################################################
    def makeHandActor(self, f=1):
        a1, a2, a3, c = (10*f,0,0), (0,7*f,0), (0,0,3*f), (.7,0.3,0.3)
        palm = Ellipsoid(pos=(0,-3,0), axis1=a1, axis2=a2, axis3=a3, alpha=0.6, c=c)
        wrist= Box(pos=(0,-9,0), length=6*f, width=5, height=2, alpha=0.4, c=c)
        arm  = Assembly([palm,wrist])
        self.vp.actors.append(arm) # add actor to internal list
        f1 = self.vp.add(Cylinder((-2, 1.5,0), axis=(0,1,0), height=5, r=.8*f, c=c))
        f2 = self.vp.add(Cylinder((-1, 3  ,0), axis=(0,1,0), height=6, r=.7*f, c=c))
        f3 = self.vp.add(Cylinder(( 0, 4  ,0), axis=(0,1,0), height=6.2, r=.75*f, c=c))
        f4 = self.vp.add(Cylinder(( 1, 3.5,0), axis=(0,1,0), height=6.1, r=.7*f, c=c))
        f5 = self.vp.add(Cylinder(( 2, 2  ,0), axis=(0,1,0), height=5, r=.6*f, c=c))
        return [arm, f1,f2,f3,f4,f5]

    def build_RH(self, hand):    
        if self.verbose: print('Building Right Hand..')
        self.rightHand = hand
        f = utils.handSizeFactor(hand.size)
        self.vpRH = self.makeHandActor(f)
        for limb in self.vpRH: # initial x positions are superseded later
            limb.x( limb.x()* 2.5 )
            limb.addPos([16.5*5+1, -7.5, 3] ) # vtkplotter < 8.7.1 was addpos()

    def build_LH(self, hand): #########################
        if self.verbose: print('Building Left Hand..')
        self.leftHand = hand
        f = utils.handSizeFactor(hand.size)
        self.vpLH = self.makeHandActor(f)
        for limb in self.vpLH: 
            limb.x( limb.x()* 2.5 ) 
            limb.addPos([16.5*3+1, -7.5, 3] ) # vtkplotter < 8.7.1 was addpos()
               

    #######################################################
    def build_keyboard(self):
        
        if self.verbose: print('Building Keyboard..')
        nts = ("C","D","E","F","G","A","B")
        tol = 0.12
        keybsize = 16.5 # in cm, span of one octave
        wb = keybsize/7
        nr_octaves = 7
        span = nr_octaves*wb*7
    
        self.vp = Plotter(title='PianoPlayer '+__version__, axes=0, size=(700,1400), bg='lb', verbose=0)

        #wooden top and base
        self.vp.add(Box(pos=(span/2+keybsize, 6,  1), length=span+1, height=3, width= 5).texture('wood5')) #top
        self.vp.add(Box(pos=(span/2+keybsize, 0, -1), length=span+1, height=1, width=17).texture('wood5'))
        self.vp.add(Text('PianoPlayer '+__version__, pos=(18, 5.5, 2), depth=.7, c='w'))
        self.vp.add(Text('https://github.com/marcomusy/pianoplayer', pos=(105,4.8,2), depth=.7, c='w', s=.8))
        leggio = self.vp.add(Box(pos=(span/1.55,8,10), length=span/2, height=span/8, width=0.08, c=(1,1,0.9)))
        leggio.rotateX(-20)
        self.vp.add(Text('Playing\n\n'+self.songname, pos=[0,0,0], s=1.2, c='k').rotateX(70).pos([49,7,9]))

        for ioct in range(nr_octaves):
            for ik in range(7):              #white keys
                x  = ik * wb + (ioct+1)*keybsize +wb/2
                tb = self.vp.add(Box(pos=(x,-2,0), length=wb-tol, height=1, width=12, c='white'))
                self.KB.update({nts[ik]+str(ioct+1) : tb})
                if not nts[ik] in ("E","B"): #black keys
                    tn=self.vp.add(Box(pos=(x+wb/2,0,1), length=wb*.6, height=1, width=8, c='black'))
                    self.KB.update({nts[ik]+"#"+str(ioct+1) : tn})
        self.vp.show(interactive=0)
        self.vp.camera.Azimuth(4)
        self.vp.camera.Elevation(-30)


    #####################################################################
    def play(self):
        printc('Press [0-9] to proceed by one note or for more seconds', c=1)
        printc('Press Esc to exit.', c=1)
        self.vp.keyPressFunction = self.runTime    # enable observer

        if self.rightHand:
            self.engagedkeysR    = [False]*len(self.rightHand.noteseq)
            self.engagedfingersR = [False]*6  # element 0 is dummy
        if self.leftHand:           
            self.engagedkeysL    = [False]*len(self.leftHand.noteseq)
            self.engagedfingersL = [False]*6        

        t=0.0
        while True:
            if self.rightHand: self._moveHand( 1, t)
            if self.leftHand:  self._moveHand(-1, t)
            if t > 1000: break                                         
            t += self.dt                      # absolute time flows
        
        if self.verbose: printc('End of note sequence reached.')
        self.vp.keyPressFunction = None       # disable observer

    ###################################################################
    def _moveHand(self, side, t):############# runs inside play() loop
        if side == 1: 
            c1,c2 = 'tomato', 'orange'
            engagedkeys    = self.engagedkeysR
            engagedfingers = self.engagedfingersR
            H              = self.rightHand
            vpH            = self.vpRH
        else:               
            c1,c2 = 'purple', 'mediumpurple'
            engagedkeys    = self.engagedkeysL
            engagedfingers = self.engagedfingersL
            H              = self.leftHand
            vpH            = self.vpLH

        for i, n in enumerate(H.noteseq):##################### 
            start, stop, f = n.time, n.time+n.duration, n.fingering
            if isinstance(f, str): continue
            if f and stop <= t <= stop+self.dt and engagedkeys[i]: #release key
                engagedkeys[i]    = False
                engagedfingers[f] = False
                name = nameof(n)
                krelease(self.KB[name])
                frelease(vpH[f])
                self.vp.interactor.Render()

        for i, n in enumerate(H.noteseq):##################### 
            start, stop, f = n.time, n.time+n.duration, n.fingering   
            if isinstance(f, str):
                print('Warning: cannot understand lyrics:',f, 'skip note',i)
                continue
            if f and start <= t < stop and not engagedkeys[i] and not engagedfingers[f]: #press key
                if i >= len(H.fingerseq): return                    
                engagedkeys[i]    = True
                engagedfingers[f] = True
                name = nameof(n)
                
                if t> self.t0 + self.vp.clock: 
                    self.t0 = t
                    self.vp.show(zoom=2, interactive=True)

                for g in [1,2,3,4,5]: 
                    vpH[g].x( side * H.fingerseq[i][g] ) 
                vpH[0].x(vpH[3].x()) # index 0 is arm, put it where middle finger is
                
                fpress(vpH[f],  c1)
                kpress(self.KB[name], c2)
                self.vp.show(zoom=2, interactive=False)

                if self.verbose:
                    msg = 'meas.'+str(n.measure)+' t='+str(round(t,2))
                    if side==1: printc(msg,'\t\t\t\tRH.finger', f, 'hit', name, c='b')
                    else:       printc(msg,      '\tLH.finger', f, 'hit', name, c='m')

                if self.playsounds: 
                    playSound(n, self.speedfactor)
                else: 
                    time.sleep(n.duration*self.speedfactor)


    ##########################################
    def runTime(self, key):
        secs = [str(i) for i in range(10)]
        if key not in secs: return
        printc('Will execute score for '+key+' seconds')
        self.vp.interactive = False
        self.vp.clock = int(key)
        self.vp.interactor.ExitCallback()


############################ test
if __name__ == "__main__":

    vk = VirtualKeyboard('Chopin Valse in A minor')
    vk.build_LH(None)

    fpress(vk.vpLH[1], 'b')
    kpress(vk.KB['E3'], 'db')
    vk.vp.show(zoom=2, interactive=1)

    frelease(vk.vpLH[1])
    krelease(vk.KB['E3'])
    vk.vp.show(zoom=2, interactive=1)





