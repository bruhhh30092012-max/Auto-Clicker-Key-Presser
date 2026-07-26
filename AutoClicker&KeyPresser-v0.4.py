import os
import sys
import time
import gc
import json
import threading
import random
import ctypes
from collections import deque
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox

keyboard = None
mouse = None

_INPUT_LIBS_READY = threading.Event()


def _load_input_libs():
    global keyboard, mouse
    import keyboard as _keyboard
    import mouse as _mouse

    keyboard = _keyboard
    mouse = _mouse
    _INPUT_LIBS_READY.set()

ALL_KEYS = [

    *[c for c in "abcdefghijklmnopqrstuvwxyz"],
    *[str(n) for n in range(10)],
    *[f"f{n}" for n in range(1, 13)],
    "space", "enter", "esc", "tab", "backspace", "delete", "insert",
    "home", "end", "pageup", "pagedown",
    "up", "down", "left", "right",
    "shift", "shiftleft", "shiftright",
    "ctrl", "ctrlleft", "ctrlright",
    "alt", "altleft", "altright",
    "win", "winleft", "winright",
    "capslock", "numlock", "scrolllock",
    "printscreen", "pause", "menu",
    "`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/",
    *[f"num{n}" for n in range(10)],
    "add", "subtract", "multiply", "divide", "decimal", "separator",
]

COLOR_BG = "#f0f0f0"
COLOR_CARD = "#ffffff"
COLOR_BORDER = "#c8c8c8"
COLOR_HEADER_BG = "#3d3d3d"
COLOR_HEADER_TEXT = "#ffffff"
COLOR_TEXT = "#222222"
COLOR_MUTED = "#777777"
COLOR_START = "#e0e0e0"
COLOR_START_ACTIVE = "#cfcfcf"
COLOR_STOP = "#3d3d3d"
COLOR_STOP_ACTIVE = "#2a2a2a"
COLOR_BTN_IDLE = "#e6e6e6"
COLOR_BTN_IDLE_ACTIVE = "#d8d8d8"

SMART_CLICK_RADIUS = 5
MEMORY_CLEANUP_THRESHOLD_MB = 45
DEFAULT_MOVE_RECORD_INTERVAL_MS = 100
MIN_MOVE_RECORD_INTERVAL_MS = 10
# Gap between the individual clicks that make up a Double/Triple click.
# Firing mouse.click() back-to-back with zero delay is fast enough that
# some apps only ever see the *last* press/release pair (the earlier ones
# get coalesced), so double/triple click wasn't reliably recognized as
# such. A small, consistent gap (well under Windows' default ~500ms
# double-click threshold) makes each click land as a distinct event.
MULTI_CLICK_GAP_S = 0.02


if hasattr(ctypes, "windll"):
    class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_uint32),
            ("PageFaultCount", ctypes.c_uint32),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]


def get_process_memory_mb():
    if not hasattr(ctypes, "windll"):
        return 0.0
    try:
        counters = _PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        return counters.WorkingSetSize / (1024 * 1024)
    except Exception:
        return 0.0



COLOR_SECTION_BG = "#ffffff"
COLOR_SECTION_BORDER = "#dcdcdc"
COLOR_SECTION_TITLE = "#555555"
COLOR_SCROLL_TROUGH = "#e8e8e8"
COLOR_SCROLL_THUMB = "#b5b5b5"
COLOR_SCROLL_THUMB_ACTIVE = "#8f8f8f"

BACKGROUND_WIDGET_CLASSES = {"Frame", "TFrame", "Label", "TLabel", "Canvas", "TLabelframe", "Toplevel"}


class RateCounter:
    def __init__(self, window=1.0):
        self.window = window
        self._times = deque()
        self._lock = threading.Lock()

    def tick(self, n=1):
        now = time.time()
        with self._lock:
            for _ in range(max(1, n)):
                self._times.append(now)
            cutoff = now - self.window
            while self._times and self._times[0] < cutoff:
                self._times.popleft()

    def rate(self):
        now = time.time()
        with self._lock:
            cutoff = now - self.window
            while self._times and self._times[0] < cutoff:
                self._times.popleft()
            return len(self._times) / self.window

    def reset(self):
        with self._lock:
            self._times.clear()


