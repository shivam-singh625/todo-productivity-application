"""analysis_db.py — Test Analysis System: schema, CRUD, and aggregate queries."""
import sqlite3
from datetime import datetime


# Default subjects — overridden dynamically from DB
DEFAULT_SUBJECTS = ["Biology", "Physics", "Chemistry", "Mathematics", "English"]


def get_subjects(conn) -> list:
    """Return subjects from DB, falling back to defaults."""
    try:
        rows = conn.execute(
            "SELECT name FROM test_subjects ORDER BY position, name"
        ).fetchall()
        if rows:
            return [r[0] for r in rows]
    except Exception:
        pass
    return list(DEFAULT_SUBJECTS)


def add_subject(conn, name: str) -> bool:
    """Add a new subject. Returns True if added, False if already exists."""
    try:
        mp = conn.execute(
            "SELECT COALESCE(MAX(position),0) FROM test_subjects"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO test_subjects(name,position) VALUES(?,?)",
            (name.strip(), mp + 1))
        conn.commit()
        return True
    except Exception:
        return False


def delete_subject(conn, name: str):
    """Remove a subject (entries become subject-less)."""
    try:
        conn.execute("DELETE FROM test_subjects WHERE name=?", (name,))
        conn.commit()
    except Exception:
        pass


def ensure_analysis_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS test_subjects (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL UNIQUE,
            color    TEXT    NOT NULL DEFAULT '#5294e2',
            position INTEGER NOT NULL DEFAULT 0
        );

        -- Subjects inserted separately after table creation
        ;

        CREATE TABLE IF NOT EXISTS test_entries (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            subject           TEXT    NOT NULL DEFAULT 'Biology',
            total_questions   INTEGER NOT NULL DEFAULT 0,
            attempted         INTEGER NOT NULL DEFAULT 0,
            correct           INTEGER NOT NULL DEFAULT 0,
            incorrect         INTEGER NOT NULL DEFAULT 0,
            skipped           INTEGER NOT NULL DEFAULT 0,
            time_taken_min    REAL    NOT NULL DEFAULT 0,
            marks_correct     REAL    NOT NULL DEFAULT 4.0,
            marks_negative    REAL    NOT NULL DEFAULT 1.0,
            accuracy          REAL    NOT NULL DEFAULT 0.0,
            score             REAL    NOT NULL DEFAULT 0.0,
            notes             TEXT    NOT NULL DEFAULT '',
            taken_at          TEXT    NOT NULL DEFAULT (datetime('now')),
            created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    # Only insert default subjects if table is completely empty (first run)
    count = conn.execute("SELECT COUNT(*) FROM test_subjects").fetchone()[0]
    if count == 0:
        for name, color, pos in [
            ('Biology','#a6e3a1',0), ('Physics','#89b4fa',1),
            ('Chemistry','#f9e2af',2), ('Mathematics','#cba6f7',3),
            ('English','#f38ba8',4)
        ]:
            conn.execute(
                "INSERT OR IGNORE INTO test_subjects(name,color,position) VALUES(?,?,?)",
                (name, color, pos))
        conn.commit()

    # Migrate existing table — add marks columns if missing
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(test_entries)")}
        for col, defn in [("marks_correct","REAL NOT NULL DEFAULT 4.0"),
                          ("marks_negative","REAL NOT NULL DEFAULT 1.0")]:
            if col not in cols:
                conn.execute(f"ALTER TABLE test_entries ADD COLUMN {col} {defn}")
        conn.commit()
    except Exception:
        pass
    # Migrate existing test_entries — add any missing columns
    try:
        te_cols = {r[1] for r in conn.execute("PRAGMA table_info(test_entries)")}
        migrations = [
            ("taken_at",       "TEXT NOT NULL DEFAULT (datetime('now'))"),
            ("marks_correct",  "REAL NOT NULL DEFAULT 4.0"),
            ("marks_negative", "REAL NOT NULL DEFAULT 0.0"),
            ("notes",          "TEXT NOT NULL DEFAULT ''"),
        ]
        for col, defn in migrations:
            if col not in te_cols:
                conn.execute(f"ALTER TABLE test_entries ADD COLUMN {col} {defn}")
        conn.commit()
    except Exception:
        pass
    conn.commit()


def add_test_entry(conn, subject, total_questions, attempted, correct,
                   incorrect, skipped=None, time_taken_min=0.0,
                   marks_correct=4.0, marks_negative=1.0,
                   accuracy=None, notes="", taken_at=None):
    if skipped is None:
        skipped = max(0, total_questions - attempted)
    if accuracy is None:
        accuracy = round((correct / attempted * 100), 2) if attempted > 0 else 0.0
    score = (correct * marks_correct) - (incorrect * marks_negative)
    if taken_at is None:
        taken_at = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute("""
        INSERT INTO test_entries
            (subject, total_questions, attempted, correct, incorrect,
             skipped, time_taken_min, marks_correct, marks_negative,
             accuracy, score, notes, taken_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (subject, total_questions, attempted, correct, incorrect,
          skipped, time_taken_min, marks_correct, marks_negative,
          accuracy, score, notes, taken_at))
    conn.commit()
    return cur.lastrowid


def update_test_entry(conn, entry_id, subject, total_questions, attempted,
                      correct, incorrect, skipped=None, time_taken_min=0.0,
                      marks_correct=4.0, marks_negative=1.0,
                      accuracy=None, notes="", taken_at=None):
    if skipped is None:
        skipped = max(0, total_questions - attempted)
    if accuracy is None:
        accuracy = round((correct / attempted * 100), 2) if attempted > 0 else 0.0
    score = (correct * marks_correct) - (incorrect * marks_negative)
    if taken_at is None:
        taken_at = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        UPDATE test_entries SET
            subject=?, total_questions=?, attempted=?, correct=?, incorrect=?,
            skipped=?, time_taken_min=?, marks_correct=?, marks_negative=?,
            accuracy=?, score=?, notes=?, taken_at=?
        WHERE id=?
    """, (subject, total_questions, attempted, correct, incorrect,
          skipped, time_taken_min, marks_correct, marks_negative,
          accuracy, score, notes, taken_at, entry_id))
    conn.commit()


def delete_test_entry(conn, entry_id: int):
    conn.execute("DELETE FROM test_entries WHERE id=?", (entry_id,))
    conn.commit()


def fetch_all_entries(conn, subject=None):
    sql = "SELECT * FROM test_entries"
    params = []
    if subject:
        sql += " WHERE subject=?"
        params.append(subject)
    sql += " ORDER BY taken_at DESC"
    return conn.execute(sql, params).fetchall()


def fetch_overview_stats(conn, subject=None):
    """Overview stats, optionally filtered by subject."""
    sql = """
        SELECT
            COUNT(*)                         AS total_tests,
            COALESCE(AVG(score), 0)          AS avg_score,
            COALESCE(AVG(accuracy), 0)       AS avg_accuracy,
            COALESCE(MAX(score), 0)          AS best_score,
            COALESCE(MIN(score), 0)          AS worst_score,
            COALESCE(SUM(time_taken_min), 0) AS total_time_min
        FROM test_entries WHERE 1=1
    """
    params = []
    if subject:
        sql += " AND subject=?"
        params.append(subject)
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else {}
    except Exception:
        return {}


def fetch_subject_stats(conn, subject=None):
    """Per-subject stats. If subject given, returns only that subject's row."""
    sql = """
        SELECT
            subject,
            COUNT(*)                         AS tests,
            COALESCE(AVG(accuracy), 0)       AS avg_accuracy,
            COALESCE(AVG(score), 0)          AS avg_score,
            COALESCE(SUM(time_taken_min), 0) AS total_time_min,
            COALESCE(MAX(score), 0)          AS best_score
        FROM test_entries WHERE 1=1
    """
    params = []
    if subject:
        sql += " AND subject=?"
        params.append(subject)
    sql += " GROUP BY subject ORDER BY subject"
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:
        return []


def fetch_trend_data(conn, subject=None, limit=20):
    """Return entries oldest-first for trend display, optionally filtered."""
    inner_sql = "SELECT taken_at, accuracy, score, subject FROM test_entries"
    params = []
    if subject:
        inner_sql += " WHERE subject=?"
        params.append(subject)
    inner_sql += " ORDER BY taken_at DESC LIMIT ?"
    params.append(limit)
    # Wrap to get oldest-first for chart display
    sql = f"SELECT * FROM ({inner_sql}) ORDER BY taken_at ASC"
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:
        return []
