#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  XFCE Productivity Todo — Arch Linux Installer
# ─────────────────────────────────────────────────────────────────────────────

set -e

APP_NAME="xfce-productivity-todo"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"
ICON_DIR="$HOME/.local/share/icons/hicolor/128x128/apps"
ICON_FILE="$ICON_DIR/$APP_NAME.png"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   XFCE Productivity Todo — Arch Installer   ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# ── Verify Arch ───────────────────────────────────────────────────────────────
if ! command -v pacman &>/dev/null; then
    echo "❌ pacman not found. This installer is for Arch Linux only."
    exit 1
fi

if   [ -f /etc/manjaro-release ];     then DISTRO="Manjaro"
elif [ -f /etc/endeavouros-release ]; then DISTRO="EndeavourOS"
elif grep -q "CachyOS" /etc/os-release 2>/dev/null; then DISTRO="CachyOS"
elif grep -q "Garuda"  /etc/os-release 2>/dev/null; then DISTRO="Garuda"
elif [ -f /etc/arch-release ];        then DISTRO="Arch Linux"
else                                       DISTRO="Arch-based"
fi
echo "  ✓ $DISTRO detected"

# ── Handle pacman lock ────────────────────────────────────────────────────────
LOCK="/var/lib/pacman/db.lck"

wait_for_pacman() {
    if [ -f "$LOCK" ]; then
        echo ""
        echo "  ⚠ pacman database is locked ($LOCK)"
        echo "    This means another package manager (pamac, octopi, yay) is running."
        echo ""
        echo "  Options:"
        echo "  [1] Wait and retry automatically (recommended)"
        echo "  [2] Remove lock and continue (only if NO package manager is running)"
        echo "  [3] Skip package install (if GTK4 is already installed)"
        echo "  [q] Quit"
        echo ""
        read -rp "  Your choice [1/2/3/q]: " choice

        case "$choice" in
            1)
                echo "  Waiting for pacman lock to clear..."
                for i in $(seq 1 30); do
                    sleep 2
                    if [ ! -f "$LOCK" ]; then
                        echo "  ✓ Lock cleared, continuing..."
                        return 0
                    fi
                    echo "    Still waiting... ($((i*2))s)"
                done
                echo "  ❌ Timed out waiting for lock. Try option 2 or 3."
                wait_for_pacman
                ;;
            2)
                echo "  Removing lock..."
                sudo rm -f "$LOCK"
                echo "  ✓ Lock removed"
                ;;
            3)
                echo "  Skipping package install..."
                SKIP_PACMAN=1
                ;;
            q|Q)
                echo "  Cancelled."
                exit 0
                ;;
            *)
                wait_for_pacman
                ;;
        esac
    fi
}

SKIP_PACMAN=0
wait_for_pacman

# ── Install dependencies ──────────────────────────────────────────────────────
if [ "$SKIP_PACMAN" -eq 0 ]; then
    echo "▶ Installing dependencies..."

    PKGS=(
        python
        python-gobject
        python-cairo
        gtk4
        glib2
        pango
        libnotify
        hicolor-icon-theme
        adwaita-icon-theme
        dconf
    )

    OPTIONAL=(
        libpulse
        pipewire-pulse
        xdotool
    )

    echo "  Installing core packages..."
    if ! sudo pacman -S --noconfirm --needed "${PKGS[@]}" 2>/tmp/pacman_err; then
        # Try one by one if bulk fails
        echo "  Bulk install failed, trying individually..."
        for pkg in "${PKGS[@]}"; do
            sudo pacman -S --noconfirm --needed "$pkg" 2>/dev/null \
                && echo "    ✓ $pkg" \
                || echo "    ⚠ skipped: $pkg"
        done
    else
        echo "  ✓ Core packages installed"
    fi

    echo "  Installing optional packages..."
    for pkg in "${OPTIONAL[@]}"; do
        sudo pacman -S --noconfirm --needed "$pkg" 2>/dev/null \
            && echo "    ✓ $pkg" \
            || echo "    - $pkg (not available, skipped)"
    done
fi

# ── Verify GTK4 import ────────────────────────────────────────────────────────
echo "▶ Verifying GTK4..."
if python3 -c "import gi; gi.require_version('Gtk','4.0'); from gi.repository import Gtk" 2>/dev/null; then
    echo "  ✓ GTK4 + PyGObject working"
else
    echo ""
    echo "  ❌ GTK4 import failed."
    echo ""
    echo "  Fix manually then re-run installer:"
    echo "    sudo rm -f /var/lib/pacman/db.lck   # if lock exists"
    echo "    sudo pacman -S python python-gobject gtk4"
    echo "    bash install.sh"
    echo ""
    exit 1
fi

# ── Install app files ─────────────────────────────────────────────────────────
echo "▶ Installing app files to $INSTALL_DIR..."
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/." "$INSTALL_DIR/"
find "$INSTALL_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$INSTALL_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
chmod +x "$INSTALL_DIR/run.sh" "$INSTALL_DIR/main.py"
echo "  ✓ Files installed + cache cleared"

# ── Icon ──────────────────────────────────────────────────────────────────────
mkdir -p "$ICON_DIR"
[ -f "$INSTALL_DIR/assets/icon.png" ] && \
    cp "$INSTALL_DIR/assets/icon.png" "$ICON_FILE" && \
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# ── Desktop entry ─────────────────────────────────────────────────────────────
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=XFCE Productivity Todo
GenericName=To-Do Manager
Comment=Task manager with timers, streaks, Pomodoro and test analysis
Exec=bash $INSTALL_DIR/run.sh
Icon=$APP_NAME
Terminal=false
StartupNotify=true
StartupWMClass=xfce-productivity-todo
Categories=Utility;Productivity;GTK;
Keywords=todo;task;productivity;pomodoro;timer;streak;analysis;
DESKTOP
chmod +x "$DESKTOP_FILE"
cp "$DESKTOP_FILE" "$HOME/Desktop/$APP_NAME.desktop" 2>/dev/null && \
    chmod +x "$HOME/Desktop/$APP_NAME.desktop" && \
    gio set "$HOME/Desktop/$APP_NAME.desktop" metadata::trusted true 2>/dev/null || true
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# ── 'todo' command ────────────────────────────────────────────────────────────
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/todo" << CMD
#!/usr/bin/env bash
exec bash $INSTALL_DIR/run.sh "\$@"
CMD
chmod +x "$HOME/.local/bin/todo"

# PATH setup — handle both bash and zsh
SHELL_RC="$HOME/.bashrc"
[ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo "  Added ~/.local/bin to PATH in $SHELL_RC"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║        ✅ Installation complete!             ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""
echo "  Launch:    todo"
echo "  Or search 'Todo' in your app launcher"
echo "  Uninstall: bash $INSTALL_DIR/uninstall.sh"
echo ""
