#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Name:         VirtualKeyboard
# Purpose:      Find optimal fingering for piano scores
# URL:          https://github.com/marcomusy/pianoplayer
# Author:       Marco Musy
#-------------------------------------------------------------------------------
import logging

try:
    from vedo import Assembly, Box, Cylinder, Ellipsoid, Plotter, Text3D, dataurl, printc
except ImportError as exc:
    Plotter = Assembly = printc = Ellipsoid = Box = Cylinder = Text3D = None
    dataurl = ""
    _VEDO_IMPORT_ERROR = exc
else:
    _VEDO_IMPORT_ERROR = None

from pianoplayer import __version__
from pianoplayer.hand import Hand
from pianoplayer.wavegenerator import playSound

logger = logging.getLogger(__name__)


def nameof(n):
    """Return a normalized pitch name used by the keyboard actor map."""
    a = n.name + str(n.octave)
    if "--" in a:
        b = a.replace("B--", "A")
        b = b.replace("A--", "G")
        b = b.replace("G--", "F")
        b = b.replace("E--", "D")
        b = b.replace("D--", "C")
        return b
    if "-" in a:
        b = a.replace("C-", "B")
        b = b.replace("D-", "C#")
        b = b.replace("E-", "D#")
        b = b.replace("F-", "E")
        b = b.replace("G-", "F#")
        b = b.replace("A-", "G#")
        b = b.replace("B-", "A#")
        return b
    if "##" in a:
        b = a.replace("C##", "D")
        b = b.replace("D##", "E")
        b = b.replace("F##", "G")
        b = b.replace("G##", "A")
        b = b.replace("A##", "B")
        return b
    if "E#" in a:
        return a.replace("E#", "F")
    if "B#" in a:
        return a.replace("B#", "C")
    return a


