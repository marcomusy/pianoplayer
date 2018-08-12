__author__  = "Marco Musy"
__license__ = "MIT" 
__maintainer__ = "M. Musy"
__email__   = "marco.musy@gmail.com"
__status__  = "dev"
__website__ = "https://github.com/marcomusy/pianoplayer"


from pianoplayer.hand import Hand
from pianoplayer.scorereader import  reader
from pianoplayer.vtk_keyboard import VirtualKeyboard


import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
