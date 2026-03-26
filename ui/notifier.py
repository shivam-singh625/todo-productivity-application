"""
notifier.py — Smart due-date notification service.

Runs a background GLib timer that checks for tasks due soon and fires
Linux desktop notifications via notify-send.

Notification schedule per task:
  • 60 minutes before due  → "Due in 1 hour"
  • 30 minutes before due  → "Due in 30 minutes"
  • 15 minutes before due  → "Due in 15 minutes"
  •  5 minutes before due  → "Due in 5 minutes — start now!"
  •  0 minutes (overdue)   → "Task is now overdue!"
"""

import subprocess
from datetime import datetime, timedelta
from gi.repository import GLib


# Check intervals in minutes → notification text
_WINDOWS = [
    (60, "Due in 1 hour"),
    (30, "Due in 30 minutes"),
    (15, "Due in 15 minutes"),
    (5,  "Due in 5 minutes — start now!"),
    (0,  "Task is now overdue!"),
]

# How often to poll (every 60 seconds)
_POLL_INTERVAL_MS = 60_000


class NotificationService:
    """
    Start with .start(tm, cfg).
    Automatically fires notify-send for tasks approaching their due time.
    """

    def __init__(self):
        self._tm        = None
        self._cfg       = None
        self._timer_id  = None
        # Track which (task_id, window_minutes) pairs were already notified
        self._notified  = set()

    def start(self, task_manager, config: dict):
        self._tm  = task_manager
        self._cfg = config
        if self._timer_id is not None:
            return
        # Run immediately once, then every minute
        self._check()
        self._timer_id = GLib.timeout_add(_POLL_INTERVAL_MS, self._check)

    def stop(self):
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def _check(self) -> bool:
        """Called every minute. Scan for tasks due soon."""
        if not self._cfg.get("notifications", True):
            return True  # keep timer alive, just skip

        try:
            self._scan()
        except Exception:
            pass
        return True  # keep GLib timer running

    def _scan(self):
        now = datetime.now()

        # Look at tasks due today
        tasks = self._tm.get_tasks_due_soon(minutes=65)

        for task in tasks:
            due_str = task["due_date"]
            if not due_str:
                continue

            # Build a naive due datetime — use end-of-day if no time set
            try:
                due_dt = datetime.fromisoformat(due_str)
            except ValueError:
                # date-only format "YYYY-MM-DD" — treat as end of day
                try:
                    due_dt = datetime.strptime(due_str, "%Y-%m-%d").replace(
                        hour=23, minute=59)
                except ValueError:
                    continue

            minutes_left = (due_dt - now).total_seconds() / 60
            tid = task["id"]

            for window, message in _WINDOWS:
                key = (tid, window)
                if key in self._notified:
                    continue
                # Fire if we're within ±2 minutes of the window
                if abs(minutes_left - window) <= 2:
                    self._notify(task["title"], message, window)
                    self._notified.add(key)
                    self._tm.mark_task_notified(tid)

    def _notify(self, task_title: str, message: str, urgency_mins: int):
        if urgency_mins <= 5:
            urgency = "critical"
            icon    = "appointment-missed"
        elif urgency_mins <= 15:
            urgency = "normal"
            icon    = "appointment-soon"
        else:
            urgency = "low"
            icon    = "appointment"

        summary = f"Task: {task_title}"
        body    = message

        try:
            subprocess.Popen(
                ["notify-send",
                 f"--urgency={urgency}",
                 f"--icon={icon}",
                 "--app-name=XFCE Todo",
                 summary, body],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass  # notify-send not installed

    def reset_for_task(self, task_id: int):
        """Call when a task's due date changes — clears its notification history."""
        self._notified = {k for k in self._notified if k[0] != task_id}


# Global singleton
_service = NotificationService()


def start_notifications(task_manager, config: dict):
    _service.start(task_manager, config)


def stop_notifications():
    _service.stop()


def reset_task_notifications(task_id: int):
    _service.reset_for_task(task_id)
