#!/usr/bin/env bash
# Executado pelo proprietário na própria máquina: cria repositório e Release públicos.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI não encontrado. No Ubuntu: sudo apt install gh"
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "Git não encontrado. No Ubuntu: sudo apt install git"
  exit 1
fi
if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb não encontrado. Instale dpkg-dev na sua distribuição."
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "Faça login em sua conta GitHub no terminal com: gh auth login"
  exit 1
fi
ACCOUNT="$(gh api user --jq '.login')"
if [ "$ACCOUNT" != "pizzatto" ]; then
  echo "Conta conectada é $ACCOUNT, mas o destino é pizzatto."
  echo "Confirme qual conta deve publicar e faça login corretamente antes de continuar."
  exit 1
fi
./packaging/build_deb.sh
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -b main
fi
git add .
if ! git diff --cached --quiet; then
  git commit -m "feat: lançar Instala Fácil 2.0, interface renovada e documentação"
fi
if gh repo view "pizzatto/instala-facil" >/dev/null 2>&1; then
  echo "O repositório pizzatto/instala-facil já existe. Não vou sobrescrever o conteúdo."
  echo "Faça uma revisão antes de publicar ou executar git push manualmente."
  exit 1
fi
gh repo create "pizzatto/instala-facil" --public \
  --description "Instalador gráfico open source para arquivos DEB, RPM, AppImage e Flatpak no Linux." \
  --source . --remote origin --push
if gh release view "v2.0.0" >/dev/null 2>&1; then
  echo "A release v2.0.0 já existe."
else
  gh release create "v2.0.0" "dist/instala-facil_2.0.0_all.deb" \
    --title "Instala Fácil 2.0.0" --notes-file RELEASE_NOTES.md
fi
echo "Publicado em: https://github.com/pizzatto/instala-facil"
echo "Downloads: https://github.com/pizzatto/instala-facil/releases"
