#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_PYTHON="${PROJECT_PYTHON:-$(command -v python3)}"

if [[ ! -x "$PROJECT_PYTHON" ]]; then
  echo "Python was not found. Set PROJECT_PYTHON to a Python executable." >&2
  exit 1
fi

cd "$SCRIPT_DIR"

"$PROJECT_PYTHON" -m PyInstaller \
  --onedir \
  --name ebook2kindle \
  --noconfirm \
  --windowed \
  --icon img/ebook.icns \
  --clean \
  main.py

ditto -c -k --sequesterRsrc --keepParent \
  dist/ebook2kindle.app \
  dist/ebook2kindle.zip

rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/dist/ebook2kindle"

echo "Built dist/ebook2kindle.app and dist/ebook2kindle.zip"
