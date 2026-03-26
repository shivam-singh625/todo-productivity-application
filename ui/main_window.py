"""main_window.py — Main window with sidebar nav, stacked views, floating timer."""
import gi, math
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

from ui.theme            import build_css, get_colors
from ui.task_widget      import TaskWidget
from ui.task_dialog      import TaskDialog
from ui.calendar_view    import CalendarView
from ui.pomodoro_timer   import PomodoroTimer
from ui.settings_window  import SettingsWindow
from ui.category_dialog  import CategoryDialog
from ui.dashboard        import DashboardPanel
from ui.analysis_panel   import AnalysisPanel
from ui.templates_dialog import TemplatesDialog
from ui.analysis_panel   import AnalysisPanel
from ui.notifier         import start_notifications, stop_notifications, reset_task_notifications
from ui.floating_timer   import FloatingTimerWindow
import ui.task_timer as tt_module


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


class MainWindow(Gtk.ApplicationWindow):

    def __init__(self, app, tm, cfg, dark=True):
        super().__init__(application=app)
        self._tm   = tm
        self._cfg  = cfg
        self._dark = dark
        self._c    = get_colors(dark)

        self._active_view   = "dashboard"
        self._active_filter = None
        self._active_cat    = None
        self._search_text   = ""
        self._task_widgets  = []
        self._bulk_mode     = False
        self._selected_ids  = set()
        self._cal_date      = None

        self.set_title("XFCE Productivity Todo")
        self.set_default_size(cfg.get("window_width", 1200), cfg.get("window_height", 750))
        self.set_resizable(True)     # ← allow resize + maximize

        # Global CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(build_css(dark))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Create floating window first
        self._float_win = FloatingTimerWindow()
        self._float_win._main_win_ref = self

        # Register float window with task timer module
        tt_module.set_float_window(self._float_win)

        self._build()
        self._setup_shortcuts()
        self._show_view("dashboard")

    # ── Build layout ──────────────────────────────────────────────────────────

    def _build(self):
        # Paned gives a draggable divider between sidebar and main area
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_wide_handle(True)   # wider grab area for easier resizing
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)
        paned.set_resize_start_child(False)  # sidebar doesn't auto-resize on window resize
        paned.set_resize_end_child(True)
        paned.set_position(230)
        self.set_child(paned)
        paned.set_start_child(self._build_sidebar())

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(120)
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
        paned.set_end_child(self._stack)

        self._dashboard = DashboardPanel(self._tm, self._c)
        self._stack.add_named(self._dashboard, "dashboard")
        self._stack.add_named(self._build_tasks_page(), "tasks")
        self._stack.add_named(self._build_calendar_page(), "calendar")
        self._analysis = AnalysisPanel(self._tm, self._c)
        self._stack.add_named(self._analysis, "analysis")

    def _build_sidebar(self):
        # Outer container: fills full height, fixed width
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.add_css_class("sidebar-panel")
        outer.set_size_request(220, -1)

        # ── Scrollable top section (nav + categories) ─────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)   # takes all available space above Pomodoro
        scroll.set_propagate_natural_height(False)

        sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        title = Gtk.Label(label="✅ Todo")
        title.add_css_class("app-title")
        title.set_halign(Gtk.Align.START)
        sb.append(title)
        sb.append(Gtk.Separator())

        sec = Gtk.Label(label="MAIN MENU")
        sec.add_css_class("sidebar-section-label")
        sec.set_halign(Gtk.Align.START)
        sb.append(sec)

        self._nav_btns = {}
        for icon, label, view in [
            ("view-grid-symbolic",            "Dashboard",    "dashboard"),
            ("view-list-symbolic",            "All Tasks",    "tasks_all"),
            ("appointment-soon-symbolic",     "Today",        "tasks_today"),
            ("go-next-symbolic",              "Upcoming",     "tasks_upcoming"),
            ("x-office-calendar-symbolic",    "Calendar",     "calendar"),
            ("emblem-default-symbolic",       "Completed",    "tasks_completed"),
            ("x-office-spreadsheet-symbolic", "📊 Analysis",  "analysis"),
        ]:
            btn = self._nav_btn(icon, label, view)
            self._nav_btns[view] = btn
            sb.append(btn)

        sb.append(Gtk.Separator())

        cat_hdr = Gtk.Box(spacing=4)
        cl = Gtk.Label(label="CATEGORIES")
        cl.add_css_class("sidebar-section-label")
        cl.set_halign(Gtk.Align.START)
        cl.set_hexpand(True)
        cat_hdr.append(cl)
        ab = Gtk.Button(icon_name="list-add-symbolic")
        ab.add_css_class("flat")
        ab.set_margin_end(6)
        ab.connect("clicked", self._open_cat_dialog)
        cat_hdr.append(ab)
        sb.append(cat_hdr)

        self._cat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sb.append(self._cat_box)
        self._rebuild_cats()

        scroll.set_child(sb)
        outer.append(scroll)

        # ── Fixed bottom section (Pomodoro + settings) ───────────────────────
        # This is always visible regardless of window height
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bottom.add_css_class("sidebar-bottom")

        outer.append(Gtk.Separator())

        self._pomodoro = PomodoroTimer(self._tm, self._cfg)
        self._pomodoro.connect("session-completed", lambda _: self._dashboard.refresh())
        self._pomodoro.set_float_window(self._float_win)
        bottom.append(self._pomodoro)

        s_btn = Gtk.Button(icon_name="preferences-system-symbolic")
        s_btn.add_css_class("flat")
        s_btn.set_margin_start(8); s_btn.set_margin_end(8)
        s_btn.set_margin_top(4);   s_btn.set_margin_bottom(8)
        s_btn.set_tooltip_text("Settings")
        s_btn.connect("clicked", self._open_settings)
        bottom.append(s_btn)

        outer.append(bottom)
        return outer

    def _nav_btn(self, icon, label, view):
        btn = Gtk.Button()
        btn.add_css_class("nav-btn")
        box = Gtk.Box(spacing=8)
        box.append(Gtk.Image.new_from_icon_name(icon))
        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.START)
        box.append(lbl)
        btn.set_child(box)
        btn.connect("clicked", lambda b, v=view: self._show_view(v))
        return btn

    def _rebuild_cats(self):
        while self._cat_box.get_first_child():
            self._cat_box.remove(self._cat_box.get_first_child())
        for cat in self._tm.get_categories():
            btn = Gtk.Button()
            btn.add_css_class("nav-btn")
            row = Gtk.Box(spacing=8)
            row.append(_dot(cat["color"], 10))
            lbl = Gtk.Label(label=cat["name"])
            lbl.set_halign(Gtk.Align.START)
            row.append(lbl)
            btn.set_child(row)
            btn.connect("clicked", lambda b, cid=cat["id"], cn=cat["name"]: self._show_cat(cid, cn))
            self._nav_btns[f"cat_{cat['id']}"] = btn
            self._cat_box.append(btn)

    def _build_tasks_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        topbar = Gtk.Box(spacing=8)
        topbar.add_css_class("topbar")
        page.append(topbar)

        self._view_title = Gtk.Label(label="All Tasks")
        self._view_title.add_css_class("section-heading")
        self._view_title.set_halign(Gtk.Align.START)
        self._view_title.set_hexpand(True)
        topbar.append(self._view_title)

        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search tasks…")
        self._search_entry.set_size_request(200, -1)
        self._search_entry.connect("search-changed", self._on_search)
        topbar.append(self._search_entry)

        tpl_btn = Gtk.Button(icon_name="document-new-symbolic")
        tpl_btn.add_css_class("flat")
        tpl_btn.set_tooltip_text("Task Templates (Ctrl+T)")
        tpl_btn.connect("clicked", lambda _: self._open_templates())
        topbar.append(tpl_btn)

        # Bulk select toggle
        self._bulk_btn = Gtk.ToggleButton(label="☑ Select")
        self._bulk_btn.add_css_class("flat")
        self._bulk_btn.set_tooltip_text("Toggle bulk selection mode")
        self._bulk_btn.connect("toggled", self._on_bulk_toggled)
        topbar.append(self._bulk_btn)

        new_btn = Gtk.Button(icon_name="list-add-symbolic")
        new_btn.add_css_class("suggested-action")
        new_btn.set_tooltip_text("New task (Ctrl+N)")
        new_btn.connect("clicked", lambda _: self._open_task_dialog())
        topbar.append(new_btn)

        # Bulk action bar (shown only in bulk mode) — goes ABOVE the scroll area
        self._bulk_bar = Gtk.Box(spacing=8)
        self._bulk_bar.add_css_class("bulk-action-bar")
        self._bulk_bar.set_margin_start(12); self._bulk_bar.set_margin_end(12)
        self._bulk_bar.set_margin_top(6);    self._bulk_bar.set_margin_bottom(6)
        self._bulk_bar.set_visible(False)

        self._bulk_count_lbl = Gtk.Label(label="0 selected")
        self._bulk_count_lbl.set_hexpand(True)
        self._bulk_count_lbl.set_halign(Gtk.Align.START)
        self._bulk_bar.append(self._bulk_count_lbl)

        for label, handler in [
            ("✓ Complete",     self._bulk_complete),
            ("⧉ Duplicate",    self._bulk_duplicate),
            ("⊕ Category",     self._bulk_category),
            ("🗑 Delete",      self._bulk_delete),
        ]:
            btn = Gtk.Button(label=label); btn.add_css_class("flat")
            btn.connect("clicked", handler)
            self._bulk_bar.append(btn)

        sel_all = Gtk.Button(label="Select All"); sel_all.add_css_class("flat")
        sel_all.connect("clicked", self._bulk_select_all)
        self._bulk_bar.append(sel_all)
        page.append(self._bulk_bar)   # append to page, not tasks_page

        sc = Gtk.ScrolledWindow()
        sc.set_vexpand(True)
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._task_lb = Gtk.ListBox()
        self._task_lb.set_selection_mode(Gtk.SelectionMode.NONE)
        self._task_lb.add_css_class("task-list-box")
        sc.set_child(self._task_lb)
        page.append(sc)

        # Quick-add bar
        qa = Gtk.Box(spacing=8)
        qa.add_css_class("topbar")
        self._quick_entry = Gtk.Entry()
        self._quick_entry.set_placeholder_text("Quick add task… (press Enter)")
        self._quick_entry.set_hexpand(True)
        self._quick_entry.connect("activate", self._on_quick_add)
        qa.append(self._quick_entry)
        page.append(qa)

        return page

    def _build_calendar_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        topbar = Gtk.Box(spacing=8); topbar.add_css_class("topbar")
        tl = Gtk.Label(label="Calendar"); tl.add_css_class("section-heading"); topbar.append(tl)
        page.append(topbar)

        content = Gtk.Box(spacing=0); content.set_vexpand(True)
        self._calendar = CalendarView(self._tm)
        self._calendar.connect("date-selected", self._on_cal_date)
        self._calendar.set_size_request(300, -1)
        content.append(self._calendar)
        content.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right.set_hexpand(True)
        self._cal_title = Gtk.Label(label="Select a date")
        self._cal_title.add_css_class("section-heading")
        self._cal_title.set_margin_start(16); self._cal_title.set_margin_top(16)
        self._cal_title.set_halign(Gtk.Align.START)
        right.append(self._cal_title)
        sc2 = Gtk.ScrolledWindow(); sc2.set_vexpand(True); sc2.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._cal_task_lb = Gtk.ListBox()
        self._cal_task_lb.set_selection_mode(Gtk.SelectionMode.NONE)
        self._cal_task_lb.add_css_class("task-list-box")
        sc2.set_child(self._cal_task_lb); right.append(sc2)
        content.append(right)
        page.append(content)
        return page

    # ── View switching ────────────────────────────────────────────────────────

    def _show_view(self, view: str):
        self._active_view = view
        for k, b in self._nav_btns.items():
            b.remove_css_class("nav-btn-active")
        if view in self._nav_btns:
            self._nav_btns[view].add_css_class("nav-btn-active")

        if view == "analysis":
            self._stop_dashboard_refresh()
            self._analysis.refresh()
            self._stack.set_visible_child_name("analysis")
        elif view == "dashboard":
            self._dashboard.refresh()
            self._stack.set_visible_child_name("dashboard")
            self._start_dashboard_refresh()
        elif view == "calendar":
            self._stop_dashboard_refresh()
            self._stack.set_visible_child_name("calendar")
        elif view.startswith("tasks"):
            self._stop_dashboard_refresh()
            self._stack.set_visible_child_name("tasks")
            self._active_cat = None
            titles = {
                "tasks_all":       "All Tasks",
                "tasks_today":     "Today",
                "tasks_upcoming":  "Upcoming",
                "tasks_completed": "Completed",
            }
            self._view_title.set_text(titles.get(view, "Tasks"))
            self._active_filter = {
                "tasks_all":       None,
                "tasks_today":     "today",
                "tasks_upcoming":  "upcoming",
                "tasks_completed": "completed",
            }.get(view)
            self._load_tasks()

    def _show_cat(self, cat_id, cat_name):
        for b in self._nav_btns.values(): b.remove_css_class("nav-btn-active")
        k = f"cat_{cat_id}"
        if k in self._nav_btns: self._nav_btns[k].add_css_class("nav-btn-active")
        self._active_view = "tasks"; self._active_cat = cat_id
        self._active_filter = None; self._view_title.set_text(cat_name)
        self._stack.set_visible_child_name("tasks")
        self._load_tasks()

    # ── Task loading ──────────────────────────────────────────────────────────

    def _load_tasks(self):
        for w in self._task_widgets: w.cleanup()
        self._task_widgets.clear()
        while self._task_lb.get_first_child():
            self._task_lb.remove(self._task_lb.get_first_child())

        completed = None; due_today = False; upcoming = False
        if self._active_filter == "completed":  completed = True
        elif self._active_filter == "today":    due_today = True
        elif self._active_filter == "upcoming": upcoming  = True

        tasks = self._tm.get_tasks(
            category_id=self._active_cat, completed=completed,
            search=self._search_text or None,
            due_today=due_today, upcoming=upcoming)

        if not tasks:
            e = Gtk.Label(label="No tasks here. Press Ctrl+N or use the quick-add bar.")
            e.add_css_class("empty-state")
            r = Gtk.ListBoxRow(); r.set_activatable(False); r.set_child(e)
            self._task_lb.append(r); return

        # ── Group tasks by due_date ───────────────────────────────────────────
        from datetime import date as _date
        from collections import OrderedDict

        def _group_key(t):
            """Return (sort_key, display_label) for a task."""
            d = t["due_date"]
            today = _date.today()
            is_completed = bool(t["completed"])

            if not d:
                return ("9999-99-99", "📌 No Due Date")
            try:
                td = _date.fromisoformat(d)
                delta = (td - today).days
                if delta < 0 and not is_completed:
                    # Only show Overdue for tasks that are NOT completed
                    label = f"⚠️ Overdue — {td.strftime('%d %b %Y')}"
                elif delta < 0 and is_completed:
                    # Completed past tasks go under their date (not overdue)
                    label = f"✅ {td.strftime('%d %b %Y')}"
                elif delta == 0:
                    label = "📅 Today"
                elif delta == 1:
                    label = "📅 Tomorrow"
                elif delta <= 7:
                    label = f"📅 {td.strftime('%A')}  ({td.strftime('%d %b')})"
                else:
                    label = f"📅 {td.strftime('%d %b %Y')}"
                return (d, label)
            except Exception:
                return ("9999-99-98", f"📅 {d}")

        # Build ordered groups preserving sort order
        groups = OrderedDict()
        for t in tasks:
            key, label = _group_key(t)
            if key not in groups:
                groups[key] = {"label": label, "tasks": []}
            groups[key]["tasks"].append(t)

        # Only show date groups when viewing All Tasks, Upcoming, or category views
        # For Today/Completed views, skip headers (they'd all be the same)
        show_headers = self._active_filter not in ("today", "completed")

        for key, group in sorted(groups.items()):
            if show_headers and len(groups) > 1:
                self._task_lb.append(self._make_date_header(group["label"], key))

            for t in group["tasks"]:
                w = TaskWidget(t, tm=self._tm)
                w.connect("toggled",             self._on_toggled)
                w.connect("edit-requested",      self._on_edit)
                w.connect("delete-requested",    self._on_delete)
                w.connect("duplicate-requested", self._on_duplicate)
                w.connect("star-requested",      self._on_star)
                w.connect("select-changed",      self._on_select_changed)
                if self._bulk_mode:
                    w.set_select_mode(True)
                self._task_widgets.append(w)
                lr = Gtk.ListBoxRow(); lr.set_activatable(False); lr.set_child(w)
                self._task_lb.append(lr)

        self._calendar.refresh_task_dates()

    def _make_date_header(self, label: str, date_key: str) -> Gtk.ListBoxRow:
        """Create a non-interactive date group header row."""
        from datetime import date as _date
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        row.set_selectable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(14)
        box.set_margin_bottom(4)

        lbl = Gtk.Label(label=label)
        lbl.set_halign(Gtk.Align.START)
        lbl.add_css_class("date-group-header")

        # Determine color based on date
        c = self._c
        try:
            today = _date.today()
            td    = _date.fromisoformat(date_key)
            delta = (td - today).days
            # Check if this header is for completed past tasks (label starts with ✅)
            if label.startswith("✅"):
                color = c["green"]
            elif delta < 0:
                color = c["red"]
            elif delta == 0:
                color = c["accent"]
            elif delta == 1:
                color = c["teal"]
            else:
                color = c["muted"]
        except Exception:
            color = c["muted"]

        provider = Gtk.CssProvider()
        provider.load_from_data(f"* {{ color: {color}; }}".encode())
        lbl.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Separator line after label
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_hexpand(True)
        sep.set_valign(Gtk.Align.CENTER)
        sep.set_opacity(0.25)

        # Task count badge
        box.append(lbl)
        box.append(sep)

        row.set_child(box)
        return row

    def _on_cal_date(self, _, ds):
        from datetime import date
        try:
            d = date.fromisoformat(ds)
            label = f"Tasks for {d.strftime('%d %b %Y')}"
        except Exception:
            label = f"Tasks for {ds}"
        self._cal_title.set_text(label)
        self._cal_date = ds   # remember selected date for refresh
        self._reload_cal_tasks()

    def _reload_cal_tasks(self):
        """Reload calendar task list for the currently selected date."""
        ds = getattr(self, "_cal_date", None)
        if not ds:
            return
        while self._cal_task_lb.get_first_child():
            self._cal_task_lb.remove(self._cal_task_lb.get_first_child())
        tasks = self._tm.get_tasks_by_date(ds)
        if not tasks:
            e = Gtk.Label(label="No tasks on this date.")
            e.add_css_class("empty-state")
            r = Gtk.ListBoxRow(); r.set_activatable(False); r.set_child(e)
            self._cal_task_lb.append(r)
            return
        for t in tasks:
            w = TaskWidget(t, tm=self._tm)
            # Wire up signals so toggle/edit/delete work from calendar view
            w.connect("toggled",          self._on_cal_toggled)
            w.connect("edit-requested",   self._on_edit)
            w.connect("delete-requested", self._on_delete)
            lr = Gtk.ListBoxRow(); lr.set_activatable(False); lr.set_child(w)
            self._cal_task_lb.append(lr)

    def _on_cal_toggled(self, w, tid):
        """Toggle from calendar view — refresh calendar + dashboard."""
        self._tm.toggle_complete(tid)
        GLib.idle_add(self._reload_cal_tasks)
        GLib.idle_add(self._calendar.refresh_task_dates)
        self._dashboard.refresh()

    def _on_search(self, entry):
        self._search_text = entry.get_text(); self._load_tasks()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def _open_task_dialog(self, tid=None):
        tr  = self._tm.get_task(tid) if tid else None
        dlg = TaskDialog(self, self._tm, tr)
        dlg.connect("response", self._on_dlg_resp, tid)
        dlg.present()

    def _on_dlg_resp(self, dlg, rid, tid):
        if rid == Gtk.ResponseType.OK:
            data = dlg.get_task_data()
            if data:
                if tid: self._tm.update_task(tid, **data)
                else:   self._tm.add_task(**data)
                self._load_tasks(); self._dashboard.refresh()
        dlg.destroy()

    def _on_quick_add(self, entry):
        title = entry.get_text().strip()
        if title:
            self._tm.add_task(title=title, category_id=self._active_cat)
            entry.set_text(""); self._load_tasks(); self._dashboard.refresh()

    def _on_toggled(self, w, tid):
        self._tm.toggle_complete(tid)
        GLib.idle_add(self._load_tasks)
        self._dashboard.refresh()

    def _on_edit(self, w, tid): self._open_task_dialog(tid)

    def _on_delete(self, w, tid):
        dlg = Gtk.MessageDialog(transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO, text="Delete this task?")
        def on_r(d, r):
            d.destroy()
            if r == Gtk.ResponseType.YES:
                self._tm.delete_task(tid); self._load_tasks(); self._dashboard.refresh()
        dlg.connect("response", on_r); dlg.present()

    # ── Settings / Categories ─────────────────────────────────────────────────

    # ── Duplicate / Star ─────────────────────────────────────────────────────

    def _on_duplicate(self, w, tid):
        new_id = self._tm.duplicate_task(tid)
        if new_id:
            self._load_tasks()
            self._dashboard.refresh()
            # Open edit dialog immediately for the duplicate
            GLib.idle_add(lambda: self._open_task_dialog(new_id))

    def _on_star(self, w, tid):
        starred = self._tm.toggle_star(tid)
        # Update the star button visually without full reload
        for widget in self._task_widgets:
            if hasattr(widget, "task_id") and widget.task_id == tid:
                widget.update_star(starred)
                break

    # ── Bulk actions ──────────────────────────────────────────────────────────

    def _on_bulk_toggled(self, btn):
        self._bulk_mode = btn.get_active()
        self._selected_ids.clear()
        self._bulk_bar.set_visible(self._bulk_mode)
        self._bulk_count_lbl.set_label("0 selected")
        for w in self._task_widgets:
            w.set_select_mode(self._bulk_mode)

    def _on_select_changed(self, w, tid, selected):
        if selected:
            self._selected_ids.add(tid)
        else:
            self._selected_ids.discard(tid)
        n = len(self._selected_ids)
        self._bulk_count_lbl.set_label(f"{n} selected")

    def _bulk_select_all(self, _):
        for w in self._task_widgets:
            if hasattr(w, "_sel_check") and w._sel_check.get_visible():
                w._sel_check.set_active(True)

    def _bulk_complete(self, _):
        if not self._selected_ids: return
        self._tm.bulk_complete(list(self._selected_ids))
        self._selected_ids.clear()
        self._load_tasks(); self._dashboard.refresh()

    def _bulk_duplicate(self, _):
        if not self._selected_ids: return
        self._tm.bulk_duplicate(list(self._selected_ids))
        self._selected_ids.clear()
        self._load_tasks(); self._dashboard.refresh()

    def _bulk_delete(self, _):
        if not self._selected_ids: return
        n = len(self._selected_ids)
        d = Gtk.MessageDialog(transient_for=self, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete {n} task{'s' if n>1 else ''}?")
        def on_r(dd, r):
            dd.destroy()
            if r == Gtk.ResponseType.YES:
                self._tm.bulk_delete(list(self._selected_ids))
                self._selected_ids.clear()
                self._load_tasks(); self._dashboard.refresh()
        d.connect("response", on_r); d.present()

    def _bulk_category(self, _):
        if not self._selected_ids: return
        dlg = Gtk.Dialog(title="Change Category", transient_for=self, modal=True)
        dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("Apply", Gtk.ResponseType.OK).add_css_class("suggested-action")
        box = dlg.get_content_area()
        box.set_margin_start(16); box.set_margin_end(16)
        box.set_margin_top(12);   box.set_margin_bottom(12)
        combo = Gtk.ComboBoxText()
        combo.append_text("— None —")
        cats = list(self._tm.get_categories())
        for c in cats: combo.append_text(c["name"])
        combo.set_active(0)
        box.append(Gtk.Label(label=f"Set category for {len(self._selected_ids)} tasks:"))
        box.append(combo)
        def on_r(d, r):
            if r == Gtk.ResponseType.OK:
                idx = combo.get_active()
                cat_id = cats[idx-1]["id"] if idx > 0 else None
                self._tm.bulk_set_category(list(self._selected_ids), cat_id)
                self._selected_ids.clear()
                self._load_tasks(); self._dashboard.refresh()
            d.destroy()
        dlg.connect("response", on_r); dlg.present()

    def _open_templates(self, _=None):
        dlg = TemplatesDialog(self, self._tm)
        dlg.connect("template-selected", self._on_template_selected)
        dlg.present()

    def _on_template_selected(self, dlg, tdict):
        """Open task dialog pre-filled from template."""
        from ui.task_dialog import TaskDialog
        # Build a fake task_row-like dict from template
        class _FakeRow(dict):
            def __getitem__(self, k): return self.get(k)
        fake = _FakeRow({
            "id": None, "title": tdict.get("title",""),
            "description": tdict.get("description",""),
            "category_id": tdict.get("category_id"),
            "priority": tdict.get("priority","medium"),
            "due_date": None, "tags": tdict.get("tags",""),
            "timer_mode": tdict.get("timer_mode"),
            "timer_seconds": tdict.get("timer_seconds",0),
            "completed": 0,
        })
        task_dlg = TaskDialog(self, self._tm, fake)
        task_dlg.connect("response", self._on_dlg_resp, None)
        task_dlg.present()

    def _open_settings(self, _=None):
        dlg = SettingsWindow(self, self._cfg)
        dlg.connect("settings-saved", self._on_settings_saved)
        dlg.present()

    def _on_settings_saved(self, dlg):
        self._cfg = dlg.get_updated_config()
        np = self._cfg.get("database_path")
        if np and np != self._tm.db_path:
            self._tm.reconnect(np)
            self._rebuild_cats()
            self._load_tasks()

    def _open_cat_dialog(self, _=None):
        dlg = CategoryDialog(self, self._tm)
        dlg.connect("categories-changed",
            lambda _: (self._rebuild_cats(), self._load_tasks()))
        dlg.present()

    # ── Shortcuts ─────────────────────────────────────────────────────────────

    def _start_dashboard_refresh(self):
        """Auto-refresh dashboard every 10s so focus time stays live."""
        if not hasattr(self, "_dash_refresh_id"):
            self._dash_refresh_id = None
        if self._dash_refresh_id is None:
            self._dash_refresh_id = GLib.timeout_add_seconds(10, self._auto_refresh_dash)

    def _stop_dashboard_refresh(self):
        if hasattr(self, "_dash_refresh_id") and self._dash_refresh_id:
            GLib.source_remove(self._dash_refresh_id)
            self._dash_refresh_id = None

    def _auto_refresh_dash(self) -> bool:
        """Refresh dashboard stats — keep running while dashboard is visible."""
        if self._active_view == "dashboard":
            # Only refresh stat cards, not full rebuild (avoid flicker)
            try:
                self._dashboard.refresh_stats_only()
            except Exception:
                self._dashboard.refresh()
            return True  # keep ticking
        self._dash_refresh_id = None
        return False

    def _setup_shortcuts(self):
        ctrl = Gdk.ModifierType.CONTROL_MASK
        def add(key, cb):
            sc = Gtk.ShortcutController()
            sc.set_scope(Gtk.ShortcutScope.MANAGED)
            sc.add_shortcut(Gtk.Shortcut(
                trigger=Gtk.KeyvalTrigger(keyval=key, modifiers=ctrl),
                action=Gtk.CallbackAction.new(lambda *_: (cb(), True)[1])))
            self.add_controller(sc)
        add(Gdk.KEY_n, lambda: self._open_task_dialog())
        add(Gdk.KEY_1, lambda: self._show_view("dashboard"))
        add(Gdk.KEY_2, lambda: self._show_view("tasks_all"))
        add(Gdk.KEY_3, lambda: self._show_view("calendar"))
        add(Gdk.KEY_t, lambda: self._open_templates())
