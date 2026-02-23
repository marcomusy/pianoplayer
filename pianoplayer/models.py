"""Typed data models used across the pianoplayer package."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


@dataclass(slots=True)
class INote:
    name: str | None = None
    isChord: bool = False
    isBlack: bool = False
    pitch: int | float = 0
    octave: int = 0
    x: float = 0.0
    time: float = 0.0
    duration: float = 0.0
    fingering: int | str = 0
    measure: int = 0
    chordnr: int = 0
    NinChord: int = 0
    chordID: int = 0
    noteID: int = 0
    cost: float = 0.0
    note21: Any = None
    chord21: Any = None


@dataclass(slots=True)
class AnnotateOptions:
    filename: str
    outputfile: str | None = "output.xml"
    n_measures: int = 100
    start_measure: int = 1
    depth: int = 0
    rbeam: int = 0
    lbeam: int = 1
    quiet: bool = False
    musescore: bool = False
    below_beam: bool = False
    with_vedo: bool = False
    vedo_speed: float = 1.5
    sound_off: bool = False
    left_only: bool = False
    right_only: bool = False
    hand_size: str = "M"
    cost_path: str | None = None

    @classmethod
    def from_namespace(cls, args: Any) -> "AnnotateOptions":
        payload = {}
        for field_name in cls.__dataclass_fields__:  # type: ignore[attr-defined]
            if hasattr(args, field_name):
                payload[field_name] = getattr(args, field_name)

        # Backward compatibility for legacy boolean hand-size flags.
        if "hand_size" not in payload:
            for size in ("XXS", "XS", "S", "M", "L", "XL", "XXL"):
                if getattr(args, f"hand_size_{size}", False):
                    payload["hand_size"] = size
                    break
        return cls(**payload)

    def to_namespace(self) -> SimpleNamespace:
        return SimpleNamespace(**{k: getattr(self, k) for k in self.__dataclass_fields__})  # type: ignore[attr-defined]
