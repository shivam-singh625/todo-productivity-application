"""
templates_dialog.py — Manage and apply task templates.
"""
import gi, math
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject

PRIORITIES = ["low", "medium", "high"]


def _dot(hex_color, size=10):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255
    da = Gtk.DrawingArea()
    da.set_size_request(size, size)
    da.set_valign(Gtk.Align.CENTER)
    def draw(w, cr, ww, hh):
        cr.arc(ww/2, hh/2, min(ww,hh)/2-0.5, 0, 2*math.pi)
        cr.set_source_rgb(r, g, b); cr.fill()
    da.set_draw_func(draw)
    return da


def _fmt_secs(s):
    s = int(s)
    if not s: return "—"
    h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    if h:  return f"{h}h {m}m" if m else f"{h}h"
    if m:  return f"{m}m {sec}s" if sec else f"{m}m"
    return f"{sec}s"


class TemplatesDialog(Gtk.Dialog):
    """List saved templates — Use / Edit / Delete each one."""

    __gsignals__ = {
        "template-selected": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self, parent, tm):
        super().__init__(title="Task Templates", transient_for=parent, modal=True)
        self._tm = tm
        self.set_default_size(560, 460)
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.connect("response", lambda d, _: d.destroy())
        self._build()

    def _build(self):
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(16); box.set_margin_end(16)
        box.set_margin_top(14);   box.set_margin_bottom(14)

        # Header
        hdr = Gtk.Box(spacing=8)
        lbl = Gtk.Label(label="Saved Templates")
        lbl.add_css_class("section-heading")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_hexpand(True)
        hdr.append(lbl)
        new_btn = Gtk.Button(label="+ New Template")
        new_btn.add_css_class("suggested-action")
        new_btn.connect("clicked", self._on_new)
        hdr.append(new_btn)
        box.append(hdr)
        box.append(Gtk.Separator())

        # List
        sc = Gtk.ScrolledWindow()
        sc.set_vexpand(True)
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        sc.set_child(self._list)
        box.append(sc)

        self._reload()

    def _reload(self):
        while self._list.get_first_child():
            self._list.remove(self._list.get_first_child())

        templates = self._tm.get_templates()
        if not templates:
            empty = Gtk.Label(
                label="No templates yet.\nClick '+ New Template' to create one.")
            empty.add_css_class("empty-state")
            empty.set_halign(Gtk.Align.CENTER)
            empty.set_justify(Gtk.Justification.CENTER)
            row = Gtk.ListBoxRow(); row.set_activatable(False)
            row.set_child(empty); self._list.append(row)
            return

        for t in templates:
            self._list.append(self._make_row(t))

    def _make_row(self, t):
        row = Gtk.ListBoxRow()
        row.set_activatable(False)

        outer = Gtk.Box(spacing=10)
        outer.set_margin_start(10); outer.set_margin_end(8)
        outer.set_margin_top(10);   outer.set_margin_bottom(10)

        # Info column
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        info.set_hexpand(True)

        name_lbl = Gtk.Label(label=t["name"])
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.add_css_class("task-title")
        info.append(name_lbl)

        if t["title"] != t["name"]:
            title_lbl = Gtk.Label(label=f'→ "{t["title"]}"')
            title_lbl.set_halign(Gtk.Align.START)
            title_lbl.add_css_class("task-meta")
            info.append(title_lbl)

        # Meta row: category · priority · timer
        meta = Gtk.Box(spacing=6)
        cats = self._tm.get_categories()
        cat_name = "—"; cat_color = "#888888"
        for c in cats:
            if c["id"] == t["category_id"]:
                cat_name = c["name"]; cat_color = c["color"]; break

        meta.append(_dot(cat_color, 9))
        cl = Gtk.Label(label=cat_name); cl.add_css_class("task-meta"); meta.append(cl)

        sep = Gtk.Label(label="·"); sep.add_css_class("task-meta"); meta.append(sep)
        pl = Gtk.Label(label=t["priority"].capitalize())
        pl.add_css_class(f"priority-{t['priority']}"); pl.add_css_class("priority-badge")
        meta.append(pl)

        if t["timer_mode"]:
            sep2 = Gtk.Label(label="·"); sep2.add_css_class("task-meta"); meta.append(sep2)
            icon = "⏱" if t["timer_mode"] == "stopwatch" else "⏳"
            ts = _fmt_secs(t["timer_seconds"]) if t["timer_mode"] == "countdown" else "Stopwatch"
            tl = Gtk.Label(label=f"{icon} {ts}"); tl.add_css_class("task-meta"); meta.append(tl)

        info.append(meta)

        if t["description"]:
            dl = Gtk.Label(label=t["description"][:80])
            dl.set_halign(Gtk.Align.START)
            dl.add_css_class("task-meta"); dl.set_ellipsize(3)
            info.append(dl)

        outer.append(info)

        # Buttons
        btns = Gtk.Box(spacing=6)
        use = Gtk.Button(label="Use")
        use.add_css_class("suggested-action")
        use.set_tooltip_text("Create a new task from this template")
        use.connect("clicked", self._on_use, dict(t))
        btns.append(use)

        edit = Gtk.Button(icon_name="document-edit-symbolic")
        edit.add_css_class("flat")
        edit.set_tooltip_text("Edit template")
        edit.connect("clicked", self._on_edit, dict(t))
        btns.append(edit)

        dele = Gtk.Button(icon_name="edit-delete-symbolic")
        dele.add_css_class("flat")
        dele.set_tooltip_text("Delete template")
        dele.connect("clicked", self._on_delete, t["id"])
        btns.append(dele)

        outer.append(btns)
        row.set_child(outer)
        return row

    def _on_use(self, _, tdict):
        self.emit("template-selected", tdict)

    def _on_new(self, _):
        dlg = TemplateEditDialog(self, self._tm)
        def on_resp(d, r):
            if r == Gtk.ResponseType.OK:
                data = d.get_data()
                if data: self._tm.save_template(**data); self._reload()
            d.destroy()
        dlg.connect("response", on_resp); dlg.present()

    def _on_edit(self, _, tdict):
        dlg = TemplateEditDialog(self, self._tm, tdict)
        def on_resp(d, r):
            if r == Gtk.ResponseType.OK:
                data = d.get_data()
                if data: self._tm.save_template(**data); self._reload()
            d.destroy()
        dlg.connect("response", on_resp); dlg.present()

    def _on_delete(self, _, tid):
        c = Gtk.MessageDialog(transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO, text="Delete this template?")
        def on_resp(d, r):
            d.destroy()
            if r == Gtk.ResponseType.YES:
                self._tm.delete_template(tid); self._reload()
        c.connect("response", on_resp); c.present()


