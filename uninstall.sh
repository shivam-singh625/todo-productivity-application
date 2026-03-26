#!/usr/bin/env bash
# Uninstaller for Arch Linux

APP_NAME="xfce-productivity-todo"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"

echo ""
echo "  Uninstalling XFCE Productivity Todo..."

rm -rf "$INSTALL_DIR"
rm -f  "$HOME/.local/share/applications/$APP_NAME.desktop"
rm -f  "$HOME/.local/share/icons/hicolor/128x128/apps/$APP_NAME.png"
rm -f  "$HOME/.local/bin/todo"
rm -f  "$HOME/Desktop/$APP_NAME.desktop"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "  ✓ Uninstalled. Your data (~/.local/share/xfce-todo/tasks.db) was kept."
echo ""
