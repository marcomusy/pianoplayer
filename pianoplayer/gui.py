"""Tkinter GUI for pianoplayer."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from tkinter import BOTH, BooleanVar, DoubleVar, Frame, IntVar, StringVar, TclError, Tk, messagebox
from tkinter import filedialog as tk_filedialog
from tkinter.ttk import (
    Button,
    Checkbutton,
    Combobox,
    Entry,
    Label,
    LabelFrame,
    Notebook,
    Spinbox,
    Style,
)
from tkinter.ttk import Frame as TtkFrame

from pianoplayer import core
from pianoplayer.errors import PianoPlayerError


class PianoGUI(Frame):
    """Tkinter interface for score import and fingering generation."""

    def __init__(self, parent: Tk):
        """Initialize GUI state and build widgets."""
        super().__init__(parent, bg="white")
        self.parent = parent

        self.filename_var = StringVar(value=str(Path("scores/bach_invention4.xml")))
        self.output_file_var = StringVar(value="output.xml")
        self.right_enabled = BooleanVar(value=True)
        self.left_enabled = BooleanVar(value=True)

        self.hand_size_var = StringVar(value="M")
        self.n_measures_var = IntVar(value=100)
        self.start_measure_var = IntVar(value=1)

        self.depth_var = IntVar(value=0)
        self.rbeam_var = IntVar(value=0)
        self.lbeam_var = IntVar(value=1)
        self.chord_stagger_var = DoubleVar(value=0.05)
        self.with_vedo_var = BooleanVar(value=False)
        self.sound_off_var = BooleanVar(value=False)
        self.below_beam_var = BooleanVar(value=False)
        self.quiet_var = BooleanVar(value=False)
        self.auto_open_musescore_var = BooleanVar(value=False)

        self.status_var = StringVar(value="Ready")
        self._busy = False
        self.init_ui()

    def init_ui(self) -> None:
        """Create and place all GUI controls in Basic/Advanced tabs."""
        self.parent.title("PianoPlayer")
        style = Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f6f8fb")
        style.configure("TLabelframe", background="#f6f8fb")
        style.configure("TLabelframe.Label", background="#f6f8fb")
        style.configure("TLabel", background="#f6f8fb")
        style.configure("TNotebook", background="#f6f8fb")
        style.configure("TNotebook.Tab", background="#e8edf5", padding=(12, 6))
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#d8e1ee"), ("active", "#e2e9f3")],
            padding=[("selected", (13, 7)), ("!selected", (12, 6))],
        )
        style.configure("Primary.TButton", foreground="white", background="#1f6feb")
        style.map("Primary.TButton", background=[("active", "#388bfd")])
        style.configure("Secondary.TButton", foreground="#0b3a67", background="#dbeafe")
        style.map("Secondary.TButton", background=[("active", "#bfdbfe")])
        style.configure("QuietDanger.TButton", foreground="#7f1d1d", background="#fee2e2")
        style.map("QuietDanger.TButton", background=[("active", "#fecaca")])
        self.pack(fill=BOTH, expand=True)
        self.parent.bind("<KeyPress-q>", self._close_cmd)
        self.parent.bind("<Control-w>", self._close_cmd)

        container = TtkFrame(self)
        container.pack(fill=BOTH, expand=True, padx=12, pady=10)

        io_row = TtkFrame(container)
        io_row.pack(fill="x", pady=(0, 8))
        Label(io_row, text="Input Score").pack(side="left")
        Entry(io_row, textvariable=self.filename_var).pack(
            side="left",
            fill="x",
            expand=True,
            padx=8,
        )
        self.import_btn = Button(
            io_row,
            text="Import Score",
            style="Secondary.TButton",
            command=self.import_cmd,
        )
        self.import_btn.pack(side="left")

        notebook = Notebook(container)
        notebook.pack(fill=BOTH, expand=True)
        basic_tab = TtkFrame(notebook)
        advanced_tab = TtkFrame(notebook)
        notebook.add(basic_tab, text="Basic")
        notebook.add(advanced_tab, text="Advanced")

        self._build_basic_tab(basic_tab)
        self._build_advanced_tab(advanced_tab)

        bottom = TtkFrame(container)
        bottom.pack(fill="x", pady=(8, 0))
        self.generate_btn = Button(
            bottom,
            text="Generate",
            style="Primary.TButton",
            command=self.generate_cmd,
        )
        self.generate_btn.pack(side="left")
        if platform.system() != "Windows":
            self.musescore_btn = Button(
                bottom,
                text="Open Musescore",
                style="Secondary.TButton",
                command=self.musescore_cmd,
            )
            self.musescore_btn.pack(side="left", padx=6)
        else:
            self.musescore_btn = None
        self.quit_btn = Button(
            bottom,
            text="Quit",
            style="QuietDanger.TButton",
            command=self._close_cmd,
        )
        self.quit_btn.pack(
            side="right"
        )
        Label(bottom, textvariable=self.status_var).pack(side="right", padx=10)

    def _set_busy(self, busy: bool, alpha: float = 0.78) -> None:
        """Apply a lightweight busy visual state while generation is running."""
        self._busy = busy
        controls = [self.import_btn, self.generate_btn, self.quit_btn]
        if self.musescore_btn is not None:
            controls.append(self.musescore_btn)
        for control in controls:
            try:
                if busy:
                    control.state(["disabled"])
                else:
                    control.state(["!disabled"])
            except TclError:
                pass
        try:
            if busy:
                self.parent.configure(cursor="watch")
                self.parent.attributes("-alpha", alpha)
            else:
                self.parent.configure(cursor="")
                self.parent.attributes("-alpha", 1.0)
        except TclError:
            # Some Tk builds may not support alpha attributes.
            pass
        self.parent.update_idletasks()

    def _build_basic_tab(self, parent: TtkFrame) -> None:
        """Build frequently used options."""
        opts = LabelFrame(parent, text="Core Options")
        opts.pack(fill="x", padx=10, pady=10)

        Label(opts, text="Output File").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        Entry(opts, textvariable=self.output_file_var, width=26).grid(
            row=0, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Hand Size").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        hand_values = ("XXS", "XS", "S", "M", "L", "XL", "XXL")
        Combobox(
            opts, state="readonly", values=hand_values, textvariable=self.hand_size_var, width=5
        ).grid(row=1, column=1, sticky="w", padx=8, pady=6)

        Label(opts, text="Scan").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        hand_checks = TtkFrame(opts)
        hand_checks.grid(row=2, column=1, sticky="w", padx=8, pady=6)
        Checkbutton(hand_checks, text="Right", variable=self.right_enabled).pack(side="left")
        Checkbutton(hand_checks, text="Left", variable=self.left_enabled).pack(side="left", padx=10)

        Label(opts, text="Start at Measure").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        Spinbox(opts, from_=1, to=9999, textvariable=self.start_measure_var, width=8).grid(
            row=3, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Stop at Measure").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        Spinbox(opts, from_=1, to=9999, textvariable=self.n_measures_var, width=8).grid(
            row=4, column=1, sticky="w", padx=8, pady=6
        )

        if platform.system() != "Windows":
            Checkbutton(
                opts,
                text="Open MuseScore after generation",
                variable=self.auto_open_musescore_var,
            ).grid(row=5, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 8))

    def _build_advanced_tab(self, parent: TtkFrame) -> None:
        """Build less frequently used configuration options."""
        opts = LabelFrame(parent, text="Advanced Options")
        opts.pack(fill="x", padx=10, pady=10)

        Label(opts, text="Depth of search (0=auto)").grid(
            row=0,
            column=0,
            sticky="w",
            padx=8,
            pady=6,
        )
        Spinbox(opts, from_=0, to=9, textvariable=self.depth_var, width=8).grid(
            row=0, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Right Beam number").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        Spinbox(opts, from_=0, to=16, textvariable=self.rbeam_var, width=8).grid(
            row=1, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Left Beam number").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        Spinbox(opts, from_=0, to=16, textvariable=self.lbeam_var, width=8).grid(
            row=2, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Chord Stagger (sec)").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        Spinbox(
            opts,
            from_=0.0,
            to=1.0,
            increment=0.01,
            textvariable=self.chord_stagger_var,
            width=8,
        ).grid(row=3, column=1, sticky="w", padx=8, pady=6)

        Checkbutton(opts, text="Enable 3D playback (vedo)", variable=self.with_vedo_var).grid(
            row=4, column=0, sticky="w", padx=8, pady=6
        )
        Checkbutton(opts, text="3D sound off", variable=self.sound_off_var).grid(
            row=4, column=1, sticky="w", padx=8, pady=6
        )
        Checkbutton(opts, text="Show annotations below beam", variable=self.below_beam_var).grid(
            row=5, column=0, sticky="w", padx=8, pady=6
        )
        Checkbutton(opts, text="Quiet logs", variable=self.quiet_var).grid(
            row=6, column=0, sticky="w", padx=8, pady=6
        )

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
            self.filename_var.set(filename)
            self.status_var.set("Loaded input score")

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

    @staticmethod
    def _as_int(value: int | str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_float(value: float | str, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def generate_cmd(self) -> None:
        """Run fingering generation for the selected score/options."""
        filename = self.filename_var.get().strip()
        output_file = self.output_file_var.get().strip() or "output.xml"
        if not filename:
            messagebox.showerror("PianoPlayer", "Please choose an input score first.")
            return
        if not self._validate_hand_selection():
            return

        self._set_busy(True)
        try:
            core.run_annotate(
                filename=filename,
                outputfile=output_file,
                n_measures=max(1, self._as_int(self.n_measures_var.get(), 100)),
                start_measure=max(1, self._as_int(self.start_measure_var.get(), 1)),
                depth=max(0, self._as_int(self.depth_var.get(), 0)),
                rbeam=max(0, self._as_int(self.rbeam_var.get(), 0)),
                lbeam=max(0, self._as_int(self.lbeam_var.get(), 1)),
                quiet=bool(self.quiet_var.get()),
                musescore=bool(self.auto_open_musescore_var.get())
                and platform.system() != "Windows",
                below_beam=bool(self.below_beam_var.get()),
                with_vedo=bool(self.with_vedo_var.get()),
                sound_off=bool(self.sound_off_var.get()),
                hand_size=(self.hand_size_var.get() or "M"),
                chord_note_stagger_s=max(0.0, self._as_float(self.chord_stagger_var.get(), 0.05)),
                **self._hand_mode_flags(),
            )
            self.status_var.set(f"Generated: {output_file}")
        except (PianoPlayerError, ValueError) as exc:
            messagebox.showerror("PianoPlayer", str(exc))
            self.status_var.set("Generation failed")
        finally:
            self._set_busy(False)

    def musescore_cmd(self) -> None:
        """Open the generated output score with the platform MuseScore command."""
        if platform.system() == "Windows":
            messagebox.showinfo(
                "PianoPlayer",
                "MuseScore launch from GUI is not available on Windows.",
            )
            return
        output_file = self.output_file_var.get().strip() or "output.xml"
        if not Path(output_file).exists():
            messagebox.showinfo("PianoPlayer", "Generate output first.")
            return

        self._set_busy(True, alpha=0.8)
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", output_file], check=True)
            else:
                subprocess.run(
                    ["musescore", output_file],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            self.status_var.set(f"Opened: {output_file}")
        except Exception as exc:
            messagebox.showerror("PianoPlayer", f"Unable to open MuseScore: {exc}")
            self.status_var.set("Unable to open output in MuseScore")
        finally:
            self._set_busy(False)

    def _close_cmd(self, _event=None) -> None:
        """Close the GUI window (bound to q and Ctrl+W)."""
        self.parent.destroy()


def launch() -> None:
    """Create and run the PianoPlayer GUI application."""
    root = Tk()
    root.geometry("700x500")
    PianoGUI(root)
    root.mainloop()
