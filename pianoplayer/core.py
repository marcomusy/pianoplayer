from __future__ import annotations

import csv
import logging
import os
import platform
import subprocess
from types import SimpleNamespace
from typing import Any

from music21 import converter, stream
from music21.articulations import Fingering

from pianoplayer.errors import ConversionError, ExternalToolError
from pianoplayer.hand import Hand
from pianoplayer.models import AnnotateOptions
from pianoplayer.scorereader import PIG2Stream, reader, reader_PIG, reader_pretty_midi

logger = logging.getLogger(__name__)


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
    vedo_speed=False,
    sound_off=False,
    left_only=False,
    right_only=False,
    hand_size_XXS=False,
    hand_size_XS=False,
    hand_size_S=False,
    hand_size_M=False,
    hand_size_L=False,
    hand_size_XL=True,
    hand_size_XXL=False,
):
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
        vedo_speed=vedo_speed,
        sound_off=sound_off,
        left_only=left_only,
        right_only=right_only,
        hand_size_XXS=hand_size_XXS,
        hand_size_XS=hand_size_XS,
        hand_size_S=hand_size_S,
        hand_size_M=hand_size_M,
        hand_size_L=hand_size_L,
        hand_size_XL=hand_size_XL,
        hand_size_XXL=hand_size_XXL,
    )
    annotate(options)


def _as_namespace(args: Any) -> SimpleNamespace:
    if isinstance(args, AnnotateOptions):
        return args.to_namespace()
    if isinstance(args, SimpleNamespace):
        return args
    return AnnotateOptions.from_namespace(args).to_namespace()


def annotate_fingers_xml(sf, hand, args, is_right=True):
    p0 = sf.parts[args.rbeam if is_right else args.lbeam]
    idx = 0
    for el in p0.flat.getElementsByClass("GeneralNote"):
        if el.isNote:
            n = hand.noteseq[idx]
            if hand.lyrics:
                el.addLyric(n.fingering)
            else:
                el.articulations.append(Fingering(n.fingering))
            idx += 1
        elif el.isChord:
            for _, cn in enumerate(el.pitches):
                n = hand.noteseq[idx]
                if hand.lyrics:
                    nl = len(cn.chord21.pitches) - cn.chordnr
                    el.addLyric(cn.fingering, nl)
                else:
                    el.articulations.append(Fingering(n.fingering))
                idx += 1

    return sf


def annotate_PIG(hand, is_right=True):
    ans = []
    for n in hand.noteseq:
        onset_time = "{:.4f}".format(n.time)
        offset_time = "{:.4f}".format(n.time + n.duration)
        spelled_pitch = n.pitch
        onset_velocity = str(None)
        offset_velocity = str(None)
        channel = "0" if is_right else "1"
        finger_number = n.fingering if is_right else -n.fingering
        cost = n.cost
        ans.append(
            (
                onset_time,
                offset_time,
                spelled_pitch,
                onset_velocity,
                offset_velocity,
                channel,
                finger_number,
                cost,
                n.noteID,
            )
        )
    return ans


def _hand_size_from_args(args):
    hand_size = "M"
    if args.hand_size_XXS:
        hand_size = "XXS"
    if args.hand_size_XS:
        hand_size = "XS"
    if args.hand_size_S:
        hand_size = "S"
    if args.hand_size_M:
        hand_size = "M"
    if args.hand_size_L:
        hand_size = "L"
    if args.hand_size_XL:
        hand_size = "XL"
    if args.hand_size_XXL:
        hand_size = "XXL"
    return hand_size


