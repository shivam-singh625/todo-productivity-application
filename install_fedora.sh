#!/usr/bin/env bash
set -e
APP_NAME="xfce-productivity-todo"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "▶ Installing dependencies (Fedora)..."
sudo dnf install -y python3 python3-gobject python3-cairo \
    gtk4 libnotify adwaita-icon-theme 2>/dev/null || true

python3 -c "import gi; gi.require_version('Gtk','4.0'); from gi.repository import Gtk" 2>/dev/null \
    && echo "  ✓ GTK4 working" || { echo "❌ GTK4 failed"; exit 1; }

rm -rf "$INSTALL_DIR"; mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/." "$INSTALL_DIR/"
find "$INSTALL_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
chmod +x "$INSTALL_DIR/run.sh"

mkdir -p "$HOME/.local/bin"
echo "#!/usr/bin/env bash
exec bash $INSTALL_DIR/run.sh \"\$@\"" > "$HOME/.local/bin/todo"
chmod +x "$HOME/.local/bin/todo"
grep -q 'local/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"

echo "✅ Done! Run: todo"
