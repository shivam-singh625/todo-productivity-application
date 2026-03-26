"""
database.py — Full SQLite schema with time tracking, dashboard stats.
"""
import sqlite3, os
from datetime import datetime


def get_connection(db_path: str) -> sqlite3.Connection:
    # Expand ~ and env vars, then ensure directory exists
    db_path = os.path.expandvars(os.path.expanduser(db_path))
    db_dir  = os.path.dirname(db_path)
    try:
        os.makedirs(db_dir, exist_ok=True)
    except PermissionError:
        # Path is inaccessible (external drive, wrong mount, etc.)
        # Fall back to a safe default in the user's home directory
        fallback = os.path.join(os.path.expanduser("~"), ".local", "share", "xfce-todo", "tasks.db")
        print(f"[Warning] Cannot access DB path: {db_path}")
        print(f"[Warning] Falling back to: {fallback}")
        db_path = fallback
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialise_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL UNIQUE,
            color    TEXT    NOT NULL DEFAULT '#5294e2',
            position INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT    NOT NULL,
            description   TEXT    NOT NULL DEFAULT '',
            category_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            priority      TEXT    NOT NULL DEFAULT 'medium'
                              CHECK(priority IN ('low','medium','high')),
            due_date      TEXT,
            completed     INTEGER NOT NULL DEFAULT 0,
            completed_at  TEXT,
            tags          TEXT    NOT NULL DEFAULT '',
            position      INTEGER NOT NULL DEFAULT 0,
            timer_mode    TEXT    DEFAULT NULL,
            timer_seconds INTEGER NOT NULL DEFAULT 0,
            notified_at   TEXT    DEFAULT NULL,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS task_templates (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL UNIQUE,
            title         TEXT    NOT NULL,
            description   TEXT    NOT NULL DEFAULT '',
            category_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            priority      TEXT    NOT NULL DEFAULT 'medium',
            tags          TEXT    NOT NULL DEFAULT '',
            timer_mode    TEXT    DEFAULT NULL,
            timer_seconds INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS time_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
            category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            started_at  TEXT NOT NULL,
            ended_at    TEXT,
            duration    INTEGER NOT NULL DEFAULT 0,
            session_type TEXT NOT NULL DEFAULT 'task'
        );
        CREATE TABLE IF NOT EXISTS pomodoro_sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            duration   INTEGER NOT NULL DEFAULT 25,
            completed  INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO categories(name,color,position) VALUES
            ('Work','#e25252',0),('Study','#5294e2',1),
            ('Personal','#52b152',2),('Health','#e2a452',3);
    """)
    # Fix stale data: tasks marked incomplete but still have completed_at
    # This caused "Done Today" to show wrong counts
    conn.execute(
        "UPDATE tasks SET completed_at=NULL WHERE completed=0 AND completed_at IS NOT NULL"
    )
    conn.commit()

    # Migrations for existing DBs
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
    for col, defn in [("timer_mode",     "TEXT DEFAULT NULL"),
                      ("timer_seconds",  "INTEGER NOT NULL DEFAULT 0"),
                      ("timer_elapsed",  "INTEGER NOT NULL DEFAULT 0"),
                      ("starred",        "INTEGER NOT NULL DEFAULT 0"),
                      ("completed_at",   "TEXT"),
                      ("notified_at",    "TEXT DEFAULT NULL")]:
        if col not in cols:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {defn}")
    conn.commit()


# ── Categories ────────────────────────────────────────────────────────────────
def fetch_categories(conn): return conn.execute("SELECT * FROM categories ORDER BY position,id").fetchall()
def add_category(conn, name, color="#5294e2"):
    mp = conn.execute("SELECT COALESCE(MAX(position),0) FROM categories").fetchone()[0]
    cur = conn.execute("INSERT INTO categories(name,color,position) VALUES(?,?,?)",(name,color,mp+1))
    conn.commit(); return cur.lastrowid
def rename_category(conn, cid, name): conn.execute("UPDATE categories SET name=? WHERE id=?",(name,cid)); conn.commit()
def delete_category(conn, cid): conn.execute("DELETE FROM categories WHERE id=?",(cid,)); conn.commit()

# ── Tasks ─────────────────────────────────────────────────────────────────────
def fetch_tasks(conn, category_id=None, completed=None, search=None, due_today=False, upcoming=False):
    sql = "SELECT t.*,c.name AS category_name,c.color AS category_color FROM tasks t LEFT JOIN categories c ON t.category_id=c.id WHERE 1=1"
    p = []
    if category_id is not None: sql += " AND t.category_id=?"; p.append(category_id)
    if completed is not None: sql += " AND t.completed=?"; p.append(1 if completed else 0)
    if search:
        sql += " AND (t.title LIKE ? OR t.description LIKE ? OR t.tags LIKE ?)"
        like = f"%{search}%"; p += [like,like,like]
    today = datetime.now().date().isoformat()
    if due_today: sql += " AND t.due_date=? AND t.completed=0"; p.append(today)
    elif upcoming: sql += " AND t.due_date>? AND t.completed=0"; p.append(today)
    sql += " ORDER BY t.position,t.id"
    return conn.execute(sql,p).fetchall()

def fetch_task(conn, tid):
    return conn.execute("SELECT t.*,c.name AS category_name FROM tasks t LEFT JOIN categories c ON t.category_id=c.id WHERE t.id=?",(tid,)).fetchone()

def add_task(conn, title, description="", category_id=None, priority="medium", due_date=None, tags="", timer_mode=None, timer_seconds=0, starred=0):
    mp = conn.execute("SELECT COALESCE(MAX(position),0) FROM tasks").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO tasks(title,description,category_id,priority,due_date,tags,position,timer_mode,timer_seconds,starred) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (title,description,category_id,priority,due_date,tags,mp+1,timer_mode,timer_seconds,int(starred)))
    conn.commit(); return cur.lastrowid

def update_task(conn, tid, **fields):
    allowed = {"title","description","category_id","priority","due_date","completed","completed_at","tags","position","timer_mode","timer_seconds","timer_elapsed","starred","notified_at"}
    sets,vals = [],[]
    for k,v in fields.items():
        if k in allowed: sets.append(f"{k}=?"); vals.append(v)
    if not sets: return
    sets.append("updated_at=datetime('now')"); vals.append(tid)
    conn.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id=?",vals); conn.commit()

def delete_task(conn, tid): conn.execute("DELETE FROM tasks WHERE id=?",(tid,)); conn.commit()
def reorder_tasks(conn, ids):
    for i,tid in enumerate(ids): conn.execute("UPDATE tasks SET position=? WHERE id=?",(i,tid))
    conn.commit()
def fetch_tasks_by_date(conn, ds): return conn.execute("SELECT t.*,c.name AS category_name,c.color AS category_color FROM tasks t LEFT JOIN categories c ON t.category_id=c.id WHERE t.due_date=? ORDER BY t.position",(ds,)).fetchall()

# ── Time Sessions ─────────────────────────────────────────────────────────────
def start_time_session(conn, task_id, category_id=None):
    cur = conn.execute("INSERT INTO time_sessions(task_id,category_id,started_at) VALUES(?,?,datetime('now'))",(task_id,category_id))
    conn.commit(); return cur.lastrowid

def end_time_session(conn, session_id):
    conn.execute("""UPDATE time_sessions
        SET ended_at = datetime('now'),
            duration = MAX(1, CAST((julianday('now') - julianday(started_at)) * 86400 AS INTEGER))
        WHERE id=?""", (session_id,))
    conn.commit()


def update_time_session_duration(conn, session_id, elapsed_seconds: int):
    """Update duration of a live session without closing it.
    Used for live dashboard refresh while timer is still running."""
    conn.execute(
        "UPDATE time_sessions SET duration=? WHERE id=?",
        (max(1, elapsed_seconds), session_id)
    )
    conn.commit()

def get_today_focus_seconds(conn):
    today = datetime.now().date().isoformat()
    r = conn.execute("SELECT COALESCE(SUM(duration),0) FROM time_sessions WHERE DATE(started_at)=? AND duration>0",(today,)).fetchone()
    return r[0] if r else 0

def get_today_completed_count(conn):
    """
    Count tasks with due_date = today that are marked completed.
    This is the clearest definition: how many of today's planned tasks are done.
    Does NOT use completed_at timestamp (avoids stale data bugs).
    """
    today = datetime.now().date().isoformat()
    r = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE completed=1 AND due_date=?",
        (today,)
    ).fetchone()
    return r[0] if r else 0

def get_category_focus_today(conn):
    today = datetime.now().date().isoformat()
    return conn.execute("""SELECT c.name,c.color,COALESCE(SUM(ts.duration),0) as total
        FROM time_sessions ts JOIN categories c ON ts.category_id=c.id
        WHERE DATE(ts.started_at)=? AND ts.duration>0 GROUP BY c.id ORDER BY total DESC""",(today,)).fetchall()

def get_weekly_focus(conn):
    return conn.execute("""SELECT DATE(started_at) as day, COALESCE(SUM(duration),0) as total
        FROM time_sessions WHERE started_at >= datetime('now','-7 days') AND duration>0
        GROUP BY DATE(started_at) ORDER BY day""").fetchall()

def get_total_tasks_count(conn): return conn.execute("SELECT COUNT(*) FROM tasks WHERE completed=0").fetchone()[0]
def get_completed_tasks_count(conn): return conn.execute("SELECT COUNT(*) FROM tasks WHERE completed=1").fetchone()[0]
def get_overdue_count(conn):
    today = datetime.now().date().isoformat()
    return conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE completed=0 AND due_date IS NOT NULL AND due_date < ?",
        (today,)
    ).fetchone()[0]
def get_upcoming_count(conn):
    today = datetime.now().date().isoformat()
    return conn.execute("SELECT COUNT(*) FROM tasks WHERE completed=0 AND due_date>=?",(today,)).fetchone()[0]

# ── Pomodoro ──────────────────────────────────────────────────────────────────
def add_pomodoro_session(conn, duration=25, completed=False):
    cur = conn.execute("INSERT INTO pomodoro_sessions(duration,completed) VALUES(?,?)",(duration,1 if completed else 0)); conn.commit(); return cur.lastrowid
def count_pomodoro_sessions_today(conn):
    today = datetime.now().date().isoformat()
    r = conn.execute("SELECT COUNT(*) FROM pomodoro_sessions WHERE completed=1 AND date(started_at)=?",(today,)).fetchone()
    return r[0] if r else 0


# ── Streak helpers ────────────────────────────────────────────────────────────
#
# STREAK RULE:
#   A day "counts" if ALL tasks that were DUE on that day were completed.
#   If a day had no due tasks but the user completed tasks anyway, it also counts.
#   If a day had due tasks and ANY were left incomplete, the streak breaks.
#
# For days with no due_date tasks, we fall back to: did the user complete
# at least one task that day (any task, regardless of due_date).
# This gives students a fair streak even when they don't set due dates.

def _get_streak_days(conn):
    """
    Returns a set of date strings (YYYY-MM-DD) that are "perfect days"
    — days where the user completed all tasks they had planned (due that day),
    OR completed at least one task if no tasks were due.
    """
    from datetime import date, timedelta
    perfect = set()

    # Get all days that had tasks due
    due_days = conn.execute("""
        SELECT DISTINCT due_date as day FROM tasks
        WHERE due_date IS NOT NULL AND due_date != ''
        ORDER BY due_date DESC
    """).fetchall()
    due_day_set = {r["day"] for r in due_days}

    # For each day that had due tasks: check if ALL were completed
    for row in due_days:
        day = row["day"]
        total = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE due_date=?", (day,)
        ).fetchone()[0]
        done = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE due_date=? AND completed=1", (day,)
        ).fetchone()[0]
        if total > 0 and done == total:
            perfect.add(day)

    # For days with NO due tasks, count days where user completed at least 1 task
    completed_days = conn.execute("""
        SELECT DISTINCT DATE(completed_at) as day
        FROM tasks WHERE completed=1 AND completed_at IS NOT NULL
    """).fetchall()
    for row in completed_days:
        day = row["day"]
        if day and day not in due_day_set:
            perfect.add(day)

    return perfect


def get_daily_streak(conn) -> int:
    """
    Consecutive days ending today (or yesterday) where the user had
    a perfect day (all due tasks completed, or at least one task done
    if no tasks were due).
    """
    from datetime import date, timedelta
    perfect = _get_streak_days(conn)
    if not perfect:
        return 0

    today = date.today()
    streak = 0
    check  = today

    # Allow streak to be active if yesterday was perfect (today not yet done)
    if today.isoformat() not in perfect:
        yesterday = (today - timedelta(days=1)).isoformat()
        if yesterday not in perfect:
            return 0
        check = today - timedelta(days=1)

    while check.isoformat() in perfect:
        streak += 1
        check  -= timedelta(days=1)

    return streak


def get_longest_daily_streak(conn) -> int:
    """All-time best consecutive perfect days."""
    from datetime import date, timedelta
    perfect = _get_streak_days(conn)
    if not perfect:
        return 0

    days = sorted(date.fromisoformat(d) for d in perfect)
    best = cur = 1
    for i in range(1, len(days)):
        if days[i] - days[i-1] == timedelta(days=1):
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def get_weekly_streak(conn) -> int:
    """
    Consecutive weeks where the user had at least one perfect day.
    """
    from datetime import date, timedelta
    perfect = _get_streak_days(conn)
    if not perfect:
        return 0

    # Build set of (iso_year, iso_week) for each perfect day
    wset = set()
    for d_str in perfect:
        try:
            d = date.fromisoformat(d_str)
            wset.add(d.isocalendar()[:2])   # (year, week)
        except Exception:
            pass

    if not wset:
        return 0

    today = date.today()
    ty, tw, _ = today.isocalendar()
    streak = 0
    cy, cw = ty, tw

    while (cy, cw) in wset:
        streak += 1
        cw -= 1
        if cw == 0:
            cw = 52
            cy -= 1

    return streak


def get_longest_weekly_streak(conn) -> int:
    """All-time best consecutive perfect weeks."""
    from datetime import date
    perfect = _get_streak_days(conn)
    if not perfect:
        return 0

    wset = set()
    for d_str in perfect:
        try:
            d = date.fromisoformat(d_str)
            wset.add(d.isocalendar()[:2])
        except Exception:
            pass

    weeks = sorted(wset)
    if not weeks:
        return 0

    best = cur = 1
    for i in range(1, len(weeks)):
        y1, w1 = weeks[i-1]
        y2, w2 = weeks[i]
        diff   = (y2 - y1) * 52 + (w2 - w1)
        if diff == 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def get_completed_tasks_by_day(conn, days: int = 30):
    """Returns list of (day, count) for the last N days."""
    return conn.execute("""
        SELECT DATE(completed_at) as day, COUNT(*) as cnt
        FROM tasks WHERE completed=1 AND completed_at IS NOT NULL
          AND completed_at >= datetime('now', ?)
        GROUP BY DATE(completed_at) ORDER BY day ASC
    """, (f"-{days} days",)).fetchall()


def get_today_streak_status(conn):
    """
    Returns a dict describing today's streak progress:
      total_due   — tasks due today
      completed   — tasks due today that are done
      all_done    — True if all due tasks are completed
      any_done    — True if at least one task completed today
    """
    from datetime import date
    today = date.today().isoformat()
    total = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE due_date=?", (today,)
    ).fetchone()[0]
    done = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE due_date=? AND completed=1", (today,)
    ).fetchone()[0]
    any_done = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE completed=1 AND DATE(completed_at)=?", (today,)
    ).fetchone()[0] > 0
    return {
        "total_due": total,
        "completed": done,
        "all_done":  (total == 0 or done == total),
        "any_done":  any_done,
    }


# ── Streak helpers ────────────────────────────────────────────────────────────
#
# STREAK RULE (exact):
#   A day COUNTS toward the streak if ALL tasks with due_date = that day
#   are marked completed.
#   If a day has NO due tasks → it does NOT count (no free streak days).
#   Today: if today's tasks are not all done → streak = 0 (today breaks it).
#   Yesterday: if today has no due tasks, look back to yesterday.
#
# WEEKLY STREAK: at least one "perfect day" (as above) in a Mon–Sun week.

def _perfect_days(conn) -> set:
    """
    Return set of date strings (YYYY-MM-DD) where ALL due tasks were completed.
    Days with no due tasks are excluded (no free days).
    """
    rows = conn.execute("""
        SELECT due_date,
               COUNT(*) as total,
               SUM(completed) as done
        FROM tasks
        WHERE due_date IS NOT NULL AND due_date != ''
        GROUP BY due_date
    """).fetchall()
    perfect = set()
    for r in rows:
        if r["total"] > 0 and r["done"] == r["total"]:
            perfect.add(r["due_date"])
    return perfect


def get_daily_streak(conn) -> int:
    """
    Consecutive days (ending today) where ALL due tasks were completed.
    - Today counts only if all today's tasks are done.
    - If today has no due tasks, today does NOT extend the streak.
    - Streak = 0 if today's tasks are incomplete OR today has tasks not all done.
    """
    from datetime import date, timedelta
    perfect = _perfect_days(conn)
    if not perfect:
        return 0

    today = date.today()
    check = today
    streak = 0

    while check.isoformat() in perfect:
        streak += 1
        check  -= timedelta(days=1)

    return streak


def get_longest_daily_streak(conn) -> int:
    """All-time best consecutive perfect days."""
    from datetime import date, timedelta
    perfect = _perfect_days(conn)
    if not perfect:
        return 0
    days = sorted(date.fromisoformat(d) for d in perfect)
    if not days:
        return 0
    best = cur = 1
    for i in range(1, len(days)):
        if (days[i] - days[i-1]).days == 1:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def get_weekly_streak(conn) -> int:
    """
    Consecutive Mon-Sun weeks that contain at least one perfect day.
    Current week counts only if it already has a perfect day this week.
    """
    from datetime import date, timedelta
    perfect = _perfect_days(conn)
    if not perfect:
        return 0

    # Map each perfect day to its Monday (week start)
    week_set = set()
    for d_str in perfect:
        try:
            d = date.fromisoformat(d_str)
            monday = d - timedelta(days=d.weekday())
            week_set.add(monday)
        except Exception:
            pass

    if not week_set:
        return 0

    today      = date.today()
    week_start = today - timedelta(days=today.weekday())
    streak     = 0

    while week_start in week_set:
        streak     += 1
        week_start -= timedelta(days=7)

    return streak


def get_longest_weekly_streak(conn) -> int:
    """All-time best consecutive perfect weeks."""
    from datetime import date, timedelta
    perfect = _perfect_days(conn)
    if not perfect:
        return 0

    week_set = set()
    for d_str in perfect:
        try:
            d = date.fromisoformat(d_str)
            week_set.add(d - timedelta(days=d.weekday()))
        except Exception:
            pass

    weeks = sorted(week_set)
    if not weeks:
        return 0

    best = cur = 1
    for i in range(1, len(weeks)):
        if (weeks[i] - weeks[i-1]).days == 7:
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best


def get_last_30_days_activity(conn):
    """Return daily completed task counts for the last 30 days for the line chart."""
    return conn.execute(
        """SELECT DATE(completed_at) as day, COUNT(*) as count
           FROM tasks WHERE completed=1 AND completed_at IS NOT NULL
           AND completed_at >= datetime('now','-30 days')
           GROUP BY DATE(completed_at) ORDER BY day"""
    ).fetchall()


# ── Notification settings ─────────────────────────────────────────────────────

def get_tasks_due_soon(conn, minutes_ahead: int = 30):
    """Return tasks due within the next N minutes that haven't been notified."""
    from datetime import datetime, timedelta
    now   = datetime.now()
    later = now + timedelta(minutes=minutes_ahead)
    today = now.date().isoformat()
    now_str   = now.strftime("%Y-%m-%d %H:%M")
    later_str = later.strftime("%Y-%m-%d %H:%M")
    # Tasks due today that are not completed and not yet snoozed
    return conn.execute("""
        SELECT t.*, c.name AS category_name
        FROM tasks t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.completed = 0
          AND t.due_date = ?
          AND (t.notified_at IS NULL OR t.notified_at < datetime('now', '-1 hour'))
        ORDER BY t.due_date ASC
    """, (today,)).fetchall()


