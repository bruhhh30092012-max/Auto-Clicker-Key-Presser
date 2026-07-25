import os
import sys
import time
import gc
import threading
import random
import ctypes
from collections import deque
import tkinter as tk
from tkinter import ttk

pyautogui = None
keyboard = None
mouse = None

_INPUT_LIBS_READY = threading.Event()


def _load_input_libs():
    global pyautogui, keyboard, mouse
    import pyautogui as _pyautogui
    import keyboard as _keyboard
    import mouse as _mouse

    _pyautogui.FAILSAFE = True
    _pyautogui.PAUSE = 0
    _pyautogui.MINIMUM_DURATION = 0
    _pyautogui.MINIMUM_SLEEP = 0

    pyautogui = _pyautogui
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
MEMORY_CLEANUP_THRESHOLD_MB = 40


def get_process_memory_mb():
    if not hasattr(ctypes, "windll"):
        return 0.0
    try:
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
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

        counters = PROCESS_MEMORY_COUNTERS()
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

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background=COLOR_CARD, foreground=COLOR_TEXT, font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=COLOR_CARD, foreground=COLOR_MUTED, font=("Segoe UI", 8))
        style.configure("TRadiobutton", background=COLOR_CARD, foreground=COLOR_TEXT)
        style.configure("TCheckbutton", background=COLOR_CARD, foreground=COLOR_TEXT)
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

        self.root.option_add("*TCombobox*Listbox.background", COLOR_CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", COLOR_TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#d6d6d6")
        self.root.option_add("*TCombobox*Listbox.selectForeground", COLOR_TEXT)
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))

        self.clicker_running = False
        self.presser_running = False
        self.picking_location = False
        self.capturing_hotkey_for = None
        self.hotkey_specs = {}

        self.recording = False
        self.playing = False
        self.recorded_events = []
        self.record_start_time = 0.0

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
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._build_remaining_tabs(), add="+")
        self.root.after(0, self._build_remaining_tabs)
        self.root.after(150, self.update_rate_labels)

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

        self.notebook.add(click_tab, text="Mouse Clicker")
        self.notebook.add(press_tab, text="Key Presser")
        self.notebook.add(record_tab, text="Record & Playback")

        self.build_click_tab(click_tab)

        self._press_tab = press_tab
        self._record_tab = record_tab
        self._remaining_tabs_built = False

        self.status_label = tk.Label(main_frame, text="Status: Idle", bg=COLOR_BG, fg=COLOR_MUTED,
                                      font=("Segoe UI", 10, "bold"))
        self.status_label.pack(pady=(8, 0))

    def _build_remaining_tabs(self):
        if self._remaining_tabs_built:
            return
        self._remaining_tabs_built = True
        self.build_press_tab(self._press_tab)
        self.build_record_tab(self._record_tab)
        self.root.update_idletasks()
        self.fit_window_to_screen()

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
        ttk.Combobox(opts_frame, textvariable=self.click_type_var, values=["Single", "Double"],
                     width=8, state="readonly").grid(row=0, column=3, sticky="w", pady=2)

        ttk.Label(opts_frame, text="Action mode:").grid(row=0, column=4, sticky="w", padx=(16, 4), pady=2)
        self.click_action_mode_var = tk.StringVar(value="Click")
        ttk.Combobox(opts_frame, textvariable=self.click_action_mode_var, values=["Click", "Hold"],
                     width=8, state="readonly").grid(row=0, column=5, sticky="w", pady=2)

        self.smart_click_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts_frame, text="Smart click",
                         variable=self.smart_click_var).grid(row=1, column=2, columnspan=4, sticky="w", padx=(24, 0), pady=(6, 0))

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
        self.pick_btn = tk.Button(pick_row, text="Pick", command=self.start_pick_location, width=6,
                                   relief="flat", bg=COLOR_BTN_IDLE, activebackground=COLOR_BTN_IDLE_ACTIVE,
                                   fg=COLOR_TEXT, bd=1, cursor="hand2")
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

        self.press_max_speed_var = tk.BooleanVar(value=False)
        max_pps_row = tk.Frame(key_frame, bg=COLOR_CARD)
        max_pps_row.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))
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

        self.record_count_label = tk.Label(rec_section, text="Recorded events: 0", bg=COLOR_CARD,
                                            fg=COLOR_MUTED, font=("Segoe UI", 8))
        self.record_count_label.pack(anchor="w", pady=(8, 0))

        self.record_hotkey_entry, self.record_toggle_btn = self.create_hotkey_and_toggle_row(
            rec_section, default_hotkey="f8", toggle_command=self.toggle_recording, action_label="Recording",
            hotkey_which="record", running_attr="recording")

        list_section = self.make_section(record_body, "Recorded Actions")
        list_row = tk.Frame(list_section, bg=COLOR_CARD)
        list_row.pack(fill="both", expand=True)

        list_scrollbar = ttk.Scrollbar(list_row, orient="vertical", style="Modern.Vertical.TScrollbar")
        self.record_listbox = tk.Listbox(list_row, height=8, bg=COLOR_CARD, fg=COLOR_TEXT,
                                          font=("Consolas", 8), yscrollcommand=list_scrollbar.set,
                                          selectbackground="#d6d6d6", relief="flat", bd=1,
                                          highlightthickness=1, highlightbackground=COLOR_BORDER)
        list_scrollbar.config(command=self.record_listbox.yview)
        self.record_listbox.pack(side="left", fill="both", expand=True)
        list_scrollbar.pack(side="right", fill="y")

        def _listbox_mousewheel(event):
            self.record_listbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def _listbox_mousewheel_linux_up(event):
            self.record_listbox.yview_scroll(-1, "units")
            return "break"

        def _listbox_mousewheel_linux_down(event):
            self.record_listbox.yview_scroll(1, "units")
            return "break"

        self.record_listbox.bind("<MouseWheel>", _listbox_mousewheel)
        self.record_listbox.bind("<Button-4>", _listbox_mousewheel_linux_up)
        self.record_listbox.bind("<Button-5>", _listbox_mousewheel_linux_down)

        clear_row = tk.Frame(list_section, bg=COLOR_CARD)
        clear_row.pack(fill="x", pady=(8, 0))
        tk.Button(clear_row, text="Clear", command=self.clear_recorded_events, width=10,
                  relief="flat", bg=COLOR_BTN_IDLE, activebackground=COLOR_BTN_IDLE_ACTIVE,
                  fg=COLOR_TEXT, bd=1, cursor="hand2").pack(side="left")

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

    def create_interval_row(self, parent, title):
        frame = tk.Frame(parent, bg=COLOR_CARD)
        frame.pack(fill="x", pady=(0, 4))

        ttk.Label(frame, text=title + ":", font=("Segoe UI", 9)).grid(
            row=0, column=0, columnspan=8, sticky="w", pady=(0, 4))

        ttk.Label(frame, text="Hours").grid(row=1, column=0, padx=2)
        ttk.Label(frame, text="Minutes").grid(row=1, column=2, padx=2)
        ttk.Label(frame, text="Seconds").grid(row=1, column=4, padx=2)
        ttk.Label(frame, text="Milliseconds").grid(row=1, column=6, padx=2)

        h_ent = ttk.Entry(frame, width=5, justify="right")
        h_ent.insert(0, "0")
        h_ent.grid(row=2, column=0, padx=2)

        m_ent = ttk.Entry(frame, width=5, justify="right")
        m_ent.insert(0, "0")
        m_ent.grid(row=2, column=2, padx=2)

        s_ent = ttk.Entry(frame, width=5, justify="right")
        s_ent.insert(0, "0")
        s_ent.grid(row=2, column=4, padx=2)

        ms_ent = ttk.Entry(frame, width=6, justify="right")
        ms_ent.insert(0, "100")
        ms_ent.grid(row=2, column=6, padx=2)

        rand_var = tk.BooleanVar(value=False)
        rand_chk = ttk.Checkbutton(frame, text="Random interval +/-", variable=rand_var)
        rand_chk.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

        rand_ent = ttk.Entry(frame, width=6, justify="right")
        rand_ent.insert(0, "20")
        rand_ent.grid(row=3, column=4, padx=2, pady=(6, 0))
        ttk.Label(frame, text="ms").grid(row=3, column=5, sticky="w", pady=(6, 0))

        return {'h': h_ent, 'm': m_ent, 's': s_ent, 'ms': ms_ent, 'rand_var': rand_var, 'rand_ms': rand_ent,
                'rand_chk': rand_chk}

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

        set_btn = tk.Button(row, text="Set Hotkey", command=lambda: self.start_hotkey_capture(hotkey_which),
                             relief="flat", bg=COLOR_BTN_IDLE, activebackground=COLOR_BTN_IDLE_ACTIVE,
                             fg=COLOR_TEXT, bd=1, width=10, cursor="hand2")
        set_btn.pack(side="left", padx=(0, 10))

        toggle_btn = tk.Button(row, text=f"Start {action_label} ({default_hotkey.upper()})",
                                command=toggle_command, bg=COLOR_START, fg=COLOR_TEXT,
                                font=("Segoe UI", 9, "bold"), relief="flat",
                                activebackground=COLOR_START_ACTIVE, activeforeground=COLOR_TEXT, bd=1,
                                width=20, pady=4, cursor="hand2")
        toggle_btn.pack(side="right", fill="x", expand=True)

        self.hotkey_specs[hotkey_which] = {
            'entry': hotkey_entry,
            'btn': toggle_btn,
            'toggle': toggle_command,
            'running_attr': running_attr,
            'label': action_label,
        }

        return hotkey_entry, toggle_btn

    def start_hotkey_capture(self, which):
        if self.capturing_hotkey_for is not None:
            return
        self.capturing_hotkey_for = which
        entry = self.hotkey_specs[which]['entry']
        entry.configure(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, "Press a key...")
        entry.configure(state="readonly")

        def capture():
            _INPUT_LIBS_READY.wait()
            key_name = None
            while key_name is None:
                event = keyboard.read_event(suppress=False)
                if event.event_type == "down":
                    key_name = event.name
            self.root.after(0, lambda: self.finish_hotkey_capture(which, key_name))

        threading.Thread(target=capture, daemon=True).start()

    def finish_hotkey_capture(self, which, key_name):
        entry = self.hotkey_specs[which]['entry']
        entry.configure(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, key_name)
        entry.configure(state="readonly")
        self.capturing_hotkey_for = None
        self.refresh_toggle_button_label(which)

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

    def start_pick_location(self):
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

        def on_click(event):
            x, y = event.x_root, event.y_root
            overlay.destroy()
            self.x_display.delete(0, tk.END)
            self.x_display.insert(0, str(x))
            self.y_display.delete(0, tk.END)
            self.y_display.insert(0, str(y))

        def on_cancel(event=None):
            overlay.destroy()

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
        interval = self.get_total_interval(vars_dict)
        if max_speed_enabled:
            try:
                max_rate = float(max_rate_entry.get() or 0)
            except ValueError:
                max_rate = 0
            if max_rate > 0:
                floor_interval = 1.0 / max_rate
                if floor_interval > interval:
                    interval = floor_interval
        return interval

    def _interruptible_sleep(self, duration, running_attr):
        end_time = time.time() + max(duration, 0)
        while True:
            remaining = end_time - time.time()
            if remaining <= 0:
                return True
            if not getattr(self, running_attr):
                return False
            time.sleep(min(0.05, remaining))

    def toggle_clicker(self):
        if not self.clicker_running:
            if self.clicker_thread is not None and self.clicker_thread.is_alive():
                return
            self.clicker_running = True
            self.click_toggle_btn.config(bg=COLOR_STOP, fg="white", activebackground=COLOR_STOP_ACTIVE,
                                          activeforeground="white")
            self.refresh_toggle_button_label("click")
            self.clicker_thread = threading.Thread(target=self.run_clicker, daemon=True)
            self.clicker_thread.start()
        else:
            self.clicker_running = False
            if self.clicker_thread is not None:
                self.clicker_thread.join(timeout=2.0)
                self.clicker_thread = None
            self.click_toggle_btn.config(bg=COLOR_START, fg=COLOR_TEXT, activebackground=COLOR_START_ACTIVE,
                                          activeforeground=COLOR_TEXT)
            self.refresh_toggle_button_label("click")
        self.update_status()

    def toggle_presser(self):
        if not self.presser_running:
            if self.presser_thread is not None and self.presser_thread.is_alive():
                return
            self.presser_running = True
            self.press_toggle_btn.config(bg=COLOR_STOP, fg="white", activebackground=COLOR_STOP_ACTIVE,
                                          activeforeground="white")
            self.refresh_toggle_button_label("press")
            self.presser_thread = threading.Thread(target=self.run_presser, daemon=True)
            self.presser_thread.start()
        else:
            self.presser_running = False
            if self.presser_thread is not None:
                self.presser_thread.join(timeout=2.0)
                self.presser_thread = None
            self.press_toggle_btn.config(bg=COLOR_START, fg=COLOR_TEXT, activebackground=COLOR_START_ACTIVE,
                                          activeforeground=COLOR_TEXT)
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
            self._refresh_recorded_list()
            try:
                mouse.hook(self._on_mouse_event)
            except Exception:
                pass
            try:
                keyboard.hook(self._on_keyboard_event)
            except Exception:
                pass
            self.record_toggle_btn.config(bg=COLOR_STOP, fg="white", activebackground=COLOR_STOP_ACTIVE,
                                           activeforeground="white")
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
            self.record_toggle_btn.config(bg=COLOR_START, fg=COLOR_TEXT, activebackground=COLOR_START_ACTIVE,
                                           activeforeground=COLOR_TEXT)
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
            self.playback_toggle_btn.config(bg=COLOR_STOP, fg="white", activebackground=COLOR_STOP_ACTIVE,
                                             activeforeground="white")
            self.refresh_toggle_button_label("playback")
            self.playback_thread = threading.Thread(target=self.run_playback, daemon=True)
            self.playback_thread.start()
        else:
            self.playing = False
            if self.playback_thread is not None:
                self.playback_thread.join(timeout=2.0)
                self.playback_thread = None
            self.playback_toggle_btn.config(bg=COLOR_START, fg=COLOR_TEXT, activebackground=COLOR_START_ACTIVE,
                                             activeforeground=COLOR_TEXT)
            self.refresh_toggle_button_label("playback")
        self.update_status()

    def clear_recorded_events(self):
        if self.recording or self.playing:
            return
        self.recorded_events = []
        self._refresh_recorded_list()

    def _on_mouse_event(self, event):
        if not self.recording:
            return
        t = time.time() - self.record_start_time
        if isinstance(event, mouse.ButtonEvent):
            self.recorded_events.append(
                {'type': 'button', 'time': t, 'button': event.button, 'action': event.event_type})
        elif isinstance(event, mouse.MoveEvent):
            if self.record_moves_var.get():
                self.recorded_events.append({'type': 'move', 'time': t, 'x': event.x, 'y': event.y})
        elif isinstance(event, mouse.WheelEvent):
            self.recorded_events.append({'type': 'wheel', 'time': t, 'delta': event.delta})

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
        t = time.time() - self.record_start_time
        self.recorded_events.append({'type': 'key', 'time': t, 'name': event.name, 'action': event.event_type})

    def _refresh_recorded_list(self):
        self.record_count_label.config(text=f"Recorded events: {len(self.recorded_events)}")
        self.record_listbox.delete(0, tk.END)

        lines = []
        open_holds = {}

        for ev in self.recorded_events:
            t = ev['time']
            if ev['type'] == 'key':
                hold_id = ('key', ev['name'])
                if ev['action'] == 'down':
                    open_holds.setdefault(hold_id, t)
                elif ev['action'] == 'up':
                    if hold_id in open_holds:
                        start_t = open_holds.pop(hold_id)
                        lines.append(f"{start_t:7.2f}s  hold key {ev['name']} for {t - start_t:.2f}s")
                    else:
                        lines.append(f"{t:7.2f}s  key {ev['name']} up")
                else:
                    lines.append(f"{t:7.2f}s  key {ev['name']} {ev['action']}")
            elif ev['type'] == 'button':
                hold_id = ('button', ev['button'])
                if ev['action'] == 'down':
                    open_holds.setdefault(hold_id, t)
                elif ev['action'] == 'up':
                    if hold_id in open_holds:
                        start_t = open_holds.pop(hold_id)
                        lines.append(f"{start_t:7.2f}s  hold mouse {ev['button']} for {t - start_t:.2f}s")
                    else:
                        lines.append(f"{t:7.2f}s  mouse {ev['button']} up")
                else:
                    lines.append(f"{t:7.2f}s  mouse {ev['button']} {ev['action']}")
            elif ev['type'] == 'move':
                lines.append(f"{t:7.2f}s  move to ({ev['x']}, {ev['y']})")
            elif ev['type'] == 'wheel':
                lines.append(f"{t:7.2f}s  wheel {ev['delta']}")
            else:
                lines.append(str(ev))

        for (kind, identifier), start_t in open_holds.items():
            label = "key" if kind == "key" else "mouse"
            lines.append(f"{start_t:7.2f}s  hold {label} {identifier} (chua tha)")

        preview_limit = 300
        for desc in lines[:preview_limit]:
            self.record_listbox.insert(tk.END, desc)
        if len(lines) > preview_limit:
            self.record_listbox.insert(tk.END, f"... and {len(lines) - preview_limit} more")

    def _execute_recorded_event(self, ev):
        try:
            if ev['type'] == 'move':
                pyautogui.moveTo(ev['x'], ev['y'])
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
            self.root.after(0, lambda: self.playback_toggle_btn.config(
                bg=COLOR_START, fg=COLOR_TEXT, activebackground=COLOR_START_ACTIVE, activeforeground=COLOR_TEXT))
            self.root.after(0, lambda: self.refresh_toggle_button_label("playback"))
            self.root.after(0, self.update_status)

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

    def run_clicker(self):
        _INPUT_LIBS_READY.wait()
        self._interruptible_sleep(1.0, 'clicker_running')

        count = 0
        is_finite = (self.repeat_mode_var.get() == "finite")
        try:
            limit_val = int(self.repeat_entry.get() or 100)
        except ValueError:
            limit_val = 100

        btn_type = self.mouse_btn_var.get().lower()
        clicks = 2 if self.click_type_var.get() == "Double" else 1
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
            while self.clicker_running:
                if is_finite and count >= limit_val:
                    break

                if is_hold:
                    if smart_click:
                        tx, ty = smart_point()
                        mouse.move(int(tx), int(ty), absolute=True, duration=0)
                    elif is_fixed:
                        mouse.move(fx, fy, absolute=True, duration=0)
                    mouse.press(button=btn_type)
                    held_ok = self._interruptible_sleep(
                        self.get_total_interval(self.click_hold_vars), 'clicker_running')
                    mouse.release(button=btn_type)
                    if not held_ok:
                        break
                else:
                    if smart_click:
                        tx, ty = smart_point()
                        mouse.move(int(tx), int(ty), absolute=True, duration=0)
                    elif is_fixed:
                        mouse.move(fx, fy, absolute=True, duration=0)
                    for _ in range(clicks):
                        mouse.click(button=btn_type)

                count += 1
                self.click_rate_counter.tick(1 if is_hold else clicks)

                gap_ok = self._interruptible_sleep(
                    self.get_effective_interval(self.click_int_vars, max_speed, self.click_max_cps_entry),
                    'clicker_running')
                if not gap_ok:
                    break
        finally:
            if is_hold:
                try:
                    mouse.release(button=btn_type)
                except Exception:
                    pass
            self.clicker_running = False
            self.root.after(0, lambda: self.click_toggle_btn.config(
                bg=COLOR_START, fg=COLOR_TEXT, activebackground=COLOR_START_ACTIVE, activeforeground=COLOR_TEXT))
            self.root.after(0, lambda: self.refresh_toggle_button_label("click"))
            self.root.after(0, self.update_status)

    def run_presser(self):
        _INPUT_LIBS_READY.wait()
        self._interruptible_sleep(0.5, 'presser_running')

        count = 0
        is_finite = (self.repeat_mode_var.get() == "finite")
        try:
            limit_val = int(self.repeat_entry.get() or 100)
        except ValueError:
            limit_val = 100

        key_name = self.press_key_var.get().strip() or "space"
        is_hold = (self.press_action_mode_var.get() == "Hold")
        max_speed = self.press_max_speed_var.get()
        self.press_rate_counter.reset()

        try:
            while self.presser_running:
                if is_finite and count >= limit_val:
                    break

                if is_hold:
                    try:
                        keyboard.press(key_name)
                    except Exception:
                        pass
                    held_ok = self._interruptible_sleep(
                        self.get_total_interval(self.press_hold_vars), 'presser_running')
                    try:
                        keyboard.release(key_name)
                    except Exception:
                        pass
                    if not held_ok:
                        break
                else:
                    try:
                        pyautogui.press(key_name)
                    except Exception:
                        pass

                count += 1
                self.press_rate_counter.tick(1)

                gap_ok = self._interruptible_sleep(
                    self.get_effective_interval(self.press_int_vars, max_speed, self.press_max_pps_entry),
                    'presser_running')
                if not gap_ok:
                    break
        finally:
            if is_hold:
                try:
                    keyboard.release(key_name)
                except Exception:
                    pass
            self.presser_running = False
            self.root.after(0, lambda: self.press_toggle_btn.config(
                bg=COLOR_START, fg=COLOR_TEXT, activebackground=COLOR_START_ACTIVE, activeforeground=COLOR_TEXT))
            self.root.after(0, lambda: self.refresh_toggle_button_label("press"))
            self.root.after(0, self.update_status)

    def listen_hotkeys(self):
        _INPUT_LIBS_READY.wait()
        last_values = {which: "" for which in ("click", "press", "record", "playback")}
        while True:
            try:
                if self.capturing_hotkey_for is None:
                    for which in list(last_values.keys()):
                        spec = self.hotkey_specs.get(which)
                        if spec is None:
                            continue
                        hot = spec['entry'].get().strip().lower()
                        if hot and hot != last_values[which] and hot != "press a key...":
                            try:
                                keyboard.remove_hotkey(last_values[which])
                            except Exception:
                                pass
                            keyboard.add_hotkey(hot, (lambda cmd=spec['toggle']: self.root.after(0, cmd)))
                            last_values[which] = hot
            except Exception:
                pass
            time.sleep(1)

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
