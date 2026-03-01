"""Tkinter GUI for pianoplayer."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from tkinter import BOTH, BooleanVar, Frame, Label, Scale, Tk, messagebox
from tkinter import filedialog as tk_filedialog
from tkinter.ttk import Button, Combobox, Style

from pianoplayer import core
from pianoplayer.errors import PianoPlayerError


class PianoGUI(Frame):
    """Simple Tkinter interface for score import, fingering generation, and score opening."""

    def __init__(self, parent: Tk):
        """Initialize GUI state and build widgets."""
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
        """Create and place all GUI controls."""
        self.parent.title("PianoPlayer")
        style = Style()
        style.theme_use("clam")
        self.pack(fill=BOTH, expand=True)
        self.parent.bind("<KeyPress-q>", self._close_cmd)
        self.parent.bind("<Control-w>", self._close_cmd)

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
        if platform.system() != "Windows":
            Button(self, text="Musescore", command=self.musescore_cmd).place(x=300, y=120)
        Button(self, text="Quit", command=self._close_cmd).place(x=300, y=170)

        self.measures = Scale(self, from_=1, to=100, bg="white", length=210, orient="horizontal")
        self.measures.set(100)
        self.measures.place(x=40, y=110)
        Label(self, text="Max nr. of measures", bg="white").place(x=40, y=150)

    def import_cmd(self) -> None:
        """Open a file picker and store the selected input score path."""
        ftypes = [
            ("MusicXML files", "*.xml *.mxl"),
            ("MuseScore files", "*.mscz *.mscx"),
            ("MIDI Music files", "*.mid *.midi"),
            ("PIG Music files", "*.txt"),
            ("All files", "*"),
        ]
        filename = tk_filedialog.askopenfilename(filetypes=ftypes)
        if filename:
            self.filename = filename
            print("Input File is", self.filename)

    def _selected_hand_size(self) -> str:
        """Return currently selected hand-size preset."""
        return self.hand_size.get() or "M"

    def _validate_hand_selection(self) -> bool:
        """Ensure at least one hand is enabled for scanning."""
        if not self.left_enabled.get() and not self.right_enabled.get():
            messagebox.showerror("PianoPlayer", "Select at least one hand to scan.")
            return False
        return True

    def _hand_mode_flags(self) -> dict[str, bool]:
        """Translate checkbox state to core left_only/right_only flags."""
        left_on = self.left_enabled.get()
        right_on = self.right_enabled.get()
        return {
            "left_only": left_on and not right_on,
            "right_only": right_on and not left_on,
        }

    def generate_cmd(self) -> None:
        """Run fingering generation for the selected score/options."""
        if not self.filename:
            messagebox.showerror("PianoPlayer", "Please choose an input score first.")
            return
        if not self._validate_hand_selection():
            return

        try:
            core.run_annotate(
                filename=self.filename,
                outputfile=self.output_file,
                n_measures=self.measures.get(),
                rbeam=self.right_beam,
                lbeam=self.left_beam,
                hand_size=self._selected_hand_size(),
                **self._hand_mode_flags(),
            )
        except (PianoPlayerError, ValueError) as exc:
            messagebox.showerror("PianoPlayer", str(exc))

    def musescore_cmd(self) -> None:
        """Open the generated output score with the platform MuseScore command."""
        if platform.system() == "Windows":
            messagebox.showinfo(
                "PianoPlayer",
                "MuseScore launch from GUI is not available on Windows.",
            )
            return
        if not Path(self.output_file).exists():
            messagebox.showinfo("PianoPlayer", "Generate output first.")
            return

        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", self.output_file], check=True)
            else:
                subprocess.run(
                    ["musescore", self.output_file],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as exc:
            messagebox.showerror("PianoPlayer", f"Unable to open MuseScore: {exc}")

    def _close_cmd(self, _event=None) -> None:
        """Close the GUI window (bound to q and Ctrl+W)."""
        self.parent.destroy()


def launch() -> None:
    """Create and run the PianoPlayer GUI application."""
    root = Tk()
    root.geometry("455x220")
    PianoGUI(root)
    root.mainloop()
