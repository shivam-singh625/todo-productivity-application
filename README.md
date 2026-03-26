<div align="center">

# ✅ XFCE Productivity Todo
**A powerful, lightweight productivity app for Linux**  
*Built with Python + GTK4 — zero Electron, zero bloat*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![GTK](https://img.shields.io/badge/GTK-4.0-green)](https://gtk.org)
[![Platform](https://img.shields.io/badge/Platform-Linux-orange)](https://linux.org)

</div>

---

## 📸 Screenshots

| Dashboard | Task List | Test Analysis |
|:---------:|:---------:|:-------------:|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Tasks](docs/screenshots/tasks.png) | ![Analysis](docs/screenshots/analysis.png) |

| Calendar | Floating Timer | Pomodoro |
|:--------:|:--------------:|:--------:|
| ![Calendar](docs/screenshots/calendar.png) | ![Timer](docs/screenshots/timer.png) | ![Pomodoro](docs/screenshots/pomodoro.png) |

---

## ✨ Features

### 📋 Task Management
- **Smart task list** with grouping by date (Overdue / Today / Tomorrow / Upcoming)
- **Bulk actions** — select multiple tasks → complete, delete, duplicate, change category
- **Task duplication** — clone any task in one click
- **⭐ Star / favourite** important tasks
- **Quick-add bar** — type and press Enter to add instantly
- **Auto-suggestions** while typing task titles
- **Smart defaults** — new tasks auto-fill today's date + last used category/priority

### ⏱ Timers & Focus
- **Countdown timer** per task — e.g. set 3 hours for a study session
- **Stopwatch** mode — track how long you spend on any task
- **Seek bar** — scrub forward/backward like a music track
- **Floating timer** — stays on top of all windows while you work
- **Pause saves position** — resume exactly where you left off after restart

### 🍅 Pomodoro
- Built-in Pomodoro timer in the sidebar
- Configurable work/break intervals
- Session counter
- Integrated with floating timer

### 📊 Dashboard
- **Streaks** — daily and weekly streak tracking
- **Activity charts** — 30-day focus time graph + weekly bar chart
- **Category progress** — goal vs actual time per category
- **Stats** — overdue, upcoming, focus today, tasks done

### 📅 Calendar View
- Visual calendar with task dots on dates
- Click any date to see tasks for that day
- Mark tasks complete directly from calendar

### 📈 Test Analysis (for students)
- Add test results with subject, score, accuracy, marks scheme
- **+4/−1 scoring** (NEET standard) or custom marks
- Subject-wise performance bars (Biology / Physics / Chemistry + custom)
- **Weak area detection** — highlights subjects below 60% accuracy
- **Accuracy trend** chart
- Test history with full details

### 🎯 Task Templates
- Save any task setup as a reusable template
- One-click apply — opens pre-filled task dialog
- Perfect for recurring study sessions

### 🔔 Smart Notifications
- Due-date reminders at 60 min / 30 min / 15 min / 5 min before
- System desktop notifications via `libnotify`

---

## 🚀 Quick Install

### Arch Linux / Manjaro / EndeavourOS

```bash
# 1. Clone the repo
git clone https://github.com/shivam-singh625/xfce-productivity-todo.git
cd xfce-productivity-todo

# 2. Run the installer
bash install.sh

# 3. Launch
todo
```

### Ubuntu / Debian / Linux Mint

```bash
git clone https://github.com/shivam-singh625/xfce-productivity-todo.git
cd xfce-productivity-todo
bash install_ubuntu.sh
todo
```

### Fedora / RHEL

```bash
git clone https://github.com/shivam-singh625/xfce-productivity-todo.git
cd xfce-productivity-todo
bash install_fedora.sh
todo
```
### Windows(currently not avilable)
```bash
<div align="center">
Windows version coming soon
</div>
```
> 📖 **Full installation guide with screenshots:** [INSTALL.md](docs/INSTALL.md)

---

## 📦 Requirements

| Dependency | Arch pkg | Ubuntu pkg | Purpose |
|---|---|---|---|
| Python 3.10+ | `python` | `python3` | Runtime |
| PyGObject | `python-gobject` | `python3-gi` | GTK bindings |
| GTK4 | `gtk4` | `gir1.2-gtk-4.0` | UI toolkit |
| Cairo | `python-cairo` | `python3-gi-cairo` | Rendering |
| libnotify | `libnotify` | `libnotify-bin` | Notifications |
| dconf | `dconf` | `dconf-gsettings-backend` | GTK settings |

**Optional:**
| `libpulse` / `pipewire-pulse` | Alert sounds |
| `xdotool` | Floating timer always-on-top |

---

## 🗂 Project Structure

```
xfce-productivity-todo/
├── main.py                    # App entry point
├── run.sh                     # Launch script
├── install.sh                 # Arch Linux installer
├── install_ubuntu.sh          # Ubuntu/Debian installer  
├── install_fedora.sh          # Fedora installer
├── uninstall.sh               # Uninstaller
├── debug.sh                   # Debug/diagnostic tool
├── PKGBUILD                   # AUR package build file
│
├── backend/
│   ├── database.py            # SQLite schema + queries
│   ├── task_manager.py        # Business logic
│   ├── config_manager.py      # Settings persistence
│   └── analysis_db.py         # Test analysis queries
│
├── ui/
│   ├── main_window.py         # Main window + sidebar
│   ├── dashboard.py           # Dashboard with charts
│   ├── task_widget.py         # Individual task row
│   ├── task_dialog.py         # Add/edit task dialog
│   ├── task_timer.py          # Per-task timer widget
│   ├── floating_timer.py      # Always-on-top timer window
│   ├── pomodoro_timer.py      # Pomodoro sidebar widget
│   ├── calendar_view.py       # Calendar page
│   ├── analysis_panel.py      # Test analysis dashboard
│   ├── templates_dialog.py    # Task templates manager
│   ├── settings_window.py     # Settings dialog
│   ├── category_dialog.py     # Category manager
│   ├── notifier.py            # Due-date notification service
│   ├── sound.py               # Alert sound player
│   └── theme.py               # CSS theme builder
│
├── assets/
│   └── icon.png               # App icon
│
└── docs/
    ├── INSTALL.md             # Full installation guide
    └── screenshots/           # App screenshots
```

---

## 💾 Data Storage

All data is stored locally — no cloud, no accounts, no tracking.

| File | Location |
|---|---|
| Tasks database | `~/.local/share/xfce-todo/tasks.db` |
| Settings | `~/.config/xfce-todo/config.json` |

---

## 🔧 Troubleshooting

```bash
# Run the built-in diagnostic tool
bash ~/.local/share/xfce-productivity-todo/debug.sh
```

Common fixes:

| Problem | Fix |
|---|---|
| App won't start | `sudo pacman -S python-gobject gtk4` |
| No icons | `sudo pacman -S adwaita-icon-theme` |
| No sound | `sudo pacman -S pipewire-pulse` |
| Timer won't stay on top | `sudo pacman -S xdotool` |
| pacman locked | `sudo rm -f /var/lib/pacman/db.lck` |

---

## 🗑 Uninstall

```bash
bash ~/.local/share/xfce-productivity-todo/uninstall.sh
```

Your data (`~/.local/share/xfce-todo/tasks.db`) is **never deleted** automatically.

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">
Made with ❤️ for Linux users | 
Windows version coming soon
</div>
