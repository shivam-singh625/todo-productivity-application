"""settings_window.py"""
import gi, os, subprocess
gi.require_version("Gtk","4.0")
gi.require_version("Gio","2.0")
from gi.repository import Gtk, Gio, GObject, GLib
from backend import config_manager

SOUND_OPTIONS = [
    ("System default","system-default"),
    ("Bell","/usr/share/sounds/freedesktop/stereo/bell.oga"),
    ("Message","/usr/share/sounds/freedesktop/stereo/message.oga"),
    ("Phone ring","/usr/share/sounds/freedesktop/stereo/phone-incoming-call.oga"),
    ("Complete","/usr/share/sounds/freedesktop/stereo/complete.oga"),
    ("Custom file…","custom"),
]

class SettingsWindow(Gtk.Dialog):
    __gsignals__ = {"settings-saved":(GObject.SignalFlags.RUN_FIRST,None,())}
    def __init__(self, parent, cfg):
        super().__init__(title="Settings",transient_for=parent,modal=True)
        self.set_default_size(520,440); self._cfg=dict(cfg)
        self.add_button("Cancel",Gtk.ResponseType.CANCEL)
        s=self.add_button("Save",Gtk.ResponseType.OK); s.add_css_class("suggested-action")
        self._build(); self.connect("response",self._on_response)

    def _build(self):
        box=self.get_content_area(); box.set_spacing(0)
        box.set_margin_start(20); box.set_margin_end(20); box.set_margin_top(14); box.set_margin_bottom(14)
        nb=Gtk.Notebook(); box.append(nb)
        nb.append_page(self._appearance_page(),Gtk.Label(label="Appearance"))
        nb.append_page(self._storage_page(),Gtk.Label(label="Storage"))
        nb.append_page(self._pomodoro_page(),Gtk.Label(label="Pomodoro"))
        nb.append_page(self._notif_page(),Gtk.Label(label="Notifications"))

    def _page(self):
        p=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        p.set_margin_start(16); p.set_margin_end(16); p.set_margin_top(16); p.set_margin_bottom(16); return p

    def _appearance_page(self):
        p=self._page()
        f=Gtk.Frame(label=" Theme "); b=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        b.set_margin_start(12); b.set_margin_end(12); b.set_margin_top(10); b.set_margin_bottom(10)
        cur=self._cfg.get("theme","dark")
        self._dark_btn=Gtk.CheckButton(label="🌙  Dark mode")
        self._light_btn=Gtk.CheckButton(label="☀️  Light mode"); self._light_btn.set_group(self._dark_btn)
        self._light_btn.set_active(cur=="light"); self._dark_btn.set_active(cur!="light")
        b.append(self._dark_btn); b.append(self._light_btn)
        n=Gtk.Label(label="⚠ Restart the app after changing theme"); n.add_css_class("dim-label"); n.set_halign(Gtk.Align.START); b.append(n)
        f.set_child(b); p.append(f); return p

    def _storage_page(self):
        p=self._page()
        p.append(Gtk.Label(label="Database file location:"))
        r=Gtk.Box(spacing=8); self._path=Gtk.Entry(); self._path.set_text(self._cfg.get("database_path","")); self._path.set_hexpand(True); r.append(self._path)
        bb=Gtk.Button(label="Browse…"); bb.connect("clicked",self._browse_db); r.append(bb); p.append(r)
        self._move=Gtk.CheckButton(label="Move existing database to new location"); self._move.set_active(True); p.append(self._move)
        return p

    def _browse_db(self,_):
        d=Gtk.FileChooserDialog(title="Choose database",transient_for=self,action=Gtk.FileChooserAction.SAVE)
        d.add_button("Cancel",Gtk.ResponseType.CANCEL); d.add_button("Select",Gtk.ResponseType.ACCEPT); d.set_current_name("tasks.db")
        def on_r(dd,r):
            if r==Gtk.ResponseType.ACCEPT:
                f=dd.get_file()
                if f: self._path.set_text(f.get_path())
            dd.destroy()
        d.connect("response",on_r); d.present()

    def _pomodoro_page(self):
        p=self._page(); g=Gtk.Grid(); g.set_row_spacing(10); g.set_column_spacing(12); p.append(g)
        g.attach(Gtk.Label(label="Focus duration (minutes):"),0,0,1,1)
        self._work=Gtk.SpinButton.new_with_range(1,90,1); self._work.set_value(self._cfg.get("pomodoro_work_mins",25)); g.attach(self._work,1,0,1,1)
        g.attach(Gtk.Label(label="Break duration (minutes):"),0,1,1,1)
        self._brk=Gtk.SpinButton.new_with_range(1,30,1); self._brk.set_value(self._cfg.get("pomodoro_break_mins",5)); g.attach(self._brk,1,1,1,1)
        return p

    def _notif_page(self):
        p=self._page()
        self._notif=Gtk.CheckButton(label="Enable desktop notifications"); self._notif.set_active(self._cfg.get("notifications",True)); p.append(self._notif)
        p.append(Gtk.Separator())
        p.append(Gtk.Label(label="Alert sound:"))
        sr=Gtk.Box(spacing=8); self._sound=Gtk.ComboBoxText()
        cur=self._cfg.get("alert_sound","system-default")
        custom_path=self._cfg.get("alert_sound_custom","")
        ai=0
        for i,(l,v) in enumerate(SOUND_OPTIONS):
            self._sound.append_text(l)
            if v==cur: ai=i
            elif v=="custom" and cur==custom_path and custom_path: ai=i
        self._sound.set_active(ai); self._sound.set_hexpand(True); self._sound.connect("changed",self._on_sc); sr.append(self._sound)
        tb=Gtk.Button(label="▶ Test"); tb.connect("clicked",self._test); sr.append(tb)
        self._stop_test=Gtk.Button(label="⏹"); self._stop_test.set_visible(False); self._stop_test.connect("clicked",self._stop_t); sr.append(self._stop_test)
        p.append(sr)
        self._cust_row=Gtk.Box(spacing=8); self._cust_e=Gtk.Entry(); self._cust_e.set_hexpand(True); self._cust_e.set_placeholder_text("Path to audio file…")
        cv=self._cfg.get("alert_sound_custom","")
        if cv: self._cust_e.set_text(cv)
        self._cust_row.append(self._cust_e); cb=Gtk.Button(label="Browse…"); cb.connect("clicked",self._browse_sound); self._cust_row.append(cb); p.append(self._cust_row)
        self._cust_row.set_visible(SOUND_OPTIONS[ai][1]=="custom"); self._test_proc=None; return p

    def _on_sc(self,c): self._cust_row.set_visible(SOUND_OPTIONS[c.get_active()][1]=="custom")
    def _get_sound(self):
        i=self._sound.get_active()
        if i<0: return "system-default"
        v=SOUND_OPTIONS[i][1]
        return self._cust_e.get_text().strip() or "system-default" if v=="custom" else v

    def _test(self,_):
        from ui.sound import play_sound_tracked, stop_sound; stop_sound()
        self._test_proc=play_sound_tracked(self._get_sound())
        if self._test_proc: self._stop_test.set_visible(True); GLib.timeout_add(100,self._poll)

    def _poll(self):
        if self._test_proc is None or self._test_proc.poll() is not None: self._stop_test.set_visible(False); self._test_proc=None; return False
        return True

    def _stop_t(self,_):
        if self._test_proc and self._test_proc.poll() is None:
            try: self._test_proc.terminate()
            except: pass
        self._test_proc=None; self._stop_test.set_visible(False)

    def _browse_sound(self,_):
        d=Gtk.FileChooserDialog(title="Choose sound",transient_for=self,action=Gtk.FileChooserAction.OPEN)
        d.add_button("Cancel",Gtk.ResponseType.CANCEL); d.add_button("Select",Gtk.ResponseType.ACCEPT)
        ff=Gtk.FileFilter(); ff.set_name("Audio"); [ff.add_pattern(p) for p in ["*.oga","*.ogg","*.wav","*.mp3"]]; d.add_filter(ff)
        def on_r(dd,r):
            if r==Gtk.ResponseType.ACCEPT:
                f=dd.get_file()
                if f: self._cust_e.set_text(f.get_path())
            dd.destroy()
        d.connect("response",on_r); d.present()

    def _on_response(self,_,rid):
        if rid!=Gtk.ResponseType.OK: return
        self._cfg["theme"]="light" if self._light_btn.get_active() else "dark"
        np=self._path.get_text().strip()
        if np and np!=self._cfg.get("database_path"):
            config_manager.change_database_path(self._cfg,np,move_existing=self._move.get_active())
        self._cfg["pomodoro_work_mins"]=int(self._work.get_value())
        self._cfg["pomodoro_break_mins"]=int(self._brk.get_value())
        self._cfg["notifications"]=self._notif.get_active()
        selected_sound = self._get_sound()
        self._cfg["alert_sound"] = selected_sound
        # Always keep custom path saved separately so it survives reopen
        idx = self._sound.get_active()
        if idx >= 0 and SOUND_OPTIONS[idx][1] == "custom":
            cpath = self._cust_e.get_text().strip()
            self._cfg["alert_sound_custom"] = cpath
            self._cfg["alert_sound"]        = cpath  # save actual path not "custom"
        else:
            # For preset sounds, clear custom path to avoid confusion
            pass
        config_manager.save(self._cfg); self.emit("settings-saved")

    def get_updated_config(self): return self._cfg
