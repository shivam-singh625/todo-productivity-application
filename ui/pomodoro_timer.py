"""pomodoro_timer.py — Pomodoro timer with floating window support."""
import gi, subprocess
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, GObject


class PomodoroTimer(Gtk.Box):
    __gsignals__ = {"session-completed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, tm, cfg):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._tm   = tm
        self._cfg  = cfg
        self._wm   = cfg.get("pomodoro_work_mins", 25)
        self._bm   = cfg.get("pomodoro_break_mins", 5)
        self._is_break = False
        self._secs     = self._wm * 60
        self.running   = False
        self._tid      = None
        self._sessions = tm.pomodoro_sessions_today()
        self._float_win = None   # set by MainWindow after creation
        self._build()
        self._update()

    def set_float_window(self, win):
        """Wire the shared floating window to this Pomodoro timer."""
        self._float_win = win

    def _build(self):
        self.add_css_class("pomodoro-panel")
        self.set_margin_start(8); self.set_margin_end(8)
        self.set_margin_top(6);   self.set_margin_bottom(6)

        title = Gtk.Label(label="🍅 Pomodoro")
        title.add_css_class("section-heading")
        self.append(title)

        self._mode_lbl = Gtk.Label()
        self._mode_lbl.add_css_class("pomodoro-mode")
        self.append(self._mode_lbl)

        self._clock = Gtk.Label()
        self._clock.add_css_class("pomodoro-clock")
        self.append(self._clock)

        self._prog = Gtk.ProgressBar()
        self._prog.add_css_class("pomodoro-progress")
        self.append(self._prog)

        self._sess_lbl = Gtk.Label()
        self._sess_lbl.add_css_class("stat-card-label")
        self.append(self._sess_lbl)

        row = Gtk.Box(spacing=6); row.set_halign(Gtk.Align.CENTER)

        self._sbtn = Gtk.Button(label="Start")
        self._sbtn.add_css_class("suggested-action")
        self._sbtn.connect("clicked", self._on_sp)
        row.append(self._sbtn)

        rb = Gtk.Button(label="Reset")
        rb.connect("clicked", self._on_reset)
        row.append(rb)

        self.append(row)

    def _update(self):
        m, s = divmod(self._secs, 60)
        time_str = f"{m:02d}:{s:02d}"
        self._clock.set_text(time_str)
        self._mode_lbl.set_text("☕ Break" if self._is_break else "🎯 Focus")
        self._sess_lbl.set_text(f"Sessions today: {self._sessions}")
        total = (self._bm if self._is_break else self._wm) * 60
        self._prog.set_fraction(max(0, 1 - self._secs / total))
        self._sbtn.set_label("Pause" if self.running else "Start")

        # Update floating window if it belongs to Pomodoro
        if self._float_win and self._float_win.get_visible():
            if getattr(self._float_win, '_active_timer', None) is self:
                self._float_win.update_time(time_str, self.running)

    def _on_sp(self, _):
        if self.running:
            self.running = False
            if self._tid: GLib.source_remove(self._tid); self._tid = None
            if self._float_win:
                self._float_win.hide_after_stop()
        else:
            self.running = True
            self._tid = GLib.timeout_add(1000, self._tick)
            self._show_float()
        self._update()

    def _on_reset(self, _):
        self.running = False
        if self._tid: GLib.source_remove(self._tid); self._tid = None
        self._is_break = False
        self._secs = self._wm * 60
        if self._float_win: self._float_win.hide()
        self._update()

    def _tick(self):
        if not self.running: return False
        self._secs -= 1
        if self._secs <= 0: self._phase_done(); return False
        self._update(); return True

    def _phase_done(self):
        self.running = False; self._tid = None
        if not self._is_break:
            self._sessions += 1
            self._tm.log_pomodoro(self._wm, True)
            self.emit("session-completed")
            self._notify("Focus session complete! 🍅", "Time for a break.")
            self._is_break = True; self._secs = self._bm * 60
        else:
            self._notify("Break over!", "Ready for the next session.")
            self._is_break = False; self._secs = self._wm * 60
        if self._float_win: self._float_win.hide_after_stop()
        self._update()
        # Auto-start next phase
        self.running = True; self._tid = GLib.timeout_add(1000, self._tick)
        self._update()

    def _show_float(self):
        if self._float_win is None: return
        label = "☕ Break" if self._is_break else "🎯 Pomodoro Focus"
        m, s  = divmod(self._secs, 60)
        # Wire float window to this Pomodoro (use attach_timer-like API)
        self._float_win._active_timer = self
        self._float_win._pause_resume_cb = self._toggle_pause
        self._float_win._stop_cb = self._on_reset
        self._float_win.show_for_timer(label, f"{m:02d}:{s:02d}", self.running)

    def _toggle_pause(self):
        """Called by floating window Pause button."""
        if self.running:
            self.running = False
            if self._tid: GLib.source_remove(self._tid); self._tid = None
            if self._float_win: self._float_win.hide_after_stop()
        else:
            self.running = True
            self._tid = GLib.timeout_add(1000, self._tick)
        self._update()

    def _notify(self, s, b):
        try:
            subprocess.Popen(["notify-send", s, b],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
