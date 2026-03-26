#!/usr/bin/env bash
# debug.sh — Run this any time to diagnose issues
# Usage:  bash ~/.local/share/xfce-productivity-todo/debug.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/debug.log"
cd "$SCRIPT_DIR"

echo "=== XFCE Todo Debug ===" | tee "$LOG"
echo "Date:    $(date)" | tee -a "$LOG"
echo "Python:  $(python3 --version)" | tee -a "$LOG"
echo "App dir: $SCRIPT_DIR" | tee -a "$LOG"
echo "" | tee -a "$LOG"

echo "=== Python imports ===" | tee -a "$LOG"
python3 -c "
import sys, os
sys.path.insert(0, '$SCRIPT_DIR')
tests = [
    ('gi',          'import gi'),
    ('GTK4',        'import gi; gi.require_version(\"Gtk\",\"4.0\"); from gi.repository import Gtk'),
    ('backend',     'import sys; sys.path.insert(0,\"$SCRIPT_DIR\"); from backend import config_manager'),
    ('task_manager','import sys; sys.path.insert(0,\"$SCRIPT_DIR\"); from backend.task_manager import TaskManager'),
    ('main_window', 'import sys; sys.path.insert(0,\"$SCRIPT_DIR\"); from ui.main_window import MainWindow'),
    ('analysis',    'import sys; sys.path.insert(0,\"$SCRIPT_DIR\"); from ui.analysis_panel import AnalysisPanel'),
    ('dashboard',   'import sys; sys.path.insert(0,\"$SCRIPT_DIR\"); from ui.dashboard import DashboardPanel'),
]
for name, code in tests:
    try:
        exec(code)
        print(f'  OK   {name}')
    except Exception as e:
        print(f'  FAIL {name}: {e}')
" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== DB test ===" | tee -a "$LOG"
python3 -c "
import sys, os
sys.path.insert(0, '$SCRIPT_DIR')
from backend import config_manager, database
from backend.task_manager import TaskManager

cfg = config_manager.load()
db_path = cfg['database_path']
print(f'  DB path: {db_path}')
print(f'  DB exists: {os.path.exists(db_path)}')

tm = TaskManager(db_path)
tables = sorted([t[0] for t in tm.conn.execute(\"SELECT name FROM sqlite_master WHERE type=\\'table\\'\").fetchall()])
print(f'  Tables: {tables}')

# Test all critical queries
try:
    r = tm.get_test_overview(); print(f'  get_test_overview: OK (tests={r[\"total_tests\"]})')
except Exception as e: print(f'  get_test_overview: FAIL - {e}')

try:
    r = tm.get_category_goal_progress(); print(f'  get_category_goal_progress: OK ({len(r)} rows)')
except Exception as e: print(f'  get_category_goal_progress: FAIL - {e}')

try:
    r = tm.get_monthly_time_activity(); print(f'  get_monthly_time_activity: OK ({len(r)} rows)')
except Exception as e: print(f'  get_monthly_time_activity: FAIL - {e}')

try:
    r = tm.get_tasks(); print(f'  get_tasks: OK ({len(r)} tasks)')
except Exception as e: print(f'  get_tasks: FAIL - {e}')

tm.conn.close()
print('  DB tests complete')
" 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Launching app (errors shown below) ===" | tee -a "$LOG"
export GDK_BACKEND=x11
python3 "$SCRIPT_DIR/main.py" 2>&1 | tee -a "$LOG"
echo "Log saved to: $LOG"
