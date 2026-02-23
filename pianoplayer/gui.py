"""Tkinter GUI for pianoplayer."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from tkinter import BOTH, BooleanVar, Frame, Label, Scale, Tk
from tkinter import filedialog as tk_filedialog
from tkinter import messagebox
from tkinter.ttk import Button, Combobox, Style

from pianoplayer import core


class PianoGUI(Frame):
    def __init__(self, parent: Tk):
        super().__init__(parent, bg="white")
        self.parent = parent
        self.filename = str(Path("scores/bach_invention4.xml"))
        self.right_enabled = BooleanVar(value=True)
        self.left_enabled = BooleanVar(value=True)
        self.right_beam = 0
        self.left_beam = 1
        self.output_file = "output.xml"
        self.init_ui()

    def init_ui(self) -> None:
        self.parent.title("PianoPlayer")
        style = Style()
        style.theme_use("clam")
        self.pack(fill=BOTH, expand=True)

        Button(self, text="Import Score", command=self.import_cmd).place(x=300, y=20)
        Label(self, text="Hand Size:", bg="white").place(x=40, y=50)
        hand_values = ("XXS", "XS", "S", "M", "L", "XL", "XXL")
        self.hand_size = Combobox(self, state="readonly", values=hand_values, width=4)
        self.hand_size.current(3)
        self.hand_size.place(x=130, y=50)

        Label(self, text="Scan:", bg="white").place(x=80, y=80)
        from tkinter import Checkbutton

        right_cb = Checkbutton(self, text="Right", variable=self.right_enabled, bg="white")
        right_cb.select()
        right_cb.place(x=130, y=80)
        left_cb = Checkbutton(self, text="Left", variable=self.left_enabled, bg="white")
        left_cb.select()
        left_cb.place(x=200, y=80)

        Button(self, text="GENERATE", command=self.generate_cmd).place(x=300, y=70)
        Button(self, text="Musescore", command=self.musescore_cmd).place(x=300, y=120)
        Button(self, text="3D Player", command=self.vp_cmd).place(x=300, y=170)

        self.measures = Scale(self, from_=2, to=100, bg="white", length=210, orient="horizontal")
        self.measures.set(100)
        self.measures.place(x=40, y=110)
        Label(self, text="Max nr. of measures", bg="white").place(x=40, y=150)

    def import_cmd(self) -> None:
        ftypes = [
            ("XML Music files", "*.xml"),
            ("Midi Music files", "*.mid"),
            ("PIG Music files", "*.txt"),
            ("All files", "*"),
        ]
        filename = tk_filedialog.askopenfilename(filetypes=ftypes)
        if filename:
            self.filename = filename
            print("Input File is", self.filename)

    def _size_flags(self):
        selected = self.hand_size.get()
        return {
            "hand_size_XXS": selected == "XXS",
            "hand_size_XS": selected == "XS",
            "hand_size_S": selected == "S",
            "hand_size_M": selected == "M",
            "hand_size_L": selected == "L",
            "hand_size_XL": selected == "XL",
            "hand_size_XXL": selected == "XXL",
        }

    def generate_cmd(self) -> None:
        if not self.filename:
            messagebox.showerror("PianoPlayer", "Please choose an input score first.")
            return

        core.run_annotate(
            filename=self.filename,
            outputfile=self.output_file,
            n_measures=self.measures.get(),
            rbeam=self.right_beam,
            lbeam=self.left_beam,
            left_only=not self.left_enabled.get(),
            right_only=not self.right_enabled.get(),
            **self._size_flags(),
        )

    def vp_cmd(self) -> None:
        if not self.filename:
            messagebox.showerror("PianoPlayer", "Please choose an input score first.")
            return

        core.run_annotate(
            filename=self.filename,
            outputfile=self.output_file,
            n_measures=self.measures.get(),
            rbeam=self.right_beam,
            lbeam=self.left_beam,
            left_only=not self.left_enabled.get(),
            right_only=not self.right_enabled.get(),
            with_vedo=True,
            **self._size_flags(),
        )

    def musescore_cmd(self) -> None:
        if not Path(self.output_file).exists():
            messagebox.showinfo("PianoPlayer", "Generate output first.")
            return

        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", self.output_file], check=True)
            elif platform.system() == "Windows":
                os.startfile(self.output_file)
            else:
                subprocess.run(["musescore", self.output_file], check=True)
        except Exception as exc:
            messagebox.showerror("PianoPlayer", f"Unable to open MuseScore: {exc}")


def launch() -> None:
    root = Tk()
    root.geometry("455x220")
    PianoGUI(root)
    root.mainloop()