###########################################################
class VirtualKeyboard:
    """3D keyboard player that animates left/right-hand fingering over time."""

    def __init__(self, songname=''):
        """Initialize keyboard scene, actors, and playback state."""
        if Plotter is None:
            raise ImportError("vedo is required for 3D playback") from _VEDO_IMPORT_ERROR

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
        self._release_idx_R = 0
        self._release_idx_L = 0
        self._press_idx_R = 0
        self._press_idx_L = 0
        self._abort_playback = False
        self.build_keyboard()

    ################################################################################
    def makeHandActor(self, f=1):
        """Create and register a simple hand actor assembly."""
        a1, a2, a3, c = (5*f,0,0), (0,3.5*f,0), (0,0,1.5*f), (.7,0.3,0.3)
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
        """Attach and place the right-hand actor model."""
        self.rightHand = hand
        f = getattr(hand, "hf", Hand.size_factor(hand.size))
        self.vpRH = self.makeHandActor(f)
        for limb in self.vpRH: # initial x positions are superseded later
            limb.x( limb.x()* 2.5 )
            limb.shift(16.5 * 5 + 1, -7.5, 3)

    def build_LH(self, hand): ########################Build Left Hand
        """Attach and place the left-hand actor model."""
        self.leftHand = hand
        f = getattr(hand, "hf", Hand.size_factor(hand.size))
        self.vpLH = self.makeHandActor(f)
        for limb in self.vpLH:
            limb.x( limb.x()* 2.5 )
            limb.shift(16.5 * 3 + 1, -7.5, 3)


    #######################################################Build Keyboard
    def build_keyboard(self):
        """Build the 3D keyboard scene and static decorative elements."""
        nts = ("C","D","E","F","G","A","B")
        tol = 0.12
        keybsize = 16.5 # in cm, span of one octave
        wb = keybsize/7
        nr_octaves = 7
        span = nr_octaves*wb*7

        self.vp = Plotter(title='PianoPlayer '+__version__,
                          axes=0, size=(1400,700), bg='cornsilk', bg2='lb')

        # wooden top and base
        top_box = Box(pos=(span / 2 + keybsize, 6, 1), length=span + 1, height=3, width=5)
        top_box.texture(dataurl + "textures/wood1.jpg")
        self.vp += top_box

        base_box = Box(pos=(span / 2 + keybsize, 0, -1), length=span + 1, height=1, width=17)
        base_box.texture(dataurl + "textures/wood1.jpg")
        self.vp += base_box

        title_text = Text3D(
            'PianoPlayer ^'+__version__+" ",
            pos=(18, 5., 2.3),
            depth=.5,
            c='silver',
            italic=0.8,
        )
        self.vp += title_text

        leggio_box = Box(
            pos=(span / 1.55, 8, 10),
            length=span / 2,
            height=span / 8,
            width=0.08,
            c=(1, 1, 0.9),
        )
        leggio_box.rotate(-20, axis=(1, 0, 0))
        leggio_box.texture(dataurl + "textures/paper1.jpg")
        self.vp += leggio_box

        song_text = Text3D(
            'Playing:\n'+self.songname[-30:].replace('_',"\\_"),
            font="Theemim",
            vspacing=3,
            depth=0.04,
            s=1.35,
            c='k',
            italic=0.5,
        )
        song_text.rotate(70, axis=(1, 0, 0))
        song_text.pos([55, 10, 6])
        self.vp += song_text

        for ioct in range(nr_octaves):
            for ik in range(7):              #white keys
                x  = ik * wb + (ioct+1)*keybsize +wb/2
                tb = Box(pos=(x,-2,0), length=wb-tol, height=1, width=12, c='white')
                self.KB.update({nts[ik]+str(ioct+1) : tb})
                self.vp += tb
                if nts[ik] not in ("E","B"): #black keys
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
        """Run playback loop until sequence end or user abort."""

        printc('Press space to proceed by one note', c=1)
        printc('Press Esc to exit.', c=1)

        if self.rightHand:
            self.engagedkeysR    = [False]*len(self.rightHand.noteseq)
            self.engagedfingersR = [False]*6  # element 0 is dummy
            self._release_idx_R = 0
            self._press_idx_R = 0
        if self.leftHand:
            self.engagedkeysL    = [False]*len(self.leftHand.noteseq)
            self.engagedfingersL = [False]*6
            self._release_idx_L = 0
            self._press_idx_L = 0

        t=0.0
        while True:
            if self._abort_playback:
                break
            if self.rightHand:
                self._moveHand(1, t)
            if self.leftHand:
                self._moveHand(-1, t)
            if t > 1000:
                break
            t += self.dt                      # absolute time flows

        if self.verbose:
            printc('End of note sequence reached.')
        self.vp.keyPressFunction = None       # disable observer

    def _wait_for_advance_key(self):
        """Block until Space (advance) or Esc (abort) is pressed."""
        interactor = getattr(self.vp, "interactor", None)
        if interactor is None:
            return

        state = {"abort": False}

        def _on_key(evt):
            key = getattr(evt, "keypress", "") or getattr(evt, "keyPressed", "")
            if key in ("Escape", "Esc"):
                state["abort"] = True
                try:
                    interactor.ExitCallback()
                except Exception:
                    pass
                return
            if key in ("space", " ", "Return", "KP_Enter"):
                try:
                    interactor.ExitCallback()
                except Exception:
                    pass

        cid = None
        try:
            cid = self.vp.add_callback("KeyPress", _on_key)
            interactor.Start()
        except (AttributeError, RuntimeError) as exc:
            logger.debug("Key wait unavailable: %s", exc)
            return
        finally:
            if cid is not None:
                try:
                    self.vp.remove_callback(cid)
                except (AttributeError, RuntimeError):
                    logger.debug("Unable to remove key callback.")

        if state["abort"]:
            self._abort_playback = True

    def _safe_refresh(self, interactive=False):
        """Refresh viewport without crashing on renderer lifecycle differences."""
        try:
            if hasattr(self.vp, "renderer") and self.vp.renderer is not None:
                self.vp.render()
            else:
                self.vp.show(interactive=interactive, resetcam=False)
        except (AttributeError, RuntimeError):
            # Some vedo versions transiently expose a None renderer during updates.
            logger.debug("Viewport refresh skipped: renderer/interactor unavailable.")

    def _fpress(self, finger_actor, color):
        """Animate finger press."""
        finger_actor.rotate_x(-20, around=finger_actor.pos())
        finger_actor.shift(0, 0, -1)
        finger_actor.color(color)

    def _frelease(self, finger_actor):
        """Animate finger release."""
        finger_actor.shift(0, 0, 1)
        finger_actor.rotate_x(20, around=finger_actor.pos())
        finger_actor.color((0.7, 0.3, 0.3))

    def _kpress(self, key_actor, color):
        """Animate piano key press."""
        key_actor.rotate_x(4, around=key_actor.pos())
        key_actor.shift(0, 0, -0.4)
        key_actor.color(color)

    def _krelease(self, key_actor):
        """Animate piano key release."""
        key_actor.shift(0, 0, 0.4)
        p = key_actor.pos()
        key_actor.rotate_x(-4, around=p)
        if p[2] > 0.5:
            key_actor.color("k")
        else:
            key_actor.color("w")

    ###################################################################
    def _moveHand(self, side, t):############# runs inside play() loop
        """Advance one hand state for the given absolute time."""

        if side == 1:
            c1, c2         = 'tomato', 'orange'
            engagedkeys    = self.engagedkeysR
            engagedfingers = self.engagedfingersR
            H              = self.rightHand
            vpH            = self.vpRH
            release_idx = self._release_idx_R
            press_idx = self._press_idx_R
        else:
            c1, c2         = 'purple', 'mediumpurple'
            engagedkeys    = self.engagedkeysL
            engagedfingers = self.engagedfingersL
            H              = self.leftHand
            vpH            = self.vpLH
            release_idx = self._release_idx_L
            press_idx = self._press_idx_L
        notes = H.noteseq
        total = len(notes)

        while release_idx < total:
            n = notes[release_idx]
            stop = n.time + n.duration
            f = n.fingering
            if isinstance(f, str):
                release_idx += 1
                continue
            if stop > t:
                break
            if f and engagedkeys[release_idx]:
                engagedkeys[release_idx] = False
                engagedfingers[f] = False
                name = nameof(n)
                self._krelease(self.KB[name])
                self._frelease(vpH[f])
                self._safe_refresh(interactive=False)
            release_idx += 1

        while press_idx < total:
            n = notes[press_idx]
            start, stop, f = n.time, n.time + n.duration, n.fingering
            if isinstance(f, str):
                logger.warning(
                    "Cannot understand lyrics fingering '%s'; skipping note index %s", f, press_idx
                )
                press_idx += 1
                continue

            if start > t:
                break
            if t >= stop:
                press_idx += 1
                continue
            if not (f and not engagedkeys[press_idx] and not engagedfingers[f]):
                break

            if press_idx >= len(H.fingerseq):
                break
            engagedkeys[press_idx] = True
            engagedfingers[f] = True
            name = nameof(n)

            if t > self.t0 + self.vp.clock:
                self.t0 = t
                self._safe_refresh(interactive=False)

            for g in [1, 2, 3, 4, 5]:
                vpH[g].x(side * H.fingerseq[press_idx][g])
            vpH[0].x(vpH[3].x())

            self._fpress(vpH[f], c1)
            self._kpress(self.KB[name], c2)

            if self.verbose:
                msg = 'meas.' + str(n.measure) + ' t=' + str(round(t, 2))
                if side == 1:
                    printc(msg, '\t\t\t\tRH.finger', f, 'hit', name, c='b')
                else:
                    printc(msg, '\tLH.finger', f, 'hit', name, c='m')

            self._safe_refresh(interactive=False)
            if self.playsounds:
                playSound(n, self.speedfactor, wait=True)

            self._wait_for_advance_key()
            press_idx += 1
            if self._abort_playback:
                break

        if side == 1:
            self._release_idx_R = release_idx
            self._press_idx_R = press_idx
        else:
            self._release_idx_L = release_idx
            self._press_idx_L = press_idx


############################ test
if __name__ == "__main__":
    vk = VirtualKeyboard('Chopin Valse in A minor')
    vk.vp.show(interactive=1, resetcam=0)
