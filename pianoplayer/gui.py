"""Tkinter GUI for pianoplayer."""

from __future__ import annotations

from base64 import b64encode
import platform
import subprocess
import sys
from pathlib import Path
from importlib.resources import read_binary
from tkinter import (
    BOTH,
    BooleanVar,
    DoubleVar,
    Frame,
    IntVar,
    PhotoImage,
    StringVar,
    TclError,
    Tk,
    colorchooser as tk_colorchooser,
    messagebox,
)
from tkinter import (
    Entry as TkEntry,
)
from tkinter import filedialog as tk_filedialog
from tkinter import font as tkfont
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

from pianoplayer import __version__, core
from pianoplayer.errors import PianoPlayerError


class PianoGUI(Frame):
    """Tkinter interface for score import and fingering generation."""

    def __init__(self, parent: Tk):
        """Initialize GUI state and build widgets."""
        super().__init__(parent, bg="white")
        self.parent = parent
        self._project_root = Path(__file__).resolve().parent.parent
        score_candidates = [self._project_root / "scores", Path("scores")]
        for candidate in score_candidates:
            if candidate.exists():
                self._scores_dir = candidate
                break
        else:
            self._scores_dir = score_candidates[0]

        default_score = self._scores_dir / "bach_invention4.xml"
        if default_score.exists():
            default_input = str(default_score)
        else:
            fallback = None
            if self._scores_dir.exists():
                candidates = sorted(self._scores_dir.glob("*.xml")) + sorted(self._scores_dir.glob("*.mxl"))
                if candidates:
                    fallback = candidates[0]
            default_input = str(fallback) if fallback is not None else ""

        self.filename_var = StringVar(value=default_input)
        self._default_input_hint = default_input
        self.output_file_var = StringVar(value="output.xml")
        self.right_enabled = BooleanVar(value=True)
        self.left_enabled = BooleanVar(value=True)

        self.hand_size_var = StringVar(value="M")
        self.n_measures_var = IntVar(value=1000)
        self.start_measure_var = IntVar(value=1)

        self.depth_var = IntVar(value=0)
        self.auto_routing_var = BooleanVar(value=True)
        self.rpart_var = IntVar(value=0)
        self.lpart_var = IntVar(value=1)
        self.rstaff_var = IntVar(value=0)
        self.lstaff_var = IntVar(value=0)
        self.chord_stagger_var = DoubleVar(value=0.05)
        self.with_vedo_var = BooleanVar(value=False)
        self.sound_off_var = BooleanVar(value=False)
        self.below_beam_var = BooleanVar(value=False)
        self.colorize_hands_var = BooleanVar(value=False)
        self.colorize_by_cost_var = BooleanVar(value=False)
        self.colorize_by_fingering_var = BooleanVar(value=False)
        self.cost_colormap_var = StringVar(value="traffic")
        self.finger_color_vars = {
            1: StringVar(value="#ad3030"),
            2: StringVar(value="#e06b18"),
            3: StringVar(value="#097a32"),
            4: StringVar(value="#3691ce"),
            5: StringVar(value="#2054c4"),
        }
        self.rh_color_var = StringVar(value="#d62828")
        self.lh_color_var = StringVar(value="#1d4ed8")
        self.quiet_var = BooleanVar(value=False)
        self.auto_open_musescore_var = BooleanVar(value=False)

        self.status_var = StringVar(value="Status: Ready")
        self.routing_hint_var = StringVar(value="")
        self._banner_raw = None
        self._banner_img = None
        self._banner_ratio = (1, 1)
        self._banner_label = None
        self._banner_parent = None
        self._busy = False
        default_font = tkfont.nametofont("TkDefaultFont")
        self._filename_font_normal = default_font.copy()
        self._filename_font_italic = default_font.copy()
        self._filename_font_italic.configure(slant="italic")
        self.init_ui()

    def init_ui(self) -> None:
        """Create and place all GUI controls in Basic/Advanced tabs."""
        self.parent.title(f"PianoPlayer v{__version__}")

        # Theme and palette for the full window.
        bg = "#ffffff"
        style = Style()
        style.theme_use("clam")
        style.configure("TFrame", background=bg)
        style.configure("TLabelframe", background=bg)
        style.configure("TLabelframe.Label", background=bg)
        style.configure("TLabel", background=bg)
        style.configure(
            "Hint.TLabel",
            background=bg,
            foreground="#475569",
            font=("TkDefaultFont", 9, "italic"),
        )
        style.configure("TCheckbutton", background=bg)
        style.configure("TNotebook", background=bg)
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
        self.parent.configure(bg=bg)
        self.pack(fill=BOTH, expand=True)
        self.parent.bind("<KeyPress-q>", self._close_cmd)
        self.parent.bind("<Control-w>", self._close_cmd)
        self.parent.bind("<Control-o>", lambda _event: self.import_cmd())

        # Main layout: IO row, options tabs, bottom action/status row.
        container = TtkFrame(self)
        container.pack(fill=BOTH, expand=True, padx=12, pady=10)

        io_row = TtkFrame(container)
        io_row.pack(fill="x", pady=(0, 8))
        self.import_btn = Button(
            io_row,
            text="Import Score",
            style="Primary.TButton",
            command=self.import_cmd,
        )
        self.import_btn.pack(side="left")
        self.filename_entry = TkEntry(io_row, textvariable=self.filename_var)
        self.filename_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=8,
        )
        self.filename_entry.bind("<KeyRelease>", self._refresh_filename_style)
        self.after(0, self._refresh_filename_style)

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
        status_wrap = Frame(
            bottom,
            bg=bg,
            highlightthickness=1,
            highlightbackground="#cbd5e1",
            highlightcolor="#cbd5e1",
            bd=0,
        )
        status_wrap.pack(side="left", fill="x", expand=True, padx=12, pady=1, ipady=2)
        Label(
            status_wrap,
            textvariable=self.status_var,
            style="Hint.TLabel",
            justify="center",
            anchor="center",
        ).pack(fill="x", padx=10, pady=3)

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
        self._banner_parent = parent
        opts = LabelFrame(parent, text="Options")
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

        Label(opts, text="Annotate").grid(row=2, column=0, sticky="w", padx=8, pady=6)
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

        if self._load_banner():
            parent.bind("<Configure>", lambda _event: self._resize_banner())
            self.after(0, self._resize_banner)

    def _load_banner(self) -> bool:
        """Load banner image from package resources or file-system fallback paths."""
        try:
            if self._set_banner_bytes(read_binary("webapi", "images/banner.png")):
                return True
        except Exception:
            pass

        banner_rel = Path("webapi") / "images" / "banner.png"
        search_roots: list[Path] = [
            self._project_root,
            self._project_root.parent,
            Path.cwd(),
            Path(sys.executable).resolve().parent,
        ]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            search_roots.append(Path(meipass))
        search_roots.extend(Path(path) for path in sys.path if path)

        seen: set[Path] = set()
        for root in search_roots:
            candidate = root / banner_rel
            if candidate in seen:
                continue
            seen.add(candidate)
            if self._set_banner(candidate):
                return True
        return False

    def _apply_banner(self) -> None:
        """Attach the loaded image to the label and keep a widget reference."""
        if self._banner_raw is None:
            return
        if self._banner_label is None:
            self._banner_label = Label(self._banner_parent or self.parent)
            self._banner_label.pack(fill="x", padx=10, pady=(0, 10))
        self._banner_img = self._banner_raw
        self._banner_label.configure(image=self._banner_img)
        self._banner_label.image = self._banner_img

    def _set_banner(self, banner_path: Path) -> bool:
        """Attempt to load banner PNG, return True on success."""
        if not banner_path.exists():
            return False
        try:
            self._banner_raw = PhotoImage(file=str(banner_path))
            self._apply_banner()
            return True
        except (TclError, OSError, ValueError):
            # Some Tk builds may not support PNG decoding.
            return False

    def _set_banner_bytes(self, banner_bytes: bytes) -> bool:
        """Attempt to load banner bytes, return True on success."""
        if not banner_bytes:
            return False
        try:
            self._banner_raw = PhotoImage(data=banner_bytes)
            self._apply_banner()
            return True
        except (TclError, OSError, ValueError):
            try:
                self._banner_raw = PhotoImage(data=b64encode(banner_bytes), format="png")
                self._apply_banner()
                return True
            except Exception:
                # Optional fallback to Pillow when tkinter image handlers are missing.
                try:
                    from io import BytesIO
                    from PIL import Image, ImageTk

                    image = Image.open(BytesIO(banner_bytes))
                    self._banner_raw = ImageTk.PhotoImage(image)
                    self._apply_banner()
                    return True
                except Exception:
                    return False
        except Exception:
            return False

    def _build_advanced_tab(self, parent: TtkFrame) -> None:
        """Build less frequently used configuration options."""
        opts = LabelFrame(parent, text="Options")
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

        Checkbutton(
            opts,
            text="Auto hand routing (recommended)",
            variable=self.auto_routing_var,
            command=self._sync_routing_mode,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=6)

        Label(opts, textvariable=self.routing_hint_var, style="Hint.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6)
        )

        Label(opts, text="Right Part number").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        self.rpart_spin = Spinbox(opts, from_=0, to=16, textvariable=self.rpart_var, width=8)
        self.rpart_spin.grid(
            row=3, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Left Part number").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        self.lpart_spin = Spinbox(opts, from_=0, to=16, textvariable=self.lpart_var, width=8)
        self.lpart_spin.grid(
            row=4, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Right Staff number (0=auto)").grid(
            row=5, column=0, sticky="w", padx=8, pady=6
        )
        self.rstaff_spin = Spinbox(opts, from_=0, to=16, textvariable=self.rstaff_var, width=8)
        self.rstaff_spin.grid(
            row=5, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Left Staff number (0=auto)").grid(
            row=6, column=0, sticky="w", padx=8, pady=6
        )
        self.lstaff_spin = Spinbox(opts, from_=0, to=16, textvariable=self.lstaff_var, width=8)
        self.lstaff_spin.grid(
            row=6, column=1, sticky="w", padx=8, pady=6
        )

        Label(opts, text="Chord Stagger (sec)").grid(row=7, column=0, sticky="w", padx=8, pady=6)
        Spinbox(
            opts,
            from_=0.0,
            to=1.0,
            increment=0.01,
            textvariable=self.chord_stagger_var,
            width=8,
        ).grid(row=7, column=1, sticky="w", padx=8, pady=6)

        # 3D playback controls.
        Checkbutton(opts, text="Enable 3D playback (vedo)", variable=self.with_vedo_var).grid(
            row=8, column=0, sticky="w", padx=8, pady=6
        )
        Checkbutton(opts, text="3D sound off", variable=self.sound_off_var).grid(
            row=8, column=1, sticky="w", padx=8, pady=6
        )
        # Output/diagnostic toggles.
        Checkbutton(opts, text="Show annotations below beam", variable=self.below_beam_var).grid(
            row=9, column=0, sticky="w", padx=8, pady=6
        )
        Checkbutton(
            opts,
            text="Colorize by hand",
            variable=self.colorize_hands_var,
            command=lambda: self._sync_colorize_mode("hands"),
        ).grid(row=10, column=0, sticky="w", padx=8, pady=6)
        colors_row = TtkFrame(opts)
        colors_row.grid(row=10, column=1, sticky="w", padx=8, pady=6)
        self.rh_color_pick_btn = Button(
            colors_row,
            text="RH",
            style="RHColor.TButton",
            width=3,
            command=lambda: self._pick_color(
                self.rh_color_var,
                self.rh_color_pick_btn,
                "RHColor.TButton",
            ),
        )
        self.rh_color_pick_btn.pack(side="left", padx=(0, 8))
        self.lh_color_pick_btn = Button(
            colors_row,
            text="LH",
            style="LHColor.TButton",
            width=3,
            command=lambda: self._pick_color(
                self.lh_color_var,
                self.lh_color_pick_btn,
                "LHColor.TButton",
            ),
        )
        self.lh_color_pick_btn.pack(side="left", padx=(0, 0))
        Checkbutton(
            opts,
            text="Colorize by fingering",
            variable=self.colorize_by_fingering_var,
            command=lambda: self._sync_colorize_mode("fingering"),
        ).grid(row=11, column=0, sticky="w", padx=8, pady=6)
        fingers_row = TtkFrame(opts)
        fingers_row.grid(row=11, column=1, sticky="w", padx=8, pady=6)
        self.fingering_color_pick_buttons = []
        finger_styles = (
            "Finger1Color.TButton",
            "Finger2Color.TButton",
            "Finger3Color.TButton",
            "Finger4Color.TButton",
            "Finger5Color.TButton",
        )
        for finger in (1, 2, 3, 4, 5):
            pick_btn = Button(
                fingers_row,
                text=str(finger),
                style=finger_styles[finger - 1],
                width=2,
                command=lambda f=finger: self._pick_color(
                    self.finger_color_vars[f],
                    self.fingering_color_pick_buttons[f - 1],
                    finger_styles[f - 1],
                ),
            )
            pick_btn.pack(side="left", padx=(0, 6))
            self.fingering_color_pick_buttons.append(pick_btn)
        Checkbutton(
            opts,
            text="Colorize by cost",
            variable=self.colorize_by_cost_var,
            command=lambda: self._sync_colorize_mode("cost"),
        ).grid(row=12, column=0, sticky="w", padx=8, pady=6)
        self.cost_colormap_combo = Combobox(
            opts,
            textvariable=self.cost_colormap_var,
            values=("traffic", "viridis", "plasma", "magma", "coolwarm", "turbo"),
            state="readonly",
            width=12,
        )
        self.cost_colormap_combo.grid(row=12, column=1, sticky="w", padx=8, pady=6)
        for button, color in (
            (self.rh_color_pick_btn, self.rh_color_var.get()),
            (self.lh_color_pick_btn, self.lh_color_var.get()),
            *(
                (self.fingering_color_pick_buttons[finger - 1], self.finger_color_vars[finger].get())
                for finger in (1, 2, 3, 4, 5)
            ),
        ):
            style_name = str(button.cget("style"))
            self._set_color_button_style(button, style_name, color.strip())
        Checkbutton(opts, text="Quiet logs", variable=self.quiet_var).grid(
            row=13, column=0, sticky="w", padx=8, pady=6
        )
        self._sync_routing_mode()
        self._sync_colorize_mode()

    def _sync_routing_mode(self) -> None:
        """Enable manual part/staff controls only when auto-routing is disabled."""
        auto = bool(self.auto_routing_var.get())
        state = ["disabled"] if auto else ["!disabled"]
        for widget in (
            getattr(self, "rpart_spin", None),
            getattr(self, "lpart_spin", None),
            getattr(self, "rstaff_spin", None),
            getattr(self, "lstaff_spin", None),
        ):
            if widget is None:
                continue
            widget.state(state)
        if auto:
            self.routing_hint_var.set(
                "Routing: automatic (PianoPlayer will select part and staff)."
            )
        else:
            self.routing_hint_var.set("Routing: manual (set part and staff for each hand).")

    def _sync_colorize_mode(self, selected=None) -> None:
        """Keep colorization modes mutually exclusive and update manual color inputs."""
        if selected == "hands":
            if self.colorize_hands_var.get():
                self.colorize_by_cost_var.set(False)
                self.colorize_by_fingering_var.set(False)
        elif selected == "cost":
            if self.colorize_by_cost_var.get():
                self.colorize_hands_var.set(False)
                self.colorize_by_fingering_var.set(False)
        elif selected == "fingering":
            if self.colorize_by_fingering_var.get():
                self.colorize_hands_var.set(False)
                self.colorize_by_cost_var.set(False)

        enabled = bool(self.colorize_hands_var.get())
        cost_mode = bool(self.colorize_by_cost_var.get())
        fingering_mode = bool(self.colorize_by_fingering_var.get())
        hand_state = ["!disabled"] if enabled and not cost_mode and not fingering_mode else ["disabled"]
        for widget in (getattr(self, "rh_color_pick_btn", None), getattr(self, "lh_color_pick_btn", None)):
            if widget is None:
                continue
            widget.state(hand_state)
        cost_state = ["!disabled"] if cost_mode and not enabled and not fingering_mode else ["disabled"]
        for widget in (getattr(self, "cost_colormap_combo", None),):
            if widget is None:
                continue
            widget.state(cost_state)
        fingering_state = ["!disabled"] if fingering_mode and not enabled and not cost_mode else ["disabled"]
        for widget in (getattr(self, "fingering_color_pick_buttons", []) or []):
            if widget is None:
                continue
            widget.state(fingering_state)

    def _set_color_button_style(self, target_button: Button, style_name: str, token: str) -> None:
        """Apply button colors with readable text contrast."""
        color = token if token.startswith("#") and len(token) == 7 else "#d1d5db"
        fg = "#111111"
        if color.startswith("#") and len(color) == 7:
            try:
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                yiq = (299 * r + 587 * g + 114 * b) / 1000
                fg = "#111111" if yiq >= 140 else "#ffffff"
            except ValueError:
                color = "#d1d5db"
                fg = "#111111"
        style = Style()
        style.configure(style_name, background=color, foreground=fg)
        style.map(
            style_name,
            background=[("disabled", color), ("active", color), ("pressed", color)],
            foreground=[("disabled", fg), ("active", fg), ("pressed", fg)],
        )
        target_button.configure(style=style_name)

    def _pick_color(self, target_var: StringVar, target_button: Button, style_name: str) -> None:
        """Open a native color picker and store the chosen hex color."""
        initial = target_var.get().strip() or None
        _rgb, picked = tk_colorchooser.askcolor(
            color=initial,
            parent=self.parent,
            title="Choose color",
        )
        if picked:
            target_var.set(picked)
            self._set_color_button_style(target_button, style_name, picked.strip())

    def _resize_banner(self) -> None:
        """Scale banner down so it fits horizontally in current window width."""
        if self._banner_raw is None or self._banner_label is None:
            return
        available = max(220, self.winfo_width() - 60)
        raw_w = self._banner_raw.width()
        if raw_w <= available:
            ratio = (1, 1)
        else:
            # Find best rational downscale num/den (<=1) maximizing rendered width <= available.
            best_num, best_den = 1, max(1, (raw_w + available - 1) // available)
            best_w = raw_w * best_num // best_den
            for den in range(1, 41):
                for num in range(1, den + 1):
                    w = raw_w * num // den
                    if w <= available and w > best_w:
                        best_num, best_den, best_w = num, den, w
            ratio = (best_num, best_den)

        if ratio == self._banner_ratio and self._banner_img is not None:
            return
        self._banner_ratio = ratio
        num, den = ratio
        self._banner_img = self._banner_raw.zoom(num, num).subsample(den, den)
        self._banner_label.configure(image=self._banner_img)

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
            self._refresh_filename_style()
            self.status_var.set("Status: Loaded input score")

    def _refresh_filename_style(self, _event=None) -> None:
        """Render the default sample path as an italic hint in the filename entry."""
        if not hasattr(self, "filename_entry"):
            return
        current = self.filename_var.get().strip()
        if self._default_input_hint and current == self._default_input_hint:
            self.filename_entry.configure(
                fg="#64748b",
                font=self._filename_font_italic,
            )
        else:
            self.filename_entry.configure(
                fg="#111827",
                font=self._filename_font_normal,
            )

    def generate_cmd(self) -> None:
        """Run fingering generation for the selected score/options."""
        filename = self.filename_var.get().strip()
        output_file = self.output_file_var.get().strip() or "output.xml"
        if not filename:
            messagebox.showerror("PianoPlayer", "Please choose an input score first.")
            return
        left_on = self.left_enabled.get()
        right_on = self.right_enabled.get()
        if not left_on and not right_on:
            messagebox.showerror("PianoPlayer", "Select at least one hand to scan.")
            return

        self.status_var.set(f"Status: Generating {output_file}")
        self.parent.update_idletasks()
        self._set_busy(True)
        try:
            try:
                n_measures = int(self.n_measures_var.get())
            except (TypeError, ValueError):
                n_measures = 1000

            try:
                start_measure = int(self.start_measure_var.get())
            except (TypeError, ValueError):
                start_measure = 1

            try:
                depth = int(self.depth_var.get())
            except (TypeError, ValueError):
                depth = 0

            try:
                rpart = int(self.rpart_var.get())
            except (TypeError, ValueError):
                rpart = 0

            try:
                lpart = int(self.lpart_var.get())
            except (TypeError, ValueError):
                lpart = 1

            try:
                rstaff = int(self.rstaff_var.get())
            except (TypeError, ValueError):
                rstaff = 0

            try:
                lstaff = int(self.lstaff_var.get())
            except (TypeError, ValueError):
                lstaff = 0

            try:
                chord_stagger = float(self.chord_stagger_var.get())
            except (TypeError, ValueError):
                chord_stagger = 0.05

            # Collect current widget values and call the synchronous core runner.
            auto_routing = bool(self.auto_routing_var.get())
            core.run_annotate(
                filename=filename,
                outputfile=output_file,
                n_measures=max(1, n_measures),
                start_measure=max(1, start_measure),
                depth=max(0, depth),
                rpart=0 if auto_routing else max(0, rpart),
                lpart=1 if auto_routing else max(0, lpart),
                rstaff=0 if auto_routing else max(0, rstaff),
                lstaff=0 if auto_routing else max(0, lstaff),
                auto_routing=auto_routing,
                quiet=bool(self.quiet_var.get()),
                musescore=bool(self.auto_open_musescore_var.get())
                and platform.system() != "Windows",
                below_beam=bool(self.below_beam_var.get()),
                colorize_hands=bool(self.colorize_hands_var.get()),
                colorize_by_cost=bool(self.colorize_by_cost_var.get()),
                colorize_by_fingering=bool(self.colorize_by_fingering_var.get()),
                cost_colormap=(self.cost_colormap_var.get().strip() or "traffic"),
                fingering_colors=",".join(
                    f"{finger}:{self.finger_color_vars[finger].get().strip()}"
                    for finger in (1, 2, 3, 4, 5)
                    if self.finger_color_vars[finger].get().strip()
                ),
                rh_color=(self.rh_color_var.get().strip() or "#d62828"),
                lh_color=(self.lh_color_var.get().strip() or "#1d4ed8"),
                with_vedo=bool(self.with_vedo_var.get()),
                sound_off=bool(self.sound_off_var.get()),
                hand_size=(self.hand_size_var.get() or "M"),
                chord_note_stagger_s=max(0.0, chord_stagger),
                left_only=left_on and not right_on,
                right_only=right_on and not left_on,
            )
            self.status_var.set(f"Status: Generated {output_file}")
        except (PianoPlayerError, ValueError) as exc:
            messagebox.showerror("PianoPlayer", str(exc))
            self.status_var.set("Status: Generation failed")
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
            self.status_var.set(f"Status: Opened {output_file}")
        except Exception as exc:
            messagebox.showerror("PianoPlayer", f"Unable to open MuseScore: {exc}")
            self.status_var.set("Status: Unable to open output")
        finally:
            self._set_busy(False)

    def _close_cmd(self, _event=None) -> None:
        """Close the GUI window (bound to q and Ctrl+W)."""
        self.parent.destroy()


def launch() -> None:
    """Create and run the PianoPlayer GUI application."""
    root = Tk()
    root.geometry("700x680")
    root.minsize(700, 680)
    PianoGUI(root)
    root.mainloop()