class AutoClickerPresser:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker & Key Presser")
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        try:
            myappid = 'mycompany.autoclicker.presser.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        try:
            if getattr(sys, 'frozen', False):
                base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            icon_path = os.path.join(base_path, "logo.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        try:
            if getattr(sys, 'frozen', False):
                settings_dir = os.path.dirname(sys.executable)
            else:
                settings_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            settings_dir = os.getcwd()
        self.settings_path = os.path.join(settings_dir, "autoclicker_settings.json")
        self.profiles_path = os.path.join(settings_dir, "autoclicker_profiles.json")
        self.profiles = {}
        self.active_profile_name = None

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background=COLOR_CARD, foreground=COLOR_TEXT, font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=COLOR_CARD, foreground=COLOR_MUTED, font=("Segoe UI", 8))
        style.configure("TRadiobutton", background=COLOR_CARD, foreground=COLOR_TEXT)
        style.configure("TCheckbutton", background=COLOR_CARD, foreground=COLOR_TEXT)
        # Smart click uses this style instead of the default TCheckbutton so
        # its indicator is the same round radio-button dot used everywhere
        # else (e.g. "Repeat until stopped"), not a hand-drawn shape and not
        # the default square/X checkbox. Reusing TRadiobutton's layout on a
        # TCheckbutton still toggles a plain on/off variable - it just looks
        # like a radio button.
        style.layout("Round.TCheckbutton", style.layout("TRadiobutton"))
        style.configure("Round.TCheckbutton", background=COLOR_CARD, foreground=COLOR_TEXT)
        style.configure("TEntry", padding=2, fieldbackground=COLOR_CARD, foreground=COLOR_TEXT)
        style.map("TEntry",
                  fieldbackground=[("readonly", COLOR_CARD), ("disabled", "#eeeeee")],
                  foreground=[("readonly", COLOR_TEXT), ("disabled", COLOR_MUTED)])

        style.configure("TCombobox", padding=2, fieldbackground=COLOR_CARD, background=COLOR_CARD,
                         foreground=COLOR_TEXT, arrowcolor=COLOR_TEXT, selectbackground=COLOR_CARD,
                         selectforeground=COLOR_TEXT)
        style.map("TCombobox",
                  fieldbackground=[("readonly", COLOR_CARD), ("disabled", "#eeeeee")],
                  background=[("readonly", COLOR_CARD), ("active", COLOR_CARD)],
                  foreground=[("readonly", COLOR_TEXT), ("disabled", COLOR_MUTED)])

        style.configure("Modern.Vertical.TScrollbar",
                         gripcount=0,
                         background=COLOR_SCROLL_THUMB,
                         darkcolor=COLOR_SCROLL_THUMB,
                         lightcolor=COLOR_SCROLL_THUMB,
                         troughcolor=COLOR_SCROLL_TROUGH,
                         bordercolor=COLOR_SCROLL_TROUGH,
                         arrowcolor=COLOR_MUTED,
                         arrowsize=12,
                         relief="flat",
                         borderwidth=0,
                         width=12)
        style.map("Modern.Vertical.TScrollbar",
                  background=[("active", COLOR_SCROLL_THUMB_ACTIVE), ("pressed", COLOR_SCROLL_THUMB_ACTIVE)],
                  darkcolor=[("active", COLOR_SCROLL_THUMB_ACTIVE), ("pressed", COLOR_SCROLL_THUMB_ACTIVE)],
                  lightcolor=[("active", COLOR_SCROLL_THUMB_ACTIVE), ("pressed", COLOR_SCROLL_THUMB_ACTIVE)])

        style.configure("TNotebook", background=COLOR_BG, borderwidth=0, tabmargins=[4, 6, 4, 0])
        style.configure("TNotebook.Tab", background=COLOR_BTN_IDLE, foreground=COLOR_TEXT,
                         font=("Segoe UI", 9, "bold"), padding=[16, 7], borderwidth=1)
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_CARD), ("active", COLOR_BTN_IDLE_ACTIVE)],
                  foreground=[("selected", COLOR_TEXT), ("active", COLOR_TEXT)],
                  expand=[("selected", [1, 1, 1, 0])])

        style.configure("Record.Treeview",
                         background=COLOR_BG,
                         fieldbackground=COLOR_BG,
                         foreground=COLOR_TEXT,
                         font=("Segoe UI", 9),
                         rowheight=22,
                         borderwidth=0,
                         relief="flat")
        # Heading row (Time / Type / Detail labels): light gray background, black text.
        COLOR_TREE_HEAD_BG = "#e9e9e9"
        COLOR_TREE_HEAD_TEXT = "#000000"
        style.configure("Record.Treeview.Heading",
                         background=COLOR_TREE_HEAD_BG,
                         foreground=COLOR_TREE_HEAD_TEXT,
                         font=("Segoe UI", 8, "bold"),
                         relief="flat",
                         borderwidth=0)
        style.map("Record.Treeview",
                  background=[("selected", "#d6d6d6")],
                  foreground=[("selected", COLOR_TEXT)])
        style.map("Record.Treeview.Heading",
                  background=[("active", COLOR_TREE_HEAD_BG), ("pressed", COLOR_TREE_HEAD_BG)],
                  foreground=[("active", COLOR_TREE_HEAD_TEXT), ("pressed", COLOR_TREE_HEAD_TEXT)])
        style.layout("Record.Treeview", style.layout("Treeview"))

        self.root.option_add("*TCombobox*Listbox.background", COLOR_CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", COLOR_TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#d6d6d6")
        self.root.option_add("*TCombobox*Listbox.selectForeground", COLOR_TEXT)
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))

        self.clicker_running = False
        self.presser_running = False
        # Each Start click gets its own "generation" number + private
        # threading.Event. This lets an old worker thread from a previous
        # Start/Stop keep winding down on its own in the background while a
        # brand new one starts immediately, without the two stepping on
        # each other's UI updates (see toggle_clicker/run_clicker).
        self.clicker_gen = 0
        self.clicker_stop_event = None
        self.presser_gen = 0
        self.presser_stop_event = None
        self.picking_location = False
        self.capturing_hotkey_for = None
        self._hotkey_capture_hook = None
        self._hotkey_capture_prev_value = None
        self._hotkey_capture_timeout_id = None
        self.hotkey_specs = {}

        self.recording = False
        self.playing = False
        self.recorded_events = []
        self.record_start_time = 0.0
        self._record_row_map = []
        self._keys_held = set()
        self._buttons_held = set()
        self._last_move_record_wall = 0.0
        # While recording, we only ever touch the cheap count label live -
        # never the Treeview (see _schedule_count_label_update). This flag
        # coalesces bursts of events (e.g. fast typing/clicking) into at
        # most one pending `root.after` label update at a time, instead of
        # queuing a callback per event.
        self._count_label_update_pending = False

        self.clicker_thread = None
        self.presser_thread = None
        self.playback_thread = None

        self.click_rate_counter = RateCounter()
        self.press_rate_counter = RateCounter()

        self.create_scrollable_container()
        self.create_widgets(self.scroll_frame)

        self.root.update_idletasks()
        self.fit_window_to_screen()

        self.hotkey_thread = threading.Thread(target=self.listen_hotkeys, daemon=True)
        self.hotkey_thread.start()

        self.memory_watchdog_thread = threading.Thread(target=self.watch_memory, daemon=True)
        self.memory_watchdog_thread.start()

        self.root.bind_all("<Button-1>", self._on_global_click, add="+")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed, add="+")
        self.root.after(0, self._build_remaining_tabs)
        self.root.after(150, self.update_rate_labels)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_scrollable_container(self):
        self.canvas = tk.Canvas(self.root, bg=COLOR_BG, highlightthickness=0)
        self.v_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview,
                                          style="Modern.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")

        self.scroll_frame = tk.Frame(self.canvas, bg=COLOR_BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        self.scroll_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux_up(event):
            self.canvas.yview_scroll(-1, "units")

        def _on_mousewheel_linux_down(event):
            self.canvas.yview_scroll(1, "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", _on_mousewheel_linux_up)
        self.canvas.bind_all("<Button-5>", _on_mousewheel_linux_down)

    def fit_window_to_screen(self):
        req_width = self.scroll_frame.winfo_reqwidth() + self.v_scrollbar.winfo_reqwidth() + 4
        req_height = self.scroll_frame.winfo_reqheight()

        screen_h = self.root.winfo_screenheight()
        max_height = screen_h - 120
        final_height = min(req_height, max_height)

        self.root.geometry(f"{req_width}x{final_height}")

    def make_card(self, parent, title):
        outer = tk.Frame(parent, bg=COLOR_BORDER, bd=0)
        outer.pack(fill="x", pady=(0, 10))

        header = tk.Frame(outer, bg=COLOR_HEADER_BG, height=28)
        header.pack(fill="x")
        tk.Label(header, text=title, bg=COLOR_HEADER_BG, fg=COLOR_HEADER_TEXT,
                 font=("Segoe UI", 10, "bold"), padx=10, pady=4).pack(side="left")

        body = tk.Frame(outer, bg=COLOR_CARD, padx=10, pady=8)
        body.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        return body

    def make_section(self, parent, title):
        wrap = tk.Frame(parent, bg=COLOR_SECTION_BORDER, bd=0)
        wrap.pack(fill="x", pady=(0, 8))

        inner = tk.Frame(wrap, bg=COLOR_SECTION_BG, padx=10, pady=8)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        if title:
            tk.Label(inner, text=title.upper(), bg=COLOR_SECTION_BG, fg=COLOR_SECTION_TITLE,
                      font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 6))

        return inner

    def create_widgets(self, parent):
        main_frame = tk.Frame(parent, padx=12, pady=12, bg=COLOR_BG)
        main_frame.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)

        click_tab = tk.Frame(self.notebook, bg=COLOR_CARD, padx=10, pady=10)
        press_tab = tk.Frame(self.notebook, bg=COLOR_CARD, padx=10, pady=10)
        record_tab = tk.Frame(self.notebook, bg=COLOR_CARD, padx=10, pady=10)
        profile_tab = tk.Frame(self.notebook, bg=COLOR_CARD, padx=10, pady=10)

        self.notebook.add(click_tab, text="Mouse Clicker")
        self.notebook.add(press_tab, text="Key Presser")
        self.notebook.add(record_tab, text="Record & Playback")
        self.notebook.add(profile_tab, text="Profile")

        self.build_click_tab(click_tab)

        self._press_tab = press_tab
        self._record_tab = record_tab
        self._profile_tab = profile_tab
        self._remaining_tabs_built = False

        self.status_msg_label = tk.Label(main_frame, text="", bg=COLOR_BG, fg=COLOR_MUTED, font=("Segoe UI", 8))
        self.status_msg_label.pack(pady=(6, 0))

        self.status_label = tk.Label(main_frame, text="Status: Idle", bg=COLOR_BG, fg=COLOR_MUTED,
                                      font=("Segoe UI", 10, "bold"))
        self.status_label.pack(pady=(8, 0))

    def _on_tab_changed(self, event=None):
        self._build_remaining_tabs()

        def _fix_focus():
            # ttk.Notebook's automatic tab-switch focus traversal doesn't
            # just move keyboard focus into the first focusable widget of
            # the new pane - Tk's <<TraverseIn>> handling for Entry/Spinbox
            # widgets also selects the entire contents of that widget. That
            # combo is what produced the earlier bug reports:
            #  - focusing an Entry (e.g. "Hours") shows its selected text
            #  - focusing a Checkbutton draws a dotted focus box around it
            # Simply moving focus elsewhere afterward (as before) leaves
            # that selection in place - it just renders gray/"inactive"
            # instead of blue, which is the newly reported gray highlight.
            stray = self.root.focus_get()
            if stray is not None:
                try:
                    stray.selection_clear()
                except Exception:
                    pass
            # Send focus to the root window itself rather than the
            # notebook - focusing the notebook widget draws its own focus
            # ring around the active tab's title, which is the "tab name
            # bi dinh" (tab label picking up a focus box) regression.
            # Toplevels don't render any visible focus indicator, so this
            # leaves nothing highlighted anywhere.
            self.root.focus_set()

        self.root.after_idle(_fix_focus)

    def _build_remaining_tabs(self):
        if self._remaining_tabs_built:
            return
        self._remaining_tabs_built = True
        self.build_press_tab(self._press_tab)
        self.build_record_tab(self._record_tab)
        self.build_profile_tab(self._profile_tab)
        self.root.update_idletasks()
        self.fit_window_to_screen()
        self.load_profiles_store()

    def build_click_tab(self, click_body):
        click_timing_section = self.make_section(click_body, "Timing")
        self.click_int_vars = self.create_interval_row(click_timing_section, "Click interval")

        opts_section = self.make_section(click_body, "Click Options")
        opts_frame = tk.Frame(opts_section, bg=COLOR_CARD)
        opts_frame.pack(fill="x")

        ttk.Label(opts_frame, text="Mouse button:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.mouse_btn_var = tk.StringVar(value="Left")
        ttk.Combobox(opts_frame, textvariable=self.mouse_btn_var, values=["Left", "Right", "Middle"],
                     width=8, state="readonly").grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(opts_frame, text="Click type:").grid(row=0, column=2, sticky="w", padx=(16, 4), pady=2)
        self.click_type_var = tk.StringVar(value="Single")
        ttk.Combobox(opts_frame, textvariable=self.click_type_var, values=["Single", "Double", "Triple"],
                     width=8, state="readonly").grid(row=0, column=3, sticky="w", pady=2)

        ttk.Label(opts_frame, text="Action mode:").grid(row=0, column=4, sticky="w", padx=(16, 4), pady=2)
        self.click_action_mode_var = tk.StringVar(value="Click")
        ttk.Combobox(opts_frame, textvariable=self.click_action_mode_var, values=["Click", "Hold"],
                     width=8, state="readonly").grid(row=0, column=5, sticky="w", pady=2)

        self.smart_click_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts_frame, text="Smart click", variable=self.smart_click_var,
                        style="Round.TCheckbutton").grid(
            row=1, column=2, columnspan=4, sticky="w", padx=(24, 0), pady=(6, 0))

        self.click_max_speed_var = tk.BooleanVar(value=False)
        max_cps_row = tk.Frame(opts_frame, bg=COLOR_CARD)
        max_cps_row.grid(row=3, column=0, columnspan=6, sticky="w", pady=(6, 0))
        ttk.Checkbutton(max_cps_row, text="Max CPS:",
                         variable=self.click_max_speed_var,
                         command=self.on_click_max_speed_toggle).pack(side="left")
        self.click_max_cps_entry = ttk.Entry(max_cps_row, width=6, justify="right", state="disabled")
        self.click_max_cps_entry.insert(0, "10")
        self.click_max_cps_entry.pack(side="left", padx=6)
        ttk.Label(max_cps_row, text="CPS").pack(side="left")
        self.click_cps_label = ttk.Label(max_cps_row, text="Current CPS: 0.0", style="Muted.TLabel")
        self.click_cps_label.pack(side="left", padx=(16, 0))

        self.repeat_mode_var = tk.StringVar(value="infinite")
        ttk.Radiobutton(opts_frame, text="Repeat until stopped", variable=self.repeat_mode_var,
                         value="infinite").grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        repeat_frame = tk.Frame(opts_frame, bg=COLOR_CARD)
        repeat_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=2)
        ttk.Radiobutton(repeat_frame, text="Repeat click", variable=self.repeat_mode_var, value="finite").pack(side="left")
        self.repeat_entry = ttk.Entry(repeat_frame, width=6)
        self.repeat_entry.insert(0, "100")
        self.repeat_entry.pack(side="left", padx=5)
        ttk.Label(repeat_frame, text="times").pack(side="left")

        pos_section = self.make_section(click_body, "Cursor Position")
        pos_frame = tk.Frame(pos_section, bg=COLOR_CARD)
        pos_frame.pack(fill="x")

        ttk.Label(pos_frame, text="Cursor position:").grid(row=0, column=0, sticky="w", pady=2)
        self.pos_mode_var = tk.StringVar(value="current")
        ttk.Radiobutton(pos_frame, text="Current location", variable=self.pos_mode_var, value="current").grid(
            row=1, column=0, columnspan=3, sticky="w")

        pick_row = tk.Frame(pos_frame, bg=COLOR_CARD)
        pick_row.grid(row=2, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Radiobutton(pick_row, text="Pick location", variable=self.pos_mode_var, value="fixed").pack(side="left")
        self.pick_btn = self._flat_button(pick_row, "Pick", self.start_pick_location, width=6)
        self.pick_btn.pack(side="left", padx=6)
        ttk.Label(pick_row, text="X:").pack(side="left", padx=(10, 2))
        self.x_display = ttk.Entry(pick_row, width=5)
        self.x_display.insert(0, "0")
        self.x_display.pack(side="left")
        ttk.Label(pick_row, text="Y:").pack(side="left", padx=(6, 2))
        self.y_display = ttk.Entry(pick_row, width=5)
        self.y_display.insert(0, "0")
        self.y_display.pack(side="left")

        click_hold_section = self.make_section(click_body, "Hold Duration (Hold mode)")
        self.click_hold_vars = self.create_interval_row(click_hold_section, "Hold duration")

        click_hotkey_section = self.make_section(click_body, "Hotkey & Control")
        self.click_hotkey_entry, self.click_toggle_btn = self.create_hotkey_and_toggle_row(
            click_hotkey_section, default_hotkey="f6", toggle_command=self.toggle_clicker, action_label="Clicker",
            hotkey_which="click", running_attr="clicker_running")

    def build_press_tab(self, press_body):
        press_timing_section = self.make_section(press_body, "Timing")
        self.press_int_vars = self.create_interval_row(press_timing_section, "Press interval")

        key_section = self.make_section(press_body, "Key Options")
        key_frame = tk.Frame(key_section, bg=COLOR_CARD)
        key_frame.pack(fill="x")

        ttk.Label(key_frame, text="Key to press:").grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.press_key_var = tk.StringVar(value="space")
        self.press_key_combo = ttk.Combobox(key_frame, textvariable=self.press_key_var, values=ALL_KEYS, width=14)
        self.press_key_combo.grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(key_frame, text="Action mode:").grid(row=0, column=2, sticky="w", padx=(16, 4), pady=2)
        self.press_action_mode_var = tk.StringVar(value="Click")
        ttk.Combobox(key_frame, textvariable=self.press_action_mode_var, values=["Click", "Hold"],
                     width=8, state="readonly").grid(row=0, column=3, sticky="w", pady=2)

        # Repeat mode, mirroring the Mouse Clicker tab (repeat option rows
        # come before Max Speed there too): repeat forever, or a fixed
        # number of presses. Key Presser used to silently borrow the Mouse
        # Clicker's repeat_mode_var/repeat_entry, so changing the click
        # count would also change how many times keys got pressed - it now
        # has its own independent controls.
        self.press_repeat_mode_var = tk.StringVar(value="infinite")
        ttk.Radiobutton(key_frame, text="Repeat until stopped", variable=self.press_repeat_mode_var,
                         value="infinite").grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))
        press_repeat_frame = tk.Frame(key_frame, bg=COLOR_CARD)
        press_repeat_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=2)
        ttk.Radiobutton(press_repeat_frame, text="Repeat press", variable=self.press_repeat_mode_var,
                         value="finite").pack(side="left")
        self.press_repeat_entry = ttk.Entry(press_repeat_frame, width=6)
        self.press_repeat_entry.insert(0, "100")
        self.press_repeat_entry.pack(side="left", padx=5)
        ttk.Label(press_repeat_frame, text="times").pack(side="left")

        self.press_max_speed_var = tk.BooleanVar(value=False)
        max_pps_row = tk.Frame(key_frame, bg=COLOR_CARD)
        max_pps_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))
        ttk.Checkbutton(max_pps_row, text="Max PPS:",
                         variable=self.press_max_speed_var,
                         command=self.on_press_max_speed_toggle).pack(side="left")
        self.press_max_pps_entry = ttk.Entry(max_pps_row, width=6, justify="right", state="disabled")
        self.press_max_pps_entry.insert(0, "10")
        self.press_max_pps_entry.pack(side="left", padx=6)
        ttk.Label(max_pps_row, text="PPS").pack(side="left")
        self.press_pps_label = ttk.Label(max_pps_row, text="Current PPS: 0.0", style="Muted.TLabel")
        self.press_pps_label.pack(side="left", padx=(16, 0))

        press_hold_section = self.make_section(press_body, "Hold Duration (Hold mode)")
        self.press_hold_vars = self.create_interval_row(press_hold_section, "Hold duration")

        press_hotkey_section = self.make_section(press_body, "Hotkey & Control")
        self.press_hotkey_entry, self.press_toggle_btn = self.create_hotkey_and_toggle_row(
            press_hotkey_section, default_hotkey="f7", toggle_command=self.toggle_presser, action_label="Presser",
            hotkey_which="press", running_attr="presser_running")

    def build_record_tab(self, record_body):
        rec_section = self.make_section(record_body, "Recording")

        rec_opts_row = tk.Frame(rec_section, bg=COLOR_CARD)
        rec_opts_row.pack(fill="x")
        self.record_moves_var = tk.BooleanVar(value=False)
        self.record_keys_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(rec_opts_row, text="Record mouse movement",
                        variable=self.record_moves_var).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=2)
        ttk.Checkbutton(rec_opts_row, text="Record keyboard",
                        variable=self.record_keys_var).grid(row=0, column=1, sticky="w", pady=2)

        move_rate_row = tk.Frame(rec_section, bg=COLOR_CARD)
        move_rate_row.pack(fill="x", pady=(4, 0))
        ttk.Label(move_rate_row, text="Record mouse position every (ms):").pack(side="left")
        self.record_move_interval_entry = ttk.Entry(move_rate_row, width=6, justify="center")
        self.record_move_interval_entry.insert(0, str(DEFAULT_MOVE_RECORD_INTERVAL_MS))
        self.record_move_interval_entry.pack(side="left", padx=(6, 0))
        # This hint used to sit on the same line as the label/entry above,
        # which made it the single widest row in the whole window and
        # forced the whole app wider than it needed to be. Putting it on
        # its own line (and letting it wrap) keeps the window narrow.
        move_rate_hint = ttk.Label(
            rec_section, text="Default 100ms = 10 FPS. Higher = smoother GUI.",
            style="Muted.TLabel", justify="left")
        move_rate_hint.pack(anchor="w", fill="x", pady=(2, 0))
        # Fixed wraplength (not tied to the section's live width) - see the
        # comment on desc_label in build_profile_tab for why a "live" one
        # backfires and makes the window wider instead of narrower.
        move_rate_hint.config(wraplength=440)

        self.record_count_label = tk.Label(rec_section, text="Recorded events: 0", bg=COLOR_CARD,
                                            fg=COLOR_MUTED, font=("Segoe UI", 8))
        self.record_count_label.pack(anchor="w", pady=(8, 0))

        self.record_hotkey_entry, self.record_toggle_btn = self.create_hotkey_and_toggle_row(
            rec_section, default_hotkey="f8", toggle_command=self.toggle_recording, action_label="Recording",
            hotkey_which="record", running_attr="recording")

        list_section = self.make_section(record_body, "Recorded Actions")
        list_border = tk.Frame(list_section, bg=COLOR_BORDER)
        list_border.pack(fill="both", expand=True)
        list_row = tk.Frame(list_border, bg=COLOR_CARD)
        list_row.pack(fill="both", expand=True, padx=1, pady=1)

        list_scrollbar = ttk.Scrollbar(list_row, orient="vertical", style="Modern.Vertical.TScrollbar")
        self.record_tree = ttk.Treeview(list_row, columns=("time", "type", "detail"), show="headings",
                                         height=8, yscrollcommand=list_scrollbar.set, selectmode="browse",
                                         style="Record.Treeview")
        self.record_tree.heading("time", text="Time (s)", anchor="center")
        self.record_tree.heading("type", text="Type", anchor="center")
        self.record_tree.heading("detail", text="Detail", anchor="center")
        # Columns are not user-resizable (drag blocked below). Widths are
        # kept at a fixed 30% / 30% / 40% ratio (time/type/detail) and are
        # recalculated against the tree's *actual* rendered width whenever it
        # changes, since the tree expands to fill the section and a single
        # hardcoded pixel total would drift from the real ratio.
        self._time_col_width = 90
        self._type_col_width = 90
        self._detail_col_width = 160
        self.record_tree.column("time", width=self._time_col_width, minwidth=60,
                                 anchor="center", stretch=False)
        self.record_tree.column("type", width=self._type_col_width, minwidth=60,
                                 anchor="center", stretch=False)
        self.record_tree.column("detail", width=self._detail_col_width, minwidth=80,
                                 anchor="center", stretch=False)
        list_scrollbar.config(command=self.record_tree.yview)
        self.record_tree.pack(side="left", fill="both", expand=True)
        list_scrollbar.pack(side="right", fill="y")
        self.record_tree.bind("<Double-1>", self._on_record_tree_double_click)
        # Block manual column-border dragging so the ratio-based widths stay put.
        self.record_tree.bind("<Button-1>", self._block_column_drag, add="+")

        # Two thin static lines marking the boundaries between the three
        # columns (Time | Type | Detail) — purely visual, not draggable.
        self._record_tree_divider1 = tk.Frame(list_row, bg=COLOR_BORDER, width=1)
        self._record_tree_divider2 = tk.Frame(list_row, bg=COLOR_BORDER, width=1)
        self._record_tree_divider1.place(in_=self.record_tree, x=self._time_col_width, y=0, relheight=1)
        self._record_tree_divider2.place(in_=self.record_tree,
                                          x=self._time_col_width + self._type_col_width, y=0, relheight=1)
        self._record_tree_divider1.lift()
        self._record_tree_divider2.lift()
        self.record_tree.bind("<Configure>", self._resize_record_tree_columns, add="+")

        def _tree_mousewheel(event):
            self.record_tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def _tree_mousewheel_linux_up(event):
            self.record_tree.yview_scroll(-1, "units")
            return "break"

        def _tree_mousewheel_linux_down(event):
            self.record_tree.yview_scroll(1, "units")
            return "break"

        self.record_tree.bind("<MouseWheel>", _tree_mousewheel)
        self.record_tree.bind("<Button-4>", _tree_mousewheel_linux_up)
        self.record_tree.bind("<Button-5>", _tree_mousewheel_linux_down)

        # A 2x3 grid (instead of two separately-packed rows of differently
        # sized buttons) so every button lines up into even rows AND
        # columns - "Delete Actions" being the longest label used to make
        # row 1 wider than row 2 and throw off the alignment between them.
        actions_grid = tk.Frame(list_section, bg=COLOR_CARD)
        actions_grid.pack(fill="x", pady=(8, 0))
        for col in range(3):
            actions_grid.columnconfigure(col, weight=1, uniform="record_action_btn")

        action_specs = (
            ("Add Action", self._add_new_event, 0, 0),
            ("Delete Actions", self._delete_selected_event, 0, 1),
            ("Edit", self._edit_selected_event, 0, 2),
            ("Clear", self.clear_recorded_events, 1, 0),
            ("Download", self._download_recorded_events, 1, 1),
            ("Import", self._import_recorded_events, 1, 2),
        )
        for text, command, row, col in action_specs:
            btn = self._flat_button(actions_grid, text, command, width=1)
            btn.grid(row=row, column=col, sticky="ew",
                     padx=(0 if col == 0 else 6, 0), pady=(0 if row == 0 else 6, 0))
            if text == "Add Action":
                self.add_action_btn = btn

        play_section = self.make_section(record_body, "Playback")

        self.playback_repeat_mode_var = tk.StringVar(value="infinite")
        ttk.Radiobutton(play_section, text="Repeat until stopped", variable=self.playback_repeat_mode_var,
                         value="infinite").pack(anchor="w")
        play_repeat_row = tk.Frame(play_section, bg=COLOR_CARD)
        play_repeat_row.pack(fill="x", pady=2, anchor="w")
        ttk.Radiobutton(play_repeat_row, text="Repeat playback", variable=self.playback_repeat_mode_var,
                         value="finite").pack(side="left")
        self.playback_repeat_entry = ttk.Entry(play_repeat_row, width=6)
        self.playback_repeat_entry.insert(0, "1")
        self.playback_repeat_entry.pack(side="left", padx=5)
        ttk.Label(play_repeat_row, text="times").pack(side="left")

        speed_row = tk.Frame(play_section, bg=COLOR_CARD)
        speed_row.pack(fill="x", pady=(8, 4), anchor="w")
        ttk.Label(speed_row, text="Playback speed (x):").pack(side="left")
        self.playback_speed_entry = ttk.Entry(speed_row, width=6, justify="right")
        self.playback_speed_entry.insert(0, "1.0")
        self.playback_speed_entry.pack(side="left", padx=6)

        self.playback_hotkey_entry, self.playback_toggle_btn = self.create_hotkey_and_toggle_row(
            play_section, default_hotkey="f9", toggle_command=self.toggle_playback, action_label="Playback",
            hotkey_which="playback", running_attr="playing")

    def build_profile_tab(self, profile_body):
        info_section = self.make_section(profile_body, "Active Profile")
        self.active_profile_label = tk.Label(
            info_section, text="Active: -", bg=COLOR_CARD, fg=COLOR_TEXT,
            font=("Segoe UI", 10, "bold"))
        self.active_profile_label.pack(anchor="w")

        desc_label = ttk.Label(
            info_section,
            text="Saves settings from the other 3 tabs. Select a profile and click "
                 "Apply to use it, or New to save the current settings as a profile.",
            style="Muted.TLabel", justify="left")
        desc_label.pack(anchor="w", fill="x", pady=(4, 0))
        # A wraplength that tracks the section's live width sounds nice, but
        # it creates a chicken-and-egg problem: fit_window_to_screen() sizes
        # the window from each widget's *unwrapped* required width, and the
        # <Configure> event that would shrink this label to fit only fires
        # after the window is already that wide. Net effect: this single
        # label was silently forcing the whole app ~250px wider than it
        # needed to be. A fixed wraplength breaks that loop.
        desc_label.config(wraplength=440)

        self.auto_save_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            info_section, text="Auto save changes to the active profile",
            variable=self.auto_save_var, command=self._on_auto_save_toggle).pack(anchor="w", pady=(8, 0))

        list_section = self.make_section(profile_body, "Profiles")
        list_border = tk.Frame(list_section, bg=COLOR_BORDER)
        list_border.pack(fill="both", expand=True)
        list_row = tk.Frame(list_border, bg=COLOR_CARD)
        list_row.pack(fill="both", expand=True, padx=1, pady=1)

        list_scrollbar = ttk.Scrollbar(list_row, orient="vertical", style="Modern.Vertical.TScrollbar")
        self.profile_tree = ttk.Treeview(
            list_row, columns=("name",), show="headings", height=8,
            yscrollcommand=list_scrollbar.set, selectmode="browse", style="Record.Treeview")
        self.profile_tree.heading("name", text="Profile Name", anchor="w")
        self.profile_tree.column("name", anchor="w", stretch=True)
        list_scrollbar.config(command=self.profile_tree.yview)
        self.profile_tree.pack(side="left", fill="both", expand=True)
        list_scrollbar.pack(side="right", fill="y")
        self.profile_tree.bind("<Double-1>", lambda e: self.apply_selected_profile())

        # Row 1/2: actions on a single profile, 3 per row instead of 6 in
        # one row - six buttons side by side was one of the widest elements
        # in the window and forced the whole app wider than it needed to be.
        # Row 3: bulk/backup actions - same Clear/Download/Import grouping
        # as the Record tab, for a consistent layout language across tabs.
        # Each row uses 3 equal-width grid columns so the buttons spread
        # out evenly across the full row width instead of clumping to the
        # left with empty space on the right.
        def _profile_button_row(parent, specs):
            row = tk.Frame(parent, bg=COLOR_CARD)
            for col in range(3):
                row.columnconfigure(col, weight=1, uniform="profile_btn_col")
            for col, (text, cmd) in enumerate(specs):
                pad = (0, 4) if col == 0 else ((4, 0) if col == 2 else 4)
                self._flat_button(row, text, cmd, width=9).grid(
                    row=0, column=col, sticky="ew", padx=pad)
            return row

        _profile_button_row(profile_body, [
            ("New", self.new_profile), ("Save", self.save_current_profile), ("Apply", self.apply_selected_profile),
        ]).pack(fill="x", pady=(8, 0))

        _profile_button_row(profile_body, [
            ("Rename", self.rename_selected_profile), ("Edit", self.edit_selected_profile),
            ("Delete", self.delete_selected_profile),
        ]).pack(fill="x", pady=(6, 0))

        _profile_button_row(profile_body, [
            ("Clear", self.clear_profiles), ("Download", self.download_profiles), ("Import", self.import_profiles),
        ]).pack(fill="x", pady=(6, 0))


    def refresh_profile_list(self):
        if not hasattr(self, "profile_tree"):
            return
        self.profile_tree.delete(*self.profile_tree.get_children())
        to_select = None
        for name in self.profiles.keys():
            label = f"{name}  (active)" if name == self.active_profile_name else name
            iid = self.profile_tree.insert("", "end", values=(label,))
            # Tag holds the real name so display suffix "(active)" never
            # has to be parsed back out of the label text.
            self.profile_tree.item(iid, tags=(name,))
            if name == self.active_profile_name:
                to_select = iid
        if to_select:
            self.profile_tree.selection_set(to_select)
            self.profile_tree.see(to_select)
        self.active_profile_label.config(text=f"Active: {self.active_profile_name or '-'}")

    def _selected_profile_name(self):
        sel = self.profile_tree.selection()
        if not sel:
            return None
        tags = self.profile_tree.item(sel[0], "tags")
        return tags[0] if tags else None

    def _require_selected_profile(self):
        name = self._selected_profile_name()
        if not name:
            messagebox.showinfo("No profile selected", "Select a profile from the list first.", parent=self.root)
        return name

    def _prompt_profile_name(self, title, default=""):
        result = self._prompt_fields(title, [
            {'key': 'name', 'label': 'Name', 'type': 'entry', 'default': default},
        ], over_widget=self._profile_tab)
        return result['name'].strip() if result else None

    def new_profile(self):
        name = self._prompt_profile_name("New Profile")
        if not name:
            return
        if name in self.profiles and not messagebox.askyesno(
                "Already exists", f"Profile '{name}' already exists. Overwrite?", parent=self.root):
            return
        self.profiles[name] = self.get_settings_dict()
        self.active_profile_name = name
        self.save_profiles_store()
        self.refresh_profile_list()
        self._flash_status(f"Profile '{name}' created.")

    def save_current_profile(self):
        name = self._selected_profile_name() or self.active_profile_name
        if not name:
            messagebox.showinfo("No profile selected", "Select a profile, or click New to create one.",
                                 parent=self.root)
            return
        self.profiles[name] = self.get_settings_dict()
        self.active_profile_name = name
        self.save_profiles_store()
        self.refresh_profile_list()
        self._flash_status(f"Saved current settings to '{name}'.")

    def apply_selected_profile(self):
        name = self._require_selected_profile()
        if not name:
            return
        # If Auto save is on, capture whatever was just edited into the
        # profile we're switching away FROM, so nothing is lost by
        # forgetting to hit Save before Apply.
        if name != self.active_profile_name:
            self._autosave_active_profile()
        self.apply_settings_dict(self.profiles[name])
        self._reregister_all_hotkeys()
        self.active_profile_name = name
        self.save_profiles_store()
        self.refresh_profile_list()
        self._flash_status(f"Applied profile '{name}'.")

    def rename_selected_profile(self):
        name = self._require_selected_profile()
        if not name:
            return
        new_name = self._prompt_profile_name("Rename Profile", default=name)
        if not new_name or new_name == name:
            return
        if new_name in self.profiles:
            messagebox.showwarning("Already exists", f"Profile '{new_name}' already exists.", parent=self.root)
            return
        self.profiles[new_name] = self.profiles.pop(name)
        if self.active_profile_name == name:
            self.active_profile_name = new_name
        self.save_profiles_store()
        self.refresh_profile_list()
        self._flash_status(f"Renamed '{name}' to '{new_name}'.")

    def edit_selected_profile(self):
        """Open the selected profile's stored settings as editable JSON, for
        advanced tweaks (e.g. a hotkey or interval) without switching every
        tab. Applies immediately if the edited profile is the active one."""
        name = self._require_selected_profile()
        if not name:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Profile - {name}")
        dialog.configure(bg=COLOR_CARD)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.withdraw()

        ttk.Label(dialog, text="Raw settings (JSON) - edit carefully.", style="Muted.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        text_frame = tk.Frame(dialog, bg=COLOR_CARD)
        text_frame.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 4), sticky="nsew")
        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", style="Modern.Vertical.TScrollbar")
        text_widget = tk.Text(text_frame, width=64, height=22, wrap="none",
                               yscrollcommand=text_scroll.set, font=("Consolas", 9))
        text_scroll.config(command=text_widget.yview)
        text_widget.pack(side="left", fill="both", expand=True)
        text_scroll.pack(side="right", fill="y")
        text_widget.insert("1.0", json.dumps(self.profiles.get(name, {}), indent=2, ensure_ascii=False))

        outcome = {'ok': False, 'data': None}

        def on_ok():
            try:
                parsed = json.loads(text_widget.get("1.0", "end-1c"))
            except Exception as exc:
                messagebox.showerror("Invalid JSON", f"Could not parse JSON:\n{exc}", parent=dialog)
                return
            if not isinstance(parsed, dict):
                messagebox.showerror("Invalid JSON", "Top-level value must be an object.", parent=dialog)
                return
            outcome['ok'] = True
            outcome['data'] = parsed
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        self._add_save_cancel_buttons(dialog, 2, on_ok, on_cancel)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        self._position_dialog_over_widget(dialog, self._profile_tab)
        dialog.deiconify()
        dialog.grab_set()
        self.root.wait_window(dialog)

        if not outcome['ok']:
            return
        self.profiles[name] = outcome['data']
        if name == self.active_profile_name:
            self.apply_settings_dict(self.profiles[name])
            self._reregister_all_hotkeys()
        self.save_profiles_store()
        self.refresh_profile_list()
        self._flash_status(f"Profile '{name}' updated.")

    def delete_selected_profile(self):
        name = self._require_selected_profile()
        if not name:
            return
        if len(self.profiles) <= 1:
            messagebox.showwarning("Can't delete", "At least one profile must remain.", parent=self.root)
            return
        if not messagebox.askyesno("Delete profile", f"Delete '{name}'? This can't be undone.", parent=self.root):
            return
        del self.profiles[name]
        if self.active_profile_name == name:
            self.active_profile_name = next(iter(self.profiles))
            self.apply_settings_dict(self.profiles[self.active_profile_name])
            self._reregister_all_hotkeys()
        self.save_profiles_store()
        self.refresh_profile_list()
        self._flash_status(f"Deleted profile '{name}'.")

    def _autosave_active_profile(self):
        """Silently write the current UI settings into whichever profile is
        active, if Auto save is checked. Called right before switching
        profiles and on app close - the two moments edits would otherwise
        be lost without an explicit Save click."""
        if not self.auto_save_var.get() or not self.active_profile_name:
            return
        self.profiles[self.active_profile_name] = self.get_settings_dict()
        self.save_profiles_store()

    def _on_auto_save_toggle(self):
        self.save_profiles_store()
        if self.auto_save_var.get():
            self._flash_status("Auto save enabled.")
        else:
            self._flash_status("Auto save disabled.")

    def clear_profiles(self):
        if not messagebox.askyesno(
                "Clear profiles", "Remove all profiles except the current settings as 'Default'?",
                parent=self.root):
            return
        self.profiles = {'Default': self.get_settings_dict()}
        self.active_profile_name = 'Default'
        self.save_profiles_store()
        self.refresh_profile_list()
        self._flash_status("Profiles cleared.")

    def download_profiles(self):
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Download Profiles", defaultextension=".json",
            filetypes=[("JSON file", "*.json"), ("All files", "*.*")],
            initialfile="autoclicker_profiles.json")
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'version': 1, 'active': self.active_profile_name, 'profiles': self.profiles},
                           f, indent=2)
        except Exception as exc:
            messagebox.showerror("Download failed", f"Could not save the file:\n{exc}", parent=self.root)
            return
        messagebox.showinfo("Download", "Profiles saved successfully.", parent=self.root)

    def import_profiles(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Import Profiles", filetypes=[("JSON file", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Import failed", f"Could not read the file:\n{exc}", parent=self.root)
            return

        imported = data.get('profiles') if isinstance(data, dict) else None
        if not isinstance(imported, dict) or not imported:
            messagebox.showerror("Import failed", "This file doesn't contain valid profiles.", parent=self.root)
            return

        replace = messagebox.askyesno(
            "Import", f"Found {len(imported)} profile(s).\n\nYes = replace all\nNo = merge with current",
            parent=self.root)
        self.profiles = imported if replace else {**self.profiles, **imported}
        active = data.get('active')
        self.active_profile_name = active if active in self.profiles else next(iter(self.profiles))
        self.apply_settings_dict(self.profiles[self.active_profile_name])
        self._reregister_all_hotkeys()
        self.save_profiles_store()
        self.refresh_profile_list()
        self._flash_status("Profiles imported.")

    def create_interval_row(self, parent, title):
        frame = tk.Frame(parent, bg=COLOR_CARD)
        frame.pack(fill="x", pady=(0, 4))

        ttk.Label(frame, text=title + ":", font=("Segoe UI", 9)).grid(
            row=0, column=0, columnspan=8, sticky="w", pady=(0, 4))

        ttk.Label(frame, text="Hours").grid(row=1, column=0, padx=2)
        ttk.Label(frame, text="Minutes").grid(row=1, column=2, padx=2)
        ttk.Label(frame, text="Seconds").grid(row=1, column=4, padx=2)
        ttk.Label(frame, text="Milliseconds").grid(row=1, column=6, padx=2)

        entries = {}
        for key, col, width, default in (('h', 0, 5, "0"), ('m', 2, 5, "0"),
                                          ('s', 4, 5, "0"), ('ms', 6, 6, "100")):
            ent = ttk.Entry(frame, width=width, justify="right")
            ent.insert(0, default)
            ent.grid(row=2, column=col, padx=2)
            entries[key] = ent

        rand_var = tk.BooleanVar(value=False)
        rand_chk = ttk.Checkbutton(frame, text="Random interval +/-", variable=rand_var)
        rand_chk.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

        rand_ent = ttk.Entry(frame, width=6, justify="right")
        rand_ent.insert(0, "20")
        rand_ent.grid(row=3, column=4, padx=2, pady=(6, 0))
        ttk.Label(frame, text="ms").grid(row=3, column=5, sticky="w", pady=(6, 0))

        return {'h': entries['h'], 'm': entries['m'], 's': entries['s'], 'ms': entries['ms'],
                'rand_var': rand_var, 'rand_ms': rand_ent, 'rand_chk': rand_chk}

    def on_click_max_speed_toggle(self):
        state = "normal" if self.click_max_speed_var.get() else "disabled"
        try:
            self.click_max_cps_entry.configure(state=state)
        except Exception:
            pass

    def on_press_max_speed_toggle(self):
        state = "normal" if self.press_max_speed_var.get() else "disabled"
        try:
            self.press_max_pps_entry.configure(state=state)
        except Exception:
            pass

    def update_rate_labels(self):
        try:
            self.click_cps_label.config(text=f"Current CPS: {self.click_rate_counter.rate():.1f}")
        except Exception:
            pass
        try:
            self.press_pps_label.config(text=f"Current PPS: {self.press_rate_counter.rate():.1f}")
        except Exception:
            pass
        self.root.after(150, self.update_rate_labels)

    def _on_global_click(self, event):
        try:
            cls = event.widget.winfo_class()
        except Exception:
            return
        if cls in BACKGROUND_WIDGET_CLASSES:
            try:
                self.root.focus_set()
            except Exception:
                pass


    def _fire_clicks(self, btn_type, clicks):
        """Perform `clicks` clicks (1 = single, 2 = double, 3 = triple) as
        distinct press/release events with a small gap between them, so
        Double/Triple click type is actually recognized as such by the
        target application instead of just firing clicks as fast as
        possible and hoping the OS coalesces them correctly."""
        for i in range(clicks):
            mouse.click(button=btn_type)
            if i < clicks - 1:
                time.sleep(MULTI_CLICK_GAP_S)

    def _safe_ui_after(self, callback):
        """Schedule `callback` on the Tk main loop via root.after(0, ...),
        but do nothing if the window is already gone. run_clicker/
        run_presser/run_playback call this from their `finally` blocks to
        resync UI state - if the user closes the app while one of them is
        still running, that call could otherwise land after root.destroy()
        and raise a TclError from a background thread (visible as a stray
        error in the console right when the window closes)."""
        try:
            if self.root.winfo_exists():
                self.root.after(0, callback)
        except Exception:
            pass

    def _flat_button(self, parent, text, command, width=10, **kwargs):
        """Shared factory for the plain flat/idle-styled buttons used all
        over the UI (Add Action, Delete, Edit, Clear, Download, Import,
        Pick, Set Hotkey, ...). Centralizing the style here means a future
        look change only needs editing in one place, and removes ~6 lines
        of repeated kwargs per button call-site."""
        opts = dict(relief="flat", bg=COLOR_BTN_IDLE, activebackground=COLOR_BTN_IDLE_ACTIVE,
                    fg=COLOR_TEXT, bd=1, cursor="hand2", width=width,
                    takefocus=0, highlightthickness=0)
        opts.update(kwargs)
        return tk.Button(parent, text=text, command=command, **opts)

    def _set_toggle_running_style(self, btn, running):
        """Apply the Start/Stop color scheme to a toggle button. Used by
        toggle_clicker/toggle_presser/toggle_recording/toggle_playback and
        by the worker threads' `finally` blocks when they resync the UI
        after finishing on their own."""
        if running:
            btn.config(bg=COLOR_STOP, fg="white", activebackground=COLOR_STOP_ACTIVE,
                       activeforeground="white")
        else:
            btn.config(bg=COLOR_START, fg=COLOR_TEXT, activebackground=COLOR_START_ACTIVE,
                       activeforeground=COLOR_TEXT)

    def _add_save_cancel_buttons(self, parent, row, on_ok, on_cancel):
        btn_row = tk.Frame(parent, bg=COLOR_CARD)
        btn_row.grid(row=row, column=0, columnspan=2, pady=(6, 10))
        tk.Button(btn_row, text="Save", command=on_ok, width=8, relief="flat",
                  bg=COLOR_START, activebackground=COLOR_START_ACTIVE, fg=COLOR_TEXT, bd=1,
                  cursor="hand2", takefocus=0, highlightthickness=0).pack(side="left", padx=4)
        tk.Button(btn_row, text="Cancel", command=on_cancel, width=8, relief="flat",
                  bg=COLOR_BTN_IDLE, activebackground=COLOR_BTN_IDLE_ACTIVE, fg=COLOR_TEXT, bd=1,
                  cursor="hand2", takefocus=0, highlightthickness=0).pack(side="left", padx=4)
        return btn_row

    def create_hotkey_and_toggle_row(self, parent, default_hotkey, toggle_command, action_label, hotkey_which,
                                      running_attr):
        row = tk.Frame(parent, bg=COLOR_CARD)
        row.pack(fill="x", pady=(8, 0))

        ttk.Label(row, text="Hotkey:").pack(side="left")
        hotkey_entry = ttk.Entry(row, width=10, justify="center", state="readonly")
        hotkey_entry.pack(side="left", padx=(4, 4))
        hotkey_entry.configure(state="normal")
        hotkey_entry.insert(0, default_hotkey)
        hotkey_entry.configure(state="readonly")

        set_btn = self._flat_button(row, "Set Hotkey", lambda: self.start_hotkey_capture(hotkey_which), width=10)
        set_btn.pack(side="left", padx=(0, 10))

        toggle_btn = tk.Button(row, text=f"Start {action_label} ({default_hotkey.upper()})",
                                command=toggle_command, bg=COLOR_START, fg=COLOR_TEXT,
                                font=("Segoe UI", 9, "bold"), relief="flat",
                                activebackground=COLOR_START_ACTIVE, activeforeground=COLOR_TEXT, bd=1,
                                width=20, pady=4, cursor="hand2", takefocus=0, highlightthickness=0)
        toggle_btn.pack(side="right", fill="x", expand=True)

        self.hotkey_specs[hotkey_which] = {
            'entry': hotkey_entry,
            'btn': toggle_btn,
            'toggle': toggle_command,
            'running_attr': running_attr,
            'label': action_label,
            'registered': None,
            'registered_handle': None,
        }

        return hotkey_entry, toggle_btn

    def start_hotkey_capture(self, which):
        if self.capturing_hotkey_for is not None:
            return
        if not _INPUT_LIBS_READY.is_set():
            self._flash_status("Keyboard library still loading, try again in a moment...")
            return

        self.capturing_hotkey_for = which
        entry = self.hotkey_specs[which]['entry']
        self._hotkey_capture_prev_value = entry.get()
        self._set_entry_text(entry, "Press a key... (Esc to cancel)", readonly=True)

        try:
            # Reuse one persistent bound method for every capture instead of
            # defining a fresh closure each time start_hotkey_capture runs.
            # A brand-new closure per click means every closure keeps its own
            # reference to `self` and `which` alive for as long as the
            # keyboard library holds it in its internal hook list; if a
            # teardown ever fails to unhook (e.g. a swallowed exception, or
            # the window closing mid-capture), each leftover closure is a
            # small permanent leak that also keeps firing on every keypress.
            # A single stable callback means there is at most ever one hook
            # object to leak, and it can't multiply across capture attempts.
            self._hotkey_capture_hook = keyboard.hook(self._on_hotkey_capture_key_event, suppress=False)
        except Exception as e:
            self.capturing_hotkey_for = None
            self._set_entry_text(entry, self._hotkey_capture_prev_value, readonly=True)
            self._flash_status(f"Could not capture key (try running the app as Administrator): {e}")
            return

        self._hotkey_capture_timeout_id = self.root.after(
            8000, lambda: self._cancel_hotkey_capture(which, timed_out=True))

    def _on_hotkey_capture_key_event(self, event):
        # Single persistent hook callback shared by every hotkey-capture
        # attempt (see comment in start_hotkey_capture). It reads `which`
        # from current state rather than from a per-call closure variable.
        try:
            if event.event_type != "down":
                return
            which = self.capturing_hotkey_for
            if which is None:
                return
            self.root.after(0, lambda w=which, name=event.name: self._resolve_hotkey_capture(w, name))
        except Exception:
            pass

    def _resolve_hotkey_capture(self, which, key_name):
        if self.capturing_hotkey_for != which:
            return
        if key_name == "esc":
            self._cancel_hotkey_capture(which, timed_out=False)
            return
        self._teardown_hotkey_capture_hook()
        entry = self.hotkey_specs[which]['entry']
        self._set_entry_text(entry, key_name, readonly=True)
        self.capturing_hotkey_for = None
        self._register_hotkey(which)
        self.refresh_toggle_button_label(which)
        self._flash_status(f"New hotkey: {key_name.upper()}")

    def _cancel_hotkey_capture(self, which, timed_out=False):
        if self.capturing_hotkey_for != which:
            return
        self._teardown_hotkey_capture_hook()
        entry = self.hotkey_specs[which]['entry']
        self._set_entry_text(entry, self._hotkey_capture_prev_value or "", readonly=True)
        self.capturing_hotkey_for = None
        self.refresh_toggle_button_label(which)
        if timed_out:
            self._flash_status("Timed out - keeping the previous hotkey. Try running the app as Administrator if key capture still doesn't work.")
        else:
            self._flash_status("Hotkey setup cancelled")

    def _teardown_hotkey_capture_hook(self):
        if self._hotkey_capture_timeout_id is not None:
            try:
                self.root.after_cancel(self._hotkey_capture_timeout_id)
            except Exception:
                pass
            self._hotkey_capture_timeout_id = None
        if self._hotkey_capture_hook is not None:
            try:
                keyboard.unhook(self._hotkey_capture_hook)
            except Exception:
                # Fall back to unhooking by the bound method itself in case
                # the stored reference didn't match what the library indexed
                # internally - belt and suspenders so the hook can never be
                # left dangling (and leaking) after this call returns.
                try:
                    keyboard.unhook(self._on_hotkey_capture_key_event)
                except Exception:
                    pass
            self._hotkey_capture_hook = None

    def finish_hotkey_capture(self, which, key_name):
        self._resolve_hotkey_capture(which, key_name)

    def refresh_toggle_button_label(self, which):
        spec = self.hotkey_specs[which]
        running = getattr(self, spec['running_attr'])
        hotkey = spec['entry'].get().strip().upper() or "?"
        label = spec['label']
        btn = spec['btn']

        if running:
            btn.config(text=f"Stop {label} ({hotkey})")
        else:
            btn.config(text=f"Start {label} ({hotkey})")

    def start_pick_location(self, x_entry=None, y_entry=None, on_done=None):
        if x_entry is None:
            x_entry = self.x_display
        if y_entry is None:
            y_entry = self.y_display

        overlay = tk.Toplevel(self.root)
        overlay.attributes("-fullscreen", True)
        try:
            overlay.attributes("-alpha", 0.35)
        except tk.TclError:
            pass
        try:
            overlay.attributes("-topmost", True)
        except tk.TclError:
            pass
        overlay.configure(bg="black")
        overlay.config(cursor="crosshair")

        hint = tk.Label(overlay, text="Click anywhere to set the position  \u2022  Press ESC to cancel",
                         bg="black", fg="white", font=("Segoe UI", 12, "bold"))
        hint.place(relx=0.5, rely=0.05, anchor="n")

        def finish():
            overlay.destroy()
            if on_done is not None:
                on_done()

        def on_click(event):
            x, y = event.x_root, event.y_root
            x_entry.delete(0, tk.END)
            x_entry.insert(0, str(x))
            y_entry.delete(0, tk.END)
            y_entry.insert(0, str(y))
            finish()

        def on_cancel(event=None):
            finish()

        overlay.bind("<Button-1>", on_click)
        overlay.bind("<Escape>", on_cancel)
        overlay.focus_force()

    def get_total_interval(self, vars_dict):
        try:
            h = float(vars_dict['h'].get() or 0)
            m = float(vars_dict['m'].get() or 0)
            s = float(vars_dict['s'].get() or 0)
            ms = float(vars_dict['ms'].get() or 0)
            total_ms = (h * 3600 + m * 60 + s) * 1000 + ms
        except ValueError:
            total_ms = 100.0

        if vars_dict['rand_var'].get():
            try:
                rand_val = float(vars_dict['rand_ms'].get() or 0)
                total_ms += random.uniform(-rand_val, rand_val)
            except ValueError:
                pass

        if total_ms < 1:
            total_ms = 1
        return total_ms / 1000.0

    def get_effective_interval(self, vars_dict, max_speed_enabled, max_rate_entry):
        if max_speed_enabled:
            try:
                max_rate = float(max_rate_entry.get() or 0)
            except ValueError:
                max_rate = 0
            if max_rate > 0:
                interval = 1.0 / max_rate
                if vars_dict.get('rand_var') is not None and vars_dict['rand_var'].get():
                    try:
                        rand_val = float(vars_dict['rand_ms'].get() or 0) / 1000.0
                        interval += random.uniform(-rand_val, rand_val)
                    except ValueError:
                        pass
                return max(interval, 0.0005)
        return self.get_total_interval(vars_dict)

    def _interruptible_sleep(self, duration, running_attr):
        end_time = time.time() + max(duration, 0)
        while True:
            remaining = end_time - time.time()
            if remaining <= 0:
                return True
            if not getattr(self, running_attr):
                return False
            time.sleep(min(0.05, remaining))

    def _interruptible_sleep_event(self, duration, stop_event):
        """Same as _interruptible_sleep, but driven by a per-thread
        threading.Event instead of a shared attribute. Used by
        run_clicker/run_presser so that an older, already-stopped
        generation's stop signal can never affect a newer thread that
        happens to share the same running_attr name.

        This is the hottest wait in the app - it runs once per click/press
        iteration, so at high CPS it fires many times a second. Event.wait
        blocks natively and wakes the instant stop_event is set (or the
        timeout elapses), instead of the old polling loop that woke up to
        20x/sec on a bare time.sleep(0.05) just to re-check the clock and
        the flag. That polling was both less responsive (up to 50ms of
        stop-latency) and busier on CPU than a single native wait call."""
        return not stop_event.wait(max(duration, 0))

    def _set_entry_text(self, entry, value, readonly=False):
        try:
            if readonly:
                entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
            if readonly:
                entry.configure(state="readonly")
        except Exception:
            pass

    def _interval_settings(self, vars_dict):
        return {
            'h': vars_dict['h'].get(),
            'm': vars_dict['m'].get(),
            's': vars_dict['s'].get(),
            'ms': vars_dict['ms'].get(),
            'rand': bool(vars_dict['rand_var'].get()),
            'rand_ms': vars_dict['rand_ms'].get(),
        }

    def _apply_interval_settings(self, vars_dict, data):
        if not data:
            return
        for key in ('h', 'm', 's', 'ms', 'rand_ms'):
            if key in data:
                self._set_entry_text(vars_dict[key], data[key])
        if 'rand' in data:
            vars_dict['rand_var'].set(bool(data['rand']))

    def get_settings_dict(self):
        data = {'version': 1}

        try:
            data['click'] = {
                'interval': self._interval_settings(self.click_int_vars),
                'hold_interval': self._interval_settings(self.click_hold_vars),
                'mouse_button': self.mouse_btn_var.get(),
                'click_type': self.click_type_var.get(),
                'action_mode': self.click_action_mode_var.get(),
                'smart_click': bool(self.smart_click_var.get()),
                'max_speed_enabled': bool(self.click_max_speed_var.get()),
                'max_cps': self.click_max_cps_entry.get(),
                'repeat_mode': self.repeat_mode_var.get(),
                'repeat_count': self.repeat_entry.get(),
                'pos_mode': self.pos_mode_var.get(),
                'x': self.x_display.get(),
                'y': self.y_display.get(),
                'hotkey': self.click_hotkey_entry.get(),
            }
        except Exception:
            pass

        try:
            data['press'] = {
                'interval': self._interval_settings(self.press_int_vars),
                'hold_interval': self._interval_settings(self.press_hold_vars),
                'key': self.press_key_var.get(),
                'action_mode': self.press_action_mode_var.get(),
                'max_speed_enabled': bool(self.press_max_speed_var.get()),
                'max_pps': self.press_max_pps_entry.get(),
                'repeat_mode': self.press_repeat_mode_var.get(),
                'repeat_count': self.press_repeat_entry.get(),
                'hotkey': self.press_hotkey_entry.get(),
            }
        except Exception:
            pass

        try:
            data['record'] = {
                'record_moves': bool(self.record_moves_var.get()),
                'record_keys': bool(self.record_keys_var.get()),
                'move_interval_ms': self.record_move_interval_entry.get(),
                'hotkey': self.record_hotkey_entry.get(),
            }
        except Exception:
            pass

        try:
            data['playback'] = {
                'repeat_mode': self.playback_repeat_mode_var.get(),
                'repeat_count': self.playback_repeat_entry.get(),
                'speed': self.playback_speed_entry.get(),
                'hotkey': self.playback_hotkey_entry.get(),
            }
        except Exception:
            pass

        return data

    def apply_settings_dict(self, data):
        if not isinstance(data, dict):
            return

        click = data.get('click') or {}
        try:
            self._apply_interval_settings(self.click_int_vars, click.get('interval'))
            self._apply_interval_settings(self.click_hold_vars, click.get('hold_interval'))
            if 'mouse_button' in click:
                self.mouse_btn_var.set(click['mouse_button'])
            if 'click_type' in click:
                self.click_type_var.set(click['click_type'])
            if 'action_mode' in click:
                self.click_action_mode_var.set(click['action_mode'])
            if 'smart_click' in click:
                self.smart_click_var.set(bool(click['smart_click']))
            if 'max_speed_enabled' in click:
                self.click_max_speed_var.set(bool(click['max_speed_enabled']))
            if 'max_cps' in click:
                self._set_entry_text(self.click_max_cps_entry, click['max_cps'])
            if 'repeat_mode' in click:
                self.repeat_mode_var.set(click['repeat_mode'])
            if 'repeat_count' in click:
                self._set_entry_text(self.repeat_entry, click['repeat_count'])
            if 'pos_mode' in click:
                self.pos_mode_var.set(click['pos_mode'])
            if 'x' in click:
                self._set_entry_text(self.x_display, click['x'])
            if 'y' in click:
                self._set_entry_text(self.y_display, click['y'])
            if click.get('hotkey'):
                self._set_entry_text(self.click_hotkey_entry, click['hotkey'], readonly=True)
            self.on_click_max_speed_toggle()
            self.refresh_toggle_button_label("click")
        except Exception:
            pass

        press = data.get('press') or {}
        try:
            self._apply_interval_settings(self.press_int_vars, press.get('interval'))
            self._apply_interval_settings(self.press_hold_vars, press.get('hold_interval'))
            if 'key' in press:
                self.press_key_var.set(press['key'])
            if 'action_mode' in press:
                self.press_action_mode_var.set(press['action_mode'])
            if 'max_speed_enabled' in press:
                self.press_max_speed_var.set(bool(press['max_speed_enabled']))
            if 'max_pps' in press:
                self._set_entry_text(self.press_max_pps_entry, press['max_pps'])
            if 'repeat_mode' in press:
                self.press_repeat_mode_var.set(press['repeat_mode'])
            if 'repeat_count' in press:
                self._set_entry_text(self.press_repeat_entry, press['repeat_count'])
            if press.get('hotkey'):
                self._set_entry_text(self.press_hotkey_entry, press['hotkey'], readonly=True)
            self.on_press_max_speed_toggle()
            self.refresh_toggle_button_label("press")
        except Exception:
            pass

        record = data.get('record') or {}
        try:
            if 'record_moves' in record:
                self.record_moves_var.set(bool(record['record_moves']))
            if 'record_keys' in record:
                self.record_keys_var.set(bool(record['record_keys']))
            if record.get('move_interval_ms'):
                self._set_entry_text(self.record_move_interval_entry, str(record['move_interval_ms']))
            if record.get('hotkey'):
                self._set_entry_text(self.record_hotkey_entry, record['hotkey'], readonly=True)
            self.refresh_toggle_button_label("record")
        except Exception:
            pass

        playback = data.get('playback') or {}
        try:
            if 'repeat_mode' in playback:
                self.playback_repeat_mode_var.set(playback['repeat_mode'])
            if 'repeat_count' in playback:
                self._set_entry_text(self.playback_repeat_entry, playback['repeat_count'])
            if 'speed' in playback:
                self._set_entry_text(self.playback_speed_entry, playback['speed'])
            if playback.get('hotkey'):
                self._set_entry_text(self.playback_hotkey_entry, playback['hotkey'], readonly=True)
            self.refresh_toggle_button_label("playback")
        except Exception:
            pass

    def _flash_status(self, text):
        try:
            self.status_msg_label.config(text=text)
        except Exception:
            pass

    def save_profiles_store(self):
        """Persist the full profile store (all named profiles + which one is
        currently active + the Auto save toggle) to disk. Nothing else is
        written automatically from editing fields; without Auto save on,
        the user must explicitly hit New/Save/Apply/Rename/Delete."""
        try:
            data = {
                'version': 1,
                'active': self.active_profile_name,
                'profiles': self.profiles,
                'auto_save': bool(self.auto_save_var.get()) if hasattr(self, 'auto_save_var') else False,
            }
            with open(self.profiles_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, separators=(',', ':'))
        except Exception:
            pass

    def load_profiles_store(self):
        """Load the named-profile store from disk. If it doesn't exist yet
        (first run after upgrading), migrate the old single-file
        autoclicker_settings.json (if present) into a "Default" profile so
        existing users don't lose their settings. If neither file exists,
        seed a "Default" profile from whatever the UI defaults are."""
        data = None
        try:
            with open(self.profiles_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = None

        if isinstance(data, dict) and isinstance(data.get('profiles'), dict) and data['profiles']:
            self.profiles = data['profiles']
            active = data.get('active')
            self.active_profile_name = active if active in self.profiles else next(iter(self.profiles))
            self.auto_save_var.set(bool(data.get('auto_save', False)))
        else:
            migrated = None
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    migrated = json.load(f)
            except Exception:
                migrated = None
            self.profiles = {'Default': migrated if isinstance(migrated, dict) else self.get_settings_dict()}
            self.active_profile_name = 'Default'
            self.save_profiles_store()

        try:
            self.apply_settings_dict(self.profiles[self.active_profile_name])
        except Exception:
            pass
        self._reregister_all_hotkeys()
        self.refresh_profile_list()

    def on_close(self):
        try:
            self._teardown_hotkey_capture_hook()
            self.capturing_hotkey_for = None
        except Exception:
            pass
        try:
            # Signal any running Auto Clicker / Key Presser / Playback loop
            # to stop right away, before the window goes away. Without
            # this, closing the app while one of them was running left the
            # background thread looping for up to one more interval and
            # simulating clicks/keypresses after the window had already
            # closed, then hitting the destroyed root in its `finally`
            # block (now harmless thanks to _safe_ui_after, but still
            # pointless extra clicking/typing in the meantime).
            if self.clicker_running and getattr(self, 'clicker_stop_event', None) is not None:
                self.clicker_stop_event.set()
            if self.presser_running and getattr(self, 'presser_stop_event', None) is not None:
                self.presser_stop_event.set()
            self.playing = False
        except Exception:
            pass
        try:
            # Make sure no OS-level hooks are left running after the window
            # is gone: the recording hook (mouse.hook/keyboard.hook), every
            # registered hotkey (keyboard.add_hotkey), and any leftover
            # hotkey-capture hook. Closing the app mid-recording or with a
            # hotkey still bound previously left these alive in the
            # background at the OS level even after the process's own
            # window/threads were torn down.
            if keyboard is not None:
                keyboard.unhook_all()
            if mouse is not None:
                mouse.unhook_all()
        except Exception:
            pass
        try:
            self._autosave_active_profile()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def toggle_clicker(self):
        if not self.clicker_running:
            # Always spin up a fresh thread right away, even if a previous
            # one is still winding down in the background after a recent
            # Stop. Give it its own generation number + stop_event so it
            # runs fully independently: the old thread will keep clicking
            # until its own stop_event fires, then quietly exit without
            # touching the button/status (see the `gen` check in
            # run_clicker's `finally` block below).
            self.clicker_gen += 1
            gen = self.clicker_gen
            stop_event = threading.Event()
            self.clicker_stop_event = stop_event
            self.clicker_running = True
            self._set_toggle_running_style(self.click_toggle_btn, True)
            self.refresh_toggle_button_label("click")
            self.clicker_thread = threading.Thread(target=self.run_clicker, args=(gen, stop_event), daemon=True)
            self.clicker_thread.start()
        else:
            # Signal only the currently-active generation to stop, and
            # update the UI immediately. No blocking join() here - the
            # thread will exit on its own time and, since it's still the
            # active generation, will finish resyncing the UI itself.
            self.clicker_running = False
            if self.clicker_stop_event is not None:
                self.clicker_stop_event.set()
            self._set_toggle_running_style(self.click_toggle_btn, False)
            self.refresh_toggle_button_label("click")
        self.update_status()

    def toggle_presser(self):
        if not self.presser_running:
            # See toggle_clicker for why we always start fresh here instead
            # of waiting on/blocking a previous thread.
            self.presser_gen += 1
            gen = self.presser_gen
            stop_event = threading.Event()
            self.presser_stop_event = stop_event
            self.presser_running = True
            self._set_toggle_running_style(self.press_toggle_btn, True)
            self.refresh_toggle_button_label("press")
            self.presser_thread = threading.Thread(target=self.run_presser, args=(gen, stop_event), daemon=True)
            self.presser_thread.start()
        else:
            self.presser_running = False
            if self.presser_stop_event is not None:
                self.presser_stop_event.set()
            self._set_toggle_running_style(self.press_toggle_btn, False)
            self.refresh_toggle_button_label("press")
        self.update_status()

    def toggle_recording(self):
        if self.playing:
            return
        if not self.recording:
            _INPUT_LIBS_READY.wait()
            self.recording = True
            self.recorded_events = []
            self.record_start_time = time.time()
            self._keys_held = set()
            self._buttons_held = set()
            self._last_move_record_wall = 0.0
            self._refresh_recorded_list()
            try:
                mouse.hook(self._on_mouse_event)
            except Exception:
                pass
            try:
                keyboard.hook(self._on_keyboard_event)
            except Exception:
                pass
            self._set_toggle_running_style(self.record_toggle_btn, True)
            self.refresh_toggle_button_label("record")
        else:
            self.recording = False
            try:
                mouse.unhook(self._on_mouse_event)
            except Exception:
                pass
            try:
                keyboard.unhook(self._on_keyboard_event)
            except Exception:
                pass
            self._close_open_hold_events(time.time() - self.record_start_time)
            self._keys_held = set()
            self._buttons_held = set()
            self._set_toggle_running_style(self.record_toggle_btn, False)
            self.refresh_toggle_button_label("record")
            self._refresh_recorded_list()
        self.update_status()

    def toggle_playback(self):
        if self.recording:
            return
        if not self.playing:
            if not self.recorded_events:
                return
            if self.playback_thread is not None and self.playback_thread.is_alive():
                return
            self.playing = True
            self._set_toggle_running_style(self.playback_toggle_btn, True)
            self.refresh_toggle_button_label("playback")
            self.playback_thread = threading.Thread(target=self.run_playback, daemon=True)
            self.playback_thread.start()
        else:
            self.playing = False
            if self.playback_thread is not None:
                self.playback_thread.join(timeout=2.0)
                self.playback_thread = None
            self._set_toggle_running_style(self.playback_toggle_btn, False)
            self.refresh_toggle_button_label("playback")
        self.update_status()

    def clear_recorded_events(self):
        if self.recording or self.playing:
            return
        # Drop every reference to the old recorded data (list contents, the
        # tree-row mapping, and the tree widget's own items) before asking
        # for a garbage collection, so a big recording's memory is actually
        # freed right away instead of lingering until the 5-minute memory
        # watchdog happens to run.
        self.recorded_events.clear()
        self._record_row_map.clear()
        self.record_tree.delete(*self.record_tree.get_children())
        self._refresh_recorded_list()
        gc.collect()

    def _download_recorded_events(self):
        if self.recording or self.playing:
            return
        if not self.recorded_events:
            messagebox.showinfo("Download", "There are no recorded actions to download.", parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Download Recorded Actions",
            defaultextension=".json",
            filetypes=[("JSON file", "*.json"), ("All files", "*.*")],
            initialfile="recorded_actions.json",
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'recorded_events': self.recorded_events}, f, indent=2)
        except Exception as exc:
            messagebox.showerror("Download failed", f"Could not save the file:\n{exc}", parent=self.root)
            return
        messagebox.showinfo("Download", "Recorded actions saved successfully.", parent=self.root)

    def _import_recorded_events(self):
        if self.recording or self.playing:
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Import Recorded Actions",
            filetypes=[("JSON file", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Import failed", f"Could not read the file:\n{exc}", parent=self.root)
            return

        events = data.get('recorded_events') if isinstance(data, dict) else data
        if not isinstance(events, list):
            messagebox.showerror("Import failed", "This file doesn't contain valid recorded actions.",
                                  parent=self.root)
            return

        valid_types = {'key', 'button', 'move', 'wheel'}
        cleaned = []
        for ev in events:
            if isinstance(ev, dict) and ev.get('type') in valid_types and 'time' in ev:
                cleaned.append(ev)
        if not cleaned:
            messagebox.showerror("Import failed", "This file doesn't contain valid recorded actions.",
                                  parent=self.root)
            return

        replace = messagebox.askyesno(
            "Import",
            f"Found {len(cleaned)} action(s) in this file.\n\n"
            "Yes = replace the current list\nNo = add to the current list",
            parent=self.root,
        )
        if replace:
            self.recorded_events = cleaned
        else:
            self.recorded_events.extend(cleaned)
        self.recorded_events.sort(key=lambda e: e['time'])
        self._refresh_recorded_list()

    def _close_open_hold_events(self, stop_time):
        open_holds = {}
        for ev in self.recorded_events:
            if ev['type'] == 'key':
                hold_id = ('key', ev['name'])
            elif ev['type'] == 'button':
                hold_id = ('button', ev['button'])
            else:
                continue
            if ev['action'] == 'down':
                open_holds[hold_id] = True
            elif ev['action'] == 'up':
                open_holds.pop(hold_id, None)

        for kind, identifier in open_holds:
            if kind == 'key':
                self.recorded_events.append({'type': 'key', 'time': stop_time, 'name': identifier, 'action': 'up'})
            else:
                self.recorded_events.append(
                    {'type': 'button', 'time': stop_time, 'button': identifier, 'action': 'up'})

    def _get_move_record_interval_seconds(self):
        try:
            ms = int(float(self.record_move_interval_entry.get().strip()))
        except (ValueError, AttributeError):
            ms = DEFAULT_MOVE_RECORD_INTERVAL_MS
        if ms < MIN_MOVE_RECORD_INTERVAL_MS:
            ms = MIN_MOVE_RECORD_INTERVAL_MS
        return ms / 1000.0

    def _on_mouse_event(self, event):
        if not self.recording:
            return
        t = time.time() - self.record_start_time
        appended = False
        if isinstance(event, mouse.ButtonEvent):
            button = event.button
            action = event.event_type
            if action == 'down':
                # Ignore duplicate "down" events for a button that is already
                # being held, so a single physical hold always maps to exactly
                # one down + one up in recorded_events (see _on_keyboard_event
                # for why this matters).
                if button in self._buttons_held:
                    return
                self._buttons_held.add(button)
            elif action == 'up':
                self._buttons_held.discard(button)
            self.recorded_events.append(
                {'type': 'button', 'time': t, 'button': button, 'action': action})
            appended = True
        elif isinstance(event, mouse.MoveEvent):
            if self.record_moves_var.get():
                # Raw mouse-move events can fire hundreds of times per
                # second; recording every single one bloats recorded_events,
                # spams the RAM, and makes the Recorded Actions list
                # (Treeview refresh) stutter. Sample at a user-configurable
                # rate instead (default 100ms = 10 FPS).
                now_wall = time.time()
                if now_wall - self._last_move_record_wall >= self._get_move_record_interval_seconds():
                    self._last_move_record_wall = now_wall
                    self.recorded_events.append({'type': 'move', 'time': t, 'x': event.x, 'y': event.y})
                    appended = True
        elif isinstance(event, mouse.WheelEvent):
            self.recorded_events.append({'type': 'wheel', 'time': t, 'delta': event.delta})
            appended = True
        if appended:
            self._schedule_count_label_update()

    def _on_keyboard_event(self, event):
        if not self.recording or not self.record_keys_var.get():
            return
        skip_names = set()
        for which in ('record', 'playback'):
            try:
                skip_names.add(self.hotkey_specs[which]['entry'].get().strip().lower())
            except Exception:
                pass
        if event.name and event.name.lower() in skip_names:
            return

        name = event.name
        action = event.event_type
        if action == 'down':
            # Windows (and most OSes) fire many repeated "down" events while a
            # key is held down (key auto-repeat). Without filtering these out,
            # recorded_events ends up with several extra "down" entries for the
            # same key that never get paired with an "up". The list view hides
            # the extras (only the first down/up pair is shown as one "hold"
            # row), but they stay in recorded_events. Editing/renaming that row
            # only updates the pair that is actually referenced by the row, so
            # the leftover duplicate "down" events keep the OLD key name and
            # resurface as an orphan "<old key> (not released)" row after editing,
            # while the renamed key only plays back the single edited pair.
            # Dropping duplicates here fixes the issue at the source.
            if name in self._keys_held:
                return
            self._keys_held.add(name)
        elif action == 'up':
            self._keys_held.discard(name)

        t = time.time() - self.record_start_time
        self.recorded_events.append({'type': 'key', 'time': t, 'name': name, 'action': action})
        self._schedule_count_label_update()

    def _schedule_count_label_update(self):
        """Cheap, throttled feedback while recording: bump only the
        "Recorded events: N" label, never the Treeview. The Treeview is
        only ever fully rebuilt once, when recording actually stops (see
        toggle_recording) - rebuilding it on every single mouse/keyboard
        event during a long recording is what was overloading Tkinter's
        widget/canvas memory."""
        if self._count_label_update_pending:
            return
        self._count_label_update_pending = True
        self._safe_ui_after(self._flush_count_label_update)

    def _flush_count_label_update(self):
        self._count_label_update_pending = False
        if self.recording:
            self.record_count_label.config(text=f"Recorded events: {len(self.recorded_events)}")

    def _refresh_recorded_list(self):
        self.record_count_label.config(text=f"Recorded events: {len(self.recorded_events)}")
        self.record_tree.delete(*self.record_tree.get_children())

        rows = []
        open_holds = {}
        events = self.recorded_events
        n = len(events)
        i = 0

        while i < n:
            ev = events[i]
            t = ev['time']
            if ev['type'] == 'key':
                hold_id = ('key', ev['name'])
                if ev['action'] == 'down':
                    open_holds.setdefault(hold_id, (i, t))
                elif ev['action'] == 'up':
                    if hold_id in open_holds:
                        down_i, start_t = open_holds.pop(hold_id)
                        rows.append((('hold', down_i, i), f"{start_t:.2f}", "key hold",
                                     f"{ev['name']} for {t - start_t:.2f}s"))
                    else:
                        rows.append((('single', i), f"{t:.2f}", "key", f"{ev['name']} up"))
                else:
                    rows.append((('single', i), f"{t:.2f}", "key", f"{ev['name']} {ev['action']}"))
                i += 1
            elif ev['type'] == 'button':
                hold_id = ('button', ev['button'])
                if ev['action'] == 'down':
                    open_holds.setdefault(hold_id, (i, t))
                elif ev['action'] == 'up':
                    if hold_id in open_holds:
                        down_i, start_t = open_holds.pop(hold_id)
                        rows.append((('hold', down_i, i), f"{start_t:.2f}", "mouse hold",
                                     f"{ev['button']} for {t - start_t:.2f}s"))
                    else:
                        rows.append((('single', i), f"{t:.2f}", "mouse", f"{ev['button']} up"))
                else:
                    rows.append((('single', i), f"{t:.2f}", "mouse", f"{ev['button']} {ev['action']}"))
                i += 1
            elif ev['type'] == 'move':
                rows.append((('single', i), f"{t:.2f}", "move", f"({ev['x']}, {ev['y']})"))
                i += 1
            elif ev['type'] == 'wheel':
                sign = 1 if ev['delta'] >= 0 else -1
                end_i = i
                while (end_i + 1 < n and events[end_i + 1]['type'] == 'wheel'
                       and (1 if events[end_i + 1]['delta'] >= 0 else -1) == sign):
                    end_i += 1
                direction = "up" if sign > 0 else "down"
                duration = events[end_i]['time'] - t
                rows.append((('wheel_group', i, end_i), f"{t:.2f}", "wheel", f"{direction} for {duration:.2f}s"))
                i = end_i + 1
            else:
                rows.append((('single', i), f"{t:.2f}", "unknown", str(ev)))
                i += 1

        for (kind, identifier), (down_i, start_t) in open_holds.items():
            label = "key hold" if kind == "key" else "mouse hold"
            rows.append((('open_hold', down_i), f"{start_t:.2f}", label, f"{identifier} (not released)"))

        preview_limit = 300
        visible_rows = rows[:preview_limit]
        self._record_row_map = [row_key for row_key, *_ in visible_rows]
        for row_index, (_, t_str, type_str, detail_str) in enumerate(visible_rows):
            self.record_tree.insert("", tk.END, iid=str(row_index), values=(t_str, type_str, detail_str))
        if len(rows) > preview_limit:
            self.record_tree.insert("", tk.END, iid="more",
                                     values=("", "", f"... and {len(rows) - preview_limit} more"))

    def _block_column_drag(self, event):
        # Prevents the user from manually resizing a column by dragging its
        # header border — clicking on the separator region is simply ignored.
        if self.record_tree.identify_region(event.x, event.y) == "separator":
            return "break"

    def _on_record_tree_double_click(self, event):
        if self.recording or self.playing:
            return
        item = self.record_tree.identify_row(event.y)
        if item:
            self._open_event_editor(item)

    def _edit_selected_event(self):
        if self.recording or self.playing:
            return
        sel = self.record_tree.selection()
        if sel:
            self._open_event_editor(sel[0])

    def _delete_selected_event(self):
        if self.recording or self.playing:
            return
        sel = self.record_tree.selection()
        if not sel:
            return
        row_index = self._row_index_from_iid(sel[0])
        if row_index is None:
            return
        row_key = self._record_row_map[row_index]
        if row_key[0] in ("single", "open_hold"):
            indices = {row_key[1]}
        elif row_key[0] == "hold":
            indices = {row_key[1], row_key[2]}
        else:
            indices = set(range(row_key[1], row_key[2] + 1))
        self.recorded_events = [ev for i, ev in enumerate(self.recorded_events) if i not in indices]
        self._refresh_recorded_list()

    def _row_index_from_iid(self, iid):
        if iid == "more":
            return None
        try:
            row_index = int(iid)
        except ValueError:
            return None
        if row_index >= len(self._record_row_map):
            return None
        return row_index

    def _safe_float(self, raw_value, fallback):
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            return fallback

    def _safe_int(self, raw_value, fallback):
        try:
            return int(float(raw_value))
        except (TypeError, ValueError):
            return fallback

    def _prompt_fields(self, title, specs, over_widget=None):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=COLOR_CARD)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.withdraw()

        vars_map = {}
        for row, spec in enumerate(specs):
            ttk.Label(dialog, text=spec['label'] + ":").grid(row=row, column=0, sticky="w", padx=8, pady=6)
            var = tk.StringVar(value=str(spec.get('default', '')))
            if spec['type'] == 'combobox':
                widget = ttk.Combobox(dialog, textvariable=var, values=spec['values'], width=16, state="readonly")
            else:
                widget = ttk.Entry(dialog, textvariable=var, width=18)
            widget.grid(row=row, column=1, sticky="w", padx=8, pady=6)
            vars_map[spec['key']] = var

        outcome = {'ok': False}

        def on_ok():
            outcome['ok'] = True
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        self._add_save_cancel_buttons(dialog, len(specs), on_ok, on_cancel)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        if over_widget is not None:
            self._position_dialog_over_widget(dialog, over_widget)
        dialog.deiconify()
        dialog.grab_set()
        self.root.wait_window(dialog)

        if not outcome['ok']:
            return None
        return {key: var.get() for key, var in vars_map.items()}

    def _resize_record_tree_columns(self, event=None):
        total_width = self.record_tree.winfo_width()
        if total_width < 30:
            return
        time_w = int(total_width * 0.30)
        type_w = int(total_width * 0.30)
        detail_w = total_width - time_w - type_w
        self._time_col_width = time_w
        self._type_col_width = type_w
        self._detail_col_width = detail_w
        self.record_tree.column("time", width=time_w)
        self.record_tree.column("type", width=type_w)
        self.record_tree.column("detail", width=detail_w)
        self._record_tree_divider1.place(in_=self.record_tree, x=time_w, y=0, relheight=1)
        self._record_tree_divider2.place(in_=self.record_tree, x=time_w + type_w, y=0, relheight=1)

    def _add_action_field_specs(self, category, last_t):
        if category == "Key press":
            return [
                {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{last_t:.3f}"},
                {'key': 'name', 'label': 'Key', 'type': 'combobox', 'values': ALL_KEYS, 'default': "space"},
            ]
        if category == "Key hold":
            return [
                {'key': 'time', 'label': 'Start time (s)', 'type': 'entry', 'default': f"{last_t:.3f}"},
                {'key': 'duration', 'label': 'Duration (s)', 'type': 'entry', 'default': "1.0"},
                {'key': 'name', 'label': 'Key', 'type': 'combobox', 'values': ALL_KEYS, 'default': "space"},
            ]
        if category == "Mouse click":
            return [
                {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{last_t:.3f}"},
                {'key': 'button', 'label': 'Button', 'type': 'combobox', 'values': ["left", "right", "middle"],
                 'default': "left"},
            ]
        if category == "Mouse hold":
            return [
                {'key': 'time', 'label': 'Start time (s)', 'type': 'entry', 'default': f"{last_t:.3f}"},
                {'key': 'duration', 'label': 'Duration (s)', 'type': 'entry', 'default': "1.0"},
                {'key': 'button', 'label': 'Button', 'type': 'combobox', 'values': ["left", "right", "middle"],
                 'default': "left"},
            ]
        if category == "Mouse move":
            return [
                {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{last_t:.3f}"},
            ]
        # Mouse wheel
        return [
            {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{last_t:.3f}"},
            {'key': 'direction', 'label': 'Direction', 'type': 'combobox', 'values': ["up", "down"],
             'default': "up"},
        ]

    def _position_dialog_near_widget(self, dialog, widget, gap=8):
        dialog.update_idletasks()
        dw = dialog.winfo_reqwidth()
        dh = dialog.winfo_reqheight()
        bx = widget.winfo_rootx()
        by = widget.winfo_rooty()
        bw = widget.winfo_width()
        bh = widget.winfo_height()
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()

        # Prefer just below the button; flip above if it would run off-screen.
        x = bx
        y = by + bh + gap
        if y + dh > screen_h:
            y = by - dh - gap
        if x + dw > screen_w:
            x = screen_w - dw - gap
        x = max(0, x)
        y = max(0, y)
        dialog.geometry(f"+{x}+{y}")

    def _position_dialog_over_widget(self, dialog, widget):
        dialog.update_idletasks()
        dw = dialog.winfo_reqwidth()
        dh = dialog.winfo_reqheight()
        wx = widget.winfo_rootx()
        wy = widget.winfo_rooty()
        ww = widget.winfo_width()
        wh = widget.winfo_height()
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()

        x = wx + max(0, (ww - dw) // 2)
        y = wy + max(0, (wh - dh) // 2)
        x = max(0, min(x, screen_w - dw))
        y = max(0, min(y, screen_h - dh))
        dialog.geometry(f"+{x}+{y}")

    def _prompt_add_action(self, last_t):
        categories = ["Key press", "Key hold", "Mouse click", "Mouse hold", "Mouse move", "Mouse wheel"]

        dialog = tk.Toplevel(self.root)
        dialog.title("Add Action")
        dialog.configure(bg=COLOR_CARD)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.withdraw()

        category_var = tk.StringVar(value=categories[0])
        ttk.Label(dialog, text="Action type:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        category_combo = ttk.Combobox(dialog, textvariable=category_var, values=categories,
                                       width=16, state="readonly")
        category_combo.grid(row=0, column=1, sticky="w", padx=8, pady=6)

        fields_frame = tk.Frame(dialog, bg=COLOR_CARD)
        fields_frame.grid(row=1, column=0, columnspan=2, sticky="we")

        state = {'vars': {}, 'widgets': {}}

        def do_pick_location():
            dialog.grab_release()

            def restore():
                dialog.deiconify()
                dialog.lift()
                dialog.grab_set()
                dialog.focus_force()

            self.start_pick_location(state['widgets']['x'], state['widgets']['y'], on_done=restore)

        def rebuild_fields(*_args):
            for child in fields_frame.winfo_children():
                child.destroy()
            state['vars'] = {}
            state['widgets'] = {}
            specs = self._add_action_field_specs(category_var.get(), last_t)
            for row, spec in enumerate(specs):
                ttk.Label(fields_frame, text=spec['label'] + ":").grid(
                    row=row, column=0, sticky="w", padx=8, pady=6)
                var = tk.StringVar(value=str(spec.get('default', '')))
                if spec['type'] == 'combobox':
                    widget = ttk.Combobox(fields_frame, textvariable=var, values=spec['values'],
                                           width=16, state="readonly")
                else:
                    widget = ttk.Entry(fields_frame, textvariable=var, width=18)
                widget.grid(row=row, column=1, sticky="w", padx=8, pady=6)
                state['vars'][spec['key']] = var
                state['widgets'][spec['key']] = widget

            if category_var.get() == "Mouse move":
                row = len(specs)
                ttk.Label(fields_frame, text="Position:").grid(
                    row=row, column=0, sticky="w", padx=8, pady=6)
                pos_row = tk.Frame(fields_frame, bg=COLOR_CARD)
                pos_row.grid(row=row, column=1, sticky="w", padx=8, pady=6)

                self._flat_button(pos_row, "Pick", do_pick_location, width=6).pack(side="left")
                ttk.Label(pos_row, text="X:").pack(side="left", padx=(10, 2))
                x_var = tk.StringVar(value="0")
                x_entry = ttk.Entry(pos_row, textvariable=x_var, width=6)
                x_entry.pack(side="left")
                ttk.Label(pos_row, text="Y:").pack(side="left", padx=(6, 2))
                y_var = tk.StringVar(value="0")
                y_entry = ttk.Entry(pos_row, textvariable=y_var, width=6)
                y_entry.pack(side="left")

                state['vars']['x'] = x_var
                state['vars']['y'] = y_var
                state['widgets']['x'] = x_entry
                state['widgets']['y'] = y_entry

        category_combo.bind("<<ComboboxSelected>>", rebuild_fields)
        rebuild_fields()

        outcome = {'ok': False}

        def on_ok():
            outcome['ok'] = True
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        self._add_save_cancel_buttons(dialog, 2, on_ok, on_cancel)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

        self._position_dialog_over_widget(dialog, self._record_tab)
        dialog.deiconify()
        dialog.grab_set()

        self.root.wait_window(dialog)

        if not outcome['ok']:
            return None
        result = {key: var.get() for key, var in state['vars'].items()}
        result['category'] = category_var.get()
        return result

    def _add_new_event(self):
        if self.recording or self.playing:
            return

        last_t = self.recorded_events[-1]['time'] if self.recorded_events else 0.0
        result = self._prompt_add_action(last_t)
        if result is None:
            return
        category = result['category']

        if category == "Key press":
            t = self._safe_float(result['time'], last_t)
            name = result['name'].strip() or "space"
            self.recorded_events.append({'type': 'key', 'time': t, 'name': name, 'action': 'down'})
            self.recorded_events.append({'type': 'key', 'time': t + 0.01, 'name': name, 'action': 'up'})

        elif category == "Key hold":
            t = self._safe_float(result['time'], last_t)
            dur = max(0.0, self._safe_float(result['duration'], 1.0))
            name = result['name'].strip() or "space"
            self.recorded_events.append({'type': 'key', 'time': t, 'name': name, 'action': 'down'})
            self.recorded_events.append({'type': 'key', 'time': t + dur, 'name': name, 'action': 'up'})

        elif category == "Mouse click":
            t = self._safe_float(result['time'], last_t)
            button = result['button']
            self.recorded_events.append({'type': 'button', 'time': t, 'button': button, 'action': 'down'})
            self.recorded_events.append({'type': 'button', 'time': t + 0.01, 'button': button, 'action': 'up'})

        elif category == "Mouse hold":
            t = self._safe_float(result['time'], last_t)
            dur = max(0.0, self._safe_float(result['duration'], 1.0))
            button = result['button']
            self.recorded_events.append({'type': 'button', 'time': t, 'button': button, 'action': 'down'})
            self.recorded_events.append({'type': 'button', 'time': t + dur, 'button': button, 'action': 'up'})

        elif category == "Mouse move":
            t = self._safe_float(result['time'], last_t)
            x = self._safe_int(result['x'], 0)
            y = self._safe_int(result['y'], 0)
            self.recorded_events.append({'type': 'move', 'time': t, 'x': x, 'y': y})

        else:  # Mouse wheel
            t = self._safe_float(result['time'], last_t)
            delta = 1 if result['direction'] == "up" else -1
            self.recorded_events.append({'type': 'wheel', 'time': t, 'delta': delta})

        self.recorded_events.sort(key=lambda e: e['time'])
        self._refresh_recorded_list()

    def _open_event_editor(self, iid):
        row_index = self._row_index_from_iid(iid)
        if row_index is None:
            return
        row_key = self._record_row_map[row_index]
        kind = row_key[0]

        if kind == 'single':
            ev = self.recorded_events[row_key[1]]
            if ev['type'] == 'key':
                result = self._prompt_fields("Edit Key Event", [
                    {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{ev['time']:.3f}"},
                    {'key': 'name', 'label': 'Key', 'type': 'combobox', 'values': ALL_KEYS, 'default': ev['name']},
                    {'key': 'action', 'label': 'Action', 'type': 'combobox', 'values': ["down", "up"],
                     'default': ev['action']},
                ])
                if result is None:
                    return
                ev['time'] = self._safe_float(result['time'], ev['time'])
                ev['name'] = result['name'].strip() or ev['name']
                ev['action'] = result['action']
            elif ev['type'] == 'button':
                result = self._prompt_fields("Edit Mouse Event", [
                    {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{ev['time']:.3f}"},
                    {'key': 'button', 'label': 'Button', 'type': 'combobox', 'values': ["left", "right", "middle"],
                     'default': ev['button']},
                    {'key': 'action', 'label': 'Action', 'type': 'combobox', 'values': ["down", "up", "double"],
                     'default': ev['action']},
                ])
                if result is None:
                    return
                ev['time'] = self._safe_float(result['time'], ev['time'])
                ev['button'] = result['button']
                ev['action'] = result['action']
            elif ev['type'] == 'move':
                result = self._prompt_fields("Edit Move Event", [
                    {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{ev['time']:.3f}"},
                    {'key': 'x', 'label': 'X', 'type': 'entry', 'default': ev['x']},
                    {'key': 'y', 'label': 'Y', 'type': 'entry', 'default': ev['y']},
                ])
                if result is None:
                    return
                ev['time'] = self._safe_float(result['time'], ev['time'])
                ev['x'] = self._safe_int(result['x'], ev['x'])
                ev['y'] = self._safe_int(result['y'], ev['y'])

        elif kind == 'wheel_group':
            start_i, end_i = row_key[1], row_key[2]
            group = self.recorded_events[start_i:end_i + 1]
            start_t = group[0]['time']
            current_dir = "up" if group[0]['delta'] >= 0 else "down"
            if len(group) == 1:
                result = self._prompt_fields("Edit Wheel Event", [
                    {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{start_t:.3f}"},
                    {'key': 'delta', 'label': 'Delta', 'type': 'entry', 'default': group[0]['delta']},
                ])
                if result is None:
                    return
                group[0]['time'] = self._safe_float(result['time'], start_t)
                group[0]['delta'] = self._safe_int(result['delta'], group[0]['delta'])
            else:
                result = self._prompt_fields("Edit Wheel Scroll", [
                    {'key': 'time', 'label': 'Start time (s)', 'type': 'entry', 'default': f"{start_t:.3f}"},
                    {'key': 'direction', 'label': 'Direction', 'type': 'combobox', 'values': ["up", "down"],
                     'default': current_dir},
                ])
                if result is None:
                    return
                new_start = self._safe_float(result['time'], start_t)
                shift = new_start - start_t
                flip = (result['direction'] != current_dir)
                for ev in group:
                    ev['time'] += shift
                    if flip:
                        ev['delta'] = -ev['delta']

        elif kind == 'hold':
            down_ev = self.recorded_events[row_key[1]]
            up_ev = self.recorded_events[row_key[2]]
            duration = up_ev['time'] - down_ev['time']
            if down_ev['type'] == 'key':
                result = self._prompt_fields("Edit Hold Key", [
                    {'key': 'time', 'label': 'Start time (s)', 'type': 'entry', 'default': f"{down_ev['time']:.3f}"},
                    {'key': 'duration', 'label': 'Duration (s)', 'type': 'entry', 'default': f"{duration:.3f}"},
                    {'key': 'name', 'label': 'Key', 'type': 'combobox', 'values': ALL_KEYS, 'default': down_ev['name']},
                ])
                if result is None:
                    return
                new_start = self._safe_float(result['time'], down_ev['time'])
                new_dur = max(0.0, self._safe_float(result['duration'], duration))
                name = result['name'].strip() or down_ev['name']
                down_ev['time'] = new_start
                down_ev['name'] = name
                up_ev['time'] = new_start + new_dur
                up_ev['name'] = name
            else:
                result = self._prompt_fields("Edit Hold Mouse", [
                    {'key': 'time', 'label': 'Start time (s)', 'type': 'entry', 'default': f"{down_ev['time']:.3f}"},
                    {'key': 'duration', 'label': 'Duration (s)', 'type': 'entry', 'default': f"{duration:.3f}"},
                    {'key': 'button', 'label': 'Button', 'type': 'combobox', 'values': ["left", "right", "middle"],
                     'default': down_ev['button']},
                ])
                if result is None:
                    return
                new_start = self._safe_float(result['time'], down_ev['time'])
                new_dur = max(0.0, self._safe_float(result['duration'], duration))
                button = result['button']
                down_ev['time'] = new_start
                down_ev['button'] = button
                up_ev['time'] = new_start + new_dur
                up_ev['button'] = button

        elif kind == 'open_hold':
            ev = self.recorded_events[row_key[1]]
            if ev['type'] == 'key':
                result = self._prompt_fields("Edit Key Event", [
                    {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{ev['time']:.3f}"},
                    {'key': 'name', 'label': 'Key', 'type': 'combobox', 'values': ALL_KEYS, 'default': ev['name']},
                ])
                if result is None:
                    return
                ev['time'] = self._safe_float(result['time'], ev['time'])
                ev['name'] = result['name'].strip() or ev['name']
            else:
                result = self._prompt_fields("Edit Mouse Event", [
                    {'key': 'time', 'label': 'Time (s)', 'type': 'entry', 'default': f"{ev['time']:.3f}"},
                    {'key': 'button', 'label': 'Button', 'type': 'combobox', 'values': ["left", "right", "middle"],
                     'default': ev['button']},
                ])
                if result is None:
                    return
                ev['time'] = self._safe_float(result['time'], ev['time'])
                ev['button'] = result['button']

        self.recorded_events.sort(key=lambda e: e['time'])
        self._refresh_recorded_list()

    def _execute_recorded_event(self, ev):
        try:
            if ev['type'] == 'move':
                mouse.move(ev['x'], ev['y'], absolute=True, duration=0)
            elif ev['type'] == 'button':
                if ev['action'] == 'down':
                    mouse.press(button=ev['button'])
                elif ev['action'] == 'up':
                    mouse.release(button=ev['button'])
                elif ev['action'] == 'double':
                    mouse.click(button=ev['button'])
            elif ev['type'] == 'wheel':
                mouse.wheel(ev['delta'])
            elif ev['type'] == 'key':
                if ev['action'] == 'down':
                    keyboard.press(ev['name'])
                elif ev['action'] == 'up':
                    keyboard.release(ev['name'])
        except Exception:
            pass

    def run_playback(self):
        _INPUT_LIBS_READY.wait()
        self._interruptible_sleep(1.0, 'playing')

        events = list(self.recorded_events)
        is_finite = (self.playback_repeat_mode_var.get() == "finite")
        try:
            limit_val = int(self.playback_repeat_entry.get() or 1)
        except ValueError:
            limit_val = 1
        try:
            speed = float(self.playback_speed_entry.get() or 1.0)
            if speed <= 0:
                speed = 1.0
        except ValueError:
            speed = 1.0

        count = 0
        try:
            while self.playing:
                if is_finite and count >= limit_val:
                    break

                last_t = 0.0
                for ev in events:
                    if not self.playing:
                        break
                    wait = (ev['time'] - last_t) / speed
                    ok = self._interruptible_sleep(wait, 'playing')
                    if not ok:
                        break
                    last_t = ev['time']
                    self._execute_recorded_event(ev)

                count += 1
        finally:
            self.playing = False
            self._safe_ui_after(lambda: self._set_toggle_running_style(self.playback_toggle_btn, False))
            self._safe_ui_after(lambda: self.refresh_toggle_button_label("playback"))
            self._safe_ui_after(self.update_status)

    def update_status(self):
        running_parts = []
        if self.clicker_running:
            running_parts.append("Clicker")
        if self.presser_running:
            running_parts.append("Presser")
        if self.recording:
            running_parts.append("Recording")
        if self.playing:
            running_parts.append("Playback")

        if running_parts:
            self.status_label.config(text="Status: " + " & ".join(running_parts) + " running", fg=COLOR_TEXT)
        else:
            self.status_label.config(text="Status: Idle", fg=COLOR_MUTED)

    def run_clicker(self, gen, stop_event):
        _INPUT_LIBS_READY.wait()

        count = 0
        is_finite = (self.repeat_mode_var.get() == "finite")
        try:
            limit_val = int(self.repeat_entry.get() or 100)
        except ValueError:
            limit_val = 100

        btn_type = self.mouse_btn_var.get().lower()
        clicks = {"Double": 2, "Triple": 3}.get(self.click_type_var.get(), 1)
        is_fixed = (self.pos_mode_var.get() == "fixed")
        is_hold = (self.click_action_mode_var.get() == "Hold")
        smart_click = self.smart_click_var.get()
        max_speed = self.click_max_speed_var.get()
        self.click_rate_counter.reset()

        fx = fy = 0
        if is_fixed:
            try:
                fx = int(self.x_display.get())
                fy = int(self.y_display.get())
            except ValueError:
                fx, fy = 0, 0

        base_x = base_y = None
        last_action_pos = None
        if smart_click:
            if is_fixed:
                base_x, base_y = fx, fy
            else:
                base_x, base_y = mouse.get_position()

        def smart_point():
            nonlocal base_x, base_y, last_action_pos
            if not is_fixed:
                cur_x, cur_y = mouse.get_position()
                if last_action_pos is None or abs(cur_x - last_action_pos[0]) > 1 or abs(cur_y - last_action_pos[1]) > 1:
                    base_x, base_y = cur_x, cur_y
            ox = random.uniform(-SMART_CLICK_RADIUS, SMART_CLICK_RADIUS)
            oy = random.uniform(-SMART_CLICK_RADIUS, SMART_CLICK_RADIUS)
            tx, ty = base_x + ox, base_y + oy
            last_action_pos = (int(round(tx)), int(round(ty)))
            return tx, ty

        try:
            while not stop_event.is_set():
                if is_finite and count >= limit_val:
                    break

                if is_hold:
                    if smart_click:
                        tx, ty = smart_point()
                        mouse.move(int(tx), int(ty), absolute=True, duration=0)
                    elif is_fixed:
                        mouse.move(fx, fy, absolute=True, duration=0)
                    mouse.press(button=btn_type)
                    held_ok = self._interruptible_sleep_event(
                        self.get_total_interval(self.click_hold_vars), stop_event)
                    mouse.release(button=btn_type)
                    if not held_ok:
                        break
                else:
                    if smart_click:
                        tx, ty = smart_point()
                        mouse.move(int(tx), int(ty), absolute=True, duration=0)
                    elif is_fixed:
                        mouse.move(fx, fy, absolute=True, duration=0)
                    self._fire_clicks(btn_type, clicks)

                count += 1
                self.click_rate_counter.tick(1 if is_hold else clicks)

                gap_ok = self._interruptible_sleep_event(
                    self.get_effective_interval(self.click_int_vars, max_speed, self.click_max_cps_entry),
                    stop_event)
                if not gap_ok:
                    break
        finally:
            if is_hold:
                try:
                    mouse.release(button=btn_type)
                except Exception:
                    pass
            # Only touch the UI/state if no newer Start click has happened
            # since this thread began. If the user already stopped and
            # restarted (gen bumped), a newer thread now owns the button/
            # status - this old one just fades out quietly.
            if gen == self.clicker_gen:
                self.clicker_running = False
                self.clicker_thread = None
                self._safe_ui_after(lambda: self._set_toggle_running_style(self.click_toggle_btn, False))
                self._safe_ui_after(lambda: self.refresh_toggle_button_label("click"))
                self._safe_ui_after(self.update_status)

    def run_presser(self, gen, stop_event):
        _INPUT_LIBS_READY.wait()

        count = 0
        is_finite = (self.press_repeat_mode_var.get() == "finite")
        try:
            limit_val = int(self.press_repeat_entry.get() or 100)
        except ValueError:
            limit_val = 100

        key_name = self.press_key_var.get().strip() or "space"
        is_hold = (self.press_action_mode_var.get() == "Hold")
        max_speed = self.press_max_speed_var.get()
        self.press_rate_counter.reset()

        try:
            while not stop_event.is_set():
                if is_finite and count >= limit_val:
                    break

                if is_hold:
                    try:
                        keyboard.press(key_name)
                    except Exception:
                        pass
                    held_ok = self._interruptible_sleep_event(
                        self.get_total_interval(self.press_hold_vars), stop_event)
                    try:
                        keyboard.release(key_name)
                    except Exception:
                        pass
                    if not held_ok:
                        break
                else:
                    try:
                        keyboard.send(key_name)
                    except Exception:
                        pass

                count += 1
                self.press_rate_counter.tick(1)

                gap_ok = self._interruptible_sleep_event(
                    self.get_effective_interval(self.press_int_vars, max_speed, self.press_max_pps_entry),
                    stop_event)
                if not gap_ok:
                    break
        finally:
            if is_hold:
                try:
                    keyboard.release(key_name)
                except Exception:
                    pass
            # Same generation guard as run_clicker: don't clobber a newer
            # thread's UI state if the user already restarted.
            if gen == self.presser_gen:
                self.presser_running = False
                self.presser_thread = None
                self._safe_ui_after(lambda: self._set_toggle_running_style(self.press_toggle_btn, False))
                self._safe_ui_after(lambda: self.refresh_toggle_button_label("press"))
                self._safe_ui_after(self.update_status)

    def _register_hotkey(self, which):
        """(Re)bind the OS-level hotkey for `which` to whatever its entry
        widget currently shows. This is only ever called when the hotkey
        actually changes (initial registration at startup, or right after
        the user finishes picking a new key in _resolve_hotkey_capture) -
        there is no background thread polling for changes anymore."""
        spec = self.hotkey_specs.get(which)
        if spec is None:
            return
        hot = spec['entry'].get().strip().lower()
        old_handle = spec.get('registered_handle')
        if old_handle is not None:
            # Unregister using the exact handle keyboard.add_hotkey gave us
            # back, not by re-parsing/matching the hotkey string. String
            # based removal can silently miss (case, spacing, or alias
            # differences between what was registered and what's re-parsed
            # now) and leave the old OS-level hook alive, so the previous
            # shortcut keeps firing in the background even after being
            # changed or cleared. The handle always removes the exact hook.
            try:
                keyboard.remove_hotkey(old_handle)
            except Exception:
                pass
            spec['registered_handle'] = None
            spec['registered'] = None
        if hot and hot != "press a key...":
            try:
                handle = keyboard.add_hotkey(hot, (lambda cmd=spec['toggle']: self._safe_ui_after(cmd)))
                spec['registered_handle'] = handle
                spec['registered'] = hot
            except Exception:
                pass

    def _reregister_all_hotkeys(self):
        for which in ("click", "press", "record", "playback"):
            self._register_hotkey(which)

    def listen_hotkeys(self):
        # One-shot setup, not a polling loop: wait for the keyboard/mouse
        # libraries to finish loading, then bind whatever hotkeys are
        # currently configured (defaults, or values restored from the
        # settings file). From this point on, hotkeys are only re-bound
        # reactively when the user changes one - see _resolve_hotkey_capture.
        _INPUT_LIBS_READY.wait()
        self._reregister_all_hotkeys()

    def cleanup_idle_threads(self):
        for attr in ("clicker_thread", "presser_thread", "playback_thread"):
            th = getattr(self, attr, None)
            if th is not None and not th.is_alive():
                setattr(self, attr, None)
        gc.collect()

    def watch_memory(self):
        while True:
            time.sleep(300)
            try:
                if get_process_memory_mb() >= MEMORY_CLEANUP_THRESHOLD_MB:
                    self.cleanup_idle_threads()
            except Exception:
                pass

if __name__ == "__main__":
    if hasattr(ctypes, "windll"):
        try:
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass

    threading.Thread(target=_load_input_libs, daemon=True).start()

    root = tk.Tk()
    app = AutoClickerPresser(root)
    try:
        root.mainloop()
    finally:
        if hasattr(ctypes, "windll"):
            try:
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
