
![banner](https://github.com/user-attachments/assets/7242fc4e-873f-42fc-99ff-edf985a412eb)

[![PyPI version](https://img.shields.io/pypi/v/pianoplayer.svg)](https://pypi.org/project/pianoplayer/)
[![Downloads](https://pepy.tech/badge/pianoplayer)](https://pepy.tech/project/pianoplayer)
[![Downloads / Month](https://pepy.tech/badge/pianoplayer/month)](https://pepy.tech/project/pianoplayer)
[![lics](https://img.shields.io/badge/license-MIT-blue.svg)](https://en.wikipedia.org/wiki/MIT_License)
[![DOI](https://zenodo.org/badge/107160052.svg)](https://zenodo.org/badge/latestdoi/107160052)
[![CI](https://github.com/marcomusy/pianoplayer/actions/workflows/ci.yml/badge.svg)](https://github.com/marcomusy/pianoplayer/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/marcomusy/pianoplayer.svg?style=social)](https://github.com/marcomusy/pianoplayer/stargazers)


Automatic piano fingering generator for MusicXML and MIDI scores.  
PianoPlayer searches for a low-effort fingering sequence for one or both hands.  

## Download and Install:
```bash
pip install pianoplayer
```
Optional extras:
```bash
pip install "pianoplayer[visual]"  # 3D rendering with vedo
pip install "pianoplayer[midi]"    # MIDI input support
pip install "pianoplayer[sound]"   # enable playback
pip install "pianoplayer[all]"     # all optional extras
```

<details>
<summary><strong>Python Setup (Beginner-Friendly)</strong></summary>

If you are new to Python, use one of these two approaches.

### Option A: Anaconda (recommended for beginners on Windows)

1. Install Anaconda from https://www.anaconda.com/download
2. Type **Anaconda Prompt** in your windows search and open it.
3. Install PianoPlayer, type:
```bash
pip install pianoplayer
```
4. Run:
```bash
pianoplayer --help
```

### Option B: Python from python.org

Windows:
1. Install Python 3.10+ from https://www.python.org/downloads/windows/
2. During installation, enable **Add Python to PATH**.
3. Open **Command Prompt** and run:
```bash
python -m pip install --upgrade pip
pip install pianoplayer
pianoplayer --help
```

macOS/Linux:
```bash
python3 -m pip install --upgrade pip
pip install pianoplayer
pianoplayer --help
```

</details>

To visualize the output annotated score (`output.xml`) install the latest
[musescore](https://musescore.org/en/download), or any other renderer
of [MusicXML](https://en.wikipedia.org/wiki/MusicXML)
files.
You can also inspect playback in 3D with [vedo](https://github.com/marcomusy/vedo).


## CLI Usage:
Example command line:
`pianoplayer scores/bach_invention4.xml -n 10 -r -v -z -m`  
This annotates the first 10 measures for the right hand, opens 3D playback, and then opens MuseScore.

The output is saved as a [MusicXML](https://en.wikipedia.org/wiki/MusicXML)
file with name `output.xml`.<br />

Pre-fingered notes are supported: if a note already has a fingering mark, `PianoPlayer` keeps it
and uses it as an anchor for the following optimization.

```bash
pianoplayer         # if no argument is given a GUI will pop up
# Or
pianoplayer [-h] [--gui] [-o] [-n] [-s] [-d] [-rbeam] [-lbeam] [--quiet] [-m] [-b] [-v]
            [-z] [-l] [-r] [--hand-size {XXS,XS,S,M,L,XL,XXL}] [--chord-note-stagger-s]
            filename
# Valid file formats: MusicXML, compressed MusicXML, MuseScore, MIDI, PIG
# (.xml, .mxl, .mscz, .mscx, .mid, .midi, .txt)
#
# Optional arguments:
#   -h, --help            show this help message and exit
#   --gui                 Launch the Tkinter GUI
#   -o , --outputfile     Annotated output xml file name
#   -n , --n-measures     [100] Number of score measures to scan
#   -s , --start-measure  Start from measure number [1]
#   -d , --depth          [auto] Depth of combinatorial search, [5-9]
#   -rbeam                [0] Specify Right Hand beam number
#   -lbeam                [1] Specify Left Hand beam number
#   --quiet               Switch off verbosity
#   -m, --musescore       Open output in musescore after processing
#   -b, --below-beam      Show fingering numbers below beam line
#   -v, --with-vedo       Play 3D scene after processing
#   -z, --sound-off       Disable sound
#   -l, --left-only       Fingering for left hand only
#   -r, --right-only      Fingering for right hand only
#   --hand-size           Hand size preset [XXS, XS, S, M, L, XL, XXL]
#   --chord-note-stagger-s [0.05] Small note staggering used to represent chords
```

### GUI Usage
Run `pianoplayer` with no filename to open the GUI, then:

![newgui](https://user-images.githubusercontent.com/32848391/63605343-09365000-c5ce-11e9-97b8-a5642e71ca24.png)

- press **Import Score** (valid formats: *MusicXML/MXL, MuseScore, MIDI, [PIG](http://beam.kisarazu.ac.jp/~saito/research/PianoFingeringDataset/)*)
- press **GENERATE** (`output.xml` is written)
- press **Musescore** to visualize the annotated score (Linux/macOS only)
- press **Quit** (or `q` / `Ctrl+W`) to close the GUI


#### Example output, as displayed in *musescore*:

(If fingering numbers are not visible enough try `-b` option.)


![bachinv4](https://user-images.githubusercontent.com/32848391/63605352-10f5f480-c5ce-11e9-8b00-34f1adc2e79b.png)


![pianoplayer3d](https://user-images.githubusercontent.com/32848391/63605322-0176ab80-c5ce-11e9-8213-b572d0303523.gif)


## How the algorithm works:
The algorithm minimizes the fingers speed needed to play a sequence of notes or chords by searching
through feasible combinations of fingerings.

One possible advantage of this algorithm over similar ones is that it is completely *dynamic*,
which means that it
takes into account the physical position and speed of fingers while moving on the keyboard
and the duration of each played note.
It is *not* based on a static look-up table of likely or unlikely combinations of fingerings.

Fingering a piano score can vary a lot from individual to individual, therefore there is not such
a thing as a "best" choice for fingering.
This algorithm is meant to suggest a fingering combination which is "optimal" in the sense that it
minimizes the effort of the hand avoiding unnecessary movements.

## Parameters you can change:
- Your hand size (from 'XXS' to 'XXL') which sets the relaxed distance between thumb and pinkie.
- The beam number associated to the right hand is by default nr.0 (nr.1 for left hand).
You can change it with `-rbeam` and `-lbeam` command line options.
- Depth of combinatorial search, from 5 up to 9 notes ahead of the currently playing note. By
default the algorithm selects this number automatically based on the duration of the notes to be played.

## Limitations
- Some specific fingering combinations, considered too unlikely in the first place, are excluded from the search (e.g. the 3rd finger crossing the 4th).
- Hands are always assumed independent from each other.
- In the 3D representation with sounds enabled, notes are played one after the other (no chords),
so the tempo within the measure is not always respected.
- Small notes/ornaments are ignored.
