# piano-fingering
Automatic piano fingering generator

## GUI Usage: 
> python main.py

## Command line usage: 
> pianofing.py score.mid

The program output is a fingering-annotated xml file which can be read with free software like Musescore:
> musescore output.xml

If VPython is installed click on "3D Player" for a visualization (right-click drag to move the scene).


## Required imports: 
- music21
- Tkinter, tkFileDialog (for the GUI)

## Optionally:
- visual, from [http://vpython.org/index.html]
- musescore, [https://musescore.org]


## How does it work:

The algorithm minimizes the finger speed by searching through feasible combinations of finger sequences. At every note the hand position is assumed to be at rest (this can be improved in the future). Some weights can also be tuned. For example thumb is assumed to be 10% faster than index finger (set variable in Hand.weights). Similarly thumb is slower when hitting a black key by 50% (in Hand.bfactor).


## Parameters you can change:
- your hand size ('XXS' to 'XXL') which sets the max distance between thumb and pinkie (e.g. 'S' = 17.2 cm)
- depth of combinatorial search (from 3 up to 9 notes ahead of the currently playing note)
- usable fingers (disabled players can exclude fingers in the list Hand.usable_fingers)
- weights for individual fingers (in Hand.weights)
