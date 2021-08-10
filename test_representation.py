import json
import os

import pretty_midi
from PyPDF2 import PdfFileMerger

from pianoplayer.core import run_annotate
import multiprocessing as mp

scores = [
    'bach_airgstring.xml',
    'bach_invention4.xml',
    'bach_joy.xml',
    'bach_prelude.xml',
    'clayderman_ladyd.xml',
    'couperin_baricades.xml',
    'fugue_bach.mxl',
    'mozart_sonfacile.xml',
    'pachelbel_canon.xml',
    'test_chords.xml',
    'test_octaves.xml',
    'test_scales.xml',
]


def run_loop(args):
    score_path = args

    run_annotate('scores/' + score_path, outputfile='temp/' + score_path, musescore=False, n_measures=100000, depth=9)


def process_pianoplayer_dataset():
    num_workers = mp.cpu_count()
    print("num_workers", num_workers)

    p = mp.Pool(processes=num_workers)
    p.map(run_loop, scores)


def concat_little():
    xmls = ['temp/' + os.path.splitext(p)[0] + '.xml' for p in scores]
    pdfs = ['temp/' + os.path.splitext(p)[0] + '.pdf' for p in scores]
    merger = PdfFileMerger()

    for xml, pdf in zip(xmls, pdfs):
        print("'/Applications/MuseScore\ 3.app/Contents/MacOS/mscore' " + xml + ' -o ' + pdf)
        os.system("/Applications/MuseScore\ 3.app/Contents/MacOS/mscore " + xml + ' -o' + pdf)
        merger.append(pdf)

    merger.write("examples/litle_dataset.pdf")
    merger.close()


def convert_little2midi():

    xmls = ['scores/' + os.path.splitext(p)[0] + '.xml' for p in scores]
    midis = ['temp/' + os.path.splitext(p)[0] + '.mid' for p in scores]
    midis_rh = ['temp/' + os.path.splitext(p)[0] + '_rh.mid' for p in scores]
    midis_lh = ['temp/' + os.path.splitext(p)[0] + '_lh.mid' for p in scores]

    for xml, midi, midi_rh, midi_lh in zip(xmls, midis, midis_rh, midis_lh):
        print("'/Applications/MuseScore\ 3.app/Contents/MacOS/mscore' " + xml + ' -o ' + midi)

        os.system("/Applications/MuseScore\ 3.app/Contents/MacOS/mscore " + xml + ' -o' + midi)


def test_xmls_midis():
    num_workers = mp.cpu_count()
    xmls = ['scores/' + os.path.splitext(p)[0] + '.xml' for p in scores]
    midis = ['temp/' + os.path.splitext(p)[0] + '.mid' for p in scores]
    xmls_txt = ['scores/' + os.path.splitext(p)[0] + '_txt.mid' for p in scores]
    midis_txt = ['temp/' + os.path.splitext(p)[0] + '_txt.txt' for p in scores]

    args_midi = [(midi, xmidi) for midi, xmidi in zip(midis, midis_txt)]

    p = mp.Pool(processes=num_workers)
    p.map(run_loop, args_midi)

    args_xml = [(xml, xtxt) for xml, xtxt in zip(xmls, xmls_txt)]

    p = mp.Pool(processes=num_workers)
    p.map(run_loop, args_xml)


if __name__ == '__main__':
    process_pianoplayer_dataset()
    concat_little()
    # convert_little2midi()
    # test_xmls_midis()