#!/usr/bin/env python
# -------------------------------------------------------------------------------
# Name:         PianoPlayer
# Purpose:      Find optimal fingering for piano scores
# Author:       Marco Musy
# -------------------------------------------------------------------------------
import os

from music21 import converter

import pianoplayer
import sys

from pianoplayer import Hand, reader, core

if len(sys.argv) < 2:  # no args are passed, pop up GUI

    if sys.version_info >= (3, 0):
        from tkinter import Frame, Tk, BOTH, Label, Scale, Checkbutton, BooleanVar
        from tkinter.ttk import Button, Style, Combobox
        from tkinter import filedialog as tkFileDialog
    else:
        from Tkinter import Frame, Tk, BOTH, Label, Scale, Checkbutton, BooleanVar
        from ttk import Button, Style, Combobox
        import tkFileDialog


    ######################
    class PianoGUI(Frame):

        def __init__(self, parent):
            Frame.__init__(self, parent, bg="white")
            self.parent = parent
            self.filename = 'scores/bach_invention4.xml'
            self.Rcb = BooleanVar()
            self.Lcb = BooleanVar()
            self.RightHandBeam = 0
            self.LeftHandBeam = 1
            self.initUI()

        def initUI(self):
            self.parent.title("PianoPlayer")
            self.style = Style()
            self.style.theme_use("clam")
            self.pack(fill=BOTH, expand=True)

            Button(self, text="Import Score", command=self.importCMD).place(x=300, y=20)

            Label(self, text="Hand Size:", bg="white").place(x=40, y=50)
            hvalues = ('XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL')
            self.handsize = Combobox(self, state="readonly", values=hvalues, width=4)
            self.handsize.current(3)
            self.handsize.place(x=130, y=50)

            Label(self, text="Scan:", bg="white").place(x=80, y=80)
            Rcb = Checkbutton(self, text="Right", variable=self.Rcb, bg="white")
            Rcb.select()
            Rcb.place(x=130, y=80)
            Lcb = Checkbutton(self, text="Left", variable=self.Lcb, bg="white")
            Lcb.select()
            Lcb.place(x=200, y=80)

            Button(self, text="GENERATE", command=self.generateCMD).place(x=300, y=70)

            Button(self, text="Musescore", command=self.musescoreCMD).place(x=300, y=120)

            Button(self, text="3D Player", command=self.vpCMD).place(x=300, y=170)

            self.meas = Scale(self, from_=2, to=100, bg='white', length=210, orient='horizontal')
            self.meas.set(100)
            self.meas.place(x=40, y=110)
            Label(self, text='Max nr. of measures', bg="white").place(x=40, y=150)

        def importCMD(self):
            ftypes = [('XML Music files', '*.xml'), ('Midi Music files', '*.mid'),
                      ('PIG Music files', '*.txt'), ('All files', '*')]
            dlg = tkFileDialog.Open(self, filetypes=ftypes)
            self.filename = dlg.show()
            print('Input File is ', self.filename)

        def generateCMD(self):
            sf = converter.parse(self.filename)

            if self.Rcb.get():
                self.rh = Hand("right", self.handsize.get())
                self.rh.noteseq = reader(sf, beam=self.RightHandBeam)
                self.rh.generate(nmeasures=self.meas.get())

            if self.Lcb.get():
                self.lh = Hand("left", self.handsize.get())
                self.lh.noteseq = reader(sf, beam=self.LeftHandBeam)
                self.lh.generate(nmeasures=self.meas.get())

            print("Saving score to output.xml")
            sf.write('xml', fp='output.xml')
            print("\nTo visualize score type:\n musescore output.xml\n")

        def vpCMD(self):
            from pianoplayer.vkeyboard import VirtualKeyboard

            vk = VirtualKeyboard()
            if self.Rcb.get(): vk.build_RH(self.rh)
            if self.Lcb.get(): vk.build_LH(self.lh)
            vk.playsounds = 1
            vk.play()

            vk.vp.show(zoom=2, interactive=1)
            print('Close window and press Close to exit.')

        def musescoreCMD(self):
            print('try opening musescore')
            os.system('musescore output.xml')


    root = Tk()
    root.geometry("455x220")
    app = PianoGUI(root)
    root.mainloop()


else:  ################################################################################################# command line mode

    import argparse

    pr = argparse.ArgumentParser(description="""PianoPlayer,
    check out home page https://github.com/marcomusy/pianoplayer""")
    pr.add_argument("filename", type=str, help="Input music xml/midi file name")
    pr.add_argument("-o", "--outputfile", metavar='output.xml', type=str, help="Annotated output xml file name",
                    default='output.xml')
    pr.add_argument("-n", "--n-measures", metavar='', type=int, help="[100] Number of score measures to scan",
                    default=100)
    pr.add_argument("-s", "--start-measure", metavar='', type=int, help="Start from measure number [1]", default=1)
    pr.add_argument("-d", "--depth", metavar='', type=int, help="[auto] Depth of combinatorial search, [4-9]",
                    default=0)
    pr.add_argument("-rbeam", metavar='', type=int, help="[0] Specify Right Hand beam number", default=0)
    pr.add_argument("-lbeam", metavar='', type=int, help="[1] Specify Left Hand beam number", default=1)
    pr.add_argument("--cost-path", metavar='', type=str, help="Path to save cost function", default=None)
    pr.add_argument("--quiet", help="Switch off verbosity", action="store_true")
    pr.add_argument("-m", "--musescore", help="Open output in musescore after processing", action="store_true")
    pr.add_argument("-b", "--below-beam", help="Show fingering numbers below beam line", action="store_true")
    pr.add_argument("-v", "--with-vedo", help="Play 3D scene after processing", action="store_true")
    pr.add_argument("--vedo-speed", metavar='', type=float, help="[1] Speed factor of rendering", default=1.5)
    pr.add_argument("-z", "--sound-off", help="Disable sound", action="store_true")
    pr.add_argument("-l", "--left-only", help="Fingering for left hand only", action="store_true")
    pr.add_argument("-r", "--right-only", help="Fingering for right hand only", action="store_true")
    pr.add_argument("-XXS", "--hand-size-XXS", help="Set hand size to XXS", action="store_true")
    pr.add_argument("-XS", "--hand-size-XS", help="Set hand size to XS", action="store_true")
    pr.add_argument("-S", "--hand-size-S", help="Set hand size to S", action="store_true")
    pr.add_argument("-M", "--hand-size-M", help="Set hand size to M", action="store_true")
    pr.add_argument("-L", "--hand-size-L", help="Set hand size to L", action="store_true")
    pr.add_argument("-XL", "--hand-size-XL", help="Set hand size to XL", action="store_true")
    pr.add_argument("-XXL", "--hand-size-XXL", help="Set hand size to XXL", action="store_true")
    args = pr.parse_args()
    core.annotate(args)

