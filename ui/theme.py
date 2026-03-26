"""theme.py — Centralized dark/light theme colors and CSS."""

DARK = {
    "bg":      "#1a1b2e", "bg2": "#16213e", "bg3": "#0f3460",
    "card":    "#1e2035", "sidebar": "#12131f", "border": "#2a2d4a",
    "text":    "#e2e4f0", "muted": "#7b7f99", "accent": "#7c9ef8",
    "acc_fg":  "#0d0e1a", "green":  "#69d98c", "red":    "#f87c7c",
    "yellow":  "#f9c74f", "purple": "#c77dff", "teal":   "#56cfe1",
    "p_high":  "#f87c7c", "p_med":  "#ffb347", "p_low":  "#69d98c",
}
LIGHT = {
    "bg":      "#f8f9fa", "bg2": "#ffffff", "bg3": "#e9ecef",
    "card":    "#ffffff", "sidebar": "#f0f2f5", "border": "#dee2e6",
    "text":    "#212529", "muted": "#6c757d", "accent": "#0d6efd",
    "acc_fg":  "#ffffff", "green":  "#198754", "red":    "#dc3545",
    "yellow":  "#ffc107", "purple": "#6f42c1", "teal":   "#0dcaf0",
    "p_high":  "#dc3545", "p_med":  "#fd7e14", "p_low":  "#198754",
}

def get_colors(dark: bool) -> dict:
    return DARK if dark else LIGHT

