#!/usr/bin/env bash
# run.sh — launcher with Arch/Wayland/X11 compatibility

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Force X11 backend (GTK4 Wayland has issues with some WMs including XFCE)
# Remove or set to 'wayland' if you are on a pure Wayland compositor
export GDK_BACKEND="${GDK_BACKEND:-x11}"

# Suppress non-critical GLib warnings
export G_MESSAGES_DEBUG="${G_MESSAGES_DEBUG:-none}"

exec python3 "$SCRIPT_DIR/main.py" "$@"
