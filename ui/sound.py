"""sound.py — Sound playback with process tracking."""
import subprocess, os

_sound_process = None

def stop_sound():
    global _sound_process
    if _sound_process and _sound_process.poll() is None:
        try: _sound_process.terminate(); _sound_process.wait(timeout=1)
        except:
            try: _sound_process.kill()
            except: pass
    _sound_process = None

def play_sound_tracked(sound_path: str):
    global _sound_process
    stop_sound()
    if not sound_path or sound_path == "system-default":
        for c in ["/usr/share/sounds/freedesktop/stereo/complete.oga",
                  "/usr/share/sounds/freedesktop/stereo/bell.oga"]:
            if os.path.exists(c): sound_path = c; break
        else:
            try: return subprocess.Popen(["canberra-gtk-play","--id=complete"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            except: return None
    if sound_path and os.path.exists(sound_path):
        for cmd in [["paplay",sound_path],["aplay",sound_path]]:
            try:
                proc = subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                _sound_process = proc
                return proc
            except FileNotFoundError: continue
    return None
