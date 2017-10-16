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

