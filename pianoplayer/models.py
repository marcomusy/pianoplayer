"""Typed data models used across the pianoplayer package."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class INote:
    """Internal note representation used by readers, optimizer, and output writers."""

    name: str | None = None
    isChord: bool = False
    isBlack: bool = False
    pitch: int | float = 0
    octave: int = 0
    x: float = 0.0
    time: float = 0.0
    duration: float = 0.0
    fingering: int | str = 0
    is_anchor: bool = False
    measure: int = 0
    staff: int = 0
    chordnr: int = 0
    NinChord: int = 0
    chordID: int = 0
    noteID: int = 0
    cost: float = 0.0
    note21: Any = None
    chord21: Any = None


@dataclass(slots=True)
class AnnotateOptions:
    """Normalized options shared by CLI, GUI, and programmatic API calls."""

    filename: str
    outputfile: str | None = "output.xml"
    n_measures: int = 1000
    start_measure: int = 1
    depth: int = 0
    rpart: int = 0
    lpart: int = 1
    rstaff: int = 0
    lstaff: int = 0
    auto_routing: bool = True
    quiet: bool = False
    musescore: bool = False
    below_beam: bool = False
    with_vedo: bool = False
    sound_off: bool = False
    left_only: bool = False
    right_only: bool = False
    hand_size: str = "M"
    chord_note_stagger_s: float = 0.05
    cost_path: str | None = None

    @classmethod
    def from_namespace(cls, args: Any) -> "AnnotateOptions":
        payload = {}
        for field_name in cls.__dataclass_fields__:  # type: ignore[attr-defined]
            if hasattr(args, field_name):
                payload[field_name] = getattr(args, field_name)

        # Compatibility aliases after beam->part rename.
        if "rpart" not in payload and hasattr(args, "rbeam"):
            payload["rpart"] = getattr(args, "rbeam")
        if "lpart" not in payload and hasattr(args, "lbeam"):
            payload["lpart"] = getattr(args, "lbeam")

        # Backward compatibility for legacy boolean hand-size flags.
        if "hand_size" not in payload:
            for size in ("XXS", "XS", "S", "M", "L", "XL", "XXL"):
                if getattr(args, f"hand_size_{size}", False):
                    payload["hand_size"] = size
                    break
        return cls(**payload)

    def to_namespace(self) -> SimpleNamespace:
        payload = {k: getattr(self, k) for k in self.__dataclass_fields__}  # type: ignore[attr-defined]
        return SimpleNamespace(**payload)


_kb_layout = {
    "C": 0.5,
    "D": 1.5,
    "E": 2.5,
    "F": 3.5,
    "G": 4.5,
    "A": 5.5,
    "B": 6.5,
    "B#": 0.5,
    "C#": 1.0,
    "D#": 2.0,
    "E#": 3.5,
    "F#": 4.0,
    "G#": 5.0,
    "A#": 6.0,
    "C-": 6.5,
    "D-": 1.0,
    "E-": 2.0,
    "F-": 2.5,
    "G-": 4.0,
    "A-": 5.0,
    "B-": 6.0,
    "C##": 1.5,
    "D##": 2.5,
    "F##": 4.5,
    "G##": 5.5,
    "A##": 6.5,
    "D--": 0.5,
    "E--": 1.5,
    "G--": 3.5,
    "A--": 4.5,
    "B--": 5.5,
}


def keypos_midi(n):  # position of notes on keyboard
    """Return horizontal key position from MIDI pitch (in cm)."""
    keybsize = 16.5  # cm
    k = keybsize / 7.0  # 7 notes
    step = (n.pitch % 12) * k
    return keybsize * (n.pitch // 12) + step


def keypos(n):  # position of notes on keyboard
    """Return horizontal key position from note name/octave (in cm)."""
    step = 0.0
    keybsize = 16.5  # cm
    k = keybsize / 7.0  # 7 notes
    if n.name in _kb_layout:
        step = _kb_layout[n.name] * k
    else:
        logger.warning("Note not found in keyboard layout: %s", n.name)
    return keybsize * n.octave + step
