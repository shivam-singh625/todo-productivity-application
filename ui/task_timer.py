"""
task_timer.py — Per-task timer widget.

Fixes:
1. Closing app/float does NOT reset timer — elapsed is saved to DB
2. Auto-hide removed — float stays until manually closed
3. Seek bar — scrub forward/backward like a music track
4. Pause saves position to DB — resumes from exact position
5. Close only hides float, timer state persists in task row
"""
import gi, subprocess
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, GObject, Gdk
from backend import config_manager
from ui.sound import play_sound_tracked, stop_sound

_active_timers: dict = {}
_float_win = None


def set_float_window(win):
    global _float_win
    _float_win = win


def get_float_window():
    return _float_win


def stop_all_timers():
    """Pause all timers and save state — called on app close."""
    for t in list(_active_timers.values()):
        if t.running:
            t.pause()   # pause saves elapsed to DB
    stop_sound()


def stop_all_except(task_id: int):
    for k, t in _active_timers.items():
        if k != task_id and t.running:
            t.pause()


class TaskTimer(Gtk.Box):

    __gsignals__ = {
        "timer-finished": (GObject.SignalFlags.RUN_FIRST, None, (int, str)),
    }

    def __init__(self, task_id, task_title, mode,
                 initial_seconds=0, elapsed_seconds=0,
                 category_id=None, tm=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.task_id          = task_id
        self.task_title       = task_title
        self.mode             = mode
        self.initial_secs     = initial_seconds
        self.category_id      = category_id
        self._tm              = tm
        self.running          = False
        self._timer_id        = None
        self._session_id      = None
        self._session_elapsed = 0
        self._live_update_id  = None

        # Fix 4: resume from saved position
        if mode == "countdown":
            # elapsed_seconds = how many seconds already counted down
            self._seconds = max(0, initial_seconds - elapsed_seconds)
        else:
            self._seconds = elapsed_seconds  # stopwatch: resume from where stopped

        _active_timers[task_id] = self
        self._build()
        self._update_display()
        self._apply_css()

    def _build(self):
        self.add_css_class("task-timer-box")

        icon = Gtk.Label(label="⏱" if self.mode == "stopwatch" else "⏳")
        icon.set_margin_end(2)
        self.append(icon)

        self._time_lbl = Gtk.Label()
        self._time_lbl.add_css_class("task-timer-label")
        self._time_lbl.set_width_chars(7)
        self.append(self._time_lbl)

        # Progress bar — also acts as seek bar for countdown
        if self.mode == "countdown" and self.initial_secs > 0:
            self._progress = Gtk.ProgressBar()
            self._progress.add_css_class("task-timer-progress")
            self._progress.set_hexpand(True)
            self._progress.set_tooltip_text("Click to seek")
            # Make progress bar clickable for seeking
            click = Gtk.GestureClick()
            click.connect("released", self._on_seek_click)
            self._progress.add_controller(click)
            self.append(self._progress)
        else:
            self._progress = None

        # Fix 2: seek backward 30s
        if self.mode == "countdown":
            bk_btn = Gtk.Button(label="«")
            bk_btn.add_css_class("flat")
            bk_btn.add_css_class("task-timer-btn")
            bk_btn.set_tooltip_text("Back 30 seconds")
            bk_btn.connect("clicked", lambda _: self._seek(-30))
            self.append(bk_btn)

        self._start_btn = Gtk.Button(label="▶")
        self._start_btn.add_css_class("flat")
        self._start_btn.add_css_class("task-timer-btn")
        self._start_btn.set_tooltip_text("Start / Pause")
        self._start_btn.connect("clicked", self._on_start_pause)
        self.append(self._start_btn)

        # Fix 2: seek forward 30s
        if self.mode == "countdown":
            fw_btn = Gtk.Button(label="»")
            fw_btn.add_css_class("flat")
            fw_btn.add_css_class("task-timer-btn")
            fw_btn.set_tooltip_text("Forward 30 seconds")
            fw_btn.connect("clicked", lambda _: self._seek(30))
            self.append(fw_btn)

        reset_btn = Gtk.Button(label="↺")
        reset_btn.add_css_class("flat")
        reset_btn.add_css_class("task-timer-btn")
        reset_btn.set_tooltip_text("Reset to beginning")
        reset_btn.connect("clicked", lambda _: self.reset())
        self.append(reset_btn)

        self._stop_snd_btn = Gtk.Button(label="🔇")
        self._stop_snd_btn.add_css_class("task-timer-stop-btn")
        self._stop_snd_btn.set_tooltip_text("Stop alert sound")
        self._stop_snd_btn.connect("clicked", self._on_stop_sound)
        self._stop_snd_btn.set_visible(False)
        self.append(self._stop_snd_btn)

    def _fmt(self, s):
        s = abs(int(s))
        h, r = divmod(s, 3600)
        m, sec = divmod(r, 60)
        return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

    def _get_fraction(self) -> float:
        if self.mode == "countdown":
            if self.initial_secs <= 0: return 0.0
            return max(0.0, min(1.0, 1.0 - self._seconds / self.initial_secs))
        return min(1.0, self._seconds / 7200)

    def _update_display(self):
        txt = self._fmt(self._seconds)
        self._time_lbl.set_text(txt)
        self._start_btn.set_label("⏸" if self.running else "▶")
        if self._progress and self.initial_secs > 0:
            self._progress.set_fraction(self._get_fraction())
        if _float_win and _float_win.get_visible():
            if getattr(_float_win, "_active_timer", None) is self:
                mode = "Stopwatch" if self.mode == "stopwatch" else "Countdown"
                _float_win.update_time(txt, self.running, self._get_fraction(), mode)

    def _get_elapsed(self) -> int:
        """Total seconds elapsed (used for DB persistence)."""
        if self.mode == "countdown":
            return self.initial_secs - self._seconds
        return self._seconds

    # ── Seek ─────────────────────────────────────────────────────────────────

    def _seek(self, delta_seconds: int):
        """Seek forward (positive) or backward (negative) by delta_seconds."""
        if self.mode != "countdown":
            return
        self._seconds = max(0, min(self.initial_secs, self._seconds - delta_seconds))
        self._save_elapsed()
        self._update_display()

    def _on_seek_click(self, gesture, n_press, x, y):
        """Clicking the progress bar seeks to that position."""
        if self.mode != "countdown" or self.initial_secs <= 0:
            return
        bar = self._progress
        width = bar.get_allocated_width()
        if width <= 0:
            return
        frac = max(0.0, min(1.0, x / width))
        # frac = how much is elapsed (filled)
        self._seconds = int(self.initial_secs * (1.0 - frac))
        self._save_elapsed()
        self._update_display()

    # ── Controls ──────────────────────────────────────────────────────────────

    def start(self):
        if self.running:
            return
        stop_all_except(self.task_id)
        self.running   = True
        self._timer_id = GLib.timeout_add(1000, self._tick)
        if self._tm and self._session_id is None:
            self._session_id      = self._tm.start_session(self.task_id, self.category_id)
            self._session_elapsed = 0
        if self._live_update_id is None:
            self._live_update_id = GLib.timeout_add(5000, self._live_write)
        self._show_float()
        self._update_display()

    def pause(self):
        if not self.running:
            return
        self.running = False
        if self._timer_id:
            GLib.source_remove(self._timer_id); self._timer_id = None
        if self._live_update_id:
            GLib.source_remove(self._live_update_id); self._live_update_id = None
        if self._tm and self._session_id:
            self._tm.end_session(self._session_id)
            self._session_id = None; self._session_elapsed = 0
        # Fix 3 + Fix 1: save elapsed position to DB on every pause
        self._save_elapsed()
        self._update_display()
        # Fix 1: do NOT hide float window on pause

    def reset(self):
        """Reset to beginning — clears saved position."""
        was_running = self.running
        self.pause()
        self._seconds = self.initial_secs if self.mode == "countdown" else 0
        self._save_elapsed()  # save 0 elapsed
        self._stop_snd_btn.set_visible(False)
        self._update_display()
        # Fix 1: don't hide float on reset

    def _save_elapsed(self):
        """Persist current position to DB."""
        if self._tm:
            self._tm.save_timer_elapsed(self.task_id, self._get_elapsed())

    def _on_start_pause(self, _):
        if self.running: self.pause()
        else:            self.start()

    def _on_stop_sound(self, _):
        stop_sound(); self._stop_snd_btn.set_visible(False)

    def _tick(self) -> bool:
        if not self.running: return False
        self._session_elapsed += 1
        if self.mode == "stopwatch":
            self._seconds += 1
        else:
            self._seconds -= 1
            if self._seconds <= 0:
                self._seconds = 0
                self._update_display()
                self._on_finished()
                return False
        self._update_display()
        return True

    def _live_write(self) -> bool:
        if not self.running: self._live_update_id = None; return False
        self._session_elapsed += 5
        if self._tm and self._session_id:
            self._tm.update_session_live(self._session_id, self._session_elapsed)
        # Also persist position every 5s
        self._save_elapsed()
        return True

    def _on_finished(self):
        self.running = False; self._timer_id = None
        if self._live_update_id:
            GLib.source_remove(self._live_update_id); self._live_update_id = None
        if self._tm and self._session_id:
            self._tm.end_session(self._session_id)
            self._session_id = None; self._session_elapsed = 0
        self._save_elapsed()
        self._send_notif()
        proc = play_sound_tracked(config_manager.load().get("alert_sound", "system-default"))
        if proc:
            self._stop_snd_btn.set_visible(True)
            GLib.timeout_add(200, self._poll_sound)
        self.emit("timer-finished", self.task_id, self.task_title)
        if _float_win:
            _float_win.flash_finished()
            # Fix 1: don't auto-hide — let user close manually

    def _send_notif(self):
        try:
            subprocess.Popen(["notify-send", "--urgency=normal", "--icon=alarm",
                "Task timer finished", f"'{self.task_title}' time is over."],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception: pass

    def _poll_sound(self):
        from ui.sound import _sound_process
        if _sound_process is None or _sound_process.poll() is not None:
            self._stop_snd_btn.set_visible(False); return False
        return True

    def _show_float(self):
        if _float_win is None: return
        icon  = "⏱" if self.mode == "stopwatch" else "⏳"
        title = f"{icon} {self.task_title}"
        mode  = "Stopwatch" if self.mode == "stopwatch" else "Countdown"
        _float_win.attach_timer(self)
        _float_win.show_for_timer(title, self._fmt(self._seconds),
                                  self.running, self._get_fraction(), mode)

    def _apply_css(self):
        css = b"""
        .task-timer-box {
            background-color: rgba(137,180,250,0.08);
            border-radius: 8px; padding: 5px 10px;
            border: 1px solid rgba(137,180,250,0.25);
            margin-top: 6px;
        }
        .task-timer-label {
            font-size: 0.85em; font-variant-numeric: tabular-nums;
            font-weight: 700; min-width: 55px; color: #89b4fa;
        }
        .task-timer-btn { padding: 0 4px; min-width: 22px; min-height: 22px; font-size: 0.8em; }
        .task-timer-stop-btn {
            padding: 2px 6px; font-size: 0.78em;
            background-color: rgba(243,139,168,0.15);
            color: #f38ba8; border-radius: 4px;
            border: 1px solid rgba(243,139,168,0.35);
        }
        .task-timer-progress {
            min-height: 5px; border-radius: 3px; /* cursor: pointer */;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def cleanup(self):
        if self.running: self.pause()
        _active_timers.pop(self.task_id, None)
