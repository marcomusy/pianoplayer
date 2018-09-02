# PianoPlayer 2.0
Automatic piano fingering generator. 
Find and animate the optimal fingering combination to play a score 
and visualize it in 3D with [vtkplotter](https://github.com/marcomusy/vtkplotter)
and [music21](http://web.mit.edu/music21).<br />

## Download and Install:
```bash
(sudo) pip install --upgrade pianoplayer
```

### Optional:
To visualize the annotated score install for free [musescore](https://musescore.org/it/download):
```bash
sudo apt install musescore
```

To open a 3D visualization, install VTK with one of these command lines:
```bash
sudo apt install vtk7
# or
conda install -c conda-forge vtk
# or 
(sudo) pip install vtk
#
# for sound:
sudo apt install libasound2-dev
(sudo) pip install simpleaudio
```

## Usage: 
```bash
pianoplayer         # if no argument is given a GUI will pop up (on windows try `python pianoplayer`)
# Or
pianoplayer [-h] [-o] [-n] [-s] [-d] [-k] [-rbeam] [-lbeam] [-q] [-m] [-v] [--vtk-speed] 
            [-z] [-l] [-r] [-XXS] [-XS] [-S] [-M] [-L] [-XL] [-XXL]
            filename
# Valid file formats: music-xml, musescore, midi (.xml, .mscz, .mscx, .mid)
#
# Optional arguments:
#   -h, --help            show this help message and exit
#   -o , --outputfile     Annotated output xml file name
#   -n , --n-measures     [100] Number of score measures to scan
#   -s , --start-measure  Start from measure number [1]
#   -d , --depth          [auto] Depth of combinatorial search, [4-9]
#   -rbeam                [0] Specify Right Hand beam number
#   -lbeam                [1] Specify Left Hand beam number
#   --debug               Switch on verbosity
#   -m, --musescore       Open output in musescore after processing
#   -b, --below-beam      Show fingering numbers below beam line
#   -v, --with-vtk        Play 3D scene after processing
#   --vtk-speed           [1] Speed factor of 3D rendering
#   -z, --sound-off       Disable sound
#   -l, --left-only       Fingering for left hand only
#   -r, --right-only      Fingering for right hand only
#   -XXS, --hand-size-XXS Set hand size to XXS
#   -XS, --hand-size-XS   Set hand size to XS
#   -S, --hand-size-S     Set hand size to S
#   -M, --hand-size-M     Set hand size to M
#   -L, --hand-size-L     Set hand size to L
#   -XL, --hand-size-XL   Set hand size to XL
#   -XXL, --hand-size-XXL Set hand size to XXL
```
Example command line:
`pianoplayer scores/bach_invention4.xml -n10 -r -v --vtk-speed 2 --debug -mb`<br />
will find fingerings for the first 10 measures right hand, pop up the 3D rendering and invoke musescore.<br />

If using the GUI:<br />
- press Import Score
- press GENERATE (a file output.xml is written)
- press Musescore to visualise the annotated score
- press 3D Player to show the animation (closing it with Esc will quit the application)

![alt text](https://user-images.githubusercontent.com/32848391/31662571-42a05c94-b33f-11e7-9a5e-989fea82ad4c.png)

![alt text](https://user-images.githubusercontent.com/32848391/31663245-a9e23e0c-b341-11e7-9e07-d90d4959521b.png)

If VTK is installed click on "3D Player" for a visualization (in interactive mode, drag mouse 
to move the scene, right-click drag to zoom). You will see the both hands playing but hear the right hand notes only. 
Chords are rendered as a rapid sequence of notes.

![pianoplayer3d](https://user-images.githubusercontent.com/32848391/44957809-b2c09500-aed6-11e8-9dc5-c2e52b632f94.gif)


## How does the algorithm work:
The algorithm minimizes the fingers speed needed to play a sequence of notes or chords by searching 
through feasible combinations of fingerings. 
At every note the hand position is assumed to be at rest (this can be improved in the future). 

## Parameters you can change:
- your hand size (from 'XXS' to 'XXL') which sets the relaxed distance between thumb and pinkie (e.g. 'M' = 17 cm)
- the beam number associated to the right hand is by default nr.0 (nr.1 for left hand). 
You can change it with `-rbeam` and `-lbeam` command line options.
- depth of combinatorial search (from 4 up to 9 notes ahead of the currently playing note, by
default the algorithm selects this number automatically based on the duration of the notes to be played).

## Advantages
One possible advantage is that this algorithm is completely *dynamic* which means that it 
takes into account the physical position and speed of fingers while moving on the keyboard and the duration of each played note. 
It is *not* based on a static look-up table of likely or unlikely combinations of fingerings.

## Limitations
- Some specific fingering combinations, which are unlikely in the first place, are excluded from the 
search (e.g. the 3rd finger crossing the 4th). 
- Hands are always considered independent from each other.
- Repeated notes for which pianists often alternate fingers will be assigned to the same finger.
- In the 3D representation with sounds enabled, notes are played one after the other (no chords), 
so the rithmic tempo within the measure is not respected.
<br />

Fingering a piano score can vary a lot from indivual to individual, therefore there is not such 
a thing as a "best" choiche for fingering. 
This algorithm is meant to suggest a fingering combination which is "optimal" in the sense that it
minimizes the effort of the hand avoiding unnecessary movements. 

## In this release / To do list:
- Improved fingering prediction by allowing some degree of hand stretching.
- Patch in [music21](http://web.mit.edu/music21) for fingering positions as shown in musescore. 
If notes are still hiding fingering numbers use `-b` option.
- A user reported an odd behaviour when substituting C flat to B which I could not reproduce.
- Some odd fingering in left hand of scores/mozart_fantasia.xml needs to be fixed.
- Small notes/ornaments are ignored at the moment.

