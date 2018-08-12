# PianoPlayer
Automatic piano fingering generator. 
Find and show the optimal fingering combination to play a score and visualize it in 3D.<br />
(3D functionality is disabled in this release due to migration from vpython to vtkplotter).<br />

## Download and Install:
```bash
(sudo) pip install --upgrade pianoplayer
```

### Optional :
To have 3D visualization, install VTK with one of these command lines:
```bash
sudo apt install vtk7
# or
conda install -c conda-forge vtk
# or 
(sudo) pip install vtk
```
To visualize the annotated score install for free [musescore](https://musescore.org/it/download):
```bash
sudo apt install musescore
```


## Usage: 
```bash
pianoplayer [myscore.xml] # if no xml file is given a GUI will open
```
Then:<br />
- press Import Score
- press GENERATE (a file output.xml is written)
- press Musescore to visualise the annotated score
- press 3D Player to show the animation (closing it with Esc will quit the application)

![alt text](https://user-images.githubusercontent.com/32848391/31662571-42a05c94-b33f-11e7-9a5e-989fea82ad4c.png)

![alt text](https://user-images.githubusercontent.com/32848391/31663245-a9e23e0c-b341-11e7-9e07-d90d4959521b.png)

If [vtkplotter](https://github.com/marcomusy/vtkplotter) is installed click on "3D Player" for a visualization (drag mouse 
to move the scene, right-click drag to zoom). You will see the both hands playing but hear the right hand notes only. 
Chords are rendered as a rapid sequence of notes.

![alt text](https://user-images.githubusercontent.com/32848391/31662850-515dc946-b340-11e7-86c8-999e68451078.png)


## How does the algorithm work:
The algorithm minimizes the fingers speed needed to play a sequence of notes or chords by searching through feasible combinations of fingerings. At every note the hand position is assumed to be at rest (this can be improved in the future). Some weights can also be tuned. For example thumb is assumed to be 10% faster than index finger (variable in Hand.weights). Similarly thumb is slower when hitting a black key by 50% (in Hand.bfactor). 

## Parameters you can change:
- your hand size ('XXS' to 'XXL') which sets the max distance between thumb and pinkie (e.g. 'S' = 17.2 cm)
- the beam number associated to the right hand is nr.0 (nr.1 for left hand). 
- depth of combinatorial search (from 3 up to 9 notes ahead of the currently playing note, default is 'auto' which selects this value based on the duration of the notes to be played)
- usable fingers (disabled players can exclude fingers in the list Hand.usable_fingers)
- weights for individual fingers (in Hand.weights)
- step of notes: you can skip the prediction of the next note at the price of precision (default in Hand.fstep is 2, which is a reasonable trade-off that speeds up the algorithm by a factor 2)

## Limitations
The limitation of this method is that some specific fingering combinations, which are very unlikely in the first place, are excluded from the search (e.g. the 3rd finger crossing the 4th). Hand are considered independent from each other.
Repeated notes for which pianists often change finger will be assigned the same finger as this choice minimises fingers speed globally.

## Bugs
- The last nine notes of the input score are not correctly fingered.
- Odd behaviour reported when substituting Cb to B.
