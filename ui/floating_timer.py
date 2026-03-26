"""
floating_timer.py — Two separate windows: expanded toolbar + slim pill.
Switching between them hides one and shows the other.
"""
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

_FLASH = ["#f38ba8", "#1a1b2e"] * 3


def _fmt_time(secs: int) -> str:
    secs = abs(int(secs))
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _make_css():
    css = b"""
    .float-toolbar {
        background-color: rgba(18,19,35,0.97);
        border-radius: 14px;
        border: 1px solid rgba(137,180,250,0.25);
        padding: 10px 14px;
    }
    .float-toolbar.flash {
        background-color: rgba(243,139,168,0.2);
        border-color: rgba(243,139,168,0.6);
    }
    .float-pill {
        background-color: rgba(18,19,35,0.97);
        border-radius: 12px;
        border: 1px solid rgba(137,180,250,0.28);
        padding: 6px 4px;
    }
    .float-pill.flash { background-color: rgba(243,139,168,0.2); }
    .float-task    { font-size:0.82em; font-weight:600; color:#cdd6f4; }
    .float-task:hover { color:#89b4fa; }
    .float-time    { font-size:1.55em; font-weight:900;
                     font-variant-numeric:tabular-nums;
                     color:#89b4fa; letter-spacing:2px; }
    .float-time.warning { color:#f9e2af; }
    .float-time.urgent  { color:#f38ba8; }
    .float-pill-time { font-size:0.68em; font-weight:800;
                       font-variant-numeric:tabular-nums; color:#89b4fa; }
    .float-mode    { font-size:0.62em; color:rgba(137,180,250,0.55);
                     letter-spacing:1px; font-weight:600; }
    .float-btn     { padding:4px 14px; font-size:0.78em; font-weight:600;
                     border-radius:8px; min-width:72px;
                     background-color:rgba(137,180,250,0.13);
                     color:#89b4fa; border:1px solid rgba(137,180,250,0.28); }
    .float-btn:hover { background-color:rgba(137,180,250,0.25); }
    .float-reset   { padding:4px 14px; font-size:0.78em; font-weight:600;
                     border-radius:8px; min-width:72px;
                     background-color:rgba(203,166,247,0.11);
                     color:#cba6f7; border:1px solid rgba(203,166,247,0.22); }
    .float-reset:hover { background-color:rgba(203,166,247,0.22); }
    .float-icon    { padding:2px 5px; font-size:0.75em; font-weight:700;
                     border-radius:6px; min-width:22px; min-height:22px;
                     background-color:rgba(137,180,250,0.1);
                     color:rgba(137,180,250,0.7);
                     border:1px solid rgba(137,180,250,0.15); }
    .float-icon:hover { background-color:rgba(137,180,250,0.22); color:#89b4fa; }
    .float-close   { padding:2px 5px; font-size:0.8em; font-weight:700;
                     border-radius:6px; min-width:22px; min-height:22px;
                     background-color:rgba(243,139,168,0.1);
                     color:rgba(243,139,168,0.7);
                     border:1px solid rgba(243,139,168,0.15); }
    .float-close:hover { background-color:rgba(243,139,168,0.25); color:#f38ba8; }
    .float-progress { min-height:4px; border-radius:3px; }
    """
    p = Gtk.CssProvider()
    p.load_from_data(css)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), p,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 20)

_css_loaded = False


# ── Shared drag helper ────────────────────────────────────────────────────────

def _add_drag(window):
    """Add WM-native drag to a window's root child."""
    state = {"sx": 0.0, "sy": 0.0, "active": False}
    drag = Gtk.GestureDrag()

    def begin(g, x, y):
        state["sx"] = x; state["sy"] = y; state["active"] = True

    def update(g, dx, dy):
        if not state["active"]: return
        try:
            surface = window.get_surface()
            if surface is None: return
            seat = window.get_display().get_default_seat()
            ptr  = seat.get_pointer()
            if hasattr(surface, "begin_move"):
                surface.begin_move(ptr, 1,
                    int(state["sx"]), int(state["sy"]), Gdk.CURRENT_TIME)
                state["active"] = False
        except Exception:
            pass

    def end(g, dx, dy): state["active"] = False

    drag.connect("drag-begin",  begin)
    drag.connect("drag-update", update)
    drag.connect("drag-end",    end)
    return drag


