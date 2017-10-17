#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         PianoFing
# Purpose:      Find optimal fingering for piano scores
# Author:       Marco Musy
#-------------------------------------------------------------------------------
import sys, scorereader
from music21 import converter
from hand import *

#####################################################
Nmeasures = 10
handsize  = 'S'
rate      = 100
visual    = 1
#####################################################

# in case of "decoding error" message uncomment:
# reload(sys); sys.setdefaultencoding('utf8')

if len(sys.argv)<2:
    print "Usage: pianofing myscore.xml"
    sys.exit(1)
sf = converter.parse(sys.argv[1])
#sf = test_scales.s4

rh = Hand("right", handsize)
rh.noteseq = scorereader.reader(sf, beam=0)
rh.generateFingering(nmeasures=Nmeasures)

lh = Hand("left", handsize)
lh.noteseq = scorereader.reader(sf, beam=1)
lh.generateFingering(nmeasures=Nmeasures)

print "Saving score to output.xml"
sf.write('xml', fp='output.xml')
print "\nTo visualize score type:\n musescore output.xml\n"

if visual:
    import vkeyboard
    vk = vkeyboard.VirtualKeyboard()
    vk.build_RH(rh)
    vk.build_LH(lh)
    vk.rate = rate
    vk.playsounds = 1
    vk.playKeyboard()