class TemplateEditDialog(Gtk.Dialog):
    """Create or edit a single template."""

    def __init__(self, parent, tm, template=None):
        super().__init__(
            title="Edit Template" if template else "New Template",
            transient_for=parent, modal=True)
        self._tm   = tm
        self._tmpl = template
        self.set_default_size(480, 460)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        ok = self.add_button("Save", Gtk.ResponseType.OK)
        ok.add_css_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)
        self._build()
        if template:
            self._populate(template)

    def _build(self):
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_start(20); box.set_margin_end(20)
        box.set_margin_top(14);   box.set_margin_bottom(14)

        grid = Gtk.Grid()
        grid.set_row_spacing(10); grid.set_column_spacing(12)
        box.append(grid); r = 0

        grid.attach(self._lbl("Template Name *"), 0, r, 1, 1)
        self._name_e = Gtk.Entry()
        self._name_e.set_hexpand(True)
        self._name_e.set_placeholder_text("e.g. Physics Lecture")
        self._name_e.set_activates_default(True)
        grid.attach(self._name_e, 1, r, 2, 1); r += 1

        grid.attach(self._lbl("Task Title *"), 0, r, 1, 1)
        self._title_e = Gtk.Entry()
        self._title_e.set_hexpand(True)
        self._title_e.set_placeholder_text("Default task title when used")
        grid.attach(self._title_e, 1, r, 2, 1); r += 1

        grid.attach(self._lbl("Description"), 0, r, 1, 1)
        sc = Gtk.ScrolledWindow(); sc.set_min_content_height(55)
        self._desc = Gtk.TextView(); self._desc.set_wrap_mode(Gtk.WrapMode.WORD)
        sc.set_child(self._desc)
        grid.attach(sc, 1, r, 2, 1); r += 1

        grid.attach(self._lbl("Category"), 0, r, 1, 1)
        self._cat = Gtk.ComboBoxText()
        self._cat.append_text("— None —")
        self._categories = list(self._tm.get_categories())
        for c in self._categories: self._cat.append_text(c["name"])
        self._cat.set_active(0)
        grid.attach(self._cat, 1, r, 1, 1); r += 1

        grid.attach(self._lbl("Priority"), 0, r, 1, 1)
        self._pri = Gtk.ComboBoxText()
        for p in PRIORITIES: self._pri.append_text(p.capitalize())
        self._pri.set_active(1)
        grid.attach(self._pri, 1, r, 1, 1); r += 1

        grid.attach(self._lbl("Tags"), 0, r, 1, 1)
        self._tags = Gtk.Entry()
        self._tags.set_placeholder_text("comma, separated")
        grid.attach(self._tags, 1, r, 2, 1); r += 1

        sep = Gtk.Separator(); sep.set_margin_top(4)
        grid.attach(sep, 0, r, 3, 1); r += 1

        grid.attach(self._lbl("Timer Mode"), 0, r, 1, 1)
        self._timer_c = Gtk.ComboBoxText()
        for t in ["None", "⏳  Countdown", "⏱  Stopwatch"]:
            self._timer_c.append_text(t)
        self._timer_c.set_active(0)
        self._timer_c.connect("changed", self._on_timer_changed)
        grid.attach(self._timer_c, 1, r, 1, 1); r += 1

        self._dur_lbl = self._lbl("Duration")
        grid.attach(self._dur_lbl, 0, r, 1, 1)
        self._dur_box = Gtk.Box(spacing=6)
        self._h = Gtk.SpinButton.new_with_range(0, 23, 1)
        self._h.set_size_request(60, -1)
        self._dur_box.append(self._h); self._dur_box.append(Gtk.Label(label="h"))
        self._m = Gtk.SpinButton.new_with_range(0, 59, 1)
        self._m.set_value(25); self._m.set_size_request(60, -1)
        self._dur_box.append(self._m); self._dur_box.append(Gtk.Label(label="m"))
        self._s = Gtk.SpinButton.new_with_range(0, 59, 1)
        self._s.set_size_request(60, -1)
        self._dur_box.append(self._s); self._dur_box.append(Gtk.Label(label="s"))
        grid.attach(self._dur_box, 1, r, 2, 1)
        self._dur_lbl.set_visible(False); self._dur_box.set_visible(False)

    def _on_timer_changed(self, c):
        show = (c.get_active() == 1)
        self._dur_lbl.set_visible(show); self._dur_box.set_visible(show)

    @staticmethod
    def _lbl(t):
        l = Gtk.Label(label=t); l.set_halign(Gtk.Align.END)
        l.add_css_class("dim-label"); return l

    def _populate(self, t):
        self._name_e.set_text(t.get("name", "") or "")
        self._title_e.set_text(t.get("title", "") or "")
        self._desc.get_buffer().set_text(t.get("description", "") or "")
        self._tags.set_text(t.get("tags", "") or "")
        pri = (t.get("priority") or "medium").lower()
        self._pri.set_active(PRIORITIES.index(pri) if pri in PRIORITIES else 1)
        if t.get("category_id"):
            for i, c in enumerate(self._categories):
                if c["id"] == t["category_id"]:
                    self._cat.set_active(i+1); break
        mode = t.get("timer_mode"); secs = t.get("timer_seconds") or 0
        if mode == "countdown":
            self._timer_c.set_active(1)
            self._dur_lbl.set_visible(True); self._dur_box.set_visible(True)
            h, rem = divmod(secs, 3600); m, s = divmod(rem, 60)
            self._h.set_value(h); self._m.set_value(m); self._s.set_value(s)
        elif mode == "stopwatch":
            self._timer_c.set_active(2)

    def get_data(self):
        name  = self._name_e.get_text().strip()
        title = self._title_e.get_text().strip()
        if not name or not title: return None
        buf  = self._desc.get_buffer()
        desc = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        ci   = self._cat.get_active()
        cat_id = self._categories[ci-1]["id"] if ci > 0 and self._categories else None
        pi   = self._pri.get_active()
        pri  = PRIORITIES[pi] if pi >= 0 else "medium"
        ti   = self._timer_c.get_active()
        if ti == 1:
            tm = "countdown"
            ts = int(self._h.get_value())*3600 + int(self._m.get_value())*60 + int(self._s.get_value())
            if ts == 0: ts = 25*60
        elif ti == 2:
            tm = "stopwatch"; ts = 0
        else:
            tm = None; ts = 0
        return dict(name=name, title=title, description=desc,
                    category_id=cat_id, priority=pri,
                    tags=self._tags.get_text().strip(),
                    timer_mode=tm, timer_seconds=ts)
