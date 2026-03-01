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
        logger.debug("Hand size preset %s (span %.2f cm).", size, 21 * self.hf)

        ### HIGHLY EXPERIMENTAL: whether to keep relaxed finger targets or
        # apply memory-based smoothing after the first placement.
        self.preserve_posture_memory = False
        self.relocation_alpha = 0.3
        self._has_position_state = False
        self.max_span_cm = 21.0 * self.hf
        self.max_follow_lag_cm = 2.5 * self.hf
        self.min_finger_gap_cm = 0.15 * self.hf
        ################################

        self.finger_positions = list(self.frest)
        self.cost = -1.0

    def set_fingers_positions(
        self,
        fings: Sequence[int],
        notes: Sequence[INote],
        i: int,
        *,
        finger_positions: list[float | None] | None = None,
        force_relaxed: bool = False,
    ) -> None:
        """Update finger positions after assigning note index ``i``.

        By default it updates ``self.finger_positions`` and tracks first-placement state.
        Pass ``finger_positions=...`` to update an external temporary state instead.
        """
        if finger_positions is None:
            finger_positions = self.finger_positions
            force_relaxed = not self._has_position_state

        fi = fings[i]
        note_x = notes[i].x
        targets = self._relaxed_targets(fi, note_x)
        if not targets:
            return

        # First global placement starts from relaxed hand geometry; then memory may apply.
        if force_relaxed or not self.preserve_posture_memory:
            for j in (1, 2, 3, 4, 5):
                finger_positions[j] = targets.get(j)
            finger_positions[fi] = note_x
            if finger_positions is self.finger_positions:
                self._has_position_state = True
            return

        for j in (1, 2, 3, 4, 5):
            target = targets.get(j)
            if target is None:
                finger_positions[j] = None
                continue
            if j == fi:
                # The active finger must exactly land on the current note.
                finger_positions[j] = note_x
                continue
            prev = finger_positions[j]
            if prev is None:
                finger_positions[j] = target
            else:
                # `relocation_alpha` is memory strength:
                # 0.0 -> fully relaxed target (default behavior),
                # 1.0 -> keep previous finger posture.
                finger_positions[j] = (
                    self.relocation_alpha * prev + (1.0 - self.relocation_alpha) * target
                )
        self._apply_position_constraints(finger_positions, fi, note_x, targets)
        if finger_positions is self.finger_positions:
            self._has_position_state = True

    def _relaxed_targets(self, fi: int, note_x: float) -> dict[int, float]:
        """Return relaxed absolute target positions for all fingers around pressed finger ``fi``."""
        ifx = self.frest[fi]
        if ifx is None:
            return {}
        targets: dict[int, float] = {}
        for j in (1, 2, 3, 4, 5):
            jfx = self.frest[j]
            if jfx is None:
                continue
            targets[j] = (jfx - ifx) + note_x
        return targets

    def _apply_position_constraints(
        self,
        finger_positions: list[float | None],
        fi: int,
        note_x: float,
        targets: dict[int, float],
    ) -> None:
        """Constrain posture memory so fingers follow the hand and keep realistic spread."""
        for j in (1, 2, 3, 4, 5):
            if j == fi:
                continue
            pos = finger_positions[j]
            target = targets.get(j)
            if pos is None or target is None:
                continue
            lag = pos - target
            if lag > self.max_follow_lag_cm:
                finger_positions[j] = target + self.max_follow_lag_cm
            elif lag < -self.max_follow_lag_cm:
                finger_positions[j] = target - self.max_follow_lag_cm

        # Preserve finger ordering to avoid impossible interpenetration/cross-over poses.
        for j in (2, 3, 4, 5):
            a = finger_positions[j - 1]
            b = finger_positions[j]
            if a is None or b is None:
                continue
            min_allowed = a + self.min_finger_gap_cm
            if b < min_allowed:
                finger_positions[j] = min_allowed

        # Hard cap on thumb-pinky spread around current contact note.
        if finger_positions[1] is not None and finger_positions[5] is not None:
            span = finger_positions[5] - finger_positions[1]
            if span > self.max_span_cm:
                limit = self.max_span_cm / 2.0
                for j in (1, 2, 3, 4, 5):
                    if j == fi or finger_positions[j] is None:
                        continue
                    off = finger_positions[j] - note_x
                    if off > limit:
                        finger_positions[j] = note_x + limit
                    elif off < -limit:
                        finger_positions[j] = note_x - limit

        # Keep active finger exactly on the note after clamping.
        finger_positions[fi] = note_x

    def ave_velocity(self, fingering: Sequence[int], notes: Sequence[INote]) -> float:
        """Compute average weighted finger velocity for a candidate fingering."""
        # Evaluate candidates from a stable starting posture without mutating shared state.
        finger_positions = list(self.finger_positions)
        self.set_fingers_positions(
            fingering,
            notes,
            0,
            finger_positions=finger_positions,
            force_relaxed=False,
        )

        vmean = 0.0
        for i in range(1, self.depth):
            na = notes[i - 1]
            nb = notes[i]
            fb = fingering[i]
            finger_pos = finger_positions[fb]
            if finger_pos is None:
                continue

            dx = abs(nb.x - finger_pos)
            dt = abs(nb.time - na.time) + 0.1
            v = dx / dt

            weight = self.weights[fb] or 1.0
            if nb.isBlack:
                bfactor = self.bfactor[fb] or 1.0
                v /= weight * bfactor
            else:
                v /= weight

            vmean += v
            self.set_fingers_positions(
                fingering,
                notes,
                i,
                finger_positions=finger_positions,
                force_relaxed=False,
            )

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

    @staticmethod
    def _preset_finger(value: int | str) -> int:
        """Normalize a pre-annotated finger value to 1..5, or return 0 when absent/invalid."""
        if isinstance(value, str):
            text = value.strip()
            if not text.lstrip("+-").isdigit():
                return 0
            value = int(text)

        finger = abs(int(value))
        if 1 <= finger <= 5:
            return finger
        return 0

    def generate(
        self,
        start_measure: int = 0,
        nmeasures: int = 1000,
        show_progress=None,
    ) -> None:
        """Generate fingering assignments for the configured note sequence."""
        initial_autodepth = self.autodepth
        initial_depth = self.depth
        original_x = None

        if start_measure == 1:
            start_measure = 0

        if self.LR == "left":
            # Reuse right-hand geometry/cost logic by mirroring x-coordinates for LH.
            original_x = [anote.x for anote in self.noteseq]
            for anote in self.noteseq:
                anote.x = -anote.x

        self.fingerseq = []
        try:
            self.finger_positions = list(self.frest)
            self._has_position_state = False
            start_finger = 0
            out: list[int] = []
            vel = 0.0
            n_total = len(self.noteseq)
            max_measure = start_measure + nmeasures - 1
            self.depth = max(3, min(self.depth, 9))
            for i in range(n_total):
                an = self.noteseq[i]
                if an.measure:
                    if an.measure < start_measure:
                        continue
                    if an.measure > max_measure:
                        break

                if i > n_total - 11:
                    # Near the tail, disable autodepth but keep manual depth if explicitly set.
                    if self.autodepth:
                        self.autodepth = False
                        self.depth = 9

                ninenotes = self._window9(self.noteseq, i)
                if not ninenotes:
                    break

                anchored_finger = self._preset_finger(an.fingering)
                if anchored_finger:
                    # Preserve existing annotation and resume optimization from this anchor.
                    an.fingering = anchored_finger
                    out, vel = self.optimize_seq(ninenotes, anchored_finger)
                    start_finger = out[1] if len(out) > 1 else anchored_finger
                    self.set_fingers_positions(out, ninenotes, 0)
                    self.fingerseq.append(list(self.finger_positions))
                    an.cost = vel
                    if show_progress is not None:
                        show_progress(i + 1, n_total, an.measure)
                    continue

                best_finger = 0
                if i > n_total - 10:
                    if len(out) > 1:
                        # Reuse remaining fingers from the previously solved 9-note window.
                        best_finger = out.pop(1)
                        # Keep solver state aligned with the actual finger applied to this note.
                        out[0] = best_finger
                        start_finger = out[1] if len(out) > 1 else best_finger
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
                self.fingerseq.append(list(self.finger_positions))
                an.cost = vel

                if self.verbose:
                    hand_tag = "RH" if self.LR == "right" else "LH"
                    meas_tag = f"meas.{an.measure}" if an.measure else "meas.--"
                    seq_preview = str(out[0 : self.depth])
                    depth_tag = f" d={self.depth}" if self.autodepth else ""
                    if i < n_total - 10:
                        logger.info(
                            "%s %s f%s pitch=%s oct=%s v=%.1f %s%s",
                            hand_tag,
                            meas_tag,
                            best_finger,
                            an.pitch,
                            an.octave,
                            vel,
                            seq_preview,
                            depth_tag,
                        )
                    else:
                        logger.info(
                            "%s %s f%s pitch=%s oct=%s",
                            hand_tag,
                            meas_tag,
                            best_finger,
                            an.pitch,
                            an.octave,
                        )
                elif show_progress is None and i and not i % 100 and an.measure:
                    logger.info(
                        "%s progress %s/%s notes (measure %s)",
                        "RH" if self.LR == "right" else "LH",
                        i,
                        n_total,
                        an.measure + 1,
                    )

                if show_progress is not None:
                    show_progress(i + 1, n_total, an.measure)
        finally:
            self.autodepth = initial_autodepth
            self.depth = initial_depth
            if original_x is not None:
                # Restore original LH coordinates for downstream consumers.
                for anote, x in zip(self.noteseq, original_x):
                    anote.x = x
