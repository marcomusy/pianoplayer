import os, sys
from music21 import converter, stream
from pianoplayer.hand import Hand
from pianoplayer.scorereader import reader, PIG2Stream, reader_pretty_midi
from operator import attrgetter
import pretty_midi
###########################################################
__author__ = "Marco Musy"
__email__ = "marco.musy@gmail.com"
__version__ = "2.2.0"  # defined in setup.py
__status__ = "dev"
__website__ = "https://github.com/marcomusy/pianoplayer"
__license__ = "MIT"
###########################################################
# Piano Player main analyse and annotate
###########################################################
def run_analyse():
    pass


def analyse():
    pass


def run_annotate(filename,
                 outputfile='output.xml',
                 n_measures=100,
                 start_measure=1,
                 depth=0,
                 rbeam=0,
                 lbeam=1,
                 cost_path=None,
                 quiet=False,
                 musescore=False,
                 below_beam=False,
                 with_vedo=1.5,
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
    args.cost_path = cost_path
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
        sf = stream.Stream()

        if not args.left_only:
            ptr = PIG2Stream(args.filename, args.rbeam)
            rh_noteseq = reader(ptr, beam=args.rbeam)
        if not args.right_only:
            ptl = PIG2Stream(args.filename, args.lbeam)
            lh_noteseq = reader(ptl, beam=args.lbeam)
    elif '.mid' in args.filename or '.midi' in args.filename:
        pm = pretty_midi.PrettyMIDI(args.filename)
        if not args.left_only:
            pm_right = pm.instruments[args.rbeam]
            rh_noteseq = reader_pretty_midi(pm_right, beam=args.rbeam)
        if not args.right_only:
            pm_left = pm.instruments[args.lbeam]
            lh_noteseq = reader_pretty_midi(pm_left, beam=args.lbeam)

    else:
        sf = converter.parse(xmlfn)
        if not args.left_only:
            rh_noteseq = reader(sf, beam=args.rbeam)
        if not args.right_only:
            lh_noteseq = reader(sf, beam=args.lbeam)

    if not args.left_only:
        rh = Hand("right", hand_size)
        rh.verbose = not (args.quiet)
        if args.depth == 0:
            rh.autodepth = True
        else:
            rh.autodepth = False
            rh.depth = args.depth
        rh.lyrics = args.below_beam

        rh.noteseq = rh_noteseq
        rh.generate(args.start_measure, args.n_measures, cost_path=cost_path)

    if not args.right_only:
        lh = Hand("left", hand_size)
        lh.verbose = not (args.quiet)
        if args.depth == 0:
            lh.autodepth = True
        else:
            lh.autodepth = False
            lh.depth = args.depth
        lh.lyrics = args.below_beam

        lh.noteseq = lh_noteseq
        lh.generate(args.start_measure, args.n_measures, filename=os.path.splitext(args.filename)[0])

    # sf.write('xml', fp=args.outputfile)

    # if args.musescore:  # -m option
    #     print('Opening musescore with output score:', args.outputfile)
    #     os.system('musescore "' + args.outputfile + '" > /dev/null 2>&1')
    # else:
    #     print("\nTo visualize annotated score with fingering type:\n musescore '" + args.outputfile + "'")

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