# ── Expanded toolbar window ───────────────────────────────────────────────────

class ExpandedWindow(Gtk.Window):
    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(305, 115)
        self.set_title("Timer")
        self.connect("realize", self._on_realize)
        self._build()

    def _on_realize(self, _):
        self._apply_keep_above()

    def _apply_keep_above(self):
        """Force the window to stay above all others via X11."""
        try:
            s = self.get_surface()
            if s and hasattr(s, "set_keep_above"):
                s.set_keep_above(True)
        except Exception:
            pass
        # Fallback: use xdotool to set always-on-top property
        try:
            import subprocess
            title = self.get_title() or "Timer"
            subprocess.Popen(
                ["xdotool", "search", "--name", title, "set_window", "--overrideredirect", "0"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _build(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.add_css_class("float-toolbar")
        self._box = box

        # Row 1: name | mode | [<<] [x]
        top = Gtk.Box(spacing=6)

        nb = Gtk.Button(); nb.add_css_class("flat")
        self._name = Gtk.Label(label="Timer")
        self._name.add_css_class("float-task")
        self._name.set_halign(Gtk.Align.START)
        self._name.set_ellipsize(3)
        self._name.set_max_width_chars(18)
        nb.set_child(self._name); nb.set_hexpand(True)
        nb.connect("clicked", lambda _: self._owner._on_name_click())
        top.append(nb)

        self._mode = Gtk.Label(label="")
        self._mode.add_css_class("float-mode")
        top.append(self._mode)

        col = Gtk.Button(label="<<")
        col.add_css_class("float-icon")
        col.set_tooltip_text("Collapse to pill")
        col.connect("clicked", lambda _: self._owner.collapse())
        top.append(col)

        xb = Gtk.Button(label="x")
        xb.add_css_class("float-close")
        xb.set_tooltip_text("Close timer")
        xb.connect("clicked", lambda _: self._owner._on_close())
        top.append(xb)
        box.append(top)

        # Time
        self._time = Gtk.Label(label="00:00")
        self._time.add_css_class("float-time")
        self._time.set_halign(Gtk.Align.CENTER)
        box.append(self._time)

        # Progress
        self._prog = Gtk.ProgressBar()
        self._prog.add_css_class("float-progress")
        self._prog.set_fraction(0.0)
        box.append(self._prog)

        # Buttons
        btns = Gtk.Box(spacing=8)
        btns.set_halign(Gtk.Align.CENTER)
        btns.set_margin_top(2)

        self._pp = Gtk.Button(label="Start")
        self._pp.add_css_class("float-btn")
        self._pp.connect("clicked", lambda _: self._owner._on_pause_resume())
        btns.append(self._pp)

        rst = Gtk.Button(label="Reset")
        rst.add_css_class("float-reset")
        rst.set_tooltip_text("Reset — window stays open")
        rst.connect("clicked", lambda _: self._owner._on_reset())
        btns.append(rst)
        box.append(btns)

        self.set_child(box)

        drag = _add_drag(self)
        box.add_controller(drag)

        hover = Gtk.EventControllerMotion()
        hover.connect("enter", lambda *_: self._owner._cancel_hide())
        # No auto-hide on leave — user must close manually
        self.add_controller(hover)

    def set_time(self, t, running, frac, mode):
        self._time.set_label(t)
        self._pp.set_label("Pause" if running else "Start")
        self._prog.set_fraction(max(0.0, min(1.0, frac)))
        self._mode.set_label(mode.upper())
        self._time.remove_css_class("warning")
        self._time.remove_css_class("urgent")
        if frac > 0:
            rem = 1.0 - frac
            if   rem < 0.10: self._time.add_css_class("urgent")
            elif rem < 0.25: self._time.add_css_class("warning")

    def set_name(self, name):
        short = name[:20] + ("…" if len(name) > 20 else "")
        self._name.set_label(short)

    def flash(self, on):
        if on: self._box.add_css_class("flash")
        else:  self._box.remove_css_class("flash")


# ── Pill window ───────────────────────────────────────────────────────────────

class PillWindow(Gtk.Window):
    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self.set_decorated(False)
        self.set_resizable(False)
        # Fixed small size — GTK will honour this for an undecorated window
        self.set_default_size(46, 170)
        self.set_size_request(46, 170)
        self.set_title("Timer")
        self.connect("realize", self._on_realize)
        self._build()

    def _on_realize(self, _):
        try:
            s = self.get_surface()
            if s and hasattr(s, "set_keep_above"):
                s.set_keep_above(True)
        except Exception:
            pass

    def _build(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_size_request(46, 170)

        pill = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        pill.add_css_class("float-pill")
        pill.set_size_request(42, -1)
        pill.set_halign(Gtk.Align.CENTER)
        pill.set_valign(Gtk.Align.START)
        self._pill = pill

        # >> expand
        exp = Gtk.Button(label=">>")
        exp.add_css_class("float-icon")
        exp.set_halign(Gtk.Align.CENTER)
        exp.set_tooltip_text("Expand")
        exp.connect("clicked", lambda _: self._owner.expand())
        pill.append(exp)

        # icon
        self._icon = Gtk.Label(label="⏳")
        self._icon.set_halign(Gtk.Align.CENTER)
        pill.append(self._icon)

        # time
        self._time = Gtk.Label(label="00:00")
        self._time.add_css_class("float-pill-time")
        self._time.set_halign(Gtk.Align.CENTER)
        pill.append(self._time)

        # pause/resume
        self._pp = Gtk.Button(label="||")
        self._pp.add_css_class("float-icon")
        self._pp.set_halign(Gtk.Align.CENTER)
        self._pp.connect("clicked", lambda _: self._owner._on_pause_resume())
        pill.append(self._pp)

        # close
        xb = Gtk.Button(label="x")
        xb.add_css_class("float-close")
        xb.set_halign(Gtk.Align.CENTER)
        xb.set_tooltip_text("Close timer")
        xb.connect("clicked", lambda _: self._owner._on_close())
        pill.append(xb)

        outer.append(pill)
        self.set_child(outer)

        drag = _add_drag(self)
        outer.add_controller(drag)

        hover = Gtk.EventControllerMotion()
        hover.connect("enter", lambda *_: self._owner._cancel_hide())
        # No auto-hide on leave — user must close manually
        self.add_controller(hover)

    def set_time(self, t, running, is_sw):
        self._time.set_label(t)
        self._icon.set_label("⏱" if is_sw else "⏳")
        self._pp.set_label("||" if running else "|>")

    def flash(self, on):
        if on: self._pill.add_css_class("flash")
        else:  self._pill.remove_css_class("flash")


# ── Controller ────────────────────────────────────────────────────────────────

class FloatingTimerWindow:
    """
    Controller that owns both windows and switches between them.
    Presents the same interface to task_timer and pomodoro_timer.
    """

    def __init__(self):
        global _css_loaded
        if not _css_loaded:
            _make_css()
            _css_loaded = True

        self._active_timer    = None
        self._active_pomodoro = None
        self._main_win_ref    = None
        self._hide_timer      = None
        self._flash_id        = None
        self._flash_step      = 0
        self._resetting       = False
        self._collapsed       = False
        self._mode_label      = ""
        self._is_sw           = False

        self._exp  = ExpandedWindow(self)
        self._pill = PillWindow(self)
        # Keep-above timer — re-applies every 2 seconds to prevent going behind
        GLib.timeout_add(2000, self._enforce_keep_above)

    # ── Collapse / Expand ─────────────────────────────────────────────────────

    def collapse(self):
        self._collapsed = True
        if self._exp.get_visible():
            self._exp.hide()
        self._pill.present()

    def expand(self):
        self._collapsed = False
        if self._pill.get_visible():
            self._pill.hide()
        self._exp.present()

    # ── Public API (same interface as before) ─────────────────────────────────

    def attach_timer(self, t):
        self._active_timer = t; self._active_pomodoro = None

    def attach_pomodoro(self, p):
        self._active_pomodoro = p; self._active_timer = None

    def get_visible(self):
        return self._exp.get_visible() or self._pill.get_visible()

    def present(self):
        if self._collapsed:
            self._pill.present()
            GLib.idle_add(self._pill._apply_keep_above)
        else:
            self._exp.present()
            GLib.idle_add(self._exp._apply_keep_above)

    def hide(self):
        self._exp.hide()
        self._pill.hide()

    def _enforce_keep_above(self) -> bool:
        """Re-apply always-on-top every 2s to prevent window going behind."""
        if self._exp.get_visible():
            self._exp._apply_keep_above()
        if self._pill.get_visible():
            self._pill._apply_keep_above()
        return True  # keep timer running

    def show_for_timer(self, title, time_str, running,
                       fraction=0.0, mode_label=""):
        self._mode_label = mode_label
        self._is_sw      = "stopwatch" in mode_label.lower()
        self._exp.set_name(title)
        self._exp.set_time(time_str, running, fraction, mode_label)
        self._pill.set_time(time_str, running, self._is_sw)
        self._cancel_flash()
        if not self.get_visible():
            self.present()
        self._cancel_hide()

    def update_time(self, time_str, running, fraction=0.0, mode_label=""):
        self._mode_label = mode_label
        self._is_sw      = "stopwatch" in mode_label.lower()
        self._exp.set_time(time_str, running, fraction, mode_label)
        self._pill.set_time(time_str, running, self._is_sw)

    def flash_finished(self):
        self._flash_step = 0
        self._cancel_flash()
        self._flash_id = GLib.timeout_add(300, self._do_flash)

    def hide_after_stop(self, seconds=15):
        if self._resetting:
            self._resetting = False
            return
        self._schedule_hide(seconds)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _do_flash(self):
        if self._flash_step >= len(_FLASH):
            self._flash_id = None
            self._exp.flash(False); self._pill.flash(False)
            return False
        on = (self._flash_step % 2 == 0)
        self._exp.flash(on); self._pill.flash(on)
        self._flash_step += 1
        return True

    def _cancel_flash(self):
        if self._flash_id:
            GLib.source_remove(self._flash_id); self._flash_id = None
        self._exp.flash(False); self._pill.flash(False)

    def _schedule_hide(self, s):
        self._cancel_hide()
        self._hide_timer = GLib.timeout_add_seconds(s, self._auto_hide)

    def _cancel_hide(self):
        if self._hide_timer:
            GLib.source_remove(self._hide_timer); self._hide_timer = None

    def _auto_hide(self):
        """Auto-hide disabled — timer widget stays until user closes it."""
        self._hide_timer = None
        return False

    # ── Button actions ────────────────────────────────────────────────────────

    def _on_pause_resume(self):
        if self._active_timer is not None:
            t = self._active_timer
            if t.running: t.pause()
            else:         t.start()
            lbl = "Pause" if t.running else "Start"
            self._exp._pp.set_label(lbl)
            self._pill._pp.set_label("||" if t.running else "|>")
        elif self._active_pomodoro is not None:
            self._active_pomodoro.float_pause_resume()

    def _on_reset(self):
        self._resetting = True
        self._cancel_hide(); self._cancel_flash()
        if self._active_timer is not None:
            t = self._active_timer
            t.reset()
            reset_str = _fmt_time(t.initial_secs if t.mode == "countdown" else 0)
            self._exp.set_time(reset_str, False, 0.0, self._mode_label)
            self._pill.set_time(reset_str, False, self._is_sw)
        elif self._active_pomodoro is not None:
            self._active_pomodoro.float_reset()
            self._exp._pp.set_label("Start")
            self._pill._pp.set_label("|>")
        self._resetting = False
        if not self.get_visible():
            self.present()

    def _on_close(self):
        """Close the floating window — PAUSE the timer (saves position), do NOT reset."""
        self._cancel_hide(); self._cancel_flash()
        if self._active_timer is not None:
            if self._active_timer.running:
                self._active_timer.pause()   # pause saves elapsed to DB
            # Keep _active_timer reference — user can reopen from task row
        if self._active_pomodoro is not None:
            if self._active_pomodoro._running:
                self._active_pomodoro.float_pause_resume()  # pause it
        self.hide()

    def _on_name_click(self):
        if self._main_win_ref:
            self._main_win_ref.present()
