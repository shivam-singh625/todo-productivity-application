#!/usr/bin/env python3
"""main.py — Entry point. Run with: ./run.sh"""
import sys, os

# Must be set before GTK imports
os.environ.setdefault("GDK_BACKEND", "x11")

# Ensure THIS directory is first on path so backend/ and ui/ are found
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, Gdk

from backend import config_manager
from backend.task_manager import TaskManager
from ui.main_window import MainWindow


class XFCETodoApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            # Use NON_UNIQUE so multiple instances are allowed
            # and do_activate is always called even if another instance ran before
            application_id="org.xfce.todo.app",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

    def do_activate(self):
        cfg  = config_manager.load()
        dark = (cfg.get("theme", "dark") != "light")
        tm   = TaskManager(cfg["database_path"])
        win  = MainWindow(self, tm, cfg, dark=dark)
        win.set_resizable(True)
        win.set_opacity(1.0)
        win.connect("close-request", self._on_close)
        win.present()

    def _on_close(self, win):
        from ui.task_timer import stop_all_timers
        stop_all_timers()
        return False


if __name__ == "__main__":
    sys.exit(XFCETodoApp().run(sys.argv))
