"""Command line interface for pianoplayer."""

from __future__ import annotations

import argparse
import logging

from rich.logging import RichHandler

from pianoplayer import __version__, __website__
from pianoplayer.errors import PianoPlayerError


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser used by the `pianoplayer` entry point."""
    parser = argparse.ArgumentParser(
        description="PianoPlayer, check out home page https://github.com/marcomusy/pianoplayer"
    )

    parser.add_argument("filename", nargs="?", type=str, help="Input music xml/midi file name")
    parser.add_argument("--gui", action="store_true", help="Launch the Tkinter GUI")
    parser.add_argument(
        "-o",
        "--outputfile",
        metavar="output.xml",
        type=str,
        help="Annotated output xml file name",
        default="output.xml",
    )
    parser.add_argument(
        "-n",
        "--n-measures",
        metavar="",
        type=int,
        help="[1000] Number of score measures to scan",
        default=1000,
    )
    parser.add_argument(
        "-s",
        "--start-measure",
        metavar="",
        type=int,
        help="Start from measure number [1]",
        default=1,
    )
    parser.add_argument(
        "-d",
        "--depth",
        metavar="",
        type=int,
        help="[auto] Depth of combinatorial search, [5-9]",
        default=0,
    )
    parser.add_argument(
        "-rpart", metavar="", type=int, help="[0] Specify Right Hand part number", default=0
    )
    parser.add_argument(
        "-lpart", metavar="", type=int, help="[1] Specify Left Hand part number", default=1
    )
    parser.add_argument(
        "--rstaff",
        metavar="",
        type=int,
        default=0,
        help="[auto] Right-hand staff number for MusicXML (single-part scores).",
    )
    parser.add_argument(
        "--lstaff",
        metavar="",
        type=int,
        default=0,
        help="[auto] Left-hand staff number for MusicXML (single-part scores).",
    )
    routing_group = parser.add_mutually_exclusive_group()
    routing_group.add_argument(
        "--auto-routing",
        dest="auto_routing",
        action="store_true",
        help="Let PianoPlayer resolve part/staff routing automatically (default).",
    )
    routing_group.add_argument(
        "--manual-routing",
        dest="auto_routing",
        action="store_false",
        help="Use explicit -rpart/-lpart/--rstaff/--lstaff values.",
    )
    parser.set_defaults(auto_routing=True)
    parser.add_argument(
        "--cost-path", metavar="", type=str, help="Path to save cost function", default=None
    )
    parser.add_argument("--quiet", help="Switch off verbosity", action="store_true")
    parser.add_argument(
        "-m", "--musescore", help="Open output in musescore after processing", action="store_true"
    )
    parser.add_argument(
        "-b", "--below-beam", help="Show fingering numbers below beam line", action="store_true"
    )
    parser.add_argument(
        "--colorize-hands",
        action="store_true",
        help="Colorize annotated notes/fingerings by hand.",
    )
    parser.add_argument(
        "--colorize-by-cost",
        action="store_true",
        help="Colorize notes/fingerings by computed cost (green->red).",
    )
    parser.add_argument(
        "--colorize-by-fingering",
        action="store_true",
        help="Colorize notes/fingerings by fingering (1=red, 5=blue).",
    )
    parser.add_argument(
        "--rh-color",
        metavar="",
        type=str,
        default="#d62828",
        help="[#d62828] Color for right-hand annotations/notes.",
    )
    parser.add_argument(
        "--lh-color",
        metavar="",
        type=str,
        default="#1d4ed8",
        help="[#1d4ed8] Color for left-hand annotations/notes.",
    )
    parser.add_argument(
        "-v", "--with-vedo", help="Play 3D scene after processing", action="store_true"
    )
    parser.add_argument("-z", "--sound-off", help="Disable sound", action="store_true")
    parser.add_argument(
        "-l", "--left-only", help="Fingering for left hand only", action="store_true"
    )
    parser.add_argument(
        "-r", "--right-only", help="Fingering for right hand only", action="store_true"
    )
    parser.add_argument(
        "--hand-size",
        type=str,
        choices=["XXS", "XS", "S", "M", "L", "XL", "XXL"],
        default="M",
        help="Hand size preset",
    )
    parser.add_argument(
        "--chord-note-stagger-s",
        metavar="",
        type=float,
        default=0.05,
        help="[0.05] Chord note staggering in seconds for optimization.",
    )
    return parser


def show_startup_banner(args: argparse.Namespace) -> None:
    """Print a compact startup panel before the annotation run begins."""
    if args.quiet or not args.filename:
        return

    if args.left_only:
        hand_mode = "left hand only"
    elif args.right_only:
        hand_mode = "right hand only"
    else:
        hand_mode = "both hands"

    lines = [
        f"[bold]PianoPlayer[/bold] v{__version__}",
        f"[dim]{__website__}[/dim]",
        "",
        f"[cyan]Input:[/cyan] {args.filename}",
        f"[cyan]Output:[/cyan] {args.outputfile}",
        f"[cyan]Mode:[/cyan] {hand_mode}",
        f"[cyan]Hand size:[/cyan] {args.hand_size}",
    ]
    if args.sound_off:
        lines.append("[cyan]Audio:[/cyan] off")
    if args.colorize_hands:
        lines.append(f"[cyan]Colors:[/cyan] RH {args.rh_color} | LH {args.lh_color}")
    if args.colorize_by_fingering:
        lines.append("[cyan]Colors:[/cyan] by fingering")

    body = "\n".join(lines)
    try:
        from rich.console import Console
        from rich.panel import Panel

        Console().print(Panel.fit(body, border_style="bright_blue"))
    except Exception:
        print(f"PianoPlayer v{__version__}")
        print(f"Input: {args.filename}")
        print(f"Output: {args.outputfile}")
        print(f"Mode: {hand_mode}")
        print(f"Hand size: {args.hand_size}")


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    level = logging.WARNING if getattr(args, "quiet", False) else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_path=False,
                markup=True,
            )
        ],
    )

    if args.gui or args.filename is None:
        from pianoplayer.gui import launch

        launch()
        return

    from pianoplayer import core

    try:
        show_startup_banner(args)
        # Enable progress UI by default unless quiet mode is requested.
        args._show_progress = not args.quiet
        core.annotate(args)
    except (PianoPlayerError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
