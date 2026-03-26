"""calendar_view.py"""
import gi, calendar as cal_mod
gi.require_version("Gtk","4.0")
from gi.repository import Gtk, GObject
from datetime import date

class CalendarView(Gtk.Box):
    __gsignals__ = {"date-selected":(GObject.SignalFlags.RUN_FIRST,None,(str,))}
    def __init__(self, tm):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._tm=tm; self._today=date.today()
        self._current=date(self._today.year,self._today.month,1)
        self._selected=self._today; self._task_dates=set()
        self._build(); self.refresh_task_dates()

    def _build(self):
        self.add_css_class("calendar-view")
        self.set_margin_start(8); self.set_margin_end(8)
        self.set_margin_top(8); self.set_margin_bottom(8)
        hdr=Gtk.Box(spacing=4); hdr.set_halign(Gtk.Align.CENTER)
        pb=Gtk.Button(icon_name="go-previous-symbolic"); pb.add_css_class("flat"); pb.connect("clicked",self._prev); hdr.append(pb)
        self._hdr_lbl=Gtk.Label(); self._hdr_lbl.add_css_class("calendar-header-label"); hdr.append(self._hdr_lbl)
        nb=Gtk.Button(icon_name="go-next-symbolic"); nb.add_css_class("flat"); nb.connect("clicked",self._next); hdr.append(nb)
        self.append(hdr)
        dow=Gtk.Box(spacing=2); dow.set_homogeneous(True)
        for d in ["Mo","Tu","We","Th","Fr","Sa","Su"]: l=Gtk.Label(label=d); l.add_css_class("dow-label"); dow.append(l)
        self.append(dow)
        self._grid=Gtk.Grid(); self._grid.set_row_spacing(2); self._grid.set_column_spacing(2)
        self._grid.set_row_homogeneous(True); self._grid.set_column_homogeneous(True)
        self.append(self._grid)
        self._btns=[]
        for r in range(6):
            for c in range(7):
                b=Gtk.Button(); b.add_css_class("flat"); b.add_css_class("day-btn")
                b.connect("clicked",self._on_day); self._grid.attach(b,c,r,1,1); self._btns.append(b)
        self._render()

    def _prev(self,_):
        y,m=self._current.year,self._current.month; m-=1
        if m==0: m,y=12,y-1
        self._current=date(y,m,1); self._render()

    def _next(self,_):
        y,m=self._current.year,self._current.month; m+=1
        if m==13: m,y=1,y+1
        self._current=date(y,m,1); self._render()

    def _render(self):
        self._hdr_lbl.set_text(self._current.strftime("%B %Y"))
        c=cal_mod.monthcalendar(self._current.year,self._current.month)
        while len(c)<6: c.append([0]*7)
        idx=0
        for week in c[:6]:
            for dn in week:
                b=self._btns[idx]
                for cl in ["day-today","day-selected","day-has-task","day-empty"]: b.remove_css_class(cl)
                if dn==0: b.set_label(""); b.set_sensitive(False); b.add_css_class("day-empty")
                else:
                    b.set_sensitive(True); b.set_label(str(dn))
                    d=date(self._current.year,self._current.month,dn)
                    if d==self._today: b.add_css_class("day-today")
                    if d==self._selected: b.add_css_class("day-selected")
                    if d.isoformat() in self._task_dates: b.add_css_class("day-has-task")
                idx+=1

    def _on_day(self, b):
        l=b.get_label()
        if not l: return
        d=date(self._current.year,self._current.month,int(l))
        self._selected=d; self._render(); self.emit("date-selected",d.isoformat())

    def refresh_task_dates(self):
        tasks=self._tm.get_tasks(completed=False)
        self._task_dates={t["due_date"] for t in tasks if t["due_date"]}
        self._render()
