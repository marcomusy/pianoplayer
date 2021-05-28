import csv
import json
import os, sys
import platform

from music21 import converter, stream
from music21.articulations import Fingering

from pianoplayer.hand import Hand
from pianoplayer.scorereader import reader, PIG2Stream, reader_pretty_midi, reader_PIG
import pretty_midi


###########################################################
# Piano Player main analyse and annotate
###########################################################
# def run_analyse():
#     pass
#
#
# def analyse():
#     pass


def run_annotate(filename,
                 outputfile='output.xml',
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
                 hand_size_XXL=False
                 ):
    class Args(object):
        pass
    args = Args()
    args.filename = filename
    args.outputfile = outputfile
    args.n_measures = n_measures
    args.start_measure = start_measure
    args.depth = depth
    args.rbeam = rbeam
    args.lbeam = lbeam
    args.quiet = quiet
    args.musescore = musescore
    args.below_beam = below_beam
    args.with_vedo = with_vedo
    args.vedo_speed = vedo_speed
    args.sound_off = sound_off
    args.left_only = left_only
    args.right_only = right_only
    args.hand_size_XXS = hand_size_XXS
    args.hand_size_XS = hand_size_XS
    args.hand_size_S = hand_size_S
    args.hand_size_M = hand_size_M
    args.hand_size_L = hand_size_L
    args.hand_size_XL = hand_size_XL
    args.hand_size_XXL = hand_size_XXL
    annotate(args)


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
            for j, cn in enumerate(el.pitches):
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
        channel = '0' if is_right else '1'
        finger_number = n.fingering if is_right else -n.fingering
        cost = n.cost
        ans.append((onset_time, offset_time, spelled_pitch, onset_velocity, offset_velocity, channel,
                    finger_number, cost, n.noteID))
    return ans


def annotate(args):
    hand_size = 'M'  # default
    if args.hand_size_XXS: hand_size = 'XXS'
    if args.hand_size_XS: hand_size = 'XS'
    if args.hand_size_S: hand_size = 'S'
    if args.hand_size_M: hand_size = 'M'
    if args.hand_size_L: hand_size = 'L'
    if args.hand_size_XL: hand_size = 'XL'
    if args.hand_size_XXL: hand_size = 'XXL'

    xmlfn = args.filename
    if '.msc' in args.filename:
        try:
            xmlfn = str(args.filename).replace('.mscz', '.xml').replace('.mscx', '.xml')
            print('..trying to convert your musescore file to', xmlfn)
            os.system(
                'musescore -f "' + args.filename + '" -o "' + xmlfn + '"')  # quotes avoid problems w/ spaces in filename
            sf = converter.parse(xmlfn)
            if not args.left_only:
                rh_noteseq = reader(sf, beam=args.rbeam)
            if not args.right_only:
                lh_noteseq = reader(sf, beam=args.lbeam)
        except:
            print('Unable to convert file, try to do it from musescore.')
            sys.exit()

    elif '.txt' in args.filename:
        if not args.left_only:
            rh_noteseq = reader_PIG(args.filename, args.rbeam)
        if not args.right_only:
            lh_noteseq = reader_PIG(args.filename, args.lbeam)

    elif '.mid' in args.filename or '.midi' in args.filename:
        pm = pretty_midi.PrettyMIDI(args.filename)
        if not args.left_only:
            pm_right = pm.instruments[args.rbeam]
            rh_noteseq = reader_pretty_midi(pm_right, beam=args.rbeam)
        if not args.right_only:
            pm_left = pm.instruments[args.lbeam]
            lh_noteseq = reader_pretty_midi(pm_left, beam=args.lbeam)

    else:
        sc = converter.parse(xmlfn)
        if not args.left_only:
            rh_noteseq = reader(sc, beam=args.rbeam)
        if not args.right_only:
            lh_noteseq = reader(sc, beam=args.lbeam)

    if not args.left_only:
        rh = Hand(side="right", noteseq=rh_noteseq, size=hand_size)
        rh.verbose = not (args.quiet)
        if args.depth == 0:
            rh.autodepth = True
        else:
            rh.autodepth = False
            rh.depth = args.depth
        rh.lyrics = args.below_beam

        rh.generate(args.start_measure, args.n_measures)

    if not args.right_only:
        lh = Hand(side="left", noteseq=lh_noteseq, size=hand_size)
        lh.verbose = not (args.quiet)
        if args.depth == 0:
            lh.autodepth = True
        else:
            lh.autodepth = False
            lh.depth = args.depth
        lh.lyrics = args.below_beam

        lh.noteseq = lh_noteseq
        lh.generate(args.start_measure, args.n_measures)

    if args.outputfile is not None:
        ext = os.path.splitext(args.outputfile)[1]
        # an extended PIG file  (note ID) (onset time) (offset time) (spelled pitch) (onset velocity) (offset velocity) (channel) (finger number) (cost)
        if ext == ".txt":
            pig_notes = []
            if not args.left_only:
                pig_notes.extend(annotate_PIG(rh))

            if not args.right_only:
                pig_notes.extend(annotate_PIG(lh, is_right=False))

            with open(args.outputfile, 'wt') as out_file:
                tsv_writer = csv.writer(out_file, delimiter='\t')
                for idx, (onset_time, offset_time, spelled_pitch, onset_velocity, offset_velocity, channel,
                          finger_number, cost, id_n) in enumerate(sorted(pig_notes, key=lambda tup: (float(tup[0]), int(tup[5]), int(tup[2])))):
                    tsv_writer.writerow([idx, onset_time, offset_time, spelled_pitch, onset_velocity, offset_velocity,
                                         channel, finger_number, cost, id_n])
        else:
            ext = os.path.splitext(args.filename)[1]
            if ext in ['mid', 'midi']:
                sf = converter.parse(xmlfn)
            elif ext in ['txt']:
                sf = stream.Stream()
                if not args.left_only:
                    ptr = PIG2Stream(args.filename, 0)
                    sf.insert(0, ptr)
                if not args.right_only:
                    ptl = PIG2Stream(args.filename, 1)
                    sf.insert(0, ptl)  # 0=offset
            else:
                sf = converter.parse(xmlfn)

            # Annotate fingers in XML
            if not args.left_only:
                sf = annotate_fingers_xml(sf, rh, args, is_right=True)

            if not args.right_only:
                sf = annotate_fingers_xml(sf, lh, args, is_right=False)
            sf.write('musicxml', fp=args.outputfile)

            if args.musescore:  # -m option
                print('Opening musescore with output score:', args.outputfile)
                if platform.system() == 'Darwin':
                    os.system('open "' + args.outputfile + '"')
                else:
                    os.system('musescore "' + args.outputfile + '" > /dev/null 2>&1')
            else:
                print("\nTo visualize annotated score with fingering type:\n musescore '" + args.outputfile + "'")

    if args.with_vedo:
        from pianoplayer.vkeyboard import VirtualKeyboard

        if args.start_measure != 1:
            print('Sorry, start_measure must be set to 1 when -v option is used. Exit.')
            exit()

        vk = VirtualKeyboard(songname=xmlfn)

        if not args.left_only:
            vk.build_RH(rh)
        if not args.right_only:
            vk.build_LH(lh)

        if args.sound_off:
            vk.playsounds = False

        vk.speedfactor = args.vedo_speed
        vk.play()
        vk.vp.show(zoom=2, interactive=1)


if __name__ == '__main__':
    run_annotate('../scores/test_chord.xml', outputfile="test_chord_annotate.xml", right_only=True, musescore=True, n_measures=800, depth=0)