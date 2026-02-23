"""Command line interface for pianoplayer."""

from __future__ import annotations

import argparse
import logging

from pianoplayer.errors import PianoPlayerError


def build_parser() -> argparse.ArgumentParser:
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
        help="[100] Number of score measures to scan",
        default=100,
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
        help="[auto] Depth of combinatorial search, [4-9]",
        default=0,
    )
    parser.add_argument(
        "-rbeam", metavar="", type=int, help="[0] Specify Right Hand beam number", default=0
    )
    parser.add_argument(
        "-lbeam", metavar="", type=int, help="[1] Specify Left Hand beam number", default=1
    )
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
        "-v", "--with-vedo", help="Play 3D scene after processing", action="store_true"
    )
    parser.add_argument(
        "--vedo-speed", metavar="", type=float, help="[1] Speed factor of rendering", default=1.5
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
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.WARNING if getattr(args, "quiet", False) else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.gui or args.filename is None:
        from pianoplayer.gui import launch

        launch()
        return

    from pianoplayer import core

    try:
        core.annotate(args)
    except (PianoPlayerError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
