#
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 19:22:20 2015

@author: marco musy
"""


def nameof(n):
    a = n.name + str(n.octave)
    if "--" in a:                 # order matters
        b = a.replace("B--", "A")
        b = b.replace("A--", "G") # chain b.replace not a.replace
        b = b.replace("G--", "F")
        b = b.replace("E--", "D")
        b = b.replace("D--", "C")
        return b
    elif "-" in a:
        b = a.replace("C-", "B")
        b = b.replace("D-", "C#")  # chain b.replace not a.replace
        b = b.replace("E-", "D#")
        b = b.replace("F-", "E")
        b = b.replace("G-", "F#")
        b = b.replace("A-", "G#")
        b = b.replace("B-", "A#")
        return b
    elif "##" in a:
        b = a.replace("C##", "D")
        b = b.replace("D##", "E") # chain b.replace not a.replace
        b = b.replace("F##", "G")
        b = b.replace("G##", "A")
        b = b.replace("A##", "B")
        return b
    elif "E#" in a:
        b = a.replace("E#", "F")
        return b
    elif "B#" in a:
        b = a.replace("B#", "C")
        return b
    else:
        return a


def fpress(f, color):
    f.rotate(-20, axis=(1, 0, 0), point=f.pos())
    f.addPos([0, 0, -1])
    f.color(color)


def frelease(f):
    f.addPos([0, 0, 1])
    f.rotate(20, axis=(1, 0, 0), point=f.pos())
    f.color((0.7, 0.3, 0.3))


def kpress(f, color):
    f.rotate(4, axis=(1, 0, 0), point=f.pos())
    f.addPos([0, 0, -0.4])
    f.color(color)


def krelease(f):
    f.addPos([0, 0, 0.4])
    p = f.pos()
    f.rotate(-4, axis=(1, 0, 0), point=p)
    if p[2] > 0.5:
        f.color("k")
    else:
        f.color("w")


_kb_layout = {
    "C"  : 0.5,
    "D"  : 1.5,
    "E"  : 2.5,
    "F"  : 3.5,
    "G"  : 4.5,
    "A"  : 5.5,
    "B"  : 6.5,
    "B#" : 0.5,
    "C#" : 1.0,
    "D#" : 2.0,
    "E#" : 3.5,
    "F#" : 4.0,
    "G#" : 5.0,
    "A#" : 6.0,
    "C-" : 6.5,
    "D-" : 1.0,
    "E-" : 2.0,
    "F-" : 2.5,
    "G-" : 4.0,
    "A-" : 5.0,
    "B-" : 6.0,
    "C##": 1.5,
    "D##": 2.5,
    "F##": 4.5,
    "G##": 5.5,
    "A##": 6.5,
    "D--": 0.5,
    "E--": 1.5,
    "G--": 3.5,
    "A--": 4.5,
    "B--": 5.5,
}

# TODO The assumtion of equal distance between notes is not totally true. (PRamoneda)

def keypos_midi(n):  # position of notes on keyboard
    keybsize = 16.5  # cm
    k = keybsize / 7.0  # 7 notes
    step = (n.pitch % 12) * k
    return keybsize * (n.pitch // 12) + step


def keypos(n):  # position of notes on keyboard
    step = 0.0
    keybsize = 16.5  # cm
    k = keybsize / 7.0  # 7 notes
    if n.name in _kb_layout.keys():
        step = _kb_layout[n.name] * k
    else:
        print("ERROR note not found", n.name)
    return keybsize * n.octave + step


def handSizeFactor(s):
    f = 0.82
    if s == "XXS":
        f = 0.33
    elif s == "XS":
        f = 0.46
    elif s == "S":
        f = 0.64
    elif s == "M":
        f = 0.82
    elif s == "L":
        f = 1.0
    elif s == "XL":
        f = 1.1
    elif s == "XXL":
        f = 1.2
    return f
