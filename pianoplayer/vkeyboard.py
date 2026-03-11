#!/usr/bin/env python3
"""3D keyboard visualization and step-by-step playback with vedo."""
import contextlib
import logging

from rich.console import Console

try:
    from vedo import Assembly, Box, Cylinder, Ellipsoid, Plotter, Text2D, Text3D, dataurl
except ImportError as exc:
    Plotter = Assembly = Ellipsoid = Box = Cylinder = Text2D = Text3D = None
    dataurl = ""
    _VEDO_IMPORT_ERROR = exc
else:
    _VEDO_IMPORT_ERROR = None

from pianoplayer import __version__
from pianoplayer.hand import Hand
from pianoplayer.wavegenerator import has_audio_backend, play_sound

logger = logging.getLogger(__name__)
console = Console()


def note_name(n):
    """Return a normalized pitch name used by the keyboard key map."""
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


class VirtualKeyboard:
    """3D keyboard player that animates left/right-hand fingering over time."""

    def __init__(self, songname: str = ""):
        """Initialize keyboard scene, objects, and playback state."""
        if Plotter is None:
            raise ImportError("vedo is required for 3D playback") from _VEDO_IMPORT_ERROR

        self.key_objects = {}
        self.vp = None
        self.right_hand = None
        self.left_hand = None
        self.right_hand_view = None
        self.left_hand_view = None
        self.playsounds = True
        self.verbose = True
        self.songname = songname
        self.t0 = 0  # keep track of how many seconds to play
        self.dt = 0.1
        self.speed_factor = 1
        self.engaged_fingers_r = [False] * 6  # element 0 is dummy
        self.engaged_fingers_l = [False] * 6
        self.engaged_keys_r = []
        self.engaged_keys_l = []
        self._release_idx_r = 0
        self._release_idx_l = 0
        self._press_idx_r = 0
        self._press_idx_l = 0
        self._abort_playback = False
        self._hud_rh = None
        self._hud_lh = None
        self._finger_colors_right = {
            1: (0.76, 0.35, 0.35),
            2: (0.76, 0.40, 0.33),
            3: (0.76, 0.45, 0.31),
            4: (0.76, 0.50, 0.29),
            5: (0.76, 0.55, 0.27),
        }
        self._finger_colors_left = {
            1: (0.32, 0.72, 0.98),
            2: (0.24, 0.64, 0.96),
            3: (0.16, 0.56, 0.92),
            4: (0.10, 0.48, 0.86),
            5: (0.06, 0.40, 0.78),
        }
        self.build_keyboard()

    def make_hand_model(self, f: float = 1, palm_color=(0.7, 0.3, 0.3)):
        """Create and register the palm+fingers vedo objects for one hand."""
        a1, a2, a3 = (5 * f, 0, 0), (0, 3.5 * f, 0), (0, 0, 1.5 * f)
        palm = Ellipsoid(
            pos=(0, -3, 0), axis1=a1, axis2=a2, axis3=a3, alpha=0.6, c=palm_color
        )
        arm = Assembly([palm])
        f1 = Cylinder((-2, 1.5, 0), axis=(0, 1, 0), height=5, r=0.8 * f, c=palm_color)
        f2 = Cylinder((-1, 3, 0), axis=(0, 1, 0), height=6, r=0.7 * f, c=palm_color)
        f3 = Cylinder((0, 4, 0), axis=(0, 1, 0), height=6.2, r=0.75 * f, c=palm_color)
        f4 = Cylinder((1, 3.5, 0), axis=(0, 1, 0), height=6.1, r=0.7 * f, c=palm_color)
        f5 = Cylinder((2, 2, 0), axis=(0, 1, 0), height=5, r=0.6 * f, c=palm_color)
        self.vp += [arm, f1, f2, f3, f4, f5]
        return [arm, f1, f2, f3, f4, f5]

    def build_right_hand(self, hand):
        """Attach and place the right-hand model."""
        self.right_hand = hand
        f = getattr(hand, "hf", Hand.size_factor(hand.size))
        self.right_hand_view = self.make_hand_model(f, palm_color=(0.7, 0.3, 0.3))
        # Initial x positions are superseded later by `fingerseq`.
        for limb in self.right_hand_view:
            limb.x(limb.x() * 2.5)
            limb.shift(16.5 * 5 + 1, -7.5, 3)
        for finger in (1, 2, 3, 4, 5):
            self.right_hand_view[finger].color(self._finger_colors_right[finger])

    def build_left_hand(self, hand):
        """Attach and place the left-hand model."""
        self.left_hand = hand
        f = getattr(hand, "hf", Hand.size_factor(hand.size))
        self.left_hand_view = self.make_hand_model(f, palm_color=(0.12, 0.42, 0.86))
        for limb in self.left_hand_view:
            limb.x(limb.x() * 2.5)
            limb.shift(16.5 * 3 + 1, -7.5, 3)
        for finger in (1, 2, 3, 4, 5):
            self.left_hand_view[finger].color(self._finger_colors_left[finger])

    def build_keyboard(self):
        """Build the 3D keyboard scene and static decorative elements."""
        nts = ("C", "D", "E", "F", "G", "A", "B")
        tol = 0.12
        keybsize = 16.5  # in cm, span of one octave
        wb = keybsize / 7
        nr_octaves = 7
        span = nr_octaves * wb * 7

        self.vp = Plotter(
            title="PianoPlayer " + __version__,
            axes=0,
            size=(1400, 700),
            bg="cornsilk",
            bg2="lb",
        )

        # wooden top and base
        top_box = Box(pos=(span / 2 + keybsize, 6, 1), length=span + 1, height=3, width=5)
        top_box.texture(dataurl + "textures/wood1.jpg")
        self.vp += top_box

        base_box = Box(pos=(span / 2 + keybsize, 0, -1), length=span + 1, height=1, width=17)
        base_box.texture(dataurl + "textures/wood1.jpg")
        self.vp += base_box

        title_text = Text3D(
            "PianoPlayer ^" + __version__ + " ",
            pos=(18, 5., 2.3),
            depth=.5,
            c="silver",
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
            "Playing:\n" + self.songname[-30:].replace("_", "\\_"),
            font="Theemim",
            vspacing=3,
            depth=0.04,
            s=1.35,
            c="k",
            italic=0.5,
        )
        song_text.rotate(70, axis=(1, 0, 0))
        song_text.pos([55, 10, 6])
        self.vp += song_text

        for ioct in range(nr_octaves):
            for ik in range(7):  # white keys
                x = ik * wb + (ioct + 1) * keybsize + wb / 2
                tb = Box(pos=(x, -2, 0), length=wb - tol, height=1, width=12, c="white")
                self.key_objects.update({nts[ik] + str(ioct + 1): tb})
                self.vp += tb
                if nts[ik] not in ("E", "B"):  # black keys
                    tn = Box(pos=(x + wb / 2, 0, 1), length=wb * 0.6, height=1, width=8, c="black")
                    self.key_objects.update({nts[ik] + "#" + str(ioct + 1): tn})
                    self.vp += tn
        self._hud_lh = Text2D(
            pos="top-left", c="black", bg="w", alpha=0.05, s=1, font="Theemim"
        )
        self._hud_rh = Text2D(
            pos="top-right", c="black", bg="w", alpha=0.05, s=1, font="Theemim"
        )
        self.vp += [self._hud_rh, self._hud_lh]
        cam = dict(
            pos=(110, -51.1, 89.1),
            focal_point=(81.5, 0.531, 2.82),
            viewup=(-0.163, 0.822, 0.546),
            distance=105,
            clipping_range=(41.4, 179),
        )
        self.vp.show(interactive=0, camera=cam, resetcam=0)

    def play(self):
        """Run playback loop until sequence end or user abort."""

        console.print("[cyan]Press space to proceed by one note[/cyan]")
        console.print("[cyan]Press Esc (or q) to exit.[/cyan]")
        if self.playsounds and not has_audio_backend():
            logger.warning("Sound playback unavailable: install pygame.")

        if self.right_hand:
            self.engaged_keys_r = [False] * len(self.right_hand.noteseq)
            self.engaged_fingers_r = [False] * 6  # element 0 is dummy
            self._release_idx_r = 0
            self._press_idx_r = 0
        if self.left_hand:
            self.engaged_keys_l = [False] * len(self.left_hand.noteseq)
            self.engaged_fingers_l = [False] * 6
            self._release_idx_l = 0
            self._press_idx_l = 0

        t = 0.0
        while True:
            if self._abort_playback:
                break
            if self.right_hand:
                self._move_hand(1, t)
            if self.left_hand:
                self._move_hand(-1, t)
            if t > 1000:
                break
            t += self.dt  # absolute time flows

        if self.verbose:
            console.print("[green]End of note sequence reached.[/green]")

    def _wait_for_advance_key(self):
        """Block until Space (advance) or Esc (abort) is pressed."""
        interactor = getattr(self.vp, "interactor", None)
        if interactor is None:
            self._abort_playback = True
            return

        state = {"abort": False}

        def _on_key(evt):
            key = (
                getattr(evt, "keypress", "")
                or getattr(evt, "keyPressed", "")
                or getattr(evt, "key", "")
                or getattr(evt, "keySym", "")
            )
            if not key and interactor is not None:
                with contextlib.suppress(Exception):
                    key = interactor.GetKeySym() or ""
            key = str(key).strip().lower()

            if key in {"escape", "esc", "q"}:
                state["abort"] = True
                try:
                    interactor.ExitCallback()
                except Exception:
                    with contextlib.suppress(Exception):
                        interactor.TerminateApp()
                return
            if key in {"space", "spacebar", " ", "return", "kp_enter", "enter"}:
                try:
                    interactor.ExitCallback()
                except Exception:
                    with contextlib.suppress(Exception):
                        interactor.TerminateApp()

        cid = None
        char_cid = None
        try:
            cid = self.vp.add_callback("KeyPress", _on_key)
            # Some VTK/vedo builds deliver printable keys through CharEvent.
            char_cid = self.vp.add_callback("CharEvent", _on_key)
            interactor.Start()
        except (AttributeError, RuntimeError) as exc:
            logger.debug("Key wait unavailable: %s", exc)
            self._abort_playback = True
            return
        finally:
            if cid is not None:
                try:
                    self.vp.remove_callback(cid)
                except (AttributeError, RuntimeError):
                    logger.debug("Unable to remove key callback.")
            if char_cid is not None:
                try:
                    self.vp.remove_callback(char_cid)
                except (AttributeError, RuntimeError):
                    logger.debug("Unable to remove char callback.")

        if state["abort"]:
            self._abort_playback = True
            return

        # If the interactor/renderer disappears while waiting, stop playback cleanly.
        if (
            getattr(self.vp, "interactor", None) is None
            or getattr(self.vp, "renderer", None) is None
        ):
            self._abort_playback = True

    def _safe_refresh(self, interactive: bool = False):
        """Refresh viewport without crashing on renderer lifecycle differences."""
        try:
            if hasattr(self.vp, "renderer") and self.vp.renderer is not None:
                self.vp.render()
            else:
                self.vp.show(interactive=interactive, resetcam=False)
        except (AttributeError, RuntimeError):
            # Some vedo versions transiently expose a None renderer during updates.
            logger.debug("Viewport refresh skipped: renderer/interactor unavailable.")

    def _move_hand(self, side, t):
        """Advance one hand state for the given absolute time.

        Runs inside the main `play()` loop.
        """
        # Pick the per-hand state containers and colors.
        if side == 1:
            c1, c2 = "tomato", "orange"
            finger_base_colors = self._finger_colors_right
            engaged_keys = self.engaged_keys_r
            engaged_fingers = self.engaged_fingers_r
            hand = self.right_hand
            hand_view = self.right_hand_view
            release_idx = self._release_idx_r
            press_idx = self._press_idx_r
        else:
            c1, c2 = (0.06, 0.32, 0.86), (0.24, 0.72, 1.00)
            finger_base_colors = self._finger_colors_left
            engaged_keys = self.engaged_keys_l
            engaged_fingers = self.engaged_fingers_l
            hand = self.left_hand
            hand_view = self.left_hand_view
            release_idx = self._release_idx_l
            press_idx = self._press_idx_l
        notes = hand.noteseq
        total = len(notes)

        # First release notes/fingers whose duration elapsed.
        while release_idx < total:
            n = notes[release_idx]
            stop = n.time + n.duration
            f = n.fingering
            if isinstance(f, str):
                release_idx += 1
                continue
            if stop > t:
                break
            if f and engaged_keys[release_idx]:
                engaged_keys[release_idx] = False
                engaged_fingers[f] = False
                name = note_name(n)
                key_obj = self.key_objects[name]
                key_obj.shift(0, 0, 0.4)
                key_pos = key_obj.pos()
                key_obj.rotate_x(-4, around=key_pos)
                key_obj.color("k" if key_pos[2] > 0.5 else "w")

                finger_obj = hand_view[f]
                finger_obj.shift(0, 0, 1)
                finger_obj.rotate_x(20, around=finger_obj.pos())
                finger_obj.color(finger_base_colors[f])
                self._safe_refresh(interactive=False)
            release_idx += 1

        # Then handle note attacks at the current absolute time.
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
            if not (f and not engaged_keys[press_idx] and not engaged_fingers[f]):
                break

            if press_idx >= len(hand.fingerseq):
                break

            engaged_keys[press_idx] = True
            engaged_fingers[f] = True
            name = note_name(n)

            if t > self.t0 + self.vp.clock:
                self.t0 = t
                self._safe_refresh(interactive=False)

            for g in (1, 2, 3, 4, 5):
                hand_view[g].x(side * hand.fingerseq[press_idx][g])
            hand_view[0].x(hand_view[3].x())

            finger_obj = hand_view[f]
            finger_obj.rotate_x(-20, around=finger_obj.pos())
            finger_obj.shift(0, 0, -1)
            finger_obj.color(c1)

            key_obj = self.key_objects[name]
            key_obj.rotate_x(4, around=key_obj.pos())
            key_obj.shift(0, 0, -0.4)
            key_obj.color(c2)

            if self.verbose:
                msg = "meas." + str(n.measure) + " t=" + str(round(t, 2))
                hud_label = self._hud_rh if side == 1 else self._hud_lh
                if hud_label is not None:
                    hud_label.text(f"{msg}\nfinger {f} hits {name}")

            self._safe_refresh(interactive=False)
            if self.playsounds:
                play_sound(n, self.speed_factor, wait=True)

            self._wait_for_advance_key()
            press_idx += 1
            if self._abort_playback:
                break

        if side == 1:
            self._release_idx_r = release_idx
            self._press_idx_r = press_idx
        else:
            self._release_idx_l = release_idx
            self._press_idx_l = press_idx


if __name__ == "__main__":
    vk = VirtualKeyboard("Chopin Valse in A minor")
    vk.vp.show(interactive=1, resetcam=0)