def build_css(dark: bool) -> bytes:
    c = get_colors(dark)
    return f"""
    /* ── Window & base ───────────────────────────────────────────── */
    window, window > * {{
        background-color: {c['bg']};
        color: {c['text']};
    }}
    scrolledwindow > viewport,
    scrolledwindow > viewport > * {{
        background-color: {c['bg']};
    }}
    listbox, listbox row {{ background-color: transparent; }}

    /* ── Sidebar ─────────────────────────────────────────────────── */
    .sidebar-panel {{
        background-color: {c['sidebar']};
        border-right: 1px solid {c['border']};
        min-width: 210px;
    }}
    .app-title {{
        font-size: 1.15em; font-weight: 800;
        color: {c['accent']}; padding: 16px 16px 8px 16px;
    }}
    .sidebar-section-label {{
        font-size: 0.68em; font-weight: 700;
        letter-spacing: 1.5px; opacity: 0.55;
        padding: 10px 16px 2px 16px;
        color: {c['muted']};
    }}
    .nav-btn {{
        border-radius: 8px; padding: 7px 12px;
        margin: 1px 8px; font-size: 0.88em;
        color: {c['muted']}; background: transparent;
        border: none; transition: all 120ms;
    }}
    .nav-btn:hover {{
        background-color: alpha({c['accent']}, 0.12);
        color: {c['text']};
    }}
    .nav-btn-active {{
        background-color: alpha({c['accent']}, 0.2);
        color: {c['accent']}; font-weight: 600;
    }}

    /* ── Top bar ─────────────────────────────────────────────────── */
    .topbar {{
        background-color: {c['bg2']};
        border-bottom: 1px solid {c['border']};
        padding: 8px 16px;
    }}

    /* ── Dashboard cards ─────────────────────────────────────────── */
    .dash-card {{
        background-color: {c['card']};
        border-radius: 14px;
        border: 1px solid {c['border']};
        padding: 18px 18px 14px 18px;
    }}
    .dash-heading {{
        font-size: 1.3em; font-weight: 700;
        color: {c['text']}; margin-bottom: 4px;
    }}
    .dash-section-label {{
        font-size: 0.95em; font-weight: 600;
        color: {c['muted']}; margin-top: 4px;
    }}
    .dash-card-number {{
        font-size: 2.2em; font-weight: 800;
        font-variant-numeric: tabular-nums;
        margin: 2px 0;
    }}
    .dash-card-label {{
        font-size: 0.78em; color: {c['muted']};
    }}
    .dash-streak-number {{
        font-size: 2.6em; font-weight: 900;
        font-variant-numeric: tabular-nums;
        margin: 0;
    }}
    .dash-card-sub {{
        font-size: 0.73em; color: {c['muted']}; opacity: 0.7;
    }}
    .dash-empty {{
        font-size: 0.88em; color: {c['muted']};
        padding: 12px 0; opacity: 0.7;
    }}

    /* ── Task list ───────────────────────────────────────────────── */
    .task-list-box {{ background-color: {c['bg']}; }}
    .task-row {{
        background-color: {c['card']};
        border-radius: 10px; margin: 3px 10px;
        padding: 10px 8px; border: 1px solid {c['border']};
        transition: background 120ms;
    }}
    .task-row:hover {{ background-color: {c['bg3']}; }}
    .task-title    {{ font-weight: 600; font-size: 0.95em; color: {c['text']}; }}
    .task-completed {{ text-decoration: line-through; opacity: 0.45; }}
    .task-meta     {{ font-size: 0.78em; color: {c['muted']}; }}
    .task-actions button {{
        opacity: 0; transition: opacity 100ms;
        min-width: 28px; min-height: 28px; padding: 2px;
    }}
    .task-row:hover .task-actions button {{ opacity: 1; }}

    /* ── Priority ────────────────────────────────────────────────── */
    .priority-bar-high   {{ background-color: {c['p_high']}; border-radius: 3px; min-width: 4px; }}
    .priority-bar-medium {{ background-color: {c['p_med']};  border-radius: 3px; min-width: 4px; }}
    .priority-bar-low    {{ background-color: {c['p_low']};  border-radius: 3px; min-width: 4px; }}
    .priority-badge {{
        font-size: 0.66em; font-weight: 700;
        padding: 1px 7px; border-radius: 10px;
    }}
    .priority-high   {{ background-color: alpha({c['p_high']}, 0.15); color: {c['p_high']}; }}
    .priority-medium {{ background-color: alpha({c['p_med']},  0.15); color: {c['p_med']};  }}
    .priority-low    {{ background-color: alpha({c['p_low']},  0.15); color: {c['p_low']};  }}

    /* ── Calendar ────────────────────────────────────────────────── */
    .calendar-view {{ background-color: {c['bg']}; }}
    .calendar-header-label {{ font-weight: 700; color: {c['text']}; }}
    .dow-label {{ font-size: 0.72em; font-weight: 600; color: {c['muted']}; }}
    .day-btn   {{ min-width: 30px; min-height: 30px; padding: 2px; font-size: 0.82em; border-radius: 50%; color: {c['text']}; }}
    .day-today    {{ font-weight: 900; color: {c['accent']}; }}
    .day-selected {{ background-color: {c['accent']}; color: {c['acc_fg']}; }}
    .day-has-task {{ text-decoration: underline; color: {c['green']}; }}
    .day-empty    {{ opacity: 0; }}

    /* ── Pomodoro ────────────────────────────────────────────────── */
    .pomodoro-panel {{
        background-color: {c['bg2']};
        border-top: 1px solid {c['border']};
    }}
    .pomodoro-clock {{
        font-size: 2em; font-weight: 900;
        letter-spacing: 2px; font-variant-numeric: tabular-nums;
        color: {c['text']};
    }}
    .pomodoro-mode   {{ font-size: 0.8em; color: {c['muted']}; }}
    .pomodoro-progress {{ min-height: 4px; border-radius: 2px; }}

    /* ── Task timer ──────────────────────────────────────────────── */
    .task-timer-box {{
        background-color: alpha({c['accent']}, 0.08);
        border-radius: 8px; padding: 5px 10px;
        border: 1px solid alpha({c['accent']}, 0.25);
        margin-top: 6px;
    }}
    .task-timer-label {{
        font-size: 0.85em; font-variant-numeric: tabular-nums;
        font-weight: 700; min-width: 55px; color: {c['accent']};
    }}
    .task-timer-btn {{ padding: 0 5px; min-width: 24px; min-height: 24px; font-size: 0.8em; }}
    .task-timer-stop-btn {{
        padding: 2px 8px; font-size: 0.78em;
        background-color: alpha({c['red']}, 0.15);
        color: {c['red']}; border-radius: 4px;
        border: 1px solid alpha({c['red']}, 0.35);
    }}
    .task-timer-progress {{ min-height: 4px; border-radius: 2px; }}

    /* ── Section heading / misc ──────────────────────────────────── */
    .section-heading {{ font-size: 1.05em; font-weight: 700; color: {c['text']}; }}
    .stat-card-label {{ font-size: 0.78em; color: {c['muted']}; }}
    .empty-state     {{ font-size: 0.9em; opacity: 0.5; padding: 40px 20px; color: {c['muted']}; }}
    dialog, dialog > * {{ background-color: {c['bg']}; color: {c['text']}; }}
    .bulk-action-bar {{
        background-color: {c['bg2']};
        border-bottom: 1px solid {c['border']};
        border-radius: 6px;
    }}
    .task-starred {{ color: #f9e2af; }}
    .task-select-check {{ margin-right: 4px; }}
    .sidebar-bottom {{
        min-height: 160px;
    }}
    .analysis-row {{
        padding: 8px 4px; border-bottom: 1px solid {c['border']};
        font-size: 0.88em;
    }}
    .analysis-row:hover {{ background-color: {c['bg3']}; }}
    .analysis-row-header {{
        padding: 8px 4px; font-size: 0.82em;
        background-color: {c['bg2']};
        border-bottom: 2px solid {c['border']};
    }}
    .dash-heading {{
        font-size: 1.0em; font-weight: 700; color: {c['text']};
    }}
    .date-group-header {{
        font-size: 0.78em;
        font-weight: 700;
        letter-spacing: 0.8px;
        opacity: 0.9;
        padding: 0;
    }}
    .dash-streak-number {{
        font-size: 2.4em; font-weight: 800;
        font-variant-numeric: tabular-nums;
    }}
    .dash-streak-unit {{
        font-size: 0.9em; color: {c['muted']}; font-weight: 500;
    }}
    """.encode()
