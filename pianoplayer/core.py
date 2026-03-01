from __future__ import annotations

import contextlib
import csv
import logging
import os
import platform
import subprocess
from types import SimpleNamespace
from typing import Any

from pianoplayer.errors import ConversionError, ExternalToolError, MissingDependencyError
from pianoplayer.hand import Hand
from pianoplayer.models import AnnotateOptions
from pianoplayer.musicxml_io import annotate_part_with_fingering, parse_musicxml
from pianoplayer.scorereader import reader, reader_PIG, reader_pretty_midi

logger = logging.getLogger(__name__)

_MIN_MANUAL_DEPTH = 5
_MAX_MANUAL_DEPTH = 9
_HAND_SIZES = {"XXS", "XS", "S", "M", "L", "XL", "XXL"}


class _ProgressReporter:
    """Progress wrapper with Rich UI and a text-log fallback."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._active = False
        self._progress = None
        self._parse_task = None
        self._rh_task = None
        self._lh_task = None
        self._write_task = None
        self._text_bucket = {"right": -1, "left": -1}

    def __enter__(self):
        if not self.enabled:
            return self

        try:
            from rich.progress import (
                BarColumn,
                Progress,
                SpinnerColumn,
                TextColumn,
                TimeRemainingColumn,
            )

            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=26),
                TextColumn("{task.completed}/{task.total}"),
                TextColumn("[dim]{task.fields[status]}"),
                TimeRemainingColumn(),
            )
            self._progress.start()

            # Keep parse/write hidden: these are usually instant and add visual noise.
            # self._parse_task = self._progress.add_task("Parse score", total=1)
            self._rh_task = self._progress.add_task("Generate RH", total=1, visible=False)
            self._lh_task = self._progress.add_task("Generate LH", total=1, visible=False)
            # self._write_task = self._progress.add_task("Write output", total=1, visible=False)
            self._active = True
        except Exception:
            self._active = False

        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._active and self._progress is not None:
            with contextlib.suppress(Exception):
                self._progress.stop()

    def parse_done(self) -> None:
        if self._active and self._progress is not None and self._parse_task is not None:
            self._progress.update(self._parse_task, completed=1)

    def start_hand(self, side: str, total: int) -> None:
        # Fallback path when Rich progress is unavailable.
        if not self._active or self._progress is None:
            if self.enabled:
                logger.info("Generate %s hand: start (%s notes)", side.upper(), total)
            return

        task = self._rh_task if side == "right" else self._lh_task
        self._progress.update(
            task,
            total=max(1, total),
            completed=0,
            visible=True,
            status="m-- \u00b7 0%",
        )

    def update_hand(
        self,
        side: str,
        completed: int,
        total: int,
        measure: int | None = None,
    ) -> None:
        if not self._active or self._progress is None:
            if self.enabled and total:
                bucket = int((completed * 10) / max(1, total))
                if bucket > self._text_bucket[side]:
                    self._text_bucket[side] = bucket
                    logger.info(
                        "Generate %s hand: %s%%",
                        side.upper(),
                        min(100, bucket * 10),
                    )
            return

        task = self._rh_task if side == "right" else self._lh_task
        done = min(completed, max(1, total))
        percent = int((done * 100) / max(1, total))
        meas = "--" if not measure else str(measure)
        self._progress.update(task, completed=done, status=f"meas.{meas} \u00b7 {percent}%")

    def hand_done(self, side: str) -> None:
        if not self._active or self._progress is None:
            if self.enabled:
                logger.info("Generate %s hand: done", side.upper())
            return
        task = self._rh_task if side == "right" else self._lh_task
        current_total = int(self._progress.tasks[task].total or 1)
        self._progress.update(task, completed=current_total, status="done")

    def write_start(self) -> None:
        if self._active and self._progress is not None and self._write_task is not None:
            self._progress.update(self._write_task, total=1, completed=0, visible=True)

    def write_done(self) -> None:
        if self._active and self._progress is not None and self._write_task is not None:
            self._progress.update(self._write_task, completed=1)


def run_annotate(
    filename,
    outputfile="output.xml",
    n_measures=100,
    start_measure=1,
    depth=0,
    rbeam=0,
    lbeam=1,
    quiet=False,
    musescore=False,
    below_beam=False,
    with_vedo=0,
    sound_off=False,
    left_only=False,
    right_only=False,
    hand_size="M",
    chord_note_stagger_s=0.05,
):
    """Programmatic entry point mirroring CLI options."""
    options = AnnotateOptions(
        filename=filename,
        outputfile=outputfile,
        n_measures=n_measures,
        start_measure=start_measure,
        depth=depth,
        rbeam=rbeam,
        lbeam=lbeam,
        quiet=quiet,
        musescore=musescore,
        below_beam=below_beam,
        with_vedo=with_vedo,
        sound_off=sound_off,
        left_only=left_only,
        right_only=right_only,
        hand_size=hand_size,
        chord_note_stagger_s=chord_note_stagger_s,
    )
    options_ns = options.to_namespace()
    # GUI/programmatic callers expect progress unless quiet mode is requested.
    options_ns._show_progress = not bool(quiet)
    annotate(options_ns)


def _as_namespace(args: Any) -> SimpleNamespace:
    """Normalize accepted arg containers to ``SimpleNamespace``."""
    if isinstance(args, AnnotateOptions):
        return args.to_namespace()
    if isinstance(args, SimpleNamespace):
        return args
    return AnnotateOptions.from_namespace(args).to_namespace()


def _run_external(cmd: list[str], context: str) -> None:
    """Execute an external command while silencing stdout/stderr."""
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise ExternalToolError(f"Required executable not found for {context}: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise ExternalToolError(f"External command failed for {context}: {' '.join(cmd)}") from exc


def load_note_sequences(args):
    """Load score input and produce internal RH/LH note sequences."""
    args = _as_namespace(args)

    xmlfn = args.filename
    score_info = None
    rh_noteseq = None
    lh_noteseq = None

    try:
        ext = os.path.splitext(str(args.filename).lower())[1]
        # Dispatch by input format. MusicXML-like inputs also expose `score_info`.
        if ext in {".mscz", ".mscx"}:
            xmlfn = str(args.filename).replace(".mscz", ".xml").replace(".mscx", ".xml")
            logger.info("Converting MuseScore file %s -> %s", args.filename, xmlfn)
            _run_external(["musescore", "-f", args.filename, "-o", xmlfn], "MuseScore conversion")
            score_info = parse_musicxml(xmlfn)

            if not args.left_only:
                rh_noteseq = reader(
                    score_info,
                    beam=args.rbeam,
                    chord_note_stagger_s=args.chord_note_stagger_s,
                )

            if not args.right_only:
                lh_noteseq = reader(
                    score_info,
                    beam=args.lbeam,
                    chord_note_stagger_s=args.chord_note_stagger_s,
                )

        elif ext == ".txt":
            # Legacy PIG format stores channels directly.
            if not args.left_only:
                rh_noteseq = reader_PIG(args.filename, args.rbeam)
            if not args.right_only:
                lh_noteseq = reader_PIG(args.filename, args.lbeam)

        elif ext in {".mid", ".midi"}:
            try:
                import pretty_midi
            except ImportError as exc:
                raise MissingDependencyError(
                    "MIDI input requires optional dependency 'pretty_midi'. "
                    "Install with: pip install 'pianoplayer[midi]'"
                ) from exc

            pm = pretty_midi.PrettyMIDI(args.filename)

            if not args.left_only:
                rh_noteseq = reader_pretty_midi(
                    pm.instruments[args.rbeam],
                    beam=args.rbeam,
                    chord_note_stagger_s=args.chord_note_stagger_s,
                )

            if not args.right_only:
                lh_noteseq = reader_pretty_midi(
                    pm.instruments[args.lbeam],
                    beam=args.lbeam,
                    chord_note_stagger_s=args.chord_note_stagger_s,
                )

        else:
            score_info = parse_musicxml(xmlfn)

            if not args.left_only:
                rh_noteseq = reader(
                    score_info,
                    beam=args.rbeam,
                    chord_note_stagger_s=args.chord_note_stagger_s,
                )

            if not args.right_only:
                lh_noteseq = reader(
                    score_info,
                    beam=args.lbeam,
                    chord_note_stagger_s=args.chord_note_stagger_s,
                )
    except ExternalToolError:
        raise
    except Exception as exc:
        raise ConversionError(f"Unable to parse/convert input score: {args.filename}") from exc

    return xmlfn, score_info, rh_noteseq, lh_noteseq


def generate_hands(args, rh_noteseq, lh_noteseq, progress: _ProgressReporter | None = None):
    """Create and run right/left hand optimizers according to CLI options."""
    args = _as_namespace(args)

    hand_size = str(getattr(args, "hand_size", "M")).upper()
    if hand_size not in _HAND_SIZES:
        hand_size = "M"

    rh = None
    lh = None

    if not args.left_only:
        # Right-hand optimization.
        rh = Hand(side="right", noteseq=rh_noteseq, size=hand_size)
        rh.verbose = not args.quiet and not (progress is not None and progress.enabled)
        # `depth=0` means automatic depth selection in the hand solver.
        rh.autodepth = args.depth == 0
        if not rh.autodepth:
            rh.depth = args.depth
        rh.lyrics = args.below_beam

        total = len(rh.noteseq or [])
        if progress is not None:
            progress.start_hand("right", total)
            rh.generate(
                args.start_measure,
                args.n_measures,
                # Feed measure-aware updates to the progress UI.
                show_progress=lambda done, alln, m: progress.update_hand("right", done, alln, m),
            )
            progress.hand_done("right")
        else:
            rh.generate(args.start_measure, args.n_measures)

    if not args.right_only:
        # Left-hand optimization.
        lh = Hand(side="left", noteseq=lh_noteseq, size=hand_size)
        lh.verbose = not args.quiet and not (progress is not None and progress.enabled)
        lh.autodepth = args.depth == 0
        if not lh.autodepth:
            lh.depth = args.depth
        lh.lyrics = args.below_beam

        total = len(lh.noteseq or [])
        if progress is not None:
            progress.start_hand("left", total)
            lh.generate(
                args.start_measure,
                args.n_measures,
                show_progress=lambda done, alln, m: progress.update_hand("left", done, alln, m),
            )
            progress.hand_done("left")
        else:
            lh.generate(args.start_measure, args.n_measures)

    return rh, lh


def write_annotated_output(args, score_info, rh, lh):
    """Write annotation results either as PIG text or MusicXML."""
    args = _as_namespace(args)

    if args.outputfile is None:
        return

    if os.path.splitext(args.outputfile)[1] == ".txt":
        # Legacy PIG writer path.
        pig_rows = []

        def append_pig_rows(hand, *, is_right: bool) -> None:
            for note in hand.noteseq:
                pig_rows.append(
                    (
                        f"{note.time:.4f}",
                        f"{note.time + note.duration:.4f}",
                        note.pitch,
                        str(None),
                        str(None),
                        "0" if is_right else "1",
                        note.fingering if is_right else -note.fingering,
                        note.cost,
                        note.noteID,
                    )
                )

        if not args.left_only and rh is not None:
            append_pig_rows(rh, is_right=True)
        if not args.right_only and lh is not None:
            append_pig_rows(lh, is_right=False)

        with open(args.outputfile, "wt", encoding="utf-8") as out_file:
            writer = csv.writer(out_file, delimiter="\t")
            # Stable ordering expected by legacy tools: onset, channel, pitch.
            sorted_rows = sorted(
                pig_rows,
                key=lambda tup: (float(tup[0]), int(tup[5]), int(tup[2])),
            )
            for idx, row in enumerate(sorted_rows):
                writer.writerow([idx, *row])
        logger.info("Wrote annotated PIG output to %s", args.outputfile)
        return

    # MusicXML writer path.
    if score_info is None:
        raise ValueError("Only MusicXML inputs can produce MusicXML output in this build.")

    if not args.left_only and rh is not None:
        if len(score_info.parts) <= args.rbeam:
            logger.debug(
                "Skipping right-hand annotation: requested beam %s but score has %s part(s).",
                args.rbeam,
                len(score_info.parts),
            )
        else:
            annotate_part_with_fingering(
                score_info.parts[args.rbeam],
                rh.noteseq,
                lyrics=rh.lyrics,
                skip_chords_with=4,
            )

    if not args.right_only and lh is not None:
        if len(score_info.parts) <= args.lbeam:
            logger.debug(
                "Skipping left-hand annotation: requested beam %s but score has %s part(s).",
                args.lbeam,
                len(score_info.parts),
            )
        else:
            annotate_part_with_fingering(
                score_info.parts[args.lbeam],
                lh.noteseq,
                lyrics=lh.lyrics,
                skip_chords_with=4,
            )

    score_info.write(args.outputfile)
    logger.debug("Wrote annotated score to %s", args.outputfile)

    if args.musescore:
        # Optional auto-open after writing output.
        logger.info("Opening MuseScore with output score: %s", args.outputfile)
        if platform.system() == "Darwin":
            _run_external(["open", args.outputfile], "open output score")
        else:
            _run_external(["musescore", args.outputfile], "open MuseScore")


def maybe_play_vedo(args, xmlfn, rh, lh):
    """Run optional experimental 3D playback after annotation."""
    args = _as_namespace(args)

    if not args.with_vedo:
        return

    if args.start_measure != 1:
        raise ValueError("start_measure must be set to 1 when -v/--with-vedo is used")

    ext = os.path.splitext(str(xmlfn).lower())[1]
    if ext not in {".xml", ".mxl"}:
        logger.warning("3D playback currently requires MusicXML (.xml/.mxl) input; skipping.")
        return

    try:
        from pianoplayer.vkeyboard import VirtualKeyboard
    except ImportError:
        logger.warning(
            "vedo is not available, skipping 3D playback. "
            "Install with: pip install 'pianoplayer[visual]'"
        )
        return

    vk = VirtualKeyboard(songname=xmlfn)
    if not args.left_only and rh is not None:
        vk.build_right_hand(rh)
    if not args.right_only and lh is not None:
        vk.build_left_hand(lh)

    if args.sound_off:
        vk.playsounds = False

    vk.play()

    # Keep the final interactive viewport optional/safe.
    renderer = getattr(vk.vp, "renderer", None)
    if renderer is None:
        logger.info("3D viewport already closed; skipping final show().")
        return
    try:
        vk.vp.show(zoom=2, interactive=1)
    except AttributeError:
        logger.info("3D viewport renderer unavailable; exiting 3D playback cleanly.")


def annotate(args: AnnotateOptions | SimpleNamespace | Any):
    """End-to-end annotation pipeline used by CLI and GUI entry points."""

    def is_anchored_finger(value: Any) -> bool:
        if isinstance(value, str):
            text = value.strip()
            if not text.lstrip("+-").isdigit():
                return False
            value = int(text)
        if not isinstance(value, int):
            return False
        return 1 <= abs(value) <= 5

    def hand_status(is_right: bool, score_info) -> str:
        hand_name = "RH" if is_right else "LH"
        only_flag = args.left_only if is_right else args.right_only
        if only_flag:
            return f"{hand_name}=disabled"
        beam = args.rbeam if is_right else args.lbeam
        if score_info is not None and len(score_info.parts) <= beam:
            return f"{hand_name}=skipped(beam {beam} out of range)"
        return f"{hand_name}=ok(beam {beam})"

    def styled_status(status: str) -> str:
        if status.startswith("ok"):
            return f"[green]{status}[/green]"
        if status.startswith("skipped"):
            return f"[yellow]{status}[/yellow]"
        if status.startswith("disabled"):
            return f"[dim]{status}[/dim]"
        return status

    # Normalize caller input and execution flags.
    show_progress = bool(getattr(args, "_show_progress", False))
    args = _as_namespace(args)

    # Clamp manual search depth to the supported solver range.
    depth = int(getattr(args, "depth", 0))
    if depth > _MAX_MANUAL_DEPTH:
        logger.warning(
            "Requested depth %s is above max %s; using %s.",
            depth,
            _MAX_MANUAL_DEPTH,
            _MAX_MANUAL_DEPTH,
        )
        args.depth = _MAX_MANUAL_DEPTH
    elif depth and depth < _MIN_MANUAL_DEPTH:
        logger.warning(
            "Requested depth %s is below min %s; using %s.",
            depth,
            _MIN_MANUAL_DEPTH,
            _MIN_MANUAL_DEPTH,
        )
        args.depth = _MIN_MANUAL_DEPTH

    # Chord staggering affects note-sequence shaping for chord events.
    raw_stagger = getattr(args, "chord_note_stagger_s", 0.05)
    try:
        stagger = float(raw_stagger)
    except (TypeError, ValueError):
        logger.warning("Invalid chord_note_stagger_s %r; using 0.05.", raw_stagger)
        args.chord_note_stagger_s = 0.05
    else:
        if stagger < 0:
            logger.warning("Negative chord_note_stagger_s %s is invalid; using 0.0.", stagger)
            args.chord_note_stagger_s = 0.0
        else:
            args.chord_note_stagger_s = stagger

    # Quiet mode always suppresses progress output.
    show_progress = show_progress and not bool(args.quiet)

    # Main pipeline: parse input, generate fingering, then write output.
    with _ProgressReporter(show_progress) as progress:
        xmlfn, score_info, rh_noteseq, lh_noteseq = load_note_sequences(args)

        # Report existing score annotations that become hard anchors for optimization.
        rh_anchors = sum(
            1 for n in (rh_noteseq or []) if is_anchored_finger(getattr(n, "fingering", 0))
        )
        lh_anchors = sum(
            1 for n in (lh_noteseq or []) if is_anchored_finger(getattr(n, "fingering", 0))
        )
        if rh_anchors + lh_anchors:
            parts = []
            if not args.left_only:
                parts.append(f"RH={rh_anchors}")
            if not args.right_only:
                parts.append(f"LH={lh_anchors}")
            logger.info(
                "Detected pre-annotated fingers (%s). They will be preserved and used as anchors.",
                ", ".join(parts),
            )
        progress.parse_done()
        rh, lh = generate_hands(args, rh_noteseq, lh_noteseq, progress=progress)
        progress.write_start()
        write_annotated_output(args, score_info, rh, lh)
        progress.write_done()

    # Optional 3D playback happens after output generation.
    maybe_play_vedo(args, xmlfn, rh, lh)

    # Build compact end-of-run summary.
    rh_count = len(rh.noteseq) if rh is not None and getattr(rh, "noteseq", None) else 0
    lh_count = len(lh.noteseq) if lh is not None and getattr(lh, "noteseq", None) else 0
    parts_info = str(len(score_info.parts)) if score_info is not None else "n/a"
    depth_info = "auto" if int(getattr(args, "depth", 0)) == 0 else str(args.depth)

    rh_status = hand_status(is_right=True, score_info=score_info).replace("RH=", "")
    lh_status = hand_status(is_right=False, score_info=score_info).replace("LH=", "")

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        table = Table(title="Run Summary", title_justify="left", show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value", overflow="fold")
        table.add_row("Input", str(args.filename))
        table.add_row("Output", str(args.outputfile))
        table.add_row("Depth", depth_info)
        table.add_row("Parts", parts_info)
        table.add_row("Right Hand", f"{styled_status(rh_status)} | notes={rh_count}")
        table.add_row("Left Hand", f"{styled_status(lh_status)} | notes={lh_count}")
        Console().print(table)

        # Show a final "next command" hint when output is not auto-opened.
        if not args.musescore:
            hint = f"visualize annotated score with command: musescore '{args.outputfile}'"
            panel = Panel(
                f"[bold]💡 {hint}[/bold]",
                border_style="bright_cyan",
                expand=False,
            )
            Console().print(panel)
    except Exception:
        # Fallback for environments where Rich rendering is unavailable.
        logger.info(
            (
                "Summary | input=%s | output=%s | depth=%s | parts=%s "
                "| RH=%s(notes=%s) | LH=%s(notes=%s)"
            ),
            args.filename,
            args.outputfile,
            depth_info,
            parts_info,
            rh_status,
            rh_count,
            lh_status,
            lh_count,
        )
        if not args.musescore:
            logger.info("visualize annotated score with command: musescore '%s'", args.outputfile)
