#!/usr/bin/env bash
set -e
APP_NAME="xfce-productivity-todo"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/128x128/apps"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║   XFCE Productivity Todo — Ubuntu Installer ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

echo "▶ Installing dependencies..."
sudo apt-get update -q
sudo apt-get install -y -q \
    python3 python3-gi python3-gi-cairo \
    gir1.2-gtk-4.0 libnotify-bin \
    python3-cairo adwaita-icon-theme \
    dconf-gsettings-backend 2>/dev/null || true

python3 -c "import gi; gi.require_version('Gtk','4.0'); from gi.repository import Gtk" 2>/dev/null \
    && echo "  ✓ GTK4 + PyGObject working" || { echo "  ❌ GTK4 failed. Try: sudo apt-get install python3-gi gir1.2-gtk-4.0"; exit 1; }

echo "▶ Installing app..."
rm -rf "$INSTALL_DIR"; mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/." "$INSTALL_DIR/"
find "$INSTALL_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$INSTALL_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
chmod +x "$INSTALL_DIR/run.sh" "$INSTALL_DIR/main.py"

mkdir -p "$ICON_DIR"
[ -f "$INSTALL_DIR/assets/icon.png" ] && cp "$INSTALL_DIR/assets/icon.png" "$ICON_DIR/$APP_NAME.png"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/$APP_NAME.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=XFCE Productivity Todo
Exec=bash $INSTALL_DIR/run.sh
Icon=$APP_NAME
Terminal=false
Categories=Utility;Productivity;GTK;
DESKTOP
chmod +x "$DESKTOP_DIR/$APP_NAME.desktop"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

mkdir -p "$HOME/.local/bin"
echo "#!/usr/bin/env bash
exec bash $INSTALL_DIR/run.sh \"\$@\"" > "$HOME/.local/bin/todo"
chmod +x "$HOME/.local/bin/todo"

grep -q 'local/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

echo ""
echo "  ╔════════════════════════════════╗"
echo "  ║   ✅ Installation complete!   ║"
echo "  ╚════════════════════════════════╝"
echo "  Run: todo   (or restart terminal first)"
echo ""
