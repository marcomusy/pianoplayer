# -------------------------------------------------------------------------------
# Name:         PianoPlayer
# Purpose:      Find optimal fingering for piano scores
# Author:       Marco Musy
# -------------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import Sequence

from pianoplayer.models import INote

logger = logging.getLogger(__name__)


class Hand:
    """Finger-assignment optimizer for one hand over a note sequence."""

    _SIZE_FACTORS = {
        "XXS": 0.33,
        "XS": 0.46,
        "S": 0.64,
        "M": 0.82,
        "L": 1.0,
        "XL": 1.1,
        "XXL": 1.2,
    }

    @classmethod
    def size_factor(cls, size: str) -> float:
        """Return the scaling factor for a named hand-size preset."""
        return cls._SIZE_FACTORS.get(size, cls._SIZE_FACTORS["M"])

    def __init__(self, noteseq: Sequence[INote], side: str = "right", size: str = "M") -> None:
        """Initialize hand geometry and optimization state."""
        self.LR = side
        # fingers pos at rest first is dummy, (cm), asymmetry helps with scales
        self.frest: list[float | None]   = [None, -7.0, -2.8, 0.0, 2.8, 5.6]
        self.weights: list[float | None] = [None, 1.1, 1.0, 1.1, 0.9, 0.8]  # finger strength
        self.bfactor: list[float | None] = [None, 0.3, 1.0, 1.1, 0.8, 0.7]  # black key bias
        self.fingers = (1, 2, 3, 4, 5)
        self.noteseq = list(noteseq)
        self.fingerseq: list[list[float | None]] = []
        self.depth = 9
        self.autodepth = True
        self.verbose = True
        self.lyrics = False
        self.size = size

        self.hf = self.size_factor(size)
        for i in (1, 2, 3, 4, 5):
            if self.frest[i]:
                self.frest[i] *= self.hf
        logger.info("Your hand span set to size-%s which is %s cm", size, 21 * self.hf)
        logger.info("(max relaxed distance between thumb and pinkie)")
        self.cfps = list(self.frest)
        self.cost = -1.0

    def set_fingers_positions(self, fings: Sequence[int], notes: Sequence[INote], i: int) -> None:
        """Update current finger positions after assigning note index ``i``."""
        fi = fings[i]
        ni = notes[i]
        ifx = self.frest[fi]
        if ifx is None:
            return
        for j in (1, 2, 3, 4, 5):
            jfx = self.frest[j]
            self.cfps[j] = (jfx - ifx) + ni.x if jfx is not None else None

    def ave_velocity(self, fingering: Sequence[int], notes: Sequence[INote]) -> float:
        """Compute average weighted finger velocity for a candidate fingering."""
        self.set_fingers_positions(fingering, notes, 0)

        vmean = 0.0
        for i in range(1, self.depth):
            na = notes[i - 1]
            nb = notes[i]
            fb = fingering[i]
            cfps = self.cfps[fb]
            if cfps is None:
                continue

            dx = abs(nb.x - cfps)
            dt = abs(nb.time - na.time) + 0.1
            v = dx / dt

            weight = self.weights[fb] or 1.0
            if nb.isBlack:
                bfactor = self.bfactor[fb] or 1.0
                v /= weight * bfactor
            else:
                v /= weight

            vmean += v
            self.set_fingers_positions(fingering, notes, i)

        return vmean / (self.depth - 1)

    def skip(self, fa: int, fb: int, na: INote, nb: INote, hf: float, lr: str, level: int) -> bool:
        """Return True when a local finger transition is considered invalid/unlikely."""
        del level
        xba = nb.x - na.x

        if not na.isChord and not nb.isChord:
            # Same-finger repetitions on different notes are discouraged for short notes.
            if fa == fb and xba and na.duration < 4:
                return True
            if fa > 1:
                # Non-thumb crossing against melodic direction is disallowed.
                if fb > 1 and (fb - fa) * xba < 0:
                    return True
                # Thumb-under onto black key while moving up is disallowed.
                if fb == 1 and nb.isBlack and xba > 0:
                    return True
            # Fast thumb-out from black key to a lower note is disallowed.
            elif na.isBlack and xba < 0 and fb > 1 and na.duration < 2:
                return True

        elif na.isChord and nb.isChord and na.chordID == nb.chordID:
            axba = abs(xba) * hf / 0.8
            # Chord fingering order must respect hand directionality.
            if fa == fb:
                return True
            if fa < fb and lr == "left":
                return True
            if fa > fb and lr == "right":
                return True

            pair = (min(fa, fb), max(fa, fb))
            # Maximum allowed inter-finger stretch inside the same chord.
            threshold = {
                (3, 4): 5,
                (4, 5): 5,
                (2, 3): 6,
                (2, 4): 7,
                (3, 5): 8,
                (2, 5): 11,
                (1, 2): 12,
                (1, 3): 14,
                (1, 4): 16,
            }.get(pair)

            if threshold is not None and axba > threshold:
                return True

        return False

    def optimize_seq(self, nseq: Sequence[INote], istart: int) -> tuple[list[int], float]:
        """Search the best fingering for a 9-note window under local constraints."""
        if self.autodepth:
            if nseq[0].isChord:
                self.depth = max(3, nseq[0].NinChord - nseq[0].chordnr + 1)
            else:
                tn0 = nseq[0].time
                for i in (4, 5, 6, 7, 8, 9):
                    self.depth = i
                    if nseq[i - 1].time - tn0 > 3.5:
                        break

        depth = self.depth

        u_start = list(self.fingers) if istart == 0 else [istart]
        best_fingering = [0 for _ in range(9)]
        minvel = 1.0e10

        candidate = [0 for _ in range(9)]

        def backtrack(level: int) -> None:
            nonlocal best_fingering, minvel
            # Depth-first search over finger assignments for the current look-ahead window.
            #
            # - `level` is the note index currently being assigned a finger.
            # - `candidate` stores the in-progress sequence of chosen fingers.
            # - At `level == depth` we have a full candidate for the active window size,
            #   so we evaluate its motion cost (`ave_velocity`) and keep it if better.
            # - For intermediate levels, we enumerate possible fingers:
            #     * first note: constrained by `u_start` (either the previous carry-over
            #       finger, or all fingers when no carry-over exists),
            #     * subsequent notes: all fingers 1..5.
            # - Before recursing, we apply `skip(...)` as a local feasibility/pruning rule
            #   between the previous and current note/finger pair. This avoids exploring
            #   branches that are physically implausible or explicitly disallowed.
            # - The recursion mutates `candidate[level]`, then descends to `level + 1`.
            #   Backtracking is implicit: the next loop iteration overwrites that slot.
            if level == depth:
                velocity = self.ave_velocity(candidate, nseq)
                if velocity < minvel:
                    best_fingering = list(candidate)
                    minvel = velocity
                return

            choices = u_start if level == 0 else self.fingers
            for finger in choices:
                if level > 0 and self.skip(
                    candidate[level - 1],
                    finger,
                    nseq[level - 1],
                    nseq[level],
                    self.hf,
                    self.LR,
                    level + 1,
                ):
                    continue
                candidate[level] = finger
                backtrack(level + 1)

        backtrack(0)
        return best_fingering, minvel

    @staticmethod
    def _window9(notes: Sequence[INote], start: int) -> list[INote]:
        """Return a 9-note optimization window, padding with the last note when needed."""
        window = list(notes[start : start + 9])
        if not window:
            return []
        if len(window) < 9:
            window.extend([window[-1]] * (9 - len(window)))
        return window

    def generate(self, start_measure: int = 0, nmeasures: int = 1000) -> None:
        """Generate fingering assignments for the configured note sequence."""
        initial_autodepth = self.autodepth
        initial_depth = self.depth
        original_x = None

        if start_measure == 1:
            start_measure = 0

        if self.LR == "left":
            original_x = [anote.x for anote in self.noteseq]
            for anote in self.noteseq:
                anote.x = -anote.x

        self.fingerseq = []
        try:
            start_finger = 0
            out: list[int] = []
            vel = 0.0
            n_total = len(self.noteseq)
            self.depth = max(3, min(self.depth, 9))

            for i in range(n_total):
                an = self.noteseq[i]
                if an.measure:
                    if an.measure < start_measure:
                        continue
                    if an.measure > start_measure + nmeasures:
                        break

                if i > n_total - 11:
                    self.autodepth = False
                    self.depth = 9

                ninenotes = self._window9(self.noteseq, i)
                if not ninenotes:
                    break

                best_finger = 0
                if i > n_total - 10:
                    if len(out) > 1:
                        best_finger = out.pop(1)
                    else:
                        out, vel = self.optimize_seq(ninenotes, start_finger)
                        best_finger = out[0]
                        start_finger = out[1] if len(out) > 1 else out[0]
                else:
                    out, vel = self.optimize_seq(ninenotes, start_finger)
                    best_finger = out[0]
                    start_finger = out[1] if len(out) > 1 else out[0]

                an.fingering = best_finger
                self.set_fingers_positions(out, ninenotes, 0)
                self.fingerseq.append(list(self.cfps))
                an.cost = vel

                if self.verbose:
                    if an.measure:
                        logger.info(
                            "meas.%-3s finger_%s plays Pitch:%s Octave:%s",
                            an.measure,
                            best_finger,
                            an.pitch,
                            an.octave,
                        )
                    else:
                        logger.info(
                            "finger_%s plays Pitch:%s Octave:%s", best_finger, an.pitch, an.octave
                        )

                    if i < n_total - 10:
                        if self.autodepth:
                            logger.info(
                                "v=%s\t%s d:%s", round(vel, 1), str(out[0 : self.depth]), self.depth
                            )
                        else:
                            logger.info(
                                "v=%s\t%s%s",
                                round(vel, 1),
                                "   " * (i % self.depth),
                                str(out[0 : self.depth]),
                            )
                elif i and not i % 100 and an.measure:
                    logger.info(
                        "scanned %s / %s notes, measure %s for the %s hand...",
                        i,
                        n_total,
                        an.measure + 1,
                        self.LR,
                    )
        finally:
            self.autodepth = initial_autodepth
            self.depth = initial_depth
            if original_x is not None:
                for anote, x in zip(self.noteseq, original_x):
                    anote.x = x
