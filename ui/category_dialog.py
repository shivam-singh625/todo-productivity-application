"""category_dialog.py"""
import gi, math
gi.require_version("Gtk","4.0")
from gi.repository import Gtk, GObject

class CategoryDialog(Gtk.Dialog):
    __gsignals__ = {"categories-changed":(GObject.SignalFlags.RUN_FIRST,None,())}
    def __init__(self, parent, tm):
        super().__init__(title="Manage Categories",transient_for=parent,modal=True)
        self._tm=tm; self.set_default_size(360,420)
        self.add_button("Close",Gtk.ResponseType.CLOSE); self.connect("response",lambda d,_:d.destroy())
        self._build()

    def _swatch(self, hex_color, size=14):
        h=hex_color.lstrip("#"); r,g,b=int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255
        da=Gtk.DrawingArea(); da.set_size_request(size,size); da.set_valign(Gtk.Align.CENTER)
        def draw(w,cr,ww,hh): cr.arc(ww/2,hh/2,min(ww,hh)/2-0.5,0,2*math.pi); cr.set_source_rgb(r,g,b); cr.fill()
        da.set_draw_func(draw); return da

    def _build(self):
        box=self.get_content_area(); box.set_spacing(8)
        box.set_margin_start(16); box.set_margin_end(16); box.set_margin_top(12); box.set_margin_bottom(12)
        ar=Gtk.Box(spacing=8); self._ne=Gtk.Entry(); self._ne.set_placeholder_text("New category name…"); self._ne.set_hexpand(True); self._ne.connect("activate",self._on_add); ar.append(self._ne)
        ab=Gtk.Button(label="Add"); ab.add_css_class("suggested-action"); ab.connect("clicked",self._on_add); ar.append(ab)
        box.append(ar); box.append(Gtk.Separator())
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True); sc.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        self._lb=Gtk.ListBox(); self._lb.set_selection_mode(Gtk.SelectionMode.NONE); self._lb.add_css_class("boxed-list"); sc.set_child(self._lb); box.append(sc)
        self._reload()

    def _reload(self):
        while self._lb.get_first_child(): self._lb.remove(self._lb.get_first_child())
        for c in self._tm.get_categories():
            row=Gtk.ListBoxRow(); row.set_activatable(False)
            hb=Gtk.Box(spacing=8); hb.set_margin_start(8); hb.set_margin_end(8); hb.set_margin_top(6); hb.set_margin_bottom(6)
            hb.append(self._swatch(c["color"])); lbl=Gtk.Label(label=c["name"]); lbl.set_halign(Gtk.Align.START); lbl.set_hexpand(True); hb.append(lbl)
            rb=Gtk.Button(icon_name="document-edit-symbolic"); rb.add_css_class("flat"); rb.connect("clicked",self._on_rename,c["id"],c["name"]); hb.append(rb)
            db=Gtk.Button(icon_name="edit-delete-symbolic"); db.add_css_class("flat"); db.connect("clicked",self._on_delete,c["id"]); hb.append(db)
            row.set_child(hb); self._lb.append(row)

    def _on_add(self,_):
        n=self._ne.get_text().strip()
        if n: self._tm.add_category(n); self._ne.set_text(""); self._reload(); self.emit("categories-changed")

    def _on_rename(self,_,cid,cn):
        d=Gtk.Dialog(title="Rename",transient_for=self,modal=True); d.add_button("Cancel",Gtk.ResponseType.CANCEL); d.add_button("Rename",Gtk.ResponseType.OK); d.set_default_response(Gtk.ResponseType.OK)
        e=Gtk.Entry(); e.set_text(cn); e.set_activates_default(True); e.set_margin_start(16); e.set_margin_end(16); e.set_margin_top(12); e.set_margin_bottom(8); d.get_content_area().append(e)
        def on_r(dd,r):
            if r==Gtk.ResponseType.OK:
                n=e.get_text().strip()
                if n: self._tm.rename_category(cid,n); self._reload(); self.emit("categories-changed")
            dd.destroy()
        d.connect("response",on_r); d.present()

    def _on_delete(self,_,cid):
        c=Gtk.MessageDialog(transient_for=self,modal=True,message_type=Gtk.MessageType.WARNING,buttons=Gtk.ButtonsType.YES_NO,text="Delete this category?",secondary_text="Tasks will become uncategorised.")
        def on_r(d,r): d.destroy(); (self._tm.delete_category(cid),self._reload(),self.emit("categories-changed")) if r==Gtk.ResponseType.YES else None
        c.connect("response",on_r); c.present()
