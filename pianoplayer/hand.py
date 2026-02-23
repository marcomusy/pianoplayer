# -------------------------------------------------------------------------------
# Name:         PianoPlayer
# Purpose:      Find optimal fingering for piano scores
# Author:       Marco Musy
# -------------------------------------------------------------------------------
from __future__ import annotations

import logging
from typing import Sequence

import pianoplayer.utils as utils
from pianoplayer.models import INote

logger = logging.getLogger(__name__)


class Hand:
    def __init__(self, noteseq: Sequence[INote], side: str = "right", size: str = "M") -> None:
        self.LR = side
        # fingers pos at rest first is dummy, (cm), asymmetry helps with scales
        self.frest: list[float | None] = [None, -7.0, -2.8, 0.0, 2.8, 5.6]
        self.weights: list[float | None] = [None, 1.1, 1.0, 1.1, 0.9, 0.8]  # finger strength
        self.bfactor: list[float | None] = [None, 0.3, 1.0, 1.1, 0.8, 0.7]  # black key bias
        self.noteseq = list(noteseq)
        self.fingerseq: list[list[float | None]] = []
        self.depth = 9
        self.autodepth = True
        self.verbose = True
        self.lyrics = False
        self.size = size

        self.hf = utils.handSizeFactor(size)
        for i in (1, 2, 3, 4, 5):
            if self.frest[i]:
                self.frest[i] *= self.hf
        logger.info("Your hand span set to size-%s which is %s cm", size, 21 * self.hf)
        logger.info("(max relaxed distance between thumb and pinkie)")
        self.cfps = list(self.frest)
        self.cost = -1.0

    def set_fingers_positions(self, fings: Sequence[int], notes: Sequence[INote], i: int) -> None:
        fi = fings[i]
        ni = notes[i]
        ifx = self.frest[fi]
        if ifx is None:
            return
        for j in (1, 2, 3, 4, 5):
            jfx = self.frest[j]
            self.cfps[j] = (jfx - ifx) + ni.x if jfx is not None else None

    def ave_velocity(self, fingering: Sequence[int], notes: Sequence[INote]) -> float:
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

    def _skip(self, fa: int, fb: int, na: INote, nb: INote, hf: float, lr: str, level: int) -> bool:
        del level
        skipped = False
        xba = nb.x - na.x

        if not na.isChord and not nb.isChord:
            if fa == fb and xba and na.duration < 4:
                skipped = True
            elif fa > 1:
                if fb > 1 and (fb - fa) * xba < 0:
                    skipped = True
                elif fb == 1 and nb.isBlack and xba > 0:
                    skipped = True
            elif na.isBlack and xba < 0 and fb > 1 and na.duration < 2:
                skipped = True

        elif na.isChord and nb.isChord and na.chordID == nb.chordID:
            axba = abs(xba) * hf / 0.8
            if fa == fb:
                skipped = True
            elif fa < fb and lr == "left":
                skipped = True
            elif fa > fb and lr == "right":
                skipped = True
            elif axba > 5 and (fa == 3 and fb == 4 or fa == 4 and fb == 3):
                skipped = True
            elif axba > 5 and (fa == 4 and fb == 5 or fa == 5 and fb == 4):
                skipped = True
            elif axba > 6 and (fa == 2 and fb == 3 or fa == 3 and fb == 2):
                skipped = True
            elif axba > 7 and (fa == 2 and fb == 4 or fa == 4 and fb == 2):
                skipped = True
            elif axba > 8 and (fa == 3 and fb == 5 or fa == 5 and fb == 3):
                skipped = True
            elif axba > 11 and (fa == 2 and fb == 5 or fa == 5 and fb == 2):
                skipped = True
            elif axba > 12 and (fa == 1 and fb == 2 or fa == 2 and fb == 1):
                skipped = True
            elif axba > 14 and (fa == 1 and fb == 3 or fa == 3 and fb == 1):
                skipped = True
            elif axba > 16 and (fa == 1 and fb == 4 or fa == 4 and fb == 1):
                skipped = True

        return skipped

    def optimize_seq(self, nseq: Sequence[INote], istart: int) -> tuple[list[int], float]:
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
        fingers = (1, 2, 3, 4, 5)
        n1, n2, n3, n4, n5, n6, n7, n8, n9 = nseq

        u_start = list(fingers) if istart == 0 else [istart]
        out: tuple[list[int], float] = ([0 for _ in range(depth)], -1.0)
        minvel = 1.0e10

        for f1 in u_start:
            for f2 in fingers:
                if self._skip(f1, f2, n1, n2, self.hf, self.LR, 2):
                    continue
                for f3 in fingers:
                    if f3 and self._skip(f2, f3, n2, n3, self.hf, self.LR, 3):
                        continue
                    u = [False] if depth < 4 else fingers
                    for f4 in u:
                        if f4 and self._skip(f3, f4, n3, n4, self.hf, self.LR, 4):
                            continue
                        u = [False] if depth < 5 else fingers
                        for f5 in u:
                            if f5 and self._skip(f4, f5, n4, n5, self.hf, self.LR, 5):
                                continue
                            u = [False] if depth < 6 else fingers
                            for f6 in u:
                                if f6 and self._skip(f5, f6, n5, n6, self.hf, self.LR, 6):
                                    continue
                                u = [False] if depth < 7 else fingers
                                for f7 in u:
                                    if f7 and self._skip(f6, f7, n6, n7, self.hf, self.LR, 7):
                                        continue
                                    u = [False] if depth < 8 else fingers
                                    for f8 in u:
                                        if f8 and self._skip(f7, f8, n7, n8, self.hf, self.LR, 8):
                                            continue
                                        u = [False] if depth < 9 else fingers
                                        for f9 in u:
                                            if f9 and self._skip(f8, f9, n8, n9, self.hf, self.LR, 9):
                                                continue
                                            c = [f1, f2, f3, f4, f5, f6, f7, f8, f9]
                                            v = self.ave_velocity(c, nseq)
                                            if v < minvel:
                                                out = (c, v)
                                                minvel = v
        return out

    def generate(self, start_measure: int = 0, nmeasures: int = 1000) -> None:
        if start_measure == 1:
            start_measure = 0

        if self.LR == "left":
            for anote in self.noteseq:
                anote.x = -anote.x

        start_finger = 0
        out: list[int] = [0 for _ in range(9)]
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

            ninenotes = self.noteseq[i : i + 9]
            best_finger = 0
            if i > n_total - 10:
                if len(out) > 1:
                    best_finger = out.pop(1)
            else:
                out, vel = self.optimize_seq(ninenotes, start_finger)
                best_finger = out[0]
                start_finger = out[1]

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
                    logger.info("finger_%s plays Pitch:%s Octave:%s", best_finger, an.pitch, an.octave)

                if i < n_total - 10:
                    if self.autodepth:
                        logger.info("v=%s\t%s d:%s", round(vel, 1), str(out[0 : self.depth]), self.depth)
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
