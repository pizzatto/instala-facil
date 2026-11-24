#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="2.0.0"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PKG="$WORK/package"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/lib/instala-facil" \
  "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/scalable/apps" \
  "$PKG/usr/share/doc/instala-facil"
install -m 644 "$ROOT/src/main.py" "$PKG/usr/lib/instala-facil/main.py"
install -m 644 "$ROOT/src/core.py" "$PKG/usr/lib/instala-facil/core.py"
install -m 644 "$ROOT/packaging/instala-facil.desktop" "$PKG/usr/share/applications/instala-facil.desktop"
install -m 644 "$ROOT/assets/instala-facil.svg" "$PKG/usr/share/icons/hicolor/scalable/apps/instala-facil.svg"
install -m 644 "$ROOT/README.md" "$PKG/usr/share/doc/instala-facil/README.md"
install -m 644 "$ROOT/LICENSE" "$PKG/usr/share/doc/instala-facil/copyright"
cat > "$PKG/usr/bin/instala-facil" <<'SCRIPT'
#!/bin/sh
exec /usr/bin/python3 /usr/lib/instala-facil/main.py "$@"
SCRIPT
chmod 755 "$PKG/usr/bin/instala-facil"
cat > "$PKG/DEBIAN/control" <<CONTROL
Package: instala-facil
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: Comunidade Instala Fácil
Depends: python3 (>= 3.10), python3-tk
Recommends: pkexec
Suggests: flatpak
Description: Instalador gráfico de programas para Linux
 Instale arquivos DEB, RPM, AppImage e Flatpak baixados em sites oficiais
 com interface gráfica, fila de instalação e relatórios de erros.
CONTROL
mkdir -p "$ROOT/dist"
dpkg-deb --root-owner-group --build "$PKG" "$ROOT/dist/instala-facil_${VERSION}_all.deb"
printf 'Pacote gerado: %s\n' "$ROOT/dist/instala-facil_${VERSION}_all.deb"
