"""config_manager.py"""
import json, os, shutil

CONFIG_DIR  = os.path.expanduser("~/.config/xfce-todo")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_DB  = os.path.expanduser("~/.local/share/xfce-todo/tasks.db")

_DEFAULTS = {
    "database_path": DEFAULT_DB,
    "pomodoro_work_mins": 25,
    "pomodoro_break_mins": 5,
    "notifications": True,
    "theme": "dark",
    "alert_sound": "system-default",
    "alert_sound_custom": "",
    "window_width": 1200,
    "window_height": 750,
}

def load() -> dict:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        _write(_DEFAULTS.copy()); return _DEFAULTS.copy()
    try:
        with open(CONFIG_FILE) as f: data = json.load(f)
        for k,v in _DEFAULTS.items(): data.setdefault(k,v)
        # Always expand ~ in database_path so it works regardless of user
        data["database_path"] = os.path.expandvars(
            os.path.expanduser(data["database_path"]))
        # If path points to an inaccessible location, reset to default
        db_dir = os.path.dirname(data["database_path"])
        try:
            os.makedirs(db_dir, exist_ok=True)
        except (PermissionError, OSError):
            print(f"[Config] DB path inaccessible: {data['database_path']}")
            print(f"[Config] Resetting to default: {DEFAULT_DB}")
            data["database_path"] = DEFAULT_DB
            _write(data)
        return data
    except Exception as e:
        print(f"[Config] Error loading config: {e}, using defaults")
        _write(_DEFAULTS.copy()); return _DEFAULTS.copy()

def save(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True); _write(cfg)

def change_database_path(cfg, new_path, move_existing=True):
    old = cfg.get("database_path", DEFAULT_DB)
    new_path = os.path.expanduser(new_path)
    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    if move_existing and os.path.exists(old) and old != new_path:
        shutil.copy2(old, new_path)
    cfg["database_path"] = new_path; save(cfg); return cfg

def _write(cfg):
    with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=2)
