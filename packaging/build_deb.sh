#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="2.1.0"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PKG="$WORK/package"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/lib/instala-facil" \
  "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/scalable/apps" \
  "$PKG/usr/share/doc/instala-facil" "$PKG/usr/share/mime/packages"
install -m 644 "$ROOT/src/main.py" "$PKG/usr/lib/instala-facil/main.py"
install -m 644 "$ROOT/src/core.py" "$PKG/usr/lib/instala-facil/core.py"
install -m 644 "$ROOT/packaging/instala-facil.desktop" "$PKG/usr/share/applications/instala-facil.desktop"
install -m 644 "$ROOT/packaging/instala-facil-mime.xml" "$PKG/usr/share/mime/packages/instala-facil.xml"
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
Recommends: pkexec, desktop-file-utils, shared-mime-info
Suggests: flatpak
Description: Instalador gráfico de programas para Linux
 Instale arquivos DEB, RPM, AppImage e Flatpak baixados em sites oficiais
 com interface gráfica, fila de instalação e relatórios de erros.
CONTROL
# Atualiza associações sem alterar o aplicativo padrão do usuário.
for script in postinst postrm; do
  cat > "$PKG/DEBIAN/$script" <<'SCRIPT'
#!/bin/sh
set -e
if command -v update-mime-database >/dev/null 2>&1; then
  update-mime-database /usr/share/mime || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi
exit 0
SCRIPT
  chmod 755 "$PKG/DEBIAN/$script"
done
mkdir -p "$ROOT/dist"
dpkg-deb --root-owner-group --build "$PKG" "$ROOT/dist/instala-facil_${VERSION}_all.deb"
printf 'Pacote gerado: %s\n' "$ROOT/dist/instala-facil_${VERSION}_all.deb"
