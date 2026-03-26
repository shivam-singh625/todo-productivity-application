# Maintainer: XFCE Productivity Todo
# Arch Linux PKGBUILD — installs as a proper pacman package
# Build with: makepkg -si

pkgname=xfce-productivity-todo
pkgver=42.0
pkgrel=1
pkgdesc="GTK4 productivity app with tasks, timers, streaks, Pomodoro and test analysis"
arch=('any')
url="https://github.com/xfce-todo/app"
license=('MIT')
depends=(
    'python'
    'python-gobject'
    'python-cairo'
    'gtk4'
    'gobject-introspection'
    'libnotify'
    'adwaita-icon-theme'
)
optdepends=(
    'libpulse: alert sounds'
    'xdotool: floating timer always-on-top'
    'xdg-utils: desktop integration'
)
source=("${pkgname}::local://.")
sha256sums=('SKIP')

package() {
    INSTALL_DIR="$pkgdir/usr/share/$pkgname"
    BIN_DIR="$pkgdir/usr/bin"
    DESKTOP_DIR="$pkgdir/usr/share/applications"
    ICON_DIR="$pkgdir/usr/share/icons/hicolor/128x128/apps"

    # App files
    install -dm755 "$INSTALL_DIR"
    cp -r "$srcdir/$pkgname/." "$INSTALL_DIR/"

    # Remove build artifacts
    find "$INSTALL_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$INSTALL_DIR" -name "*.pyc" -delete 2>/dev/null || true
    rm -f "$INSTALL_DIR/PKGBUILD" "$INSTALL_DIR/install.sh"

    # Launcher script
    install -dm755 "$BIN_DIR"
    cat > "$BIN_DIR/todo" << CMD
#!/usr/bin/env bash
cd /usr/share/$pkgname && exec python3 main.py "\$@"
CMD
    chmod 755 "$BIN_DIR/todo"

    # .desktop file
    install -dm755 "$DESKTOP_DIR"
    cat > "$DESKTOP_DIR/$pkgname.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=XFCE Productivity Todo
GenericName=To-Do Manager
Comment=Task manager with timers, streaks, test analysis and Pomodoro
Exec=todo
Icon=$pkgname
Terminal=false
StartupNotify=true
StartupWMClass=xfce-productivity-todo
Categories=Utility;Productivity;GTK;
Keywords=todo;task;productivity;pomodoro;timer;study;
DESKTOP

    # Icon
    install -dm755 "$ICON_DIR"
    [ -f "$INSTALL_DIR/assets/icon.png" ] && \
        install -m644 "$INSTALL_DIR/assets/icon.png" "$ICON_DIR/$pkgname.png"
}
