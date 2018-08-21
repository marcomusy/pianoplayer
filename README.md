# PianoPlayer
Automatic piano fingering generator. 
Find and animate the optimal fingering combination to play a score 
and visualize it in 3D with [vtkplotter](https://github.com/marcomusy/vtkplotter).<br />

## Download and Install:
```bash
(sudo) pip install --upgrade pianoplayer
```

### Optional:
To visualize the annotated score install for free [musescore](https://musescore.org/it/download):
```bash
sudo apt install musescore
sudo apt install libasound2-dev
(sudo) pip install simpleaudio

```
To open a 3D visualization, install VTK with one of these command lines:
```bash
sudo apt install vtk7
# or
conda install -c conda-forge vtk
# or 
(sudo) pip install vtk
```

## Usage: 
```bash
pianoplayer         # if no argument is given a GUI will pop up
# Or
pianoplayer [-h] [-o] [-n] [-s] [-d] [-k] [-rbeam] [-lbeam] [-q] [-m] [-v] [--vtk-speed] 
            [-z] [-l] [-r] [-XXS] [-XS] [-S] [-M] [-L] [-XL] [-XXL]
            filename
# Valid file formats: music-xml, musescore, midi (.xml, .mscz, .mscx, .mid)
# Optional arguments:
#   -h, --help            show this help message and exit
#   -o , --outputfile     Annotated output xml file name
#   -n , --n-measures     [100] Number of score measures to scan
#   -s , --start-measure  Start from measure number [1]
#   -d , --depth          [auto] Depth of combinatorial search, [3-9]
#   -k, --skip            Skip one step in search loop for higher speed
#   -rbeam                [0] Specify Right Hand beam number
#   -lbeam                [1] Specify Left Hand beam number
#   -q, --quiet           Switch off verbosity
#   -m, --musescore       Open output in musescore after processing
#   -v, --with-vtk        Play 3D scene after processing
#   --vtk-speed           [1] Speed factor of rendering
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

Then:<br />
- press Import Score
- press GENERATE (a file output.xml is written)
- press Musescore to visualise the annotated score
- press 3D Player to show the animation (closing it with Esc will quit the application)

![alt text](https://user-images.githubusercontent.com/32848391/31662571-42a05c94-b33f-11e7-9a5e-989fea82ad4c.png)

![alt text](https://user-images.githubusercontent.com/32848391/31663245-a9e23e0c-b341-11e7-9e07-d90d4959521b.png)

If VTK is installed click on "3D Player" for a visualization (in interactive mode, drag mouse 
to move the scene, right-click drag to zoom). You will see the both hands playing but hear the right hand notes only. 
Chords are rendered as a rapid sequence of notes.

![alt text](https://user-images.githubusercontent.com/32848391/31662850-515dc946-b340-11e7-86c8-999e68451078.png)


## How does the algorithm work:
The algorithm minimizes the fingers speed needed to play a sequence of notes or chords by searching through feasible combinations of fingerings. 
At every note the hand position is assumed to be at rest (this can be improved in the future). 

## Parameters you can change:
- your hand size (from 'XXS' to 'XXL') which sets the max distance between thumb and pinkie (e.g. 'S' = 17.2 cm)
- the beam number associated to the right hand is by default nr.0 (nr.1 for left hand). You can change it with -rbeam 
and -lbeam command line options.
- depth of combinatorial search (from 4 up to 9 notes ahead of the currently playing note, default is 'auto' which selects this number based on the duration of the notes to be played)
- algorithm step: you can skip the calculation of the next note at the price of a small loss of precision, speeding up the algorithm by a factor 2.

## Advantages
One possible advantage is that this algorithm is *dynamic* which means that it takes into account the physical position and speed of fingers while moving on the keyboard and the duration of each played note. 
It is *not* based on a static look-up table of likely or unlikely combinations of fingerings.

## Limitations
- Some specific fingering combinations, which are unlikely in the first place, are excluded from the search (e.g. the 3rd finger crossing the 4th). 
- Hands are considered independent from each other.
- Repeated notes for which pianists often alternate fingers will be assigned to the same finger.
- In the 3D representation with sounds enabled, notes are played one after the other (no chords), so the rithmic tempo within the measure is not respected.<br />

Fingering a piano score can vary a lot from indivual to individual, therefore there is not such 
a thing as a "best" choiche for fingering. 
This algorithm is meant to suggest a fingering combination which is "optimal" in the sense that it
minimizes the effort of the hand avoiding unnecessary movements. 

## In this release / To do list:
- New graphic interface using [vtkplotter](https://github.com/marcomusy/vtkplotter)
- Extended possibilty to pass various options in *pianoplayer* command line to customize its behaviour
- A user reported an odd behaviour when substituting C flat to B.
- Small notes / ornaments are ignored.
- A patch for fingering positions as shown in musescore 
- Working now on how to improve the actual fingering prediction by allowing some degree of hand stretching