def mark_task_notified(conn, task_id: int):
    conn.execute(
        "UPDATE tasks SET notified_at = datetime('now') WHERE id = ?",
        (task_id,)
    )
    conn.commit()


# ── Task templates ────────────────────────────────────────────────────────────

def get_templates(conn):
    return conn.execute(
        "SELECT * FROM task_templates ORDER BY name ASC"
    ).fetchall()


def save_template(conn, name: str, title: str, description: str = "",
                  category_id=None, priority: str = "medium",
                  tags: str = "", timer_mode=None,
                  timer_seconds: int = 0) -> int:
    # Upsert by name
    existing = conn.execute(
        "SELECT id FROM task_templates WHERE name = ?", (name,)
    ).fetchone()
    if existing:
        conn.execute("""
            UPDATE task_templates SET
                title=?, description=?, category_id=?, priority=?,
                tags=?, timer_mode=?, timer_seconds=?,
                updated_at=datetime('now')
            WHERE name=?
        """, (title, description, category_id, priority,
              tags, timer_mode, timer_seconds, name))
        row_id = existing["id"]
    else:
        cur = conn.execute("""
            INSERT INTO task_templates
                (name, title, description, category_id, priority,
                 tags, timer_mode, timer_seconds)
            VALUES (?,?,?,?,?,?,?,?)
        """, (name, title, description, category_id, priority,
              tags, timer_mode, timer_seconds))
        row_id = cur.lastrowid
    conn.commit()
    return row_id


