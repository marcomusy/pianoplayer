# piano-fingering
Automatic generator for piano fingering

GUI Usage: 
> python main.py

Command line usage: 
> pianofing.py score.mid

The program output is a fingering-annotated xml file which can be read with free software like Musescore:
> musescore output.xml

Required imports: 
- music21
- Tkinter, tkFileDialog
Optionally:
- visual, from vpython.org
- musescore 


How does it work:

The algorithm minimizes the finger speed by searching through feasible combinations of finger sequences.


Parameters you can change:
- your hand size ('XXS' to 'XXL') which sets the max distance between thumb and pinkie (e.g. 'S' -> 17.2 cm)
- depth of combinatorial search (from 3 notes up to 9)
- usable fingers (disabled players can exclude usable_fingers in Hand class)