def _run_external(cmd: list[str], context: str) -> None:
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise ExternalToolError(f"Required executable not found for {context}: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise ExternalToolError(f"External command failed for {context}: {' '.join(cmd)}") from exc


def load_note_sequences(args):
    args = _as_namespace(args)
    xmlfn = args.filename
    rh_noteseq = None
    lh_noteseq = None

    try:
        if ".msc" in args.filename:
            xmlfn = str(args.filename).replace(".mscz", ".xml").replace(".mscx", ".xml")
            logger.info("Converting MuseScore file %s -> %s", args.filename, xmlfn)
            _run_external(["musescore", "-f", args.filename, "-o", xmlfn], "MuseScore conversion")
            score = converter.parse(xmlfn)
            if not args.left_only:
                rh_noteseq = reader(score, beam=args.rbeam)
            if not args.right_only:
                lh_noteseq = reader(score, beam=args.lbeam)
        elif ".txt" in args.filename:
            if not args.left_only:
                rh_noteseq = reader_PIG(args.filename, args.rbeam)
            if not args.right_only:
                lh_noteseq = reader_PIG(args.filename, args.lbeam)
        elif ".mid" in args.filename or ".midi" in args.filename:
            import pretty_midi

            pm = pretty_midi.PrettyMIDI(args.filename)
            if not args.left_only:
                pm_right = pm.instruments[args.rbeam]
                rh_noteseq = reader_pretty_midi(pm_right, beam=args.rbeam)
            if not args.right_only:
                pm_left = pm.instruments[args.lbeam]
                lh_noteseq = reader_pretty_midi(pm_left, beam=args.lbeam)
        else:
            score = converter.parse(xmlfn)
            if not args.left_only:
                rh_noteseq = reader(score, beam=args.rbeam)
            if not args.right_only:
                lh_noteseq = reader(score, beam=args.lbeam)
    except ExternalToolError:
        raise
    except Exception as exc:
        raise ConversionError(f"Unable to parse/convert input score: {args.filename}") from exc

    return xmlfn, rh_noteseq, lh_noteseq


def generate_hands(args, rh_noteseq, lh_noteseq):
    args = _as_namespace(args)
    hand_size = _hand_size_from_args(args)
    rh = None
    lh = None

    if not args.left_only:
        rh = Hand(side="right", noteseq=rh_noteseq, size=hand_size)
        rh.verbose = not args.quiet
        rh.autodepth = args.depth == 0
        if not rh.autodepth:
            rh.depth = args.depth
        rh.lyrics = args.below_beam
        rh.generate(args.start_measure, args.n_measures)

    if not args.right_only:
        lh = Hand(side="left", noteseq=lh_noteseq, size=hand_size)
        lh.verbose = not args.quiet
        lh.autodepth = args.depth == 0
        if not lh.autodepth:
            lh.depth = args.depth
        lh.lyrics = args.below_beam
        lh.generate(args.start_measure, args.n_measures)

    return rh, lh


def build_output_stream(args, xmlfn):
    args = _as_namespace(args)
    ext = os.path.splitext(args.filename)[1]
    if ext in ["mid", "midi"]:
        return converter.parse(xmlfn)
    if ext in ["txt"]:
        sf = stream.Stream()
        if not args.left_only:
            ptr = PIG2Stream(args.filename, 0)
            sf.insert(0, ptr)
        if not args.right_only:
            ptl = PIG2Stream(args.filename, 1)
            sf.insert(0, ptl)
        return sf
    return converter.parse(xmlfn)


def write_annotated_output(args, xmlfn, rh, lh):
    args = _as_namespace(args)
    if args.outputfile is None:
        return

    ext = os.path.splitext(args.outputfile)[1]
    if ext == ".txt":
        pig_notes = []
        if not args.left_only and rh is not None:
            pig_notes.extend(annotate_PIG(rh))
        if not args.right_only and lh is not None:
            pig_notes.extend(annotate_PIG(lh, is_right=False))

        with open(args.outputfile, "wt", encoding="utf-8") as out_file:
            tsv_writer = csv.writer(out_file, delimiter="\t")
            for idx, (
                onset_time,
                offset_time,
                spelled_pitch,
                onset_velocity,
                offset_velocity,
                channel,
                finger_number,
                cost,
                id_n,
            ) in enumerate(
                sorted(pig_notes, key=lambda tup: (float(tup[0]), int(tup[5]), int(tup[2])))
            ):
                tsv_writer.writerow(
                    [
                        idx,
                        onset_time,
                        offset_time,
                        spelled_pitch,
                        onset_velocity,
                        offset_velocity,
                        channel,
                        finger_number,
                        cost,
                        id_n,
                    ]
                )
        logger.info("Wrote annotated PIG output to %s", args.outputfile)
        return

    sf = build_output_stream(args, xmlfn)
    if not args.left_only and rh is not None:
        sf = annotate_fingers_xml(sf, rh, args, is_right=True)
    if not args.right_only and lh is not None:
        sf = annotate_fingers_xml(sf, lh, args, is_right=False)
    sf.write("musicxml", fp=args.outputfile)
    logger.info("Wrote annotated score to %s", args.outputfile)

    if args.musescore:
        logger.info("Opening MuseScore with output score: %s", args.outputfile)
        if platform.system() == "Darwin":
            _run_external(["open", args.outputfile], "open output score")
        else:
            _run_external(["musescore", args.outputfile], "open MuseScore")
    else:
        logger.info("To visualize annotated score with fingering: musescore '%s'", args.outputfile)


def maybe_play_vedo(args, xmlfn, rh, lh):
    args = _as_namespace(args)
    if not args.with_vedo:
        return

    if args.start_measure != 1:
        raise ValueError("start_measure must be set to 1 when -v/--with-vedo is used")

    from pianoplayer.vkeyboard import VirtualKeyboard

    vk = VirtualKeyboard(songname=xmlfn)
    if not args.left_only and rh is not None:
        vk.build_RH(rh)
    if not args.right_only and lh is not None:
        vk.build_LH(lh)

    if args.sound_off:
        vk.playsounds = False

    vk.speedfactor = args.vedo_speed
    vk.play()
    vk.vp.show(zoom=2, interactive=1)


def annotate(args: AnnotateOptions | SimpleNamespace | Any):
    args = _as_namespace(args)
    xmlfn, rh_noteseq, lh_noteseq = load_note_sequences(args)
    rh, lh = generate_hands(args, rh_noteseq, lh_noteseq)
    write_annotated_output(args, xmlfn, rh, lh)
    maybe_play_vedo(args, xmlfn, rh, lh)
