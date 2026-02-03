import tkinter as tk
from tkinter import font
import platform
import os
import threading
import re

try:
    import winsound
except ImportError:
    winsound = None

class VisualAlert:
    def __init__(self, root_ref):
        self.overlay = None
        self.is_active = False
        self.root_ref = root_ref
        self._cycle_id = None
        self._sound_lock = threading.Lock()

    def show(self, color):
        if self.overlay: self.stop()
        self.overlay = tk.Toplevel()
        w, h = self.overlay.winfo_screenwidth(), self.overlay.winfo_screenheight()
        self.overlay.geometry(f"{w}x{h}+0+0")
        self.overlay.overrideredirect(True)
        self.overlay.attributes('-topmost', True, '-transparentcolor', 'white')
        
        c = tk.Canvas(self.overlay, width=w, height=h, highlightthickness=0, bg='white')
        c.pack()
        c.create_rectangle(0, 0, w, h, outline=color, width=6, tags="border")
        
        self.is_active = True
        self.cycle(c)

    def play_sound(self):
        def _sound_logic():
            if not self._sound_lock.acquire(blocking=False): return
            try:
                sys_plat = platform.system()
                if sys_plat == "Windows" and winsound: winsound.Beep(1000, 200)
                elif sys_plat == "Darwin": os.system('afplay /System/Library/Sounds/Glass.aiff')
                else: self.root_ref.bell()
            except: pass
            finally: self._sound_lock.release()
        threading.Thread(target=_sound_logic, daemon=True).start()

    def cycle(self, canvas):
        if not self.overlay or not self.is_active: return
        try:
            curr = canvas.itemcget("border", "state")
            new_s = "hidden" if curr == "normal" else "normal"
            canvas.itemconfig("border", state=new_s)
            if new_s == "normal": self.play_sound()
            self._cycle_id = self.overlay.after(600, lambda: self.cycle(canvas))
        except tk.TclError: pass

    def stop(self):
        self.is_active = False
        if self._cycle_id:
            try: self.root_ref.after_cancel(self._cycle_id)
            except: pass
            self._cycle_id = None
        if self.overlay:
            try: self.overlay.destroy()
            except: pass
            self.overlay = None