def delete_template(conn, template_id: int):
    conn.execute("DELETE FROM task_templates WHERE id = ?", (template_id,))
    conn.commit()


def get_template(conn, template_id: int):
    return conn.execute(
        "SELECT * FROM task_templates WHERE id = ?", (template_id,)
    ).fetchone()


# ── Timer state persistence ───────────────────────────────────────────────────

def save_timer_elapsed(conn, task_id: int, elapsed_seconds: int):
    """Save how many seconds have been counted so far (paused position)."""
    conn.execute(
        "UPDATE tasks SET timer_elapsed=? WHERE id=?",
        (max(0, elapsed_seconds), task_id))
    conn.commit()


# ── Category goal progress ────────────────────────────────────────────────────

def get_category_goal_progress(conn, for_date: str = None):
    """
    For each category on a specific date, return:
      - total_goal_seconds   : sum of timer_seconds for tasks due on that date
      - focus_seconds_date   : actual focus time logged on that date
      - remaining_seconds    : goal - spent (can be negative if exceeded)

    If for_date is None, uses today.
    Only shows categories that have tasks due on that date OR focus time on that date.
    """
    from datetime import datetime
    if for_date is None:
        for_date = datetime.now().date().isoformat()

    return conn.execute("""
        SELECT
            c.id,
            c.name,
            c.color,
            -- Goal: sum of timer_seconds for tasks DUE on this date
            COALESCE((
                SELECT SUM(t2.timer_seconds)
                FROM tasks t2
                WHERE t2.category_id = c.id
                  AND t2.due_date = ?
                  AND t2.timer_seconds > 0
            ), 0) AS total_goal_seconds,
            -- Spent: focus time actually logged on this date
            COALESCE((
                SELECT SUM(ts.duration)
                FROM time_sessions ts
                WHERE ts.category_id = c.id
                  AND DATE(ts.started_at) = ?
                  AND ts.duration > 0
            ), 0) AS focus_seconds_date,
            -- How many tasks due on this date
            COALESCE((
                SELECT COUNT(*)
                FROM tasks t3
                WHERE t3.category_id = c.id AND t3.due_date = ?
            ), 0) AS tasks_due,
            -- How many completed
            COALESCE((
                SELECT COUNT(*)
                FROM tasks t4
                WHERE t4.category_id = c.id
                  AND t4.due_date = ?
                  AND t4.completed = 1
            ), 0) AS tasks_completed
        FROM categories c
        WHERE (
            -- Has tasks due on this date
            EXISTS (SELECT 1 FROM tasks t5 WHERE t5.category_id=c.id AND t5.due_date=?)
            OR
            -- Has focus sessions on this date
            EXISTS (SELECT 1 FROM time_sessions ts6
                    WHERE ts6.category_id=c.id
                      AND DATE(ts6.started_at)=?
                      AND ts6.duration>0)
        )
        ORDER BY focus_seconds_date DESC, total_goal_seconds DESC
    """, (for_date, for_date, for_date, for_date, for_date, for_date)).fetchall()


