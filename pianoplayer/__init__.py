import json
import os, sys
from music21 import converter, stream
from pianoplayer.hand import Hand
from pianoplayer.scorereader import reader, PIG2Stream, reader_pretty_midi
from operator import attrgetter
import pretty_midi
###########################################################
__author__ = "Marco Musy"
__email__ = "marco.musy@gmail.com"
__version__ = "2.2.0"  # defined in setup.py
__status__ = "dev"
__website__ = "https://github.com/marcomusy/pianoplayer"
__license__ = "MIT"

