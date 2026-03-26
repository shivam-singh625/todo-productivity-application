"""task_dialog.py — Add/edit task dialog with smart defaults and quick date buttons."""
import gi
gi.require_version("Gtk","4.0")
from gi.repository import Gtk
from datetime import date, timedelta

PRIORITIES = ["low","medium","high"]

def _to_display(iso):
    try: y,m,d=iso.split("-"); return f"{d}-{m}-{y}"
    except: return iso or ""

def _to_storage(s):
    if not s or not s.strip(): return None
    try: d,m,y=s.strip().split("-"); return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    except: return s or None

def _today_display():
    d = date.today()
    return f"{d.day:02d}-{d.month:02d}-{d.year}"

def _tomorrow_display():
    d = date.today() + timedelta(days=1)
    return f"{d.day:02d}-{d.month:02d}-{d.year}"


class TaskDialog(Gtk.Dialog):

    def __init__(self, parent, tm, task_row=None):
        try:
            is_edit = bool(task_row and task_row["id"])
        except (TypeError, KeyError, IndexError):
            is_edit = bool(task_row)
        super().__init__(
            title="Edit Task" if is_edit else "New Task",
            transient_for=parent, modal=True)
        self.set_default_size(540, 620)
        self._tm       = tm
        self._task_row = task_row
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        ok = self.add_button("Save", Gtk.ResponseType.OK)
        ok.add_css_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)
        self._build_form()
        if task_row:
            self._populate(task_row)
        else:
            self._apply_smart_defaults()

    # ── Form ──────────────────────────────────────────────────────────────────

    def _build_form(self):
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(20); box.set_margin_end(20)
        box.set_margin_top(14);   box.set_margin_bottom(14)

        grid = Gtk.Grid()
        grid.set_row_spacing(10); grid.set_column_spacing(12)
        box.append(grid); r = 0

        # Title
        grid.attach(self._lbl("Title *"), 0, r, 1, 1)
        self._title = Gtk.Entry()
        self._title.set_hexpand(True)
        self._title.set_placeholder_text("What needs to be done?")
        self._title.set_activates_default(True)
        # Auto-suggestions as user types
        completion = Gtk.EntryCompletion()
        store = Gtk.ListStore(str)
        try:
            recent = self._tm.conn.execute(
                "SELECT DISTINCT title FROM tasks ORDER BY created_at DESC LIMIT 30"
            ).fetchall()
            for row in recent:
                store.append([row[0]])
        except Exception:
            pass
        completion.set_model(store)
        completion.set_text_column(0)
        completion.set_minimum_key_length(2)
        self._title.set_completion(completion)
        grid.attach(self._title, 1, r, 2, 1); r += 1

        # Description
        grid.attach(self._lbl("Description"), 0, r, 1, 1)
        sc = Gtk.ScrolledWindow()
        sc.set_min_content_height(60)
        sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._desc = Gtk.TextView()
        self._desc.set_wrap_mode(Gtk.WrapMode.WORD)
        sc.set_child(self._desc)
        grid.attach(sc, 1, r, 2, 1); r += 1

        # Category
        grid.attach(self._lbl("Category"), 0, r, 1, 1)
        self._cat = Gtk.ComboBoxText()
        self._cat.append_text("— None —")
        self._categories = list(self._tm.get_categories())
        for c in self._categories:
            self._cat.append_text(c["name"])
        self._cat.set_active(0)
        grid.attach(self._cat, 1, r, 1, 1); r += 1

        # Priority
        grid.attach(self._lbl("Priority"), 0, r, 1, 1)
        self._pri = Gtk.ComboBoxText()
        for p in PRIORITIES:
            self._pri.append_text(p.capitalize())
        self._pri.set_active(1)
        grid.attach(self._pri, 1, r, 1, 1); r += 1

        # Due Date + quick buttons
        grid.attach(self._lbl("Due Date"), 0, r, 1, 1)
        date_box = Gtk.Box(spacing=6)

        self._due = Gtk.Entry()
        self._due.set_placeholder_text("DD-MM-YYYY")
        self._due.set_size_request(115, -1)
        date_box.append(self._due)

        # Quick date buttons
        for label, fn in [("Today", _today_display), ("Tomorrow", _tomorrow_display), ("Clear", lambda: "")]:
            btn = Gtk.Button(label=label)
            btn.add_css_class("flat")
            btn.set_tooltip_text(f"Set due date to {label.lower()}")
            _fn = fn  # closure capture
            btn.connect("clicked", lambda _, f=_fn: self._due.set_text(f()))
            date_box.append(btn)

        grid.attach(date_box, 1, r, 2, 1); r += 1

        # Tags
        grid.attach(self._lbl("Tags"), 0, r, 1, 1)
        self._tags = Gtk.Entry()
        self._tags.set_placeholder_text("comma, separated, tags")
        grid.attach(self._tags, 1, r, 2, 1); r += 1

        sep = Gtk.Separator(); sep.set_margin_top(6); sep.set_margin_bottom(2)
        grid.attach(sep, 0, r, 3, 1); r += 1

        # Timer mode
        grid.attach(self._lbl("Timer Mode"), 0, r, 1, 1)
        self._timer_combo = Gtk.ComboBoxText()
        for t in ["None", "⏳  Countdown (counts down to 0)", "⏱  Stopwatch (counts upward)"]:
            self._timer_combo.append_text(t)
        self._timer_combo.set_active(0)
        self._timer_combo.set_hexpand(True)
        self._timer_combo.connect("changed", self._on_timer_changed)
        grid.attach(self._timer_combo, 1, r, 2, 1); r += 1

        self._dur_lbl = self._lbl("Duration")
        grid.attach(self._dur_lbl, 0, r, 1, 1)
        self._dur_box = Gtk.Box(spacing=6)
        self._h = Gtk.SpinButton.new_with_range(0, 23, 1); self._h.set_size_request(60, -1)
        self._dur_box.append(self._h); self._dur_box.append(Gtk.Label(label="h"))
        self._m = Gtk.SpinButton.new_with_range(0, 59, 1); self._m.set_value(25); self._m.set_size_request(60, -1)
        self._dur_box.append(self._m); self._dur_box.append(Gtk.Label(label="m"))
        self._s = Gtk.SpinButton.new_with_range(0, 59, 1); self._s.set_size_request(60, -1)
        self._dur_box.append(self._s); self._dur_box.append(Gtk.Label(label="s"))
        grid.attach(self._dur_box, 1, r, 2, 1)
        self._dur_lbl.set_visible(False); self._dur_box.set_visible(False)

    def _on_timer_changed(self, c):
        show = c.get_active() == 1
        self._dur_lbl.set_visible(show); self._dur_box.set_visible(show)

    @staticmethod
    def _lbl(t):
        l = Gtk.Label(label=t)
        l.set_halign(Gtk.Align.END)
        l.add_css_class("dim-label")
        return l

    # ── Smart defaults for new tasks ──────────────────────────────────────────

    def _apply_smart_defaults(self):
        """Auto-fill today's date, last used category and priority."""
        # Default date = today
        self._due.set_text(_today_display())

        # Last used category
        try:
            last_cat_id = self._tm.get_last_used_category()
            if last_cat_id:
                for i, c in enumerate(self._categories):
                    if c["id"] == last_cat_id:
                        self._cat.set_active(i + 1)
                        break
        except Exception:
            pass

        # Last used priority
        try:
            last_pri = self._tm.get_last_used_priority()
            if last_pri and last_pri in PRIORITIES:
                self._pri.set_active(PRIORITIES.index(last_pri))
        except Exception:
            pass

    # ── Populate (edit mode) ──────────────────────────────────────────────────

    def _populate(self, t):
        self._title.set_text(t["title"] or "")
        self._desc.get_buffer().set_text(t["description"] or "")
        self._due.set_text(_to_display(t["due_date"]) if t["due_date"] else "")
        self._tags.set_text(t["tags"] or "")
        pri = (t["priority"] or "medium").lower()
        self._pri.set_active(PRIORITIES.index(pri) if pri in PRIORITIES else 1)
        if t["category_id"]:
            for i, c in enumerate(self._categories):
                if c["id"] == t["category_id"]:
                    self._cat.set_active(i + 1); break
        mode = t["timer_mode"]; secs = t["timer_seconds"] or 0
        if mode == "countdown":
            self._timer_combo.set_active(1)
            self._dur_lbl.set_visible(True); self._dur_box.set_visible(True)
            h, rem = divmod(secs, 3600); m, s = divmod(rem, 60)
            self._h.set_value(h); self._m.set_value(m); self._s.set_value(s)
        elif mode == "stopwatch":
            self._timer_combo.set_active(2)
        else:
            self._timer_combo.set_active(0)

    # ── Data extraction ───────────────────────────────────────────────────────

    def get_task_data(self):
        title = self._title.get_text().strip()
        if not title:
            return None
        buf  = self._desc.get_buffer()
        desc = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        ci   = self._cat.get_active()
        cat_id = self._categories[ci-1]["id"] if ci > 0 and self._categories else None
        pi   = self._pri.get_active()
        priority = PRIORITIES[pi] if pi >= 0 else "medium"
        ti = self._timer_combo.get_active()
        if ti == 1:
            tm = "countdown"
            ts = int(self._h.get_value())*3600 + int(self._m.get_value())*60 + int(self._s.get_value())
            if ts == 0: ts = 25 * 60
        elif ti == 2:
            tm = "stopwatch"; ts = 0
        else:
            tm = None; ts = 0
        return {
            "title":        title,
            "description":  desc,
            "category_id":  cat_id,
            "priority":     priority,
            "due_date":     _to_storage(self._due.get_text().strip()),
            "tags":         self._tags.get_text().strip(),
            "timer_mode":   tm,
            "timer_seconds": ts,
        }
