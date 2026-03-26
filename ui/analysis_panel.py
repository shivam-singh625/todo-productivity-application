"""
analysis_panel.py — Test Analysis System.
Uses analysis_db.py backend for clean separation.
"""
import gi, math
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib
from datetime import datetime, date

from backend.analysis_db import (
    DEFAULT_SUBJECTS, ensure_analysis_schema,
    get_subjects, add_subject, delete_subject,
    add_test_entry, update_test_entry, delete_test_entry,
    fetch_all_entries, fetch_overview_stats,
    fetch_subject_stats, fetch_trend_data
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bar(pct: float, width: int = 18) -> str:
    filled = max(0, min(width, round(pct / 100 * width)))
    return "█" * filled + "░" * (width - filled)

def _lbl(text, css="", halign=Gtk.Align.START, wrap=False):
    lb = Gtk.Label(label=str(text))
    if css:
        for cls in css.split(): lb.add_css_class(cls)
    lb.set_halign(halign)
    if wrap: lb.set_wrap(True); lb.set_max_width_chars(60)
    return lb

def _card(child):
    f = Gtk.Frame(); f.add_css_class("dash-card"); f.set_child(child); return f

def _hex(c):
    h = c.lstrip("#")
    return int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255


# ══════════════════════════════════════════════════════════════════════════════
# Add / Edit Test Dialog
# ══════════════════════════════════════════════════════════════════════════════

class TestDialog(Gtk.Dialog):

    def __init__(self, parent, conn=None, entry=None):
        title = "Edit Test Entry" if entry else "Add Test Entry"
        super().__init__(title=title, transient_for=parent, modal=True)
        self._entry = entry
        self._conn  = conn
        # Get subjects dynamically
        self._subjects = get_subjects(conn) if conn else list(DEFAULT_SUBJECTS)
        self.set_default_size(460, -1)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        ok = self.add_button("Save", Gtk.ResponseType.OK)
        ok.add_css_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)
        self._build()
        if entry: self._populate(entry)

    def _build(self):
        grid = Gtk.Grid()
        grid.set_row_spacing(10); grid.set_column_spacing(12)
        grid.set_margin_start(18); grid.set_margin_end(18)
        grid.set_margin_top(14);   grid.set_margin_bottom(6)

        def lbl(t): l=Gtk.Label(label=t); l.set_halign(Gtk.Align.END); l.add_css_class("dim-label"); return l
        def spin(lo, hi, val=0, step=1, digits=0):
            s=Gtk.SpinButton.new_with_range(lo,hi,step); s.set_value(val)
            s.set_digits(digits); s.set_hexpand(True); return s

        r = 0
        # Subject
        grid.attach(lbl("Subject"), 0, r, 1, 1)
        self._subj = Gtk.DropDown.new_from_strings(self._subjects)
        self._subj.set_hexpand(True)
        grid.attach(self._subj, 1, r, 2, 1); r += 1

        # Date
        grid.attach(lbl("Date (DD-MM-YYYY)"), 0, r, 1, 1)
        self._date = Gtk.Entry()
        self._date.set_text(datetime.now().strftime("%d-%m-%Y"))
        self._date.set_hexpand(True)
        grid.attach(self._date, 1, r, 1, 1); r += 1

        grid.attach(Gtk.Separator(), 0, r, 3, 1); r += 1

        # Question fields
        for label, key, default in [
            ("Total Questions",  "total",    100),
            ("Attempted",        "attempted", 100),
            ("Correct",          "correct",     0),
            ("Incorrect",        "incorrect",   0),
            ("Skipped (auto)",   "skipped",     0),
            ("Time (minutes)",   "time",       60),
        ]:
            grid.attach(lbl(label), 0, r, 1, 1)
            w = spin(0, 999, default)
            if key == "skipped":
                w.set_tooltip_text("Auto = Total − Attempted if left 0")
            self.__dict__[f"_f_{key}"] = w
            grid.attach(w, 1, r, 1, 1)
            r += 1

        grid.attach(Gtk.Separator(), 0, r, 3, 1); r += 1

        # Marks scheme
        mhdr = Gtk.Label(label="Marks Scheme  (optional — default +4 / −1)")
        mhdr.add_css_class("dim-label"); mhdr.set_halign(Gtk.Align.START)
        grid.attach(mhdr, 0, r, 3, 1); r += 1

        grid.attach(lbl("Marks / correct"), 0, r, 1, 1)
        self._mc = spin(0, 20, 4, 0.25, 2)
        self._mc.set_tooltip_text("e.g. +4 for NEET, +2 for JEE")
        grid.attach(self._mc, 1, r, 1, 1)
        grid.attach(Gtk.Label(label="e.g. 4 = +4 per correct"), 2, r, 1, 1); r += 1

        grid.attach(lbl("Negative marking"), 0, r, 1, 1)
        self._mn = spin(0, 10, 1, 0.25, 2)
        self._mn.set_tooltip_text("e.g. 1 = deduct 1 per wrong")
        grid.attach(self._mn, 1, r, 1, 1)
        grid.attach(Gtk.Label(label="e.g. 1 = −1 per wrong"), 2, r, 1, 1); r += 1

        grid.attach(Gtk.Separator(), 0, r, 3, 1); r += 1

        grid.attach(lbl("Notes"), 0, r, 1, 1)
        self._notes = Gtk.Entry(); self._notes.set_hexpand(True)
        grid.attach(self._notes, 1, r, 2, 1); r += 1

        self.get_content_area().append(grid)

        # Live score preview
        self._preview = Gtk.Label(label="")
        self._preview.add_css_class("dash-card-sub")
        self._preview.set_halign(Gtk.Align.START)
        self._preview.set_margin_start(18); self._preview.set_margin_bottom(10)
        self.get_content_area().append(self._preview)

        for w in [self._f_total, self._f_attempted, self._f_correct,
                  self._f_incorrect, self._mc, self._mn]:
            w.connect("value-changed", self._update_preview)
        self._update_preview(None)

    def _update_preview(self, _):
        total = int(self._f_total.get_value())
        att   = int(self._f_attempted.get_value())
        cor   = int(self._f_correct.get_value())
        inc   = int(self._f_incorrect.get_value())
        mc    = self._mc.get_value()
        mn    = self._mn.get_value()
        skip  = total - att if total > att else int(self._f_skipped.get_value())
        acc   = round(cor / att * 100, 1) if att > 0 else 0.0
        score = cor * mc - inc * mn
        max_s = total * mc if total > 0 else 1
        pct   = round(score / max_s * 100, 1) if max_s > 0 else 0
        self._preview.set_label(
            f"→  Score: {score:.1f} / {max_s:.0f} ({pct}%)   "
            f"Accuracy: {acc}%   Skipped: {skip}")

    def _populate(self, e):
        subj = e.get("subject", SUBJECTS[0])
        if subj in self._subjects:
            self._subj.set_selected(self._subjects.index(subj))
        try:
            d = datetime.fromisoformat(e.get("taken_at","")).strftime("%d-%m-%Y")
            self._date.set_text(d)
        except Exception: pass
        self._f_total.set_value(e.get("total_questions", 0))
        self._f_attempted.set_value(e.get("attempted", 0))
        self._f_correct.set_value(e.get("correct", 0))
        self._f_incorrect.set_value(e.get("incorrect", 0))
        self._f_skipped.set_value(e.get("skipped", 0))
        self._f_time.set_value(e.get("time_taken_min", 0))
        self._mc.set_value(e.get("marks_correct", 4.0) or 4.0)
        self._mn.set_value(e.get("marks_negative", 1.0) or 1.0)
        self._notes.set_text(e.get("notes", "") or "")
        self._update_preview(None)

    def get_data(self):
        subj = self._subjects[self._subj.get_selected()] if self._subjects else "Biology"
        try:
            d, m, y = self._date.get_text().strip().split("-")
            taken_at = f"{y}-{m.zfill(2)}-{d.zfill(2)}T{datetime.now().strftime('%H:%M:%S')}"
        except Exception:
            taken_at = datetime.now().isoformat(timespec="seconds")
        return dict(
            subject         = subj,
            total_questions = int(self._f_total.get_value()),
            attempted       = int(self._f_attempted.get_value()),
            correct         = int(self._f_correct.get_value()),
            incorrect       = int(self._f_incorrect.get_value()),
            skipped         = int(self._f_skipped.get_value()) or None,
            time_taken_min  = self._f_time.get_value(),
            marks_correct   = self._mc.get_value(),
            marks_negative  = self._mn.get_value(),
            notes           = self._notes.get_text().strip(),
            taken_at        = taken_at,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Analysis Panel
# ══════════════════════════════════════════════════════════════════════════════

class AnalysisPanel(Gtk.Box):

    def __init__(self, tm, colors: dict):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._conn = tm.conn
        self._c    = colors
        self._active_subject = None
        self._body = None
        ensure_analysis_schema(self._conn)
        self._subjects = get_subjects(self._conn)   # dynamic from DB
        self._build()
        self.refresh()

    def _build(self):
        # Top bar
        topbar = Gtk.Box(spacing=8); topbar.add_css_class("topbar")
        self.append(topbar)

        title = _lbl("📊 Test Analysis", "section-heading")
        title.set_hexpand(True); topbar.append(title)

        # Subject filter toggle buttons (rebuilt dynamically)
        self._filter_box = Gtk.Box(spacing=4)
        self._filter_btns = {}
        self._rebuild_filter_buttons()
        topbar.append(self._filter_box)

        mgr_btn = Gtk.Button(label="⚙ Subjects")
        mgr_btn.add_css_class("flat")
        mgr_btn.set_tooltip_text("Add or remove subjects")
        mgr_btn.connect("clicked", self._open_subject_mgr)
        topbar.append(mgr_btn)

        add_btn = Gtk.Button(label="+ Add Test"); add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._open_add); topbar.append(add_btn)

        # Scrollable body
        sc = Gtk.ScrolledWindow()
        sc.set_vexpand(True)
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(sc)

        self._body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self._body.set_margin_start(20); self._body.set_margin_end(20)
        self._body.set_margin_top(16);   self._body.set_margin_bottom(20)
        sc.set_child(self._body)

    def _rebuild_filter_buttons(self):
        """Rebuild subject filter buttons from current subject list."""
        while self._filter_box.get_first_child():
            self._filter_box.remove(self._filter_box.get_first_child())
        self._filter_btns = {}
        for subj in ["All"] + self._subjects:
            btn = Gtk.ToggleButton(label=subj)
            btn.add_css_class("flat")
            btn.connect("toggled", self._on_filter, subj)
            self._filter_btns[subj] = btn
            self._filter_box.append(btn)
        # Restore active selection
        active = self._active_subject or "All"
        if active in self._filter_btns:
            self._filter_btns[active].set_active(True)
        else:
            self._filter_btns["All"].set_active(True)
            self._active_subject = None

    def refresh(self):
        if self._body is None:
            return
        while self._body.get_first_child():
            self._body.remove(self._body.get_first_child())

        subj       = self._active_subject
        overview   = fetch_overview_stats(self._conn, subject=subj)
        subj_stats = fetch_subject_stats(self._conn, subject=subj)
        entries    = [dict(r) for r in fetch_all_entries(self._conn, subject=subj)]
        trends     = [dict(r) for r in fetch_trend_data(self._conn, subject=subj)]

        self._body.append(self._overview_cards(overview))
        self._body.append(self._subject_bars(subj_stats))
        self._body.append(self._weak_areas(subj_stats))
        self._body.append(self._trend_section(trends))
        self._body.append(self._history_table(entries))

    # ── Overview cards ────────────────────────────────────────────────────────

    def _overview_cards(self, ov):
        box = Gtk.Box(spacing=12); box.set_homogeneous(True)
        c = self._c
        for icon, label, val, color in [
            ("🧪", "Total Tests",  str(int(ov.get("total_tests",0))),         c["accent"]),
            ("📈", "Avg Score",    f"{ov.get('avg_score',0):.1f}",            c["green"]),
            ("🎯", "Avg Accuracy", f"{ov.get('avg_accuracy',0):.1f}%",        c["teal"]),
            ("🏆", "Best Score",   f"{ov.get('best_score',0):.0f}",           c["yellow"]),
            ("📉", "Worst Score",  f"{ov.get('worst_score',0):.0f}",          c["red"]),
            ("⏱",  "Total Time",  f"{int(ov.get('total_time_min',0))} min",  c["purple"]),
        ]:
            cb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            cb.set_margin_start(4); cb.set_margin_end(4)
            cb.set_margin_top(12);  cb.set_margin_bottom(10)
            top = Gtk.Box(spacing=6); top.append(_lbl(icon)); top.append(_lbl(label, "dash-card-label")); cb.append(top)
            nl = _lbl(val, "dash-card-number")
            p = Gtk.CssProvider(); p.load_from_data(f"* {{ color: {color}; }}".encode())
            nl.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION); cb.append(nl)
            box.append(_card(cb))
        return box

    # ── Subject bars ──────────────────────────────────────────────────────────

    def _subject_bars(self, subj_stats):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_start(4); outer.set_margin_end(4)
        outer.set_margin_top(12);  outer.set_margin_bottom(8)
        outer.append(_lbl("📚 Subject Performance", "dash-heading"))
        outer.append(_lbl("Accuracy, average score and time by subject", "dash-card-label"))

        if not subj_stats:
            outer.append(_lbl("No data yet — add a test entry to get started.", "dash-card-sub"))
            return _card(outer)

        stats_map = {s["subject"]: s for s in subj_stats}
        grid = Gtk.Grid(); grid.set_row_spacing(10); grid.set_column_spacing(14); grid.set_margin_top(10)

        # Show only selected subject or all subjects
        display_subjects = [self._active_subject] if self._active_subject else self._subjects
        for i, subj in enumerate(display_subjects):
            s    = stats_map.get(subj)
            acc  = s["avg_accuracy"]   if s else 0.0
            scr  = s["avg_score"]      if s else 0.0
            tests= s["tests"]          if s else 0
            time = s["total_time_min"] if s else 0.0
            best = s["best_score"]     if s else 0.0

            # Color by accuracy
            bar_color = self._c["green"] if acc >= 70 else self._c["yellow"] if acc >= 50 else self._c["red"]

            sl = _lbl(subj)
            p0 = Gtk.CssProvider(); p0.load_from_data(b"* { font-size: 0.92em; font-weight: 600; }")
            sl.get_style_context().add_provider(p0, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            sl.set_size_request(100, -1); grid.attach(sl, 0, i, 1, 1)

            bar_lbl = _lbl(_bar(acc, 20))
            p = Gtk.CssProvider(); p.load_from_data(f"* {{ color: {bar_color}; font-family: monospace; font-size: 0.9em; }}".encode())
            bar_lbl.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            bar_lbl.set_size_request(175, -1); grid.attach(bar_lbl, 1, i, 1, 1)

            pl = _lbl(f"{acc:.1f}%")
            p3 = Gtk.CssProvider(); p3.load_from_data(f"* {{ font-size: 0.9em; font-weight: 700; color: {bar_color}; }}".encode())
            pl.get_style_context().add_provider(p3, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            pl.set_size_request(58,-1); grid.attach(pl,2,i,1,1)

            detail = f"Avg: {scr:.1f}  |  Best: {best:.0f}  |  {tests} test{'s' if tests!=1 else ''}  |  ⏱{time:.0f}m"
            dl = _lbl(detail)
            p = Gtk.CssProvider(); p.load_from_data(b"* { font-size: 0.84em; }")
            dl.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            grid.attach(dl, 3, i, 1, 1)

        outer.append(grid)
        return _card(outer)

    # ── Weak area detection ───────────────────────────────────────────────────

    def _weak_areas(self, subj_stats):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.set_margin_start(4); outer.set_margin_end(4)
        outer.set_margin_top(10);  outer.set_margin_bottom(8)
        outer.append(_lbl("⚠️  Weak Area Detection", "dash-heading"))

        stats_map = {s["subject"]: s for s in subj_stats}
        check_subjects = [self._active_subject] if self._active_subject else self._subjects
        weak = [s for s in check_subjects if s in stats_map and stats_map[s]["avg_accuracy"] < 60]

        if not weak:
            ok = _lbl("✅  All subjects above 60% accuracy — great work!", "dash-card-label")
            outer.append(ok)
        else:
            for subj in weak:
                acc = stats_map[subj]["avg_accuracy"]
                row = Gtk.Box(spacing=8); row.set_margin_top(4)
                row.append(_lbl("🔴"))
                msg = _lbl(f"{subj} needs improvement — accuracy: {acc:.1f}% (below 60%)", wrap=True)
                p = Gtk.CssProvider(); p.load_from_data(f"* {{ color: {self._c['red']}; font-weight:600; }}".encode())
                msg.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                row.append(msg); outer.append(row)

        return _card(outer)

    # ── Trend section ─────────────────────────────────────────────────────────

    def _trend_section(self, trends):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.set_margin_start(4); outer.set_margin_end(4)
        outer.set_margin_top(10);  outer.set_margin_bottom(8)
        outer.append(_lbl("📈 Performance Trend (last 20 tests)", "dash-heading"))
        outer.append(_lbl("Accuracy and score over time", "dash-card-label"))

        if not trends:
            outer.append(_lbl("No trend data yet.", "dash-card-sub"))
            return _card(outer)

        grid = Gtk.Grid(); grid.set_row_spacing(5); grid.set_column_spacing(10); grid.set_margin_top(8)
        for h, w in [("#",30),("Date",85),("Subject",85),("Trend",160),("Accuracy",72),("Score",60)]:
            l = _lbl(h,"dash-card-label"); l.set_size_request(w,-1); grid.attach(l, ["#","Date","Subject","Trend","Accuracy","Score"].index(h), 0, 1, 1)

        for i, e in enumerate(trends):
            date_s = (e.get("taken_at") or "")[:10]
            acc    = e.get("accuracy", 0) or 0
            score  = e.get("score", 0) or 0
            subj   = e.get("subject","—")
            col    = self._c["green"] if acc>=70 else self._c["yellow"] if acc>=50 else self._c["red"]
            ri = i+1
            for ci, (text, width) in enumerate([
                (str(i+1),30),(date_s,85),(subj,85)]):
                l=_lbl(text); l.set_size_request(width,-1)
                p=Gtk.CssProvider(); p.load_from_data(b"* { font-size: 0.86em; }")
                l.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                grid.attach(l,ci,ri,1,1)
            bl=_lbl(_bar(acc,14))
            p=Gtk.CssProvider(); p.load_from_data(f"* {{ color:{col}; font-family:monospace; font-size:0.85em; }}".encode())
            bl.get_style_context().add_provider(p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            bl.set_size_request(160,-1); grid.attach(bl,3,ri,1,1)
            al=_lbl(f"{acc:.1f}%","dash-card-sub"); al.set_size_request(72,-1); grid.attach(al,4,ri,1,1)
            sl=_lbl(f"{score:.0f}","dash-card-sub"); sl.set_size_request(60,-1); grid.attach(sl,5,ri,1,1)

        outer.append(grid)
        return _card(outer)

    # ── History table ─────────────────────────────────────────────────────────

    def _history_table(self, entries):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.set_margin_start(4); outer.set_margin_end(4)
        outer.set_margin_top(10);  outer.set_margin_bottom(8)
        hdr_row = Gtk.Box(spacing=8)
        hdr_row.append(_lbl("📋 Test History", "dash-heading"))
        hdr_row.append(_lbl(f"({len(entries)} test{'s' if len(entries)!=1 else ''})", "dash-card-sub"))
        outer.append(hdr_row)

        if not entries:
            outer.append(_lbl("No tests yet. Click '+ Add Test' to record your first test.", "dash-card-sub"))
            return _card(outer)

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc.set_min_content_height(200); sc.set_max_content_height(350)

        lb = Gtk.ListBox(); lb.set_selection_mode(Gtk.SelectionMode.NONE)
        lb.add_css_class("task-list-box"); lb.append(self._history_header())

        for e in entries: lb.append(self._history_row(e))
        sc.set_child(lb); outer.append(sc)
        return _card(outer)

    def _history_header(self):
        row = Gtk.ListBoxRow(); row.set_activatable(False)
        box = Gtk.Box(spacing=0)
        box.set_margin_start(8); box.set_margin_end(8)
        box.set_margin_top(5);   box.set_margin_bottom(5)
        for text, w in [("Date",85),("Subject",85),("Total",52),("Done",52),
                        ("✓",52),("✗",52),("Skip",52),("Marks",65),
                        ("Score",60),("Acc%",65),("Time",55),("",55)]:
            l = _lbl(text)
            l.set_size_request(w,-1)
            p = Gtk.CssProvider(); p.load_from_data(f"* {{ font-size:0.74em; font-weight:700; color:{self._c['muted']}; }}".encode())
            l.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            box.append(l)
        row.set_child(box); return row

    def _history_row(self, e):
        e = dict(e)   # convert sqlite3.Row to plain dict
        row = Gtk.ListBoxRow(); row.set_activatable(False); row.add_css_class("task-row")
        box = Gtk.Box(spacing=0)
        box.set_margin_start(8); box.set_margin_end(4)
        box.set_margin_top(4);   box.set_margin_bottom(4)
        c   = self._c
        acc = e.get("accuracy", 0.0) or 0.0
        mc  = e.get("marks_correct", 4.0) or 4.0
        mn  = e.get("marks_negative", 1.0) or 1.0
        acc_col = c["green"] if acc>=70 else c["yellow"] if acc>=50 else c["red"]
        scheme = f"+{mc:.0f}" if mn==0 else f"+{mc:.0f}/−{mn:.0f}"
        date_s = (e.get("taken_at") or "")[:10]
        try:
            date_s = datetime.fromisoformat(date_s).strftime("%d-%m-%Y")
        except Exception: pass

        cells = [
            (date_s,                    85, c["muted"]),
            (e["subject"] or "—",       85, c["text"]),
            (str(e["total_questions"]), 52, c["muted"]),
            (str(e["attempted"]),        52, c["muted"]),
            (str(e["correct"]),          52, c["green"]),
            (str(e["incorrect"]),        52, c["red"]),
            (str(e["skipped"]),          52, c["muted"]),
            (scheme,                     65, c["muted"]),
            (f"{e['score']:.1f}",        60, c["accent"]),
            (f"{acc:.1f}%",              65, acc_col),
            (f"{e['time_taken_min']:.0f}m", 55, c["muted"]),
        ]
        for text, width, color in cells:
            l = _lbl(text); l.set_size_request(width,-1)
            p = Gtk.CssProvider(); p.load_from_data(f"* {{ color:{color}; font-size:0.86em; }}".encode())
            l.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            box.append(l)

        # Edit + Delete buttons
        btns = Gtk.Box(spacing=2); btns.set_size_request(55,-1)
        eb = Gtk.Button(icon_name="document-edit-symbolic"); eb.add_css_class("flat")
        eb.set_tooltip_text("Edit"); eb.connect("clicked", self._on_edit, dict(e)); btns.append(eb)
        db = Gtk.Button(icon_name="user-trash-symbolic"); db.add_css_class("flat")
        db.set_tooltip_text("Delete"); db.connect("clicked", self._on_delete, e["id"]); btns.append(db)
        box.append(btns)
        row.set_child(box); return row

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_filter(self, btn, subject):
        if not btn.get_active():
            return
        # Deactivate all other buttons
        for s, b in self._filter_btns.items():
            if s != subject:
                b.handler_block_by_func(self._on_filter)
                b.set_active(False)
                b.handler_unblock_by_func(self._on_filter)
        new_subj = None if subject == "All" else subject
        if new_subj == self._active_subject:
            return   # No change, skip refresh
        self._active_subject = new_subj
        self.refresh()

    def _open_add(self, _=None):
        dlg = TestDialog(self.get_root(), conn=self._conn)
        dlg.connect("response", self._on_dialog_resp, None); dlg.present()

    def _on_edit(self, _, edict):
        edict = dict(edict) if not isinstance(edict, dict) else edict
        dlg = TestDialog(self.get_root(), conn=self._conn, entry=edict)
        dlg.connect("response", self._on_dialog_resp, edict["id"]); dlg.present()

    def _on_dialog_resp(self, dlg, rid, entry_id):
        if rid == Gtk.ResponseType.OK:
            data = dlg.get_data()
            try:
                if entry_id:
                    update_test_entry(self._conn, entry_id, **data)
                else:
                    add_test_entry(self._conn, **data)
                dlg.destroy()
                GLib.idle_add(self.refresh)
                return
            except Exception as e:
                print(f"[Analysis] Error saving: {e}")
        dlg.destroy()

    def _open_subject_mgr(self, _=None):
        dlg = SubjectManagerDialog(self.get_root(), self._conn)
        def on_close(d, r):
            d.destroy()
            # Reload subjects and rebuild filter buttons
            self._subjects = get_subjects(self._conn)
            self._rebuild_filter_buttons()
            self.refresh()
        dlg.connect("response", on_close)
        dlg.present()

    def _on_delete(self, _, eid):
        d = Gtk.MessageDialog(transient_for=self.get_root(), modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO, text="Delete this test entry?")
        def on_r(dd, r):
            dd.destroy()
            if r == Gtk.ResponseType.YES:
                delete_test_entry(self._conn, eid); self.refresh()
        d.connect("response", on_r); d.present()


# ══════════════════════════════════════════════════════════════════════════════
# Subject Manager Dialog
# ══════════════════════════════════════════════════════════════════════════════

class SubjectManagerDialog(Gtk.Dialog):
    """Add or remove subjects from the analysis system."""

    def __init__(self, parent, conn):
        super().__init__(title="Manage Subjects", transient_for=parent, modal=True)
        self._conn = conn
        self.set_default_size(340, 400)
        self.add_button("Done", Gtk.ResponseType.CLOSE)
        self._build()

    def _build(self):
        box = self.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(16); box.set_margin_end(16)
        box.set_margin_top(12);   box.set_margin_bottom(12)

        # Add new subject row
        add_row = Gtk.Box(spacing=8)
        self._new_entry = Gtk.Entry()
        self._new_entry.set_placeholder_text("New subject name…")
        self._new_entry.set_hexpand(True)
        self._new_entry.connect("activate", self._on_add)
        add_row.append(self._new_entry)

        add_btn = Gtk.Button(label="+ Add")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add)
        add_row.append(add_btn)
        box.append(add_row)

        hint = Gtk.Label(label="You can add any subject (e.g. Mathematics, History…)")
        hint.add_css_class("dim-label")
        hint.set_halign(Gtk.Align.START)
        box.append(hint)
        box.append(Gtk.Separator())

        # Subject list
        sc = Gtk.ScrolledWindow()
        sc.set_vexpand(True)
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._lb = Gtk.ListBox()
        self._lb.set_selection_mode(Gtk.SelectionMode.NONE)
        self._lb.add_css_class("boxed-list")
        sc.set_child(self._lb)
        box.append(sc)

        self._reload()

    def _reload(self):
        while self._lb.get_first_child():
            self._lb.remove(self._lb.get_first_child())

        subjects = get_subjects(self._conn)
        for subj in subjects:
            row = Gtk.ListBoxRow()
            row.set_activatable(False)

            hbox = Gtk.Box(spacing=8)
            hbox.set_margin_start(12); hbox.set_margin_end(8)
            hbox.set_margin_top(8);    hbox.set_margin_bottom(8)

            lbl = Gtk.Label(label=subj)
            lbl.set_halign(Gtk.Align.START)
            lbl.set_hexpand(True)
            hbox.append(lbl)

            # Check how many tests use this subject
            try:
                count = self._conn.execute(
                    "SELECT COUNT(*) FROM test_entries WHERE subject=?", (subj,)
                ).fetchone()[0]
                if count > 0:
                    cl = Gtk.Label(label=f"{count} test{'s' if count!=1 else ''}")
                    cl.add_css_class("dim-label")
                    hbox.append(cl)
            except Exception:
                pass

            del_btn = Gtk.Button(icon_name="user-trash-symbolic")
            del_btn.add_css_class("flat")
            del_btn.set_tooltip_text(f"Remove '{subj}'")
            del_btn.connect("clicked", self._on_delete, subj)
            hbox.append(del_btn)

            row.set_child(hbox)
            self._lb.append(row)

    def _on_add(self, _):
        name = self._new_entry.get_text().strip()
        if not name:
            return
        if add_subject(self._conn, name):
            self._new_entry.set_text("")
            self._reload()
        else:
            # Already exists — flash the entry
            self._new_entry.add_css_class("error")
            from gi.repository import GLib
            GLib.timeout_add(600, lambda: self._new_entry.remove_css_class("error") or False)

    def _on_delete(self, _, subj):
        # Warn if subject has test entries
        try:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM test_entries WHERE subject=?", (subj,)
            ).fetchone()[0]
        except Exception:
            count = 0

        msg = f"Remove subject '{subj}'?"
        detail = (f"This subject has {count} test {'entries' if count!=1 else 'entry'} "
                  f"which will remain but become unfiltered." if count > 0
                  else "No test entries use this subject.")

        d = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=msg, secondary_text=detail)
        def on_r(dd, r):
            dd.destroy()
            if r == Gtk.ResponseType.YES:
                delete_subject(self._conn, subj)
                self._reload()
        d.connect("response", on_r)
        d.present()