class EyeCareTimer:
    def __init__(self, parent, colors, base_font):
        self.parent = parent
        self.colors = colors
        self.f_timer = base_font
        self.win = tk.Toplevel(parent)
        self.w, self.h, self.radius = 120, 44, 22
        self.work_sec, self.relax_sec = 20 * 60, 20
        self.current_sec, self.is_relaxing = self.work_sec, False
        self._timer_id = None

        self.setup_ui()
        self.update_position()
        self.tick()

    def setup_ui(self):
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        self.win.config(bg=self.colors["transparent"])
        if platform.system() == "Windows":
            self.win.attributes('-transparentcolor', self.colors["transparent"])
        self.canvas = tk.Canvas(self.win, width=self.w, height=self.h, bg=self.colors["transparent"], highlightthickness=0)
        self.canvas.pack()
        r = self.radius
        coords = [r,1, self.w-r,1, self.w-1,1, self.w-1,r, self.w-1,self.h-r, self.w-1,self.h-1, self.w-r,self.h-1, r,self.h-1, 1,self.h-1, 1,self.h-r, 1,r, 1,1]
        self.bg_rect = self.canvas.create_polygon(coords, smooth=True, fill=self.colors["bg_main"], outline=self.colors["border"])
        self.label = self.canvas.create_text(self.w//2, self.h//2, text="20:00", fill=self.colors["text_meta"], font=self.f_timer)

    def update_position(self):
        try:
            px, py = self.parent.winfo_x(), self.parent.winfo_y()
            self.win.geometry(f"+{px + 570}+{py}")
            self.win.after(100, self.update_position)
        except tk.TclError: pass

    def tick(self):
        if self.current_sec > 0: self.current_sec -= 1
        else:
            self.is_relaxing = not self.is_relaxing
            self.current_sec = self.relax_sec if self.is_relaxing else self.work_sec
            bg = self.colors["accent"] if self.is_relaxing else self.colors["bg_main"]
            fg = self.colors["bg_main"] if self.is_relaxing else self.colors["text_meta"]
            self.canvas.itemconfig(self.bg_rect, fill=bg)
            self.canvas.itemconfig(self.label, fill=fg)
            if self.is_relaxing: self.parent.bell()
        m, s = divmod(self.current_sec, 60)
        self.canvas.itemconfig(self.label, text=f"{m:02}:{s:02}")
        self._timer_id = self.win.after(1000, self.tick)

class FocusTimer:
    def __init__(self):
        self.root = tk.Tk()
        self.w, self.h, self.radius = 560, 44, 22
        self.colors = {
            "bg_main": "#1E1E1E", "text_main": "#F5F5F7", "text_meta": "#86868B",
            "accent": "#FFD60A", "success": "#30D158", "danger": "#FF453A",
            "border": "#333333", "grip": "#555555", "transparent": "#000001"
        }
        self.alert = VisualAlert(self.root)
        self.default_minutes = 90
        self.seconds = self.default_minutes * 60
        self.running = False
        self.alarm_active = False
        self._clock_id = None
        self._blink_id = None
        self.blink_state = False 
        
        self.setup_fonts()
        self.setup_window()
        self.setup_ui()
        self.eye_timer = EyeCareTimer(self.root, self.colors, self.f_timer)
        self.setup_binds()
        self.update_display_text()
        self.root.mainloop()

    def setup_fonts(self):
        fams = font.families()
        base = next((f for f in ["SF Pro Text", "Helvetica Neue", "Segoe UI"] if f in fams), "Arial")
        mono = next((f for f in ["SF Mono", "Menlo", "Consolas"] if f in fams), "Courier New")
        self.f_timer = font.Font(family=mono, size=16, weight="bold")
        self.f_task = font.Font(family=base, size=12)
        self.f_btn = font.Font(family="Segoe UI Symbol", size=10)

    def validate_task_length(self, P):
        return self.f_task.measure(P) < 290

    def setup_window(self):
        pos_x = (self.root.winfo_screenwidth() // 2) - (self.w // 2)
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.w}x{self.h}+{pos_x}+20")
        self.root.attributes('-topmost', True)
        if platform.system() == "Windows":
            self.root.config(bg=self.colors["transparent"])
            self.root.attributes('-transparentcolor', self.colors["transparent"])

    def setup_ui(self):
        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h, bg=self.colors["transparent"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        r = self.radius
        coords = [r,1, self.w-r,1, self.w-1,1, self.w-1,r, self.w-1,self.h-r, self.w-1,self.h-1, self.w-r,self.h-1, r,self.h-1, 1,self.h-1, 1,self.h-r, 1,r, 1,1]
        self.canvas.create_polygon(coords, smooth=True, fill=self.colors["bg_main"], outline=self.colors["border"])
        self.main_frame = tk.Frame(self.root, bg=self.colors["bg_main"])
        self.main_frame.place(x=r, y=2, width=self.w - 2*r, height=self.h - 4)

        self.grip = tk.Canvas(self.main_frame, width=12, height=24, bg=self.colors["bg_main"], highlightthickness=0, cursor="fleur")
        self.grip.pack(side="left", padx=(5,0))
        for y in [5, 12, 19]:
            for x in [0, 7]: self.grip.create_oval(x, y, x+3, y+3, fill=self.colors["grip"], outline="")

        vcmd = (self.root.register(self.validate_task_length), '%P')
        self.task_var = tk.StringVar()
        self.task_entry = tk.Entry(self.main_frame, textvariable=self.task_var, font=self.f_task, bg=self.colors["bg_main"], fg=self.colors["text_meta"], bd=0, highlightthickness=0, insertbackground=self.colors["text_main"], disabledbackground=self.colors["bg_main"], validate="key", validatecommand=vcmd)
        self.task_entry.pack(side="left", fill="both", expand=True, padx=10)
        self.task_entry.insert(0, "Focus...")

        tk.Frame(self.main_frame, width=1, bg="#333333").pack(side="left", fill="y", pady=8)

        self.time_entry = tk.Entry(self.main_frame, font=self.f_timer, bg=self.colors["bg_main"], fg=self.colors["text_main"], bd=0, justify='center', width=6, highlightthickness=0, insertbackground=self.colors["text_main"], disabledbackground=self.colors["bg_main"])
        self.time_entry.pack(side="left")

        self.btn_frame = tk.Frame(self.main_frame, bg=self.colors["bg_main"])
        self.btn_frame.pack(side="right", padx=5)
        self.btn_start = self.create_btn("▶", self.toggle, self.colors["text_main"])
        self.create_btn("✓", self.complete_early, self.colors["success"])
        self.create_btn("⟳", self.reset, self.colors["text_main"])
        self.create_btn("✕", self.safe_destroy, self.colors["danger"])

    def create_btn(self, text, cmd, col):
        b = tk.Button(self.btn_frame, text=text, command=cmd, bg=self.colors["bg_main"], fg=col, bd=0, font=self.f_btn, activebackground=self.colors["bg_main"], activeforeground=col, cursor="hand2", takefocus=False)
        b.pack(side="left", padx=2)
        return b

    def safe_destroy(self):
        self.running = False
        if self._clock_id: self.root.after_cancel(self._clock_id)
        self.alert.stop()
        self.root.destroy()

    def update_clock(self):
        if self._clock_id: self.root.after_cancel(self._clock_id)
        if self.running and self.seconds > 0:
            self.seconds -= 1
            self.update_display_text()
            self._clock_id = self.root.after(1000, self.update_clock)
        elif self.seconds == 0 and self.running:
            self.trigger_alarm()

    def trigger_alarm(self):
        self.running = False
        self.alarm_active = True
        self.task_entry.config(state="disabled", disabledforeground=self.colors["danger"])
        self.time_entry.config(state="disabled", disabledforeground=self.colors["danger"])
        self.alert.show(self.colors["danger"])
        self.blink_text()
        self.btn_start.config(text="■")

    def blink_text(self):
        if not self.alarm_active: return
        try:
            col = self.colors["danger"] if self.blink_state else "#FFFFFF"
            self.blink_state = not self.blink_state
            self.task_entry.config(disabledforeground=col)
            self.time_entry.config(disabledforeground=col)
            self._blink_id = self.root.after(600, self.blink_text)
        except: pass

    def toggle(self, e=None):
        if self.alarm_active: return "break"
        if not self.running:
            self.apply_input()
            self.running = True
            self.btn_start.config(text="⏸")
            self.update_clock()
        else:
            self.running = False
            self.btn_start.config(text="▶")
        return "break"

    def apply_input(self):
        val = self.time_entry.get().strip()
        m = re.match(r'^(\d+)(?::(\d{1,2}))?$', val)
        if m:
            mins, secs = m.groups()
            self.seconds = int(mins) * 60 + (int(secs) if secs else 0)
        else: self.update_display_text()

    def update_display_text(self):
        try:
            st = self.time_entry['state']
            self.time_entry.config(state='normal')
            self.time_entry.delete(0, tk.END)
            self.time_entry.insert(0, f"{self.seconds // 60:02}:{self.seconds % 60:02}")
            self.time_entry.config(state=st)
        except: pass

    def reset(self):
        self.alarm_active = False
        self.running = False
        if self._clock_id: self.root.after_cancel(self._clock_id)
        self.alert.stop()
        self.seconds = self.default_minutes * 60
        self.update_display_text()
        self.task_entry.config(state="normal", fg=self.colors["text_meta"])
        self.time_entry.config(state="normal")
        self.btn_start.config(text="▶")

    def complete_early(self):
        self.running = False
        self.alert.stop()
        self.task_entry.config(state="disabled", disabledforeground=self.colors["success"])
        self.time_entry.config(state="disabled", disabledforeground=self.colors["success"])

    def setup_binds(self):
        for w in [self.canvas, self.main_frame, self.grip]:
            w.bind('<Button-1>', self.start_move)
        self.grip.bind('<B1-Motion>', self.do_move)
        self.task_entry.bind('<FocusIn>', lambda e: self.placeholder(True))
        self.task_entry.bind('<FocusOut>', lambda e: self.placeholder(False))
        # Жесткая привязка для обоих полей ввода
        self.task_entry.bind('<Return>', self.toggle)
        self.time_entry.bind('<Return>', self.toggle)
        self.root.bind('<space>', self.toggle)
        self.root.bind('<Control-Return>', lambda e: self.complete_early())

    def placeholder(self, is_in):
        if is_in and self.task_var.get() == "Focus...":
            self.task_entry.delete(0, tk.END)
            self.task_entry.config(fg=self.colors["text_main"])
        elif not is_in and not self.task_var.get():
            self.task_entry.insert(0, "Focus...")
            self.task_entry.config(fg=self.colors["text_meta"])

    def start_move(self, e):
        self.root.focus_set()
        self.x, self.y = e.x, e.y

    def do_move(self, e):
        nx = self.root.winfo_x() + (e.x - self.x)
        ny = self.root.winfo_y() + (e.y - self.y)
        self.root.geometry(f"+{nx}+{ny}")

if __name__ == "__main__":
    FocusTimer()