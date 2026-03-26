"""task_manager.py — Service layer"""
import sqlite3
from backend import database as db

class TaskManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: sqlite3.Connection = db.get_connection(db_path)
        db.initialise_schema(self.conn)
        db.init_test_schema(self.conn)   # always ensure test tables exist
        db.init_test_schema(self.conn)   # always init test tables on startup

    def reconnect(self, new_path):
        try: self.conn.close()
        except: pass
        self.db_path = new_path
        self.conn = db.get_connection(new_path)
        db.initialise_schema(self.conn)
        db.init_test_schema(self.conn)

    # Categories
    def get_categories(self): return db.fetch_categories(self.conn)
    def add_category(self, name, color="#5294e2"): return db.add_category(self.conn, name, color)
    def rename_category(self, cid, name): db.rename_category(self.conn, cid, name)
    def delete_category(self, cid): db.delete_category(self.conn, cid)

    # Tasks
    def get_tasks(self, **kw): return db.fetch_tasks(self.conn, **kw)
    def get_task(self, tid): return db.fetch_task(self.conn, tid)
    def add_task(self, **kw): return db.add_task(self.conn, **kw)
    def update_task(self, tid, **fields): db.update_task(self.conn, tid, **fields)
    def delete_task(self, tid): db.delete_task(self.conn, tid)
    def toggle_complete(self, tid):
        row = db.fetch_task(self.conn, tid)
        new = 0 if row["completed"] else 1
        from datetime import datetime
        if new:
            # Store as YYYY-MM-DD HH:MM:SS local time — SQLite DATE() parses this correctly
            at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Unchecking — always clear completed_at completely
            at = None
        db.update_task(self.conn, tid, completed=new, completed_at=at)
        return bool(new)
    def reorder_tasks(self, ids): db.reorder_tasks(self.conn, ids)
    def get_tasks_by_date(self, ds): return db.fetch_tasks_by_date(self.conn, ds)

    # Time sessions
    def start_session(self, task_id, category_id=None):
        return db.start_time_session(self.conn, task_id, category_id)

    def end_session(self, session_id):
        db.end_time_session(self.conn, session_id)

    def update_session_live(self, session_id, elapsed_seconds: int):
        """Update duration of a live session for real-time dashboard display."""
        db.update_time_session_duration(self.conn, session_id, elapsed_seconds)

    # Dashboard stats
    def today_focus_seconds(self): return db.get_today_focus_seconds(self.conn)
    def today_completed_count(self): return db.get_today_completed_count(self.conn)
    def category_focus_today(self): return db.get_category_focus_today(self.conn)
    def weekly_focus(self): return db.get_weekly_focus(self.conn)
    def total_tasks_count(self): return db.get_total_tasks_count(self.conn)
    def completed_tasks_count(self): return db.get_completed_tasks_count(self.conn)
    def overdue_count(self): return db.get_overdue_count(self.conn)
    def upcoming_count(self): return db.get_upcoming_count(self.conn)

    # Pomodoro
    def log_pomodoro(self, duration=25, completed=True): db.add_pomodoro_session(self.conn, duration, completed)
    def pomodoro_sessions_today(self): return db.count_pomodoro_sessions_today(self.conn)

    # ── Streaks ───────────────────────────────────────────────────────────────
    def daily_streak(self):          return db.get_daily_streak(self.conn)
    def longest_daily_streak(self):  return db.get_longest_daily_streak(self.conn)
    def weekly_streak(self):         return db.get_weekly_streak(self.conn)
    def longest_weekly_streak(self): return db.get_longest_weekly_streak(self.conn)
    def completed_by_day(self, days=30): return db.get_completed_tasks_by_day(self.conn, days)
    def today_streak_status(self):   return db.get_today_streak_status(self.conn)

    # ── Streaks ───────────────────────────────────────────────────────────────
    def daily_streak(self):         return db.get_daily_streak(self.conn)
    def weekly_streak(self):        return db.get_weekly_streak(self.conn)
    def longest_daily_streak(self): return db.get_longest_daily_streak(self.conn)
    def longest_weekly_streak(self):return db.get_longest_weekly_streak(self.conn)
    def last_30_days_activity(self): return db.get_last_30_days_activity(self.conn)

    # ── Notifications ─────────────────────────────────────────────────────────
    def get_tasks_due_soon(self, minutes=30):
        return db.get_tasks_due_soon(self.conn, minutes)

    def mark_task_notified(self, task_id: int):
        db.mark_task_notified(self.conn, task_id)

    # ── Templates ─────────────────────────────────────────────────────────────
    def get_templates(self):
        return db.get_templates(self.conn)

    def save_template(self, name, title, description="", category_id=None,
                      priority="medium", tags="", timer_mode=None,
                      timer_seconds=0):
        return db.save_template(self.conn, name, title, description,
                                category_id, priority, tags,
                                timer_mode, timer_seconds)

    def delete_template(self, template_id: int):
        db.delete_template(self.conn, template_id)

    def get_template(self, template_id: int):
        return db.get_template(self.conn, template_id)

    def save_timer_elapsed(self, task_id: int, elapsed: int):
        db.save_timer_elapsed(self.conn, task_id, elapsed)

    def get_category_goal_progress(self, for_date: str = None):
        return db.get_category_goal_progress(self.conn, for_date)

    def save_timer_elapsed(self, task_id: int, elapsed: int):
        db.save_timer_elapsed(self.conn, task_id, elapsed)

    def get_category_goal_progress(self, for_date: str = None):
        return db.get_category_goal_progress(self.conn, for_date)

    def get_monthly_time_activity(self):
        return db.get_monthly_time_activity(self.conn)

    # ── Test Analysis ─────────────────────────────────────────────────────────

    def init_tests(self):
        db.init_test_schema(self.conn)

    def get_test_subjects(self):
        return db.get_test_subjects(self.conn)

    def add_test_subject(self, name, color="#5294e2"):
        return db.add_test_subject(self.conn, name, color)

    def save_test_entry(self, **kw):
        return db.save_test_entry(self.conn, **kw)

    def update_test_entry(self, entry_id, **kw):
        return db.update_test_entry(self.conn, entry_id, **kw)

    def delete_test_entry(self, entry_id):
        db.delete_test_entry(self.conn, entry_id)

    def get_test_entries(self, subject_id=None, limit=200):
        return db.get_test_entries(self.conn, subject_id, limit)

    def get_test_overview(self):
        return db.get_test_overview(self.conn)

    def get_subject_stats(self):
        return db.get_subject_stats(self.conn)

    def get_accuracy_trend(self, subject_id=None, limit=20):
        return db.get_accuracy_trend(self.conn, subject_id, limit)

    def get_weak_subjects(self, threshold=60.0):
        return db.get_weak_subjects(self.conn, threshold)

    # ── Productivity features ─────────────────────────────────────────────────

    def duplicate_task(self, tid: int) -> int:
        """Copy a task (title/desc/cat/priority/tags) — not completion/timer state."""
        t = db.fetch_task(self.conn, tid)
        if not t:
            return None
        new_id = db.add_task(
            self.conn,
            title       = f"{t['title']} (copy)",
            description = t["description"] or "",
            category_id = t["category_id"],
            priority    = t["priority"],
            due_date    = t["due_date"],
            tags        = t["tags"] or "",
            timer_mode  = t["timer_mode"],
            timer_seconds = t["timer_seconds"] or 0,
        )
        return new_id

    def bulk_delete(self, task_ids: list):
        for tid in task_ids:
            db.delete_task(self.conn, tid)

    def bulk_complete(self, task_ids: list):
        from datetime import datetime
        for tid in task_ids:
            db.update_task(self.conn, tid,
                completed    = 1,
                completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def bulk_set_category(self, task_ids: list, category_id):
        for tid in task_ids:
            db.update_task(self.conn, tid, category_id=category_id)

    def bulk_duplicate(self, task_ids: list) -> list:
        return [self.duplicate_task(tid) for tid in task_ids]

    def get_last_used_category(self) -> int:
        """Return category_id of most recently created task."""
        row = self.conn.execute(
            "SELECT category_id FROM tasks ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return row["category_id"] if row else None

    def get_last_used_priority(self) -> str:
        """Return priority of most recently created task."""
        row = self.conn.execute(
            "SELECT priority FROM tasks ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return row["priority"] if row else "medium"

    def toggle_star(self, tid: int):
        """Toggle the starred/favourite flag on a task."""
        row = db.fetch_task(self.conn, tid)
        if row:
            try:
                current = int(row["starred"] or 0)
            except (KeyError, TypeError):
                current = 0
            new_val = 0 if current else 1
            db.update_task(self.conn, tid, starred=new_val)
            return bool(new_val)
        return False

    def get_starred_tasks(self):
        return self.conn.execute(
            "SELECT * FROM tasks WHERE starred=1 AND completed=0 ORDER BY due_date ASC"
        ).fetchall()
