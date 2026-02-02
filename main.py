import tkinter as tk
from tkinter import font
import platform
import os
import threading

try:
    import winsound
except ImportError:
    winsound = None

class AppleStyleWindow:
    def __init__(self, width, height, radius=15):
        self.root = tk.Tk()
        self.w, self.h = width, height
        self.radius = radius
        
        self.colors = {
            "bg_main": "#1E1E1E",
            "text_main": "#F5F5F7",
            "text_meta": "#86868B",
            "accent": "#FFD60A",
            "success": "#30D158",
            "danger": "#FF453A",
            "border": "#333333",
            "grip": "#555555",
            "transparent": "#000001"
        }

        s_width = self.root.winfo_screenwidth()
        pos_x = (s_width // 2) - (self.w // 2)
        
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.w}x{self.h}+{pos_x}+20")
        self.root.attributes('-topmost', True)
        
        if platform.system() == "Windows":
            self.root.config(bg=self.colors["transparent"])
            self.root.attributes('-transparentcolor', self.colors["transparent"])
        else:
            self.root.config(bg=self.colors["transparent"])
            self.root.attributes('-transparent', True)

        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h, 
                                bg=self.colors["transparent"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.draw_rounded_background()

        self.main_frame = tk.Frame(self.root, bg=self.colors["bg_main"])
        self.main_frame.place(x=self.radius, y=2, width=self.w - 2*self.radius, height=self.h - 4)

    def draw_rounded_background(self):
        x1, y1 = 1, 1
        x2, y2 = self.w - 1, self.h - 1
        r = self.radius
        
        self.canvas.create_polygon(
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, 
            x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1,
            smooth=True, fill=self.colors["bg_main"], outline=self.colors["border"], width=1
        )

class VisualAlert:
    def __init__(self, root_ref):
        self.overlay = None
        self.is_active = False
        self.root_ref = root_ref

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
        sys_plat = platform.system()
        def _sound_thread():
            if sys_plat == "Windows" and winsound:
                try: winsound.Beep(1000, 200)
                except: self.root_ref.bell()
            elif sys_plat == "Darwin":
                try: os.system('afplay /System/Library/Sounds/Glass.aiff')
                except: self.root_ref.bell()
            else:
                self.root_ref.bell()
        threading.Thread(target=_sound_thread, daemon=True).start()

    def cycle(self, canvas):
        if not self.overlay or not self.is_active: return
        curr = canvas.itemcget("border", "state")
        new_s = "hidden" if curr == "normal" else "normal"
        canvas.itemconfig("border", state=new_s)
        
        if new_s == "normal":
            self.play_sound()
             
        self.overlay.after(600, lambda: self.cycle(canvas))

    def stop(self):
        self.is_active = False
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None

class FocusTimer(AppleStyleWindow):
    def __init__(self):
        super().__init__(width=560, height=44, radius=22)
        
        self.alert = VisualAlert(self.root)
        self.default_minutes = 90
        self.minutes = self.default_minutes
        self.seconds = self.minutes * 60
        self.running = False
        self.alarm_active = False
        self._anim_id = None
        self.blink_state = False 
        
        self.setup_fonts()
        self.setup_ui()
        self.setup_binds()
        self.update_display_text()
        
        self.root.after(50, lambda: self.root.focus_set())
        self.root.mainloop()

    def setup_fonts(self):
        families = font.families()
        base = next((f for f in ["SF Pro Text", "Helvetica Neue", "Segoe UI"] if f in families), "Arial")
        mono = next((f for f in ["SF Mono", "Menlo", "Consolas"] if f in families), "Courier New")
        
        self.f_timer = font.Font(family=mono, size=16, weight="bold")
        self.f_task = font.Font(family=base, size=12)
        self.f_btn = font.Font(family="Segoe UI Symbol", size=10)

    def validate_task_length(self, proposed_text):
        entry_w = self.task_entry.winfo_width()
        
        limit_w = entry_w - 14 if entry_w > 1 else 280
        
        text_w = self.f_task.measure(proposed_text)
        return text_w < limit_w

    def setup_ui(self):
        self.grip_canvas = tk.Canvas(self.root, width=11, height=24, 
                                     bg=self.colors["bg_main"], highlightthickness=0, cursor="fleur")
        self.grip_canvas.place(x=18, rely=0.5, anchor="center")
        
        dot_color = self.colors["grip"]
        d = 3; gap = 4
        cols = [0, d + gap]
        start_y = 5 
        rows = [start_y, start_y + d + gap, start_y + (d + gap) * 2]
        
        for x in cols:
            for y in rows:
                self.grip_canvas.create_oval(x, y, x+d, y+d, fill=dot_color, outline="")

        vcmd = (self.root.register(self.validate_task_length), '%P') 

        self.task_var = tk.StringVar()
        self.task_entry = tk.Entry(
            self.main_frame, textvariable=self.task_var, font=self.f_task,
            bg=self.colors["bg_main"], fg=self.colors["text_main"],
            bd=0, highlightthickness=0, insertbackground=self.colors["text_main"],
            selectbackground="#3A3A3C", selectforeground=self.colors["text_main"],
            disabledbackground=self.colors["bg_main"],
            disabledforeground=self.colors["success"],
            validate="key", validatecommand=vcmd 
        )
        self.task_entry.pack(side="left", fill="both", expand=True, padx=(18, 0))
        
        self.task_placeholder = "Focus..."
        self.task_entry.insert(0, self.task_placeholder)
        self.task_entry.config(fg=self.colors["text_meta"])
        self.task_entry.bind("<FocusIn>", self.on_task_in)
        self.task_entry.bind("<FocusOut>", self.on_task_out)

        tk.Frame(self.main_frame, width=1, bg="#333333").pack(side="left", fill="y", padx=10, pady=6)

        self.time_entry = tk.Entry(
            self.main_frame, font=self.f_timer, 
            bg=self.colors["bg_main"], fg=self.colors["text_main"],
            bd=0, justify='center', width=6, highlightthickness=0,
            insertbackground=self.colors["text_main"],
            selectbackground="#3A3A3C", selectforeground=self.colors["text_main"],
            disabledbackground=self.colors["bg_main"],
            disabledforeground=self.colors["success"]
        )
        self.time_entry.pack(side="left")

        self.btn_frame = tk.Frame(self.main_frame, bg=self.colors["bg_main"])
        self.btn_frame.pack(side="right", padx=(10, 0))

        self.btn_start = self.create_btn("▶", self.toggle, self.colors["text_main"])
        self.create_btn("✓", self.complete_early, self.colors["success"])
        self.create_btn("⟳", self.reset, self.colors["text_main"])
        self.create_btn("✕", self.root.destroy, self.colors["danger"])

    def create_btn(self, text, cmd, fg_color):
        b = tk.Button(self.btn_frame, text=text, command=cmd, 
                      bg=self.colors["bg_main"], fg=fg_color, 
                      bd=0, font=self.f_btn, activebackground=self.colors["bg_main"], 
                      activeforeground=fg_color, cursor="hand2", takefocus=False)
        b.pack(side="left", padx=3)
        return b

    def blink_text(self):
        if not self.alarm_active: return
        
        target_color = self.colors["danger"] if self.blink_state else "#FFFFFF"
        self.blink_state = not self.blink_state
        
        self.task_entry.config(disabledforeground=target_color, fg=target_color)
        self.time_entry.config(disabledforeground=target_color, fg=target_color)
        
        self.root.after(600, self.blink_text)

    def update_clock(self):
        if self.running and self.seconds > 0:
            self.seconds -= 1
            self.update_display_text()
            self.root.after(1000, self.update_clock)
        elif self.seconds == 0 and self.running:
            self.running = False
            self.alarm_active = True
            self.blink_state = True
            
            self.task_entry.config(state="disabled", disabledforeground=self.colors["danger"])
            self.time_entry.config(state="disabled", disabledforeground=self.colors["danger"])
            
            self.alert.show(self.colors["danger"])
            self.blink_text()
            self.btn_start.config(text="■")

    def toggle(self, event=None):
        if event and event.keysym == 'space' and self.root.focus_get() == self.task_entry: return
        
        if self.task_entry['state'] == 'disabled':
            return "break"

        if not self.running:
            self.apply_timer_input()
            self.running = True
            self.btn_start.config(text="⏸")
            self.alert.stop()
            self.alarm_active = False
            
            if self.task_var.get() != self.task_placeholder:
                 self.task_entry.config(fg=self.colors["text_main"])
            
            self.time_entry.config(fg=self.colors["text_main"], insertbackground=self.colors["bg_main"])
            self.root.focus_set() 
            self.update_clock()
        else:
            self.running = False
            self.btn_start.config(text="▶")
            self.time_entry.config(fg=self.colors["accent"], insertbackground=self.colors["text_main"])
        return "break"

    def complete_early(self, event=None):
        if not self.running and self.seconds == (self.minutes * 60): return
        self.running = False
        self.alarm_active = False
        self.alert.stop()
        
        self.task_entry.config(state="disabled", disabledforeground=self.colors["success"])
        self.time_entry.config(state="disabled", disabledforeground=self.colors["success"])
        
        self.btn_start.config(text="▶")
        self.root.focus_set()

    def reset(self):
        self.alert.stop()
        self.alarm_active = False
        self.running = False
        self.seconds = self.default_minutes * 60
        self.update_display_text()
        
        self.btn_start.config(text="▶")
        
        self.time_entry.config(state="normal", fg=self.colors["text_main"], insertbackground=self.colors["text_main"])
        self.task_entry.config(state="normal", fg=self.colors["text_meta"])
        
        self.task_entry.delete(0, tk.END)
        self.task_entry.insert(0, self.task_placeholder)
        self.root.focus_set()

    def on_timer_keypress(self, event):
        if self.running and event.keysym not in ["Return", "space"]: 
            return "break"

    def apply_timer_input(self):
        try:
            val = self.time_entry.get()
            p = list(map(int, val.split(":"))) if ":" in val else [int(val), 0]
            self.seconds = p[0] * 60 + p[1]
            self.minutes = self.seconds // 60
        except: pass

    def update_display_text(self):
        prev_state = self.time_entry['state']
        self.time_entry.config(state='normal')
        self.time_entry.delete(0, tk.END)
        self.time_entry.insert(0, f"{self.seconds // 60:02}:{self.seconds % 60:02}")
        self.time_entry.config(state=prev_state)

    def on_task_in(self, e):
        if self.task_var.get() == self.task_placeholder:
            self.task_entry.delete(0, tk.END)
            self.task_entry.config(fg=self.colors["text_main"])
            
    def on_task_out(self, e):
        if self.task_var.get() == "":
            self.task_entry.insert(0, self.task_placeholder)
            self.task_entry.config(fg=self.colors["text_meta"])

    def setup_binds(self):
        self.canvas.bind('<Button-1>', self.start_move)
        self.canvas.bind('<B1-Motion>', self.do_move)
        self.main_frame.bind('<Button-1>', self.start_move)
        self.grip_canvas.bind('<Button-1>', self.start_move)
        self.grip_canvas.bind('<B1-Motion>', self.do_move)
        
        self.task_entry.bind('<Return>', self.toggle)
        self.time_entry.bind('<Return>', self.toggle)
        self.time_entry.bind('<Key>', self.on_timer_keypress)
        
        self.root.bind('<Control-Return>', self.complete_early)
        self.root.bind('<space>', self.toggle)

    def start_move(self, event):
        if event.widget not in [self.task_entry, self.time_entry]:
            self.root.focus_set()
        self.x, self.y = event.x, event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    FocusTimer()