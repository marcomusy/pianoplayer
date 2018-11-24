#
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 19:22:20 2015

@author: marco musy
"""


def nameof(n):
    a = n.name+str(n.octave)
    if "-" in a:
        b = a.replace("C-","B")
        b = b.replace("D-","C#")
        b = b.replace("E-","D#")
        b = b.replace("F-","E")
        b = b.replace("G-","F#")
        b = b.replace("A-","G#")
        b = b.replace("B-","A#")
        return b 
    elif "E#" in a:
        b = a.replace("E#","F")
        return b         
    elif "B#" in a:
        b = a.replace("B#","C")
        return b         
    else:
        return a

def fpress(f, color):
    f.rotate(-20, axis=(1,0,0), axis_point=f.pos())
    f.addPos([0,0,-1])
    f.color(color)#.alpha(1)

def frelease(f):
    f.addPos([0,0,1])
    f.rotate(20, axis=(1,0,0), axis_point=f.pos())
    f.color((.7,0.3,0.3))#.alpha(.6)

def kpress(f, color):
    f.rotate(4, axis=(1,0,0), axis_point=f.pos())
    f.addPos([0,0,-.4])
    f.color(color)

def krelease(f):
    f.addPos([0,0,.4])
    p = f.pos()
    f.rotate(-4, axis=(1,0,0), axis_point=p)
    if p[2]>.5: f.color('k')
    else: f.color('w')


def keypos(n): #position of notes on keyboard
    step = 0.0
    keybsize = 16.5 #cm
    k = keybsize/7.0
    if   n.name == 'C'  : step = k *0.5
    elif n.name == 'D'  : step = k *1.5
    elif n.name == 'E'  : step = k *2.5
    elif n.name == 'F'  : step = k *3.5
    elif n.name == 'G'  : step = k *4.5
    elif n.name == 'A'  : step = k *5.5
    elif n.name == 'B'  : step = k *6.5
    elif n.name == 'B#' : step = k *0.5
    elif n.name == 'C#' : step = k
    elif n.name == 'D#' : step = k *2.
    elif n.name == 'E#' : step = k *3.5
    elif n.name == 'F#' : step = k *4.
    elif n.name == 'G#' : step = k *5.
    elif n.name == 'A#' : step = k *6.
    elif n.name == 'C-' : step = k *6.5
    elif n.name == 'D-' : step = k 
    elif n.name == 'E-' : step = k *2.
    elif n.name == 'F-' : step = k *2.5
    elif n.name == 'G-' : step = k *4.
    elif n.name == 'A-' : step = k *5.
    elif n.name == 'B-' : step = k *6.
    else: 
        print("ERROR note not found", n.name)
    return keybsize * n.octave + step


def handSizeFactor(s): 
    f=0.82       
    if    s=='XXS': f = 0.33
    elif  s=='XS' : f = 0.46
    elif  s=='S'  : f = 0.64
    elif  s=='M'  : f = 0.82
    elif  s=='L'  : f = 1.0
    elif  s=='XL' : f = 1.1
    elif  s=='XXL': f = 1.2
    return f
