# ══════════════════════════════════════════════════════════════════════════════
# TEST ANALYSIS SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

def init_test_schema(conn):
    """Create test analysis tables if they don't exist. Safe to call on old DBs."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS test_subjects (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL UNIQUE,
            color    TEXT    NOT NULL DEFAULT '#5294e2',
            position INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS test_entries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id      INTEGER REFERENCES test_subjects(id) ON DELETE SET NULL,
            test_date       TEXT    NOT NULL DEFAULT (date('now')),
            total_questions INTEGER NOT NULL DEFAULT 0,
            attempted       INTEGER NOT NULL DEFAULT 0,
            correct         INTEGER NOT NULL DEFAULT 0,
            incorrect       INTEGER NOT NULL DEFAULT 0,
            skipped         INTEGER NOT NULL DEFAULT 0,
            time_minutes    INTEGER NOT NULL DEFAULT 0,
            marks_correct   REAL    NOT NULL DEFAULT 1,
            marks_negative  REAL    NOT NULL DEFAULT 0,
            score           REAL    NOT NULL DEFAULT 0,
            accuracy        REAL    NOT NULL DEFAULT 0,
            notes           TEXT    NOT NULL DEFAULT '',
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        INSERT OR IGNORE INTO test_subjects(name,color,position) VALUES
            ('Biology','#a6e3a1',0),
            ('Physics','#89b4fa',1),
            ('Chemistry','#f9e2af',2),
            ('Mathematics','#cba6f7',3),
            ('English','#f38ba8',4);
    """)
    # Migrate existing test_entries (add marks columns if missing)
    try:
        te_cols = {r[1] for r in conn.execute("PRAGMA table_info(test_entries)")}
        for col, defn in [("marks_correct","REAL NOT NULL DEFAULT 1"),
                          ("marks_negative","REAL NOT NULL DEFAULT 0")]:
            if col not in te_cols:
                conn.execute(f"ALTER TABLE test_entries ADD COLUMN {col} {defn}")
    except Exception:
        pass
    conn.commit()


