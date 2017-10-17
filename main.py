#!/usr/bin/python
# -*- coding: utf-8 -*-
from Tkinter import Frame, Tk, BOTH, Label, Scale, Checkbutton, BooleanVar
from ttk import Button, Style, Combobox
import tkFileDialog 
import sys, os, scorereader, test_scales
from music21 import converter
from hand import *

######################
class PianoGUI(Frame):
  
    def __init__(self, parent):
        Frame.__init__(self, parent, bg="white")
        self.parent = parent
        self.filename = 'test_timetravel.xml'
        self.Rcb = BooleanVar()
        self.Lcb = BooleanVar()
        self.RightHandBeam = 0
        self.LeftHandBeam  = 1
        self.initUI()
        
    def initUI(self):      
        self.parent.title("PianoFing 4.2")
        self.style = Style()
        self.style.theme_use("clam")
        self.pack(fill=BOTH, expand=True)       

        importButton = Button(self, text="Import Score",command=self.importCMD)
        importButton.place(x=115, y=15)
        
        hlab = Label(self,text="Hand Size:", bg="white")
        hlab.place(x=40, y=67)
        hvalues = ('XXS','XS','S','M','L','XL','XXL')
        self.handsize = Combobox(self, state="readonly",values=hvalues, width=4)
        self.handsize.current(2)
        self.handsize.place(x=115, y=65)

        Rcb = Checkbutton(self, text="R", variable=self.Rcb, bg="white")
        Rcb.select()
        Rcb.place(x=220, y=65)

        Lcb = Checkbutton(self, text="L", variable=self.Lcb, bg="white")
        Lcb.select()
        Lcb.place(x=180, y=65)
 
        genButton = Button(self, text="GENERATE", command=self.generateCMD)
        genButton.place(x=300, y=20)

        museButton = Button(self, text="Musescore", command=self.musescoreCMD)
        museButton.place(x=300, y=70)

        vpButton = Button(self, text="3D Player", command=self.vpCMD)
        vpButton.place(x=300, y=120)

        closeButton = Button(self, text="Close", command=self.quit)
        closeButton.place(x=300, y=170)

        self.meas = Scale(self, from_=5, to=200, bg='white', length=120, orient='horizontal')
        self.meas.set(100)
        self.meas.place(x=130, y=110)    
        melab = Label(self, text='#max meas:', bg="white")        
        melab.place(x=40, y=130)    

        self.rate = Scale(self, from_=10, to=100, bg='white', length=120, orient='horizontal')
        self.rate.set(100)
        self.rate.place(x=130, y=150)    
        slab = Label(self, text='3D speed:', bg="white")        
        slab.place(x=40, y=170)    

    def importCMD(self):
        ftypes = [('XML Music files', '*.xml*'),('Midi Music files', '*.mid?'),
                    ('All files', '*')]
        dlg = tkFileDialog.Open(self, filetypes = ftypes)
        self.filename = dlg.show()
        print 'Input File is ', self.filename


    def generateCMD(self): 
        sf = converter.parse(self.filename)

        if self.Rcb.get():
            self.rh = Hand("right", self.handsize.get())
            self.rh.noteseq = scorereader.reader(sf, beam=self.RightHandBeam)
            self.rh.generateFingering(nmeasures=self.meas.get())

        if self.Lcb.get():
            self.lh = Hand("left", self.handsize.get())
            self.lh.noteseq = scorereader.reader(sf, beam=self.LeftHandBeam)
            self.lh.generateFingering(nmeasures=self.meas.get())

        print "Saving score to output.xml"
        sf.write('xml', fp='output.xml')
        print "\nTo visualize score type:\n musescore output.xml\n"

                 
    def vpCMD(self):  
        print 'try import vkeyboard'
        import vkeyboard
        vk = vkeyboard.VirtualKeyboard()
        if self.Rcb.get(): vk.build_RH(self.rh)
        if self.Lcb.get(): vk.build_LH(self.lh)
        vk.rate = self.rate.get()
        vk.playsounds = 1
        vk.playKeyboard()

    def musescoreCMD(self):  
        print 'try opening musescore'
        os.system('musescore output.xml')


root = Tk()
root.geometry("455x220")
app = PianoGUI(root)
root.mainloop()  
