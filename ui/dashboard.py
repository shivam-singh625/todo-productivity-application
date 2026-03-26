"""
dashboard.py — Dashboard: stat cards, streak cards, line chart, bar chart, category bars.
"""
import gi, math
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib
from datetime import datetime, timedelta, date


def _fmt_secs(s: int) -> str:
    s = int(s)
    if s < 60:   return f"{s}s"
    if s < 3600: m=s//60; r=s%60; return f"{m}m {r}s" if r else f"{m}m"
    h=s//3600; m=(s%3600)//60; return f"{h}h {m}m" if m else f"{h}h"

def _hex(c): h=c.lstrip("#"); return int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255

def _dot(hex_color, size=10):
    r,g,b=_hex(hex_color); da=Gtk.DrawingArea(); da.set_size_request(size,size); da.set_valign(Gtk.Align.CENTER)
    def draw(w,cr,ww,hh): cr.arc(ww/2,hh/2,min(ww,hh)/2-0.5,0,2*math.pi); cr.set_source_rgb(r,g,b); cr.fill()
    da.set_draw_func(draw); return da


class DashboardPanel(Gtk.Box):
    def __init__(self, tm, colors):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._tm = tm
        self._c  = colors
        self._cat_date = None   # None = today
        self._cat_date_lbl = None
        self._cat_card = None
        self._build()

    def _build(self):
        scroll=Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True); scroll.set_hexpand(True)

        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_start(20); outer.set_margin_end(20)
        outer.set_margin_top(20); outer.set_margin_bottom(20)

        # Greeting
        hour=datetime.now().hour
        g="Good morning" if hour<12 else "Good afternoon" if hour<17 else "Good evening"
        hl=Gtk.Label(label=f"{g} 👋"); hl.add_css_class("dash-heading"); hl.set_halign(Gtk.Align.START)
        outer.append(hl)

        # ── Stats row ─────────────────────────────────────────────────────────
        c=self._c
        focus_secs = self._tm.today_focus_seconds()
        done_today = self._tm.today_completed_count()
        total      = self._tm.total_tasks_count()
        overdue    = self._tm.overdue_count()
        upcoming   = self._tm.upcoming_count()
        completed  = self._tm.completed_tasks_count()

        stats_grid=Gtk.Grid(); stats_grid.set_row_spacing(12); stats_grid.set_column_spacing(12); stats_grid.set_column_homogeneous(True)
        for i,(icon,label,val,color,sub) in enumerate([
            ("🎯","Focus Today",   _fmt_secs(focus_secs), c["accent"],  "Total focused time today"),
            ("✅","Done Today",    str(done_today),        c["green"],   "Tasks completed today"),
            ("📋","Active Tasks",  str(total),             c["purple"],  "Tasks not yet completed"),
            ("⚠️","Overdue",       str(overdue),           c["red"],     "Past due date, not done"),
            ("📅","Upcoming",      str(upcoming),          c["teal"],    "Due today or later"),
            ("🏆","All Completed", str(completed),         c["yellow"],  "All-time completed tasks"),
        ]):
            r,col=divmod(i,3); stats_grid.attach(self._stat_card(icon,label,val,color,sub),col,r,1,1)
        outer.append(stats_grid)

        # ── Streak cards ──────────────────────────────────────────────────────
        streak_lbl=Gtk.Label(label="🔥 Streaks"); streak_lbl.add_css_class("dash-section-label"); streak_lbl.set_halign(Gtk.Align.START)
        outer.append(streak_lbl)

        try:
            daily_s   = self._tm.daily_streak()
            weekly_s  = self._tm.weekly_streak()
            longest_d = self._tm.longest_daily_streak()
            longest_w = self._tm.longest_weekly_streak()
        except Exception:
            daily_s=weekly_s=longest_d=longest_w=0

        streak_grid=Gtk.Grid(); streak_grid.set_row_spacing(12); streak_grid.set_column_spacing(12); streak_grid.set_column_homogeneous(True)
        for i,(icon,label,val,color,sub) in enumerate([
            ("🔥","Daily Streak",         f"{daily_s}",   c["accent"],  "Days"),
            ("📅","Weekly Streak",        f"{weekly_s}",  c["teal"],    "Weeks"),
            ("⚡","Longest Daily Streak", f"{longest_d}", c["purple"],  "Days — personal best"),
            ("🏅","Longest Weekly Streak",f"{longest_w}", c["yellow"],  "Weeks — personal best"),
        ]):
            streak_grid.attach(self._streak_card(icon,label,val,color,sub),i,0,1,1)
        outer.append(streak_grid)

        # ── Charts row: line + bar side by side ───────────────────────────────
        charts_lbl=Gtk.Label(label="📊 Activity"); charts_lbl.add_css_class("dash-section-label"); charts_lbl.set_halign(Gtk.Align.START)
        outer.append(charts_lbl)

        charts_row=Gtk.Box(spacing=12)

        # Line chart card (30-day focus time)
        line_card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        line_card.add_css_class("dash-card"); line_card.set_hexpand(True)
        ll=Gtk.Label(label="Focus Time (30 days)"); ll.add_css_class("dash-card-label"); ll.set_halign(Gtk.Align.START)
        line_card.append(ll)
        self._line_da=Gtk.DrawingArea(); self._line_da.set_size_request(-1,160); self._line_da.set_hexpand(True)
        self._line_da.set_draw_func(self._draw_monthly_time_chart); line_card.append(self._line_da)
        charts_row.append(line_card)

        # Bar chart card (weekly focus)
        bar_card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bar_card.add_css_class("dash-card"); bar_card.set_hexpand(True)
        bl=Gtk.Label(label="Weekly Focus Time"); bl.add_css_class("dash-card-label"); bl.set_halign(Gtk.Align.START)
        bar_card.append(bl)
        self._bar_da=Gtk.DrawingArea(); self._bar_da.set_size_request(-1,160); self._bar_da.set_hexpand(True)
        self._bar_da.set_draw_func(self._draw_bar_chart); bar_card.append(self._bar_da)
        charts_row.append(bar_card)

        outer.append(charts_row)

        # ── Category goal progress (date-filtered) ───────────────────────────
        cat_header_row = Gtk.Box(spacing=12)
        cat_header_row.set_valign(Gtk.Align.CENTER)

        cat_lbl = Gtk.Label(label="📂 Category Progress")
        cat_lbl.add_css_class("dash-section-label")
        cat_lbl.set_halign(Gtk.Align.START)
        cat_header_row.append(cat_lbl)

        # Date navigation: [<]  16-03-2026  [>]  [Today]
        prev_btn = Gtk.Button(label="‹")
        prev_btn.add_css_class("flat")
        prev_btn.set_tooltip_text("Previous day")
        prev_btn.connect("clicked", self._cat_prev_day)
        cat_header_row.append(prev_btn)

        self._cat_date_lbl = Gtk.Label()
        self._cat_date_lbl.set_size_request(100, -1)
        self._cat_date_lbl.set_halign(Gtk.Align.CENTER)
        self._cat_date_lbl.add_css_class("dash-card-label")
        cat_header_row.append(self._cat_date_lbl)

        next_btn = Gtk.Button(label="›")
        next_btn.add_css_class("flat")
        next_btn.set_tooltip_text("Next day")
        next_btn.connect("clicked", self._cat_next_day)
        cat_header_row.append(next_btn)

        today_btn = Gtk.Button(label="Today")
        today_btn.add_css_class("flat")
        today_btn.set_tooltip_text("Jump to today")
        today_btn.connect("clicked", self._cat_goto_today)
        cat_header_row.append(today_btn)

        outer.append(cat_header_row)

        # Category cards container — rebuilt on date change
        self._cat_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self._cat_card.add_css_class("dash-card")
        outer.append(self._cat_card)
        self._rebuild_cat_card()

        scroll.set_child(outer); self.append(scroll)

    # ── Stat card ─────────────────────────────────────────────────────────────
    def _stat_card(self, icon, label, val, color, sub):
        card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("dash-card"); card.set_hexpand(True)
        top=Gtk.Box(spacing=8); top.append(Gtk.Label(label=icon))
        lbl=Gtk.Label(label=label); lbl.add_css_class("dash-card-label"); lbl.set_halign(Gtk.Align.START); lbl.set_hexpand(True); top.append(lbl)
        card.append(top)
        vl=Gtk.Label(label=str(val)); vl.add_css_class("dash-card-number"); vl.set_halign(Gtk.Align.START)
        p=Gtk.CssProvider(); p.load_from_data(f"* {{ color: {color}; }}".encode())
        vl.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION); card.append(vl)
        sl=Gtk.Label(label=sub); sl.add_css_class("dash-card-sub"); sl.set_halign(Gtk.Align.START); card.append(sl)
        acc=Gtk.Box(); acc.set_size_request(-1,3)
        p2=Gtk.CssProvider(); p2.load_from_data(f"* {{ background-color: {color}; border-radius: 2px; }}".encode())
        acc.get_style_context().add_provider(p2, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION); card.append(acc)
        return card

    # ── Streak card ───────────────────────────────────────────────────────────
    def _streak_card(self, icon, label, val, color, sub):
        card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("dash-card"); card.set_hexpand(True)
        il=Gtk.Label(label=f"{icon}  {label}"); il.add_css_class("dash-card-label"); il.set_halign(Gtk.Align.START); card.append(il)
        row=Gtk.Box(spacing=8); row.set_valign(Gtk.Align.BASELINE)
        vl=Gtk.Label(label=val); vl.add_css_class("dash-streak-number")
        p=Gtk.CssProvider(); p.load_from_data(f"* {{ color: {color}; }}".encode())
        vl.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION); row.append(vl)
        ul=Gtk.Label(label=sub); ul.add_css_class("dash-card-sub"); ul.set_valign(Gtk.Align.END); row.append(ul)
        card.append(row)
        return card

    # ── Category goal progress bar ───────────────────────────────────────────

    def _cat_goal_bar(self, row, for_date: str = None):
        """
        Shows for each category on a specific date:
          Goal  = sum of timer_seconds for tasks DUE on that date
          Spent = actual focus time logged on that date
          Bar   = spent / goal
          Detail = Remaining · Tasks X/Y completed
        """
        from datetime import date as _date
        name         = row["name"]
        color        = row["color"]
        goal         = int(row["total_goal_seconds"])
        spent        = int(row["focus_seconds_date"])
        tasks_due    = int(row["tasks_due"])
        tasks_done   = int(row["tasks_completed"])

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        # ── Header row: dot  name  spent/goal  pct ──────────────────────────
        hdr = Gtk.Box(spacing=8)
        hdr.append(_dot(color, 10))

        name_lbl = Gtk.Label(label=name)
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.set_hexpand(True)
        hdr.append(name_lbl)

        if goal > 0:
            pct    = min(100, int(100 * spent / goal))
            remain = max(0, goal - spent)
            goal_lbl = Gtk.Label(label=f"{_fmt_secs(spent)} / {_fmt_secs(goal)}")
        else:
            pct    = 0
            remain = 0
            goal_lbl = Gtk.Label(label=f"{_fmt_secs(spent)} spent")

        goal_lbl.add_css_class("dash-card-label")
        hdr.append(goal_lbl)

        pct_lbl = Gtk.Label(label=f"{pct}%")
        pct_lbl.add_css_class("dash-card-label")
        pct_lbl.set_size_request(40, -1)
        hdr.append(pct_lbl)
        box.append(hdr)

        # ── Progress bar ─────────────────────────────────────────────────────
        frac = min(1.0, spent / goal) if goal > 0 else 0.0
        bar  = Gtk.ProgressBar()
        bar.set_fraction(frac)
        p = Gtk.CssProvider()
        p.load_from_data(
            f"progressbar > trough > progress {{ background-color: {color}; border-radius: 4px; }}".encode())
        bar.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        box.append(bar)

        # ── Detail line: Remaining · Today ───────────────────────────────────
        parts = []
        if goal > 0:
            parts.append(f"Remaining: {_fmt_secs(remain)}")
        if tasks_due > 0:
            parts.append(f"Tasks: {tasks_done}/{tasks_due} done")
        parts.append(f"Time spent: {_fmt_secs(spent)}")
        dl = Gtk.Label(label="   ·   ".join(parts))
        dl.add_css_class("dash-card-sub")
        dl.set_halign(Gtk.Align.START)
        box.append(dl)

        return box

    def _cat_bar(self, name, color, secs, total):
        """Legacy fallback."""
        return self._cat_goal_bar({
            "name": name, "color": color,
            "total_goal_seconds": total,
            "focus_seconds_date": secs,
            "tasks_due": 0, "tasks_completed": 0,
        })

    # ── Line chart (30-day completed tasks) ───────────────────────────────────
    def _draw_monthly_time_chart(self, widget, cr, w, h):
        """30-day focus time as area line chart."""
        c=self._c
        try:
            rows = self._tm.get_monthly_time_activity()
        except Exception:
            rows = []
        today = date.today()
        days  = [(today - timedelta(days=29-i)) for i in range(30)]
        day_map = {r["day"]: r["total_seconds"] for r in rows}
        values  = [day_map.get(d.isoformat(), 0) for d in days]
        max_val = max(values) if any(v > 0 for v in values) else 1

        ar,ag,ab=_hex(c["accent"])
        mr,mg,mb=_hex(c["muted"])
        gr,gg,gb=_hex(c["green"])

        pl,pr,pt,pb=14,14,16,28
        cw=w-pl-pr; ch=h-pt-pb

        # Grid lines
        for i in range(3):
            gy=pt+ch*(1-i/2)
            cr.set_source_rgba(mr,mg,mb,0.12); cr.set_line_width(0.5)
            cr.move_to(pl,gy); cr.line_to(pl+cw,gy); cr.stroke()

        # Compute points
        step=cw/max(len(days)-1,1)
        pts=[(pl+i*step, pt+ch-(values[i]/max_val)*ch) for i in range(len(days))]

        # Filled area under line
        if any(values):
            cr.move_to(pts[0][0], pt+ch)
            for x,y in pts: cr.line_to(x,y)
            cr.line_to(pts[-1][0], pt+ch)
            cr.close_path()
            cr.set_source_rgba(ar,ag,ab,0.12); cr.fill()

        # Line
        cr.set_source_rgba(ar,ag,ab,0.9); cr.set_line_width(1.8)
        cr.set_line_join(0)  # miter
        first=True
        for x,y in pts:
            if first: cr.move_to(x,y); first=False
            else: cr.line_to(x,y)
        cr.stroke()

        # Dots + time labels above each data point
        for i,(x,y) in enumerate(pts):
            if values[i] > 0:
                # Outer glow
                cr.arc(x, y, 5, 0, 2*math.pi)
                cr.set_source_rgba(ar,ag,ab,0.2); cr.fill()
                # Inner dot
                cr.arc(x, y, 3, 0, 2*math.pi)
                cr.set_source_rgba(ar,ag,ab,1.0); cr.fill()
                # Time label ABOVE the dot (aligned to same x as dot)
                secs = int(values[i])
                if secs >= 3600:
                    s = f"{secs//3600}h{(secs%3600)//60}m" if (secs%3600)//60 else f"{secs//3600}h"
                elif secs >= 60:
                    s = f"{secs//60}m"
                else:
                    s = f"{secs}s"
                cr.set_source_rgba(ar,ag,ab,0.9)
                cr.set_font_size(8)
                ext = cr.text_extents(s)
                # Label centered above the dot
                label_x = x - ext.width/2
                label_y = y - 8
                # Keep label inside chart bounds
                label_x = max(pl, min(label_x, pl+cw-ext.width))
                cr.move_to(label_x, label_y); cr.show_text(s)

        # Date labels on X-axis — show at evenly spaced positions
        # Always show first, last, and every ~7 days
        cr.set_source_rgba(mr,mg,mb,0.75); cr.set_font_size(8)
        label_indices = list(range(0, 30, 7)) + [29]
        last_lbl_x = -999
        for i in sorted(set(label_indices)):
            x = pts[i][0]
            lbl = days[i].strftime("%b %d")
            ext = cr.text_extents(lbl)
            lx = x - ext.width/2
            # Avoid overlapping labels
            if lx > last_lbl_x + 2:
                cr.move_to(lx, h - 4)
                cr.show_text(lbl)
                last_lbl_x = lx + ext.width

    # ── Bar chart (weekly focus) ──────────────────────────────────────────────
    def _draw_bar_chart(self, widget, cr, w, h):
        c=self._c
        try: rows=self._tm.weekly_focus()
        except: rows=[]
        today=date.today()
        days=[(today-timedelta(days=6-i)) for i in range(7)]
        day_map={r["day"]:r["total"] for r in rows}
        values=[day_map.get(d.isoformat(),0) for d in days]
        max_val=max(values) if any(values) else 1

        ar,ag,ab=_hex(c["accent"])
        mr,mg,mb=_hex(c["muted"])

        pl,pr,pt,pb=14,14,16,28
        cw=w-pl-pr; ch=h-pt-pb
        bar_w=cw/7*0.5; gap=cw/7

        # Grid lines
        for i in range(3):
            gy=pt+ch*(1-i/2)
            cr.set_source_rgba(mr,mg,mb,0.12); cr.set_line_width(0.5)
            cr.move_to(pl,gy); cr.line_to(pl+cw,gy); cr.stroke()

        for i,(day,val) in enumerate(zip(days,values)):
            bh=(val/max_val)*ch if max_val else 0
            x=pl+i*gap+(gap-bar_w)/2; y=pt+ch-bh
            is_today=(day==today)
            cr.set_source_rgba(ar,ag,ab,0.9 if is_today else 0.45)
            rr=min(4,bar_w/2)
            if bh>rr*2:
                cr.move_to(x+rr,y); cr.line_to(x+bar_w-rr,y)
                cr.arc(x+bar_w-rr,y+rr,rr,-math.pi/2,0)
                cr.line_to(x+bar_w,pt+ch); cr.line_to(x,pt+ch)
                cr.arc(x+rr,y+rr,rr,math.pi,3*math.pi/2); cr.fill()
            elif bh>0:
                cr.rectangle(x,y,bar_w,bh); cr.fill()
            cr.set_source_rgba(mr,mg,mb,0.8); cr.set_font_size(10)
            lbl=day.strftime("%a"); ext=cr.text_extents(lbl)
            cr.move_to(x+bar_w/2-ext.width/2,h-6); cr.show_text(lbl)
            if val>0:
                cr.set_source_rgba(ar,ag,ab,1.0); cr.set_font_size(9)
                vs=_fmt_secs(val); ext2=cr.text_extents(vs)
                cr.move_to(x+bar_w/2-ext2.width/2,y-4); cr.show_text(vs)

    def _today_streak_card(self, status):
        """Shows today's streak progress: X/Y tasks done."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("dash-card")

        total = status["total_due"]
        done  = status["completed"]
        c     = self._c

        header = Gtk.Box(spacing=8)
        icon = Gtk.Label(label="🎯")
        title = Gtk.Label(label="Today's Streak Progress")
        title.add_css_class("dash-section-label")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header.append(icon); header.append(title)
        card.append(header)

        if total == 0:
            # No tasks due today — show how many were completed anyway
            any_done = status["any_done"]
            msg = Gtk.Label()
            if any_done:
                msg.set_markup(f"<b>✅ No tasks were due today, but you completed tasks — streak counts!</b>")
                msg.set_halign(Gtk.Align.START)
                color = c["green"]
            else:
                msg.set_markup("No tasks due today. Complete any task to keep your streak alive!")
                msg.set_halign(Gtk.Align.START)
                color = c["muted"]
            p = Gtk.CssProvider()
            p.load_from_data(f"* {{ color: {color}; font-size: 0.88em; }}".encode())
            msg.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            card.append(msg)
        else:
            # Show X / Y tasks completed
            frac = done / total
            all_done = (done == total)

            # Status text
            if all_done:
                status_color = c["green"]
                status_text  = f"🎉 All {total} tasks completed — streak maintained!"
            else:
                remaining    = total - done
                status_color = c["yellow"] if frac >= 0.5 else c["red"]
                status_text  = f"{done}/{total} tasks done  —  {remaining} remaining to keep streak"

            status_lbl = Gtk.Label(label=status_text)
            status_lbl.set_halign(Gtk.Align.START)
            p = Gtk.CssProvider()
            p.load_from_data(f"* {{ color: {status_color}; font-size: 0.88em; font-weight: 600; }}".encode())
            status_lbl.get_style_context().add_provider(p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            card.append(status_lbl)

            # Progress bar
            bar = Gtk.ProgressBar()
            bar.set_fraction(frac)
            bar.set_show_text(True)
            bar.set_text(f"{done} / {total}")
            color = c["green"] if all_done else (c["yellow"] if frac >= 0.5 else c["red"])
            pb = Gtk.CssProvider()
            pb.load_from_data(
                f"progressbar > trough > progress {{ background-color: {color}; border-radius: 4px; }}".encode()
            )
            bar.get_style_context().add_provider(pb, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            card.append(bar)

        return card

    # ── Category date navigation ─────────────────────────────────────────────

    def _cat_get_date(self) -> str:
        from datetime import date
        if self._cat_date is None:
            return date.today().isoformat()
        return self._cat_date

    def _cat_prev_day(self, _):
        from datetime import date, timedelta
        d = date.fromisoformat(self._cat_get_date())
        self._cat_date = (d - timedelta(days=1)).isoformat()
        self._rebuild_cat_card()

    def _cat_next_day(self, _):
        from datetime import date, timedelta
        d = date.fromisoformat(self._cat_get_date())
        nxt = d + timedelta(days=1)
        self._cat_date = min(nxt, date.today()).isoformat()
        self._rebuild_cat_card()

    def _cat_goto_today(self, _):
        self._cat_date = None
        self._rebuild_cat_card()

    def _rebuild_cat_card(self):
        """Clear and rebuild category card for the selected date."""
        from datetime import date
        d_str = self._cat_get_date()
        try:
            d = date.fromisoformat(d_str)
            today = date.today()
            label = f"Today  ({d.strftime('%d-%m-%Y')})" if d == today else d.strftime('%d-%m-%Y')
        except Exception:
            label = d_str

        self._cat_date_lbl.set_label(label)

        # Clear
        while self._cat_card.get_first_child():
            self._cat_card.remove(self._cat_card.get_first_child())

        prog_rows = self._tm.get_category_goal_progress(for_date=d_str)
        if not prog_rows:
            msg = f"No tasks or focus sessions on {label}. Tasks need a due date and a countdown timer to appear here."
            no = Gtk.Label(label=msg)
            no.add_css_class("dash-empty")
            no.set_halign(Gtk.Align.CENTER)
            no.set_justify(Gtk.Justification.CENTER)
            no.set_wrap(True)
            self._cat_card.append(no)
        else:
            for row in prog_rows:
                self._cat_card.append(self._cat_goal_bar(row, d_str))

    def refresh_stats_only(self):
        self.refresh()

    def refresh(self):
        child=self.get_first_child()
        while child: nxt=child.get_next_sibling(); self.remove(child); child=nxt
        self._build()
