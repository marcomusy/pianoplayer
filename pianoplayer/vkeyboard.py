#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Name:         VirtualKeyboard
# Purpose:      Find optimal fingering for piano scores
# URL:          https://github.com/marcomusy/pianoplayer
# Author:       Marco Musy
#-------------------------------------------------------------------------------
try:
    from vedo import Plotter, Assembly, printc
    from vedo import Ellipsoid, Box, Cylinder, Text
except:
    pass

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

    ################################################################################
    def makeHandActor(self, f=1):
        a1, a2, a3, c = (10*f,0,0), (0,7*f,0), (0,0,3*f), (.7,0.3,0.3)
        palm = Ellipsoid(pos=(0,-3,0), axis1=a1, axis2=a2, axis3=a3, alpha=0.6, c=c)
        wrist= Box(pos=(0,-9,0), length=6*f, width=5, height=2, alpha=0.4, c=c)
        arm  = Assembly([palm,wrist])
        f1 = Cylinder((-2, 1.5,0), axis=(0,1,0), height=5, r=.8*f, c=c)
        f2 = Cylinder((-1, 3  ,0), axis=(0,1,0), height=6, r=.7*f, c=c)
        f3 = Cylinder(( 0, 4  ,0), axis=(0,1,0), height=6.2, r=.75*f, c=c)
        f4 = Cylinder(( 1, 3.5,0), axis=(0,1,0), height=6.1, r=.7*f, c=c)
        f5 = Cylinder(( 2, 2  ,0), axis=(0,1,0), height=5, r=.6*f, c=c)
        self.vp += [arm, f1,f2,f3,f4,f5] # add actors to internal list
        return [arm, f1,f2,f3,f4,f5]

    def build_RH(self, hand): #########################Build Right Hand
        self.rightHand = hand
        f = utils.handSizeFactor(hand.size)
        self.vpRH = self.makeHandActor(f)
        for limb in self.vpRH: # initial x positions are superseded later
            limb.x( limb.x()* 2.5 )
            limb.addPos([16.5*5+1, -7.5, 3] )

    def build_LH(self, hand): ########################Build Left Hand
        self.leftHand = hand
        f = utils.handSizeFactor(hand.size)
        self.vpLH = self.makeHandActor(f)
        for limb in self.vpLH:
            limb.x( limb.x()* 2.5 )
            limb.addPos([16.5*3+1, -7.5, 3] )


    #######################################################Build Keyboard
    def build_keyboard(self):
        nts = ("C","D","E","F","G","A","B")
        tol = 0.12
        keybsize = 16.5 # in cm, span of one octave
        wb = keybsize/7
        nr_octaves = 7
        span = nr_octaves*wb*7

        self.vp = Plotter(title='PianoPlayer '+__version__,
                          axes=0, size=(1400,700), bg='cornsilk', bg2='lb')

        #wooden top and base
        self.vp += Box(pos=(span/2+keybsize, 6, 1),
                       length=span+1, height=3, width= 5).texture('wood1')
        self.vp += Box(pos=(span/2+keybsize, 0, -1),
                       length=span+1, height=1, width=17).texture('wood1')
        self.vp += Text('PianoPlayer ^'+__version__+" ",
                        pos=(18, 5., 2.3), depth=.5, c='silver', italic=0.8)
        leggio = Box(pos=(span/1.55,8,10),
                     length=span/2, height=span/8, width=0.08, c=(1,1,0.9)).rotateX(-20)
        self.vp += leggio.texture('paper1')
        self.vp += Text('Playing:\n'+self.songname[-30:].replace('_',"\\_"), font="Theemim",
                        vspacing=3, depth=0.04, s=1.35, c='k', italic=0.5
                       ).rotateX(70).pos([55,10,6])

        for ioct in range(nr_octaves):
            for ik in range(7):              #white keys
                x  = ik * wb + (ioct+1)*keybsize +wb/2
                tb = Box(pos=(x,-2,0), length=wb-tol, height=1, width=12, c='white')
                self.KB.update({nts[ik]+str(ioct+1) : tb})
                self.vp += tb
                if not nts[ik] in ("E","B"): #black keys
                    tn = Box(pos=(x+wb/2,0,1), length=wb*.6, height=1, width=8, c='black')
                    self.KB.update({nts[ik]+"#"+str(ioct+1) : tn})
                    self.vp += tn
        cam = dict(pos=(110, -51.1, 89.1),
                   focalPoint=(81.5, 0.531, 2.82),
                   viewup=(-0.163, 0.822, 0.546),
                   distance=105, clippingRange=(41.4, 179))
        self.vp.show(interactive=0, camera=cam, resetcam=0)


    #####################################################################
    def play(self):

        printc('Press space to proceed by one note', c=1)
        printc('Press Esc to exit.', c=1)

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
            c1, c2         = 'tomato', 'orange'
            engagedkeys    = self.engagedkeysR
            engagedfingers = self.engagedfingersR
            H              = self.rightHand
            vpH            = self.vpRH
        else:
            c1, c2         = 'purple', 'mediumpurple'
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
                if hasattr(self.vp, 'interactor'):
                    self.vp.render()

        for i, n in enumerate(H.noteseq):#####################
            start, stop, f = n.time, n.time+n.duration, n.fingering
            if isinstance(f, str):
                print('Warning: cannot understand lyrics:',f, 'skip note',i)
                continue
            if f and start <= t < stop and not engagedkeys[i] and not engagedfingers[f]:
                # press key
                if i >= len(H.fingerseq): return
                engagedkeys[i]    = True
                engagedfingers[f] = True
                name = nameof(n)

                if t> self.t0 + self.vp.clock:
                    self.t0 = t
                    self.vp.show(interactive=False, resetcam=False)

                for g in [1,2,3,4,5]:
                    vpH[g].x( side * H.fingerseq[i][g] )
                vpH[0].x(vpH[3].x()) # index 0 is arm, put it where middle finger is

                fpress(vpH[f],  c1)
                kpress(self.KB[name], c2)

                if self.verbose:
                    msg = 'meas.'+str(n.measure)+' t='+str(round(t,2))
                    if side==1: printc(msg,'\t\t\t\tRH.finger', f, 'hit', name, c='b')
                    else:       printc(msg,      '\tLH.finger', f, 'hit', name, c='m')

                if self.playsounds:
                    self.vp.show(interactive=False, resetcam=False)
                    playSound(n, self.speedfactor, wait=True)
                    if hasattr(self.vp, 'interactor'):
                        self.vp.interactor.Start()
                else:
                    self.vp.show(interactive=1, resetcam=0)


############################ test
if __name__ == "__main__":
    vk = VirtualKeyboard('Chopin Valse in A minor')
    vk.vp.show(interactive=1, resetcam=0)