def get_test_subjects(conn):
    return conn.execute("SELECT * FROM test_subjects ORDER BY position,id").fetchall()


def add_test_subject(conn, name, color="#5294e2"):
    mp = conn.execute("SELECT COALESCE(MAX(position),0) FROM test_subjects").fetchone()[0]
    cur = conn.execute("INSERT INTO test_subjects(name,color,position) VALUES(?,?,?)", (name,color,mp+1))
    conn.commit(); return cur.lastrowid


def save_test_entry(conn, subject_id, test_date, total_questions,
                    attempted, correct, incorrect, skipped,
                    time_minutes, marks_correct=1.0, marks_negative=0.0, notes=""):
    accuracy = round(correct / attempted * 100, 1) if attempted > 0 else 0.0
    if skipped == 0 and total_questions > 0:
        skipped = total_questions - attempted
    score = (correct * marks_correct) - (incorrect * marks_negative)
    cur = conn.execute("""
        INSERT INTO test_entries
            (subject_id,test_date,total_questions,attempted,correct,
             incorrect,skipped,time_minutes,marks_correct,marks_negative,
             score,accuracy,notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (subject_id,test_date,total_questions,attempted,correct,
          incorrect,skipped,time_minutes,marks_correct,marks_negative,
          score,accuracy,notes))
    conn.commit(); return cur.lastrowid


def update_test_entry(conn, entry_id, subject_id, test_date, total_questions,
                      attempted, correct, incorrect, skipped,
                      time_minutes, marks_correct=1.0, marks_negative=0.0, notes=""):
    accuracy = round(correct / attempted * 100, 1) if attempted > 0 else 0.0
    if skipped == 0 and total_questions > 0:
        skipped = total_questions - attempted
    score = (correct * marks_correct) - (incorrect * marks_negative)
    conn.execute("""
        UPDATE test_entries SET
            subject_id=?,test_date=?,total_questions=?,attempted=?,
            correct=?,incorrect=?,skipped=?,time_minutes=?,
            marks_correct=?,marks_negative=?,score=?,accuracy=?,notes=?
        WHERE id=?
    """, (subject_id,test_date,total_questions,attempted,correct,
          incorrect,skipped,time_minutes,marks_correct,marks_negative,
          score,accuracy,notes,entry_id))
    conn.commit()


def delete_test_entry(conn, entry_id):
    conn.execute("DELETE FROM test_entries WHERE id=?", (entry_id,)); conn.commit()


def get_test_entries(conn, subject_id=None, limit=200):
    try:
        sql = """SELECT e.*,s.name AS subject_name,s.color AS subject_color
                 FROM test_entries e LEFT JOIN test_subjects s ON e.subject_id=s.id
                 WHERE 1=1"""
        p = []
        if subject_id: sql += " AND e.subject_id=?"; p.append(subject_id)
        sql += " ORDER BY e.test_date DESC,e.created_at DESC LIMIT ?"
        p.append(limit)
        return conn.execute(sql, p).fetchall()
    except Exception: return []


def get_test_overview(conn):
    try:
        return conn.execute("""
            SELECT COUNT(*) AS total_tests,
                   COALESCE(AVG(score),0)        AS avg_score,
                   COALESCE(AVG(accuracy),0)     AS avg_accuracy,
                   COALESCE(MAX(score),0)        AS best_score,
                   COALESCE(MIN(score),0)        AS worst_score,
                   COALESCE(SUM(time_minutes),0) AS total_time_mins,
                   COALESCE(AVG(time_minutes),0) AS avg_time_mins
            FROM test_entries
        """).fetchone()
    except Exception:
        # Table doesn't exist yet — return empty stats
        return {"total_tests":0,"avg_score":0,"avg_accuracy":0,
                "best_score":0,"worst_score":0,"total_time_mins":0,"avg_time_mins":0}


def get_subject_stats(conn):
    try:
        return conn.execute("""
            SELECT s.id,s.name,s.color,
                   COUNT(e.id)                    AS test_count,
                   COALESCE(AVG(e.accuracy),0)    AS avg_accuracy,
                   COALESCE(AVG(e.score),0)       AS avg_score,
                   COALESCE(MAX(e.score),0)       AS best_score,
                   COALESCE(SUM(e.time_minutes),0) AS total_time_mins
            FROM test_subjects s
            LEFT JOIN test_entries e ON e.subject_id=s.id
            WHERE e.id IS NOT NULL
            GROUP BY s.id ORDER BY avg_accuracy DESC
        """).fetchall()
    except Exception: return []


def get_accuracy_trend(conn, subject_id=None, limit=20):
    try:
        sql = """SELECT e.test_date,e.accuracy,e.score,s.name AS subject_name
                 FROM test_entries e LEFT JOIN test_subjects s ON e.subject_id=s.id
                 WHERE 1=1"""
        p = []
        if subject_id: sql += " AND e.subject_id=?"; p.append(subject_id)
        sql += " ORDER BY e.test_date ASC,e.created_at ASC LIMIT ?"
        p.append(limit)
        return conn.execute(sql, p).fetchall()
    except Exception: return []


def get_weak_subjects(conn, threshold=60.0):
    try:
        return conn.execute("""
            SELECT s.name,s.color,AVG(e.accuracy) AS avg_acc,COUNT(e.id) AS cnt
            FROM test_subjects s JOIN test_entries e ON e.subject_id=s.id
            GROUP BY s.id HAVING avg_acc < ? AND cnt >= 2 ORDER BY avg_acc ASC
        """, (threshold,)).fetchall()
    except Exception: return []


def get_monthly_time_activity(conn):
    """Daily focus seconds for the last 30 days."""
    return conn.execute("""
        SELECT DATE(started_at) as day,
               COALESCE(SUM(duration),0) as total_seconds
        FROM time_sessions
        WHERE started_at >= datetime('now','-30 days') AND duration > 0
        GROUP BY DATE(started_at) ORDER BY day ASC
    """).fetchall()
