import json
import os

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
    'schumann.xml',
    'test_chords.xml',
    'test_octaves.xml',
    'test_scales.xml',
]


def run_loop(s):
    score_path = os.path.join('scores', s)
    output_path = os.path.join('temp', os.path.splitext(s)[0] + '.xml')

    run_annotate(score_path, outputfile=output_path, musescore=False,
                 n_measures=100000, depth=9)


def test_scores():
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


if __name__ == '__main__':
    # test_scores()
    concat_little()
