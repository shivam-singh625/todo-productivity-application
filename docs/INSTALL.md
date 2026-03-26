# 📦 Installation Guide

## Table of Contents
- [Arch Linux / Manjaro](#arch-linux--manjaro--endeavouros)
- [Ubuntu / Debian / Mint](#ubuntu--debian--linux-mint)
- [Fedora](#fedora)
- [Manual Install](#manual-install-any-distro)
- [Verify Installation](#verify-installation)
- [First Launch](#first-launch)
- [Uninstall](#uninstall)
- [Troubleshooting](#troubleshooting)

---

## Arch Linux / Manjaro / EndeavourOS

### Step 1 — Open Terminal

> **XFCE:** Right-click Desktop → Open Terminal  
> **Manjaro:** Press `Ctrl + Alt + T`  
> **KDE/Garuda:** Press `Ctrl + Alt + T`

---

### Step 2 — Install Git (if needed)

```bash
sudo pacman -S git
```

---

### Step 3 — Clone the repo

```bash
git clone https://github.com/yourusername/xfce-productivity-todo.git
cd xfce-productivity-todo
```

---

### Step 4 — Run installer

```bash
bash install.sh
```

**What you will see:**

```
  ╔══════════════════════════════════════════════╗
  ║   XFCE Productivity Todo — Arch Installer   ║
  ╚══════════════════════════════════════════════╝

  ✓ Arch Linux detected
▶ Installing dependencies...
  Installing core packages...
  ✓ Core packages installed
  ✓ Optional: xdotool
▶ Verifying GTK4...
  ✓ GTK4 + PyGObject working
▶ Installing app files to ~/.local/share/xfce-productivity-todo...
  ✓ Files installed + cache cleared
▶ Creating .desktop launcher...
  ✓ App menu entry created
▶ Creating 'todo' command...

  ╔══════════════════════════════════════════════╗
  ║        ✅ Installation complete!             ║
  ╚══════════════════════════════════════════════╝

  Launch:    todo
  Or search 'Todo' in your app launcher
```

---

### Step 5 — Launch

```bash
todo
```

Or open your app launcher and search **"Todo"**.

---

## Ubuntu / Debian / Linux Mint

```bash
# Install git
sudo apt-get install git

# Clone
git clone https://github.com/yourusername/xfce-productivity-todo.git
cd xfce-productivity-todo

# Install
bash install_ubuntu.sh

# Launch
todo
```

---

## Fedora

```bash
git clone https://github.com/yourusername/xfce-productivity-todo.git
cd xfce-productivity-todo
bash install_fedora.sh
todo
```

---

## Manual Install (Any Distro)

**1. Install dependencies:**

| Distro | Command |
|--------|---------|
| Arch | `sudo pacman -S python python-gobject python-cairo gtk4 libnotify adwaita-icon-theme dconf` |
| Ubuntu | `sudo apt-get install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 libnotify-bin` |
| Fedora | `sudo dnf install python3 python3-gobject gtk4 libnotify adwaita-icon-theme` |

**2. Run directly:**

```bash
git clone https://github.com/yourusername/xfce-productivity-todo.git
cd xfce-productivity-todo
bash run.sh
```

---

## Verify Installation

```bash
bash ~/.local/share/xfce-productivity-todo/debug.sh
```

Expected output (all OK):
```
=== Python imports ===
  OK   gi
  OK   GTK4
  OK   backend
  OK   task_manager
  OK   main_window
  OK   analysis
  OK   dashboard

=== DB test ===
  DB exists: True
  get_tasks: OK (0 tasks)
  DB tests complete

=== Launching app ===
  (app opens normally, no errors)
```

---

## First Launch

When you first open the app you will see the **Dashboard** with empty stats.

**Getting started in 60 seconds:**

1. Press `Ctrl+N` → add your first task
2. Set title, due date, category, priority → Save
3. Click **Today** in sidebar → see today's tasks
4. Click **Start** on the Pomodoro timer → begin focusing
5. Check off tasks as you complete them → watch your streak grow

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `Ctrl+N` | New task |
| `Ctrl+T` | Task templates |
| `1` | Dashboard |
| `2` | All Tasks |
| `3` | Calendar |

---

## Uninstall

```bash
bash ~/.local/share/xfce-productivity-todo/uninstall.sh
```

Removes the app but **keeps your data** at `~/.local/share/xfce-todo/tasks.db`.

To delete everything including data:
```bash
rm -rf ~/.local/share/xfce-todo/
rm -rf ~/.config/xfce-todo/
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `GTK4 import failed` | `sudo pacman -S python-gobject gtk4` |
| `pacman database locked` | `sudo rm -f /var/lib/pacman/db.lck` |
| App opens blank | Run `debug.sh` and check output |
| Timer goes behind windows | `sudo pacman -S xdotool` |
| No sound alerts | `sudo pacman -S pipewire-pulse` |
| No icons in app | `sudo pacman -S adwaita-icon-theme` |

**Full diagnostic:**
```bash
bash ~/.local/share/xfce-productivity-todo/debug.sh
```
