#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:         VirtualKeyboard
# Purpose:      Find optimal fingering for piano scores
# URL:          https://github.com/marcomusy/pianoplayer
# Author:       Marco Musy
#-------------------------------------------------------------------------------
from __future__ import division, print_function
try:
    import vtk, time
    from vtkplotter import Plotter, printc
    from vtkplotter.shapes import ellipsoid, box
    from vtkplotter.utils import makeAssembly
except:
    print("VirtualKeyboard: cannot find vtk or vtkplotter packages. Not installed?")
    print('Try: (sudo) pip install --upgrade vtkplotter')
    quit()

from pianoplayer import __version__
from pianoplayer.utils import fpress, frelease, kpress, krelease, nameof
from pianoplayer.wavegenerator import playSound


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
    def makeHandActor(self):
        a1, a2, a3, c = (10,0,0), (0,7,0), (0,0,3), (.7,0.3,0.3)
        palm = ellipsoid(pos=(0,-3,0), axis1=a1, axis2=a2, axis3=a3, alpha=0.6, c=c)
        wrist= box(pos=(0,-9,0), length=6, width=5, height=2, alpha=0.4, c=c)
        arm  = makeAssembly([palm,wrist])
        self.vp.actors.append(arm) # add actor to internal list
        f1 = self.vp.cylinder((-2, 1.5,0), axis=(0,1,0), height=5, r=.8, c=c)
        f2 = self.vp.cylinder((-1, 3  ,0), axis=(0,1,0), height=6, r=.7, c=c)
        f3 = self.vp.cylinder(( 0, 4  ,0), axis=(0,1,0), height=6.2, r=.75, c=c)
        f4 = self.vp.cylinder(( 1, 3.5,0), axis=(0,1,0), height=6.1, r=.7, c=c)
        f5 = self.vp.cylinder(( 2, 2  ,0), axis=(0,1,0), height=5, r=.6, c=c)
        return [arm, f1,f2,f3,f4,f5]

    def build_RH(self, hand):    
        if self.verbose: print('Building Right Hand..')
        self.rightHand = hand
        self.vpRH = self.makeHandActor()
        for limb in self.vpRH: # initial x positions are superseded later
            limb.x( limb.x()* 2.5 )
            limb.addpos([16.5*5+1, -7.5, 3] )

    def build_LH(self, hand): #########################
        if self.verbose: print('Building Left Hand..')
        self.leftHand = hand
        self.vpLH = self.makeHandActor()
        for limb in self.vpLH: 
            limb.x( limb.x()* -2.5 ) #flip
            limb.addpos([16.5*3+1, -7.5, 3] )
               

    #######################################################
    def build_keyboard(self):
        
        if self.verbose: print('Building Keyboard..')
        nts = ("C","D","E","F","G","A","B")
        tol = 0.12
        keybsize = 16.5 # in cm, span of one octave
        wb = keybsize/7
        nr_octaves = 7
        span = nr_octaves*wb*7
    
        self.vp = Plotter(title='PianoPlayer '+__version__, axes=0, size=(1200,600), bg='lb', verbose=0)

        #wooden top and base
        self.vp.box(pos=(span/2+keybsize, 6,  1), length=span+1, height=3, width= 5, texture='wood5') #top
        self.vp.box(pos=(span/2+keybsize, 0, -1), length=span+1, height=1, width=17, texture='wood5')
        self.vp.text('PianoPlayer '+__version__, pos=(18, 5.5, 2), depth=.7)
        self.vp.text('https://github.com/marcomusy/pianoplayer', pos=(105,4.8,2), depth=.7, s=.8)
        leggio = self.vp.box(pos=(span/1.55,8,10), length=span/2, height=span/8, width=0.08, c=(1,1,0.9))
        leggio.rotateX(-20)
        self.vp.text('Playing\n\n'+self.songname, s=1.2).rotateX(70).pos([49,11,9])

        for ioct in range(nr_octaves):
            for ik in range(7):              #white keys
                x  = ik * wb + (ioct+1)*keybsize +wb/2
                tb = self.vp.box(pos=(x,-2,0), length=wb-tol, height=1, width=12, c='white')
                self.KB.update({nts[ik]+str(ioct+1) : tb})
                if not nts[ik] in ("E","B"): #black keys
                    tn=self.vp.box(pos=(x+wb/2,0,1), length=wb*.6, height=1, width=8, c='black')
                    self.KB.update({nts[ik]+"#"+str(ioct+1) : tn})
        self.vp.show(interactive=0)
        self.vp.camera.Azimuth(4)
        self.vp.camera.Elevation(-30)


    #####################################################################
    def play(self):
        printc('\nPress space to proceed one note',1)
        printc('Press [5-9] to proceed for more seconds',1)
        printc('Press Esc to exit.',1)
        self.vp.keyPressFunction = runTime # enable observer

        startR,startL, fineR,fineL = 9999,9999, 0,0

        if self.rightHand:
            self.engagedkeysR    = [False]*len(self.rightHand.noteseq)
            self.engagedfingersR = [False]*6         # element 0 is dummy
            startR = self.rightHand.noteseq[0].time  #start time of first note
            fineR  = self.rightHand.noteseq[-1].time #end time
        if self.leftHand:           
            self.engagedkeysL    = [False]*len(self.leftHand.noteseq)
            self.engagedfingersL = [False]*6         # element 0 is dummy
            startL = self.leftHand.noteseq[0].time   #start time of first note
            fineL  = self.leftHand.noteseq[-1].time  #end time
        fine = max(fineR, fineL)

        t = min(startR, startL)
        while True:
            if self.rightHand: self.moveHand( 1, t)
            if self.leftHand:  self.moveHand(-1, t)
            if t > fine: break                                         
            t += self.dt #time flows
        
        if self.verbose: printc('End of note sequence reached.')
        self.vp.keyPressFunction = None # disable observer

    #####################################################################
    def moveHand(self, side, t):########runs inside play() loop
        if side == 1: 
            c1,c2 = 'tomato', 'orange'
            engagedkeys    = self.engagedkeysR
            engagedfingers = self.engagedfingersR
            H = self.rightHand
            vpH = self.vpRH
        else:               
            c1,c2 = 'purple', 'mediumpurple'
            engagedkeys    = self.engagedkeysL
            engagedfingers = self.engagedfingersL
            H = self.leftHand
            vpH = self.vpLH

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
                
                for g in [1,2,3,4,5]: vpH[g].x( side * H.fingerseq[i][g] ) 
                vpH[0].x(vpH[3].x()) # index 0 is arm, put it where middle finger is
                
                fpress(vpH[f],  c1)
                kpress(self.KB[name], c2)
                if t> self.t0 + self.vp.clock: 
                    self.vp.interactive = True
                    self.t0 = t
                self.vp.show(zoom=2)

                if self.verbose:
                    msg = 'meas.'+str(n.measure+1)+' t='+str(round(t,2))
                    if side==1: printc((msg,'\t\t\t\tRH.finger', f, 'hit', name), 'b')
                    else:       printc((msg,      '\tLH.finger', f, 'hit', name), 'm')

                if self.playsounds: playSound(n, self.speedfactor)
                else: time.sleep(n.duration*self.speedfactor)


##########################################
def runTime(key, vplt):
    if key not in ['5','6','7','8','9','0']: return
    if key == '0': key='10'
    printc('Will execute score for '+key+' seconds')
    vplt.interactive = False
    vplt.clock = int(key)
    vplt.interactor.ExitCallback()


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





