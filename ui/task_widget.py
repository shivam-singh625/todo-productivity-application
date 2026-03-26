"""task_widget.py — Single task row with Cairo color dots and inline timer."""
import gi, math
gi.require_version("Gtk","4.0")
from gi.repository import Gtk, GObject, Pango
from ui.task_timer import TaskTimer

def _dot(hex_color, size=9):
    h = hex_color.lstrip("#")
    r,g,b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    da = Gtk.DrawingArea(); da.set_size_request(size,size); da.set_valign(Gtk.Align.CENTER)
    def draw(w,cr,ww,hh): cr.arc(ww/2,hh/2,min(ww,hh)/2-0.5,0,2*math.pi); cr.set_source_rgb(r,g,b); cr.fill()
    da.set_draw_func(draw); return da

def _to_display(iso):
    try: y,m,d=iso.split("-"); return f"{d}-{m}-{y}"
    except: return iso

class TaskWidget(Gtk.Box):
    __gsignals__ = {
        "toggled":             (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "edit-requested":      (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "delete-requested":    (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "duplicate-requested": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "star-requested":      (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "select-changed":      (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
    }
    def __init__(self, task_row, tm=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.task_id = task_row["id"]
        self._timer_widget = None
        self._tm = tm
        self._build(task_row)

    def _build(self, t):
        self.add_css_class("task-row")
        self.set_margin_start(4); self.set_margin_end(4)
        self.set_margin_top(2); self.set_margin_bottom(2)

        bar = Gtk.Box(); bar.set_size_request(4,-1); bar.add_css_class(f"priority-bar-{t['priority']}")
        self.append(bar)

        check = Gtk.CheckButton(); check.set_active(bool(t["completed"]))
        check.connect("toggled", self._on_toggle); self._check = check; self.append(check)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        content.set_hexpand(True)

        title_box = Gtk.Box(spacing=6)
        self._title_lbl = Gtk.Label(label=t["title"])
        self._title_lbl.set_halign(Gtk.Align.START)
        self._title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        self._title_lbl.add_css_class("task-title")
        if t["completed"]: self._title_lbl.add_css_class("task-completed")
        title_box.append(self._title_lbl)

        pri = Gtk.Label(label=t["priority"].capitalize())
        pri.add_css_class("priority-badge"); pri.add_css_class(f"priority-{t['priority']}")
        title_box.append(pri)
        content.append(title_box)

        # Meta row
        meta_box = Gtk.Box(spacing=6); meta_box.set_halign(Gtk.Align.START)
        cat_name  = t["category_name"] or ""
        cat_color = t["category_color"] if t["category_color"] else "#888"
        first = True
        if cat_name:
            meta_box.append(_dot(cat_color, 9))
            lbl = Gtk.Label(label=cat_name); lbl.add_css_class("task-meta"); meta_box.append(lbl); first=False
        if t["due_date"]:
            if not first: meta_box.append(Gtk.Label(label="·").__class__(label="·"))
            dl = Gtk.Label(label=f"📅 {_to_display(t['due_date'])}"); dl.add_css_class("task-meta"); meta_box.append(dl); first=False
        if t["tags"]:
            tags = " ".join(f"#{tg.strip()}" for tg in t["tags"].split(",") if tg.strip())
            tl = Gtk.Label(label=tags); tl.add_css_class("task-meta"); meta_box.append(tl)
        if cat_name or t["due_date"] or t["tags"]: content.append(meta_box)

        # Timer
        if t["timer_mode"] in ("countdown","stopwatch"):
            self._timer_widget = TaskTimer(
                task_id=t["id"], task_title=t["title"],
                mode=t["timer_mode"],
                initial_seconds=t["timer_seconds"] or 0,
                elapsed_seconds=t["timer_elapsed"] or 0,   # resume from saved pos
                category_id=t["category_id"], tm=self._tm)
            content.append(self._timer_widget)

        self.append(content)

        btn_box = Gtk.Box(spacing=2); btn_box.add_css_class("task-actions")

        # Bulk select checkbox (hidden by default, shown in bulk mode)
        self._sel_check = Gtk.CheckButton()
        self._sel_check.add_css_class("task-select-check")
        self._sel_check.set_visible(False)
        self._sel_check.connect("toggled", self._on_sel_toggled)
        btn_box.append(self._sel_check)

        # Star/favourite button
        try:
            starred = bool(t["starred"])
        except (KeyError, IndexError, TypeError):
            starred = False
        self._star_btn = Gtk.Button(label="★" if starred else "☆")
        self._star_btn.add_css_class("flat")
        self._star_btn.set_tooltip_text("Favourite / Star")
        if starred:
            self._star_btn.add_css_class("task-starred")
        self._star_btn.connect("clicked", lambda _: self.emit("star-requested", self.task_id))
        btn_box.append(self._star_btn)

        # Duplicate button
        dup_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        dup_btn.add_css_class("flat")
        dup_btn.set_tooltip_text("Duplicate task")
        dup_btn.connect("clicked", lambda _: self.emit("duplicate-requested", self.task_id))
        btn_box.append(dup_btn)

        # Edit + Delete
        for icon, sig, tip in [
            ("document-edit-symbolic",  "edit-requested",   "Edit"),
            ("edit-delete-symbolic",    "delete-requested", "Delete"),
        ]:
            btn = Gtk.Button(icon_name=icon); btn.add_css_class("flat")
            btn.set_tooltip_text(tip)
            btn.connect("clicked", lambda _,s=sig: self.emit(s, self.task_id))
            btn_box.append(btn)

        self.append(btn_box)

    def _on_toggle(self, check):
        self.emit("toggled", self.task_id)
        if check.get_active():
            self._title_lbl.add_css_class("task-completed")
            if self._timer_widget: self._timer_widget.pause()
        else: self._title_lbl.remove_css_class("task-completed")

    def _on_sel_toggled(self, check):
        self.emit("select-changed", self.task_id, check.get_active())

    def set_select_mode(self, enabled: bool):
        """Show/hide the bulk selection checkbox."""
        self._sel_check.set_visible(enabled)
        if not enabled:
            self._sel_check.set_active(False)

    def is_selected(self) -> bool:
        return self._sel_check.get_active() and self._sel_check.get_visible()

    def update_star(self, starred: bool):
        self._star_btn.set_label("★" if starred else "☆")
        if starred:
            self._star_btn.add_css_class("task-starred")
        else:
            self._star_btn.remove_css_class("task-starred")

    def cleanup(self):
        if self._timer_widget: self._timer_widget.cleanup()
