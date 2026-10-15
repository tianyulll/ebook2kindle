#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_PYTHON="${PROJECT_PYTHON:-$(command -v python3)}"
APP_VERSION="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION")"

if [[ ! -x "$PROJECT_PYTHON" ]]; then
  echo "Python was not found. Set PROJECT_PYTHON to a Python executable." >&2
  exit 1
fi

if [[ ! "$APP_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "VERSION must contain a semantic version such as 1.0.0." >&2
  exit 1
fi

cd "$SCRIPT_DIR"

"$PROJECT_PYTHON" -m PyInstaller \
  --onedir \
  --name ebook2kindle \
  --noconfirm \
  --windowed \
  --icon img/ebook.icns \
  --osx-bundle-identifier io.github.tianyulll.ebook2kindle \
  --clean \
  main.py

/usr/libexec/PlistBuddy \
  -c "Set :CFBundleShortVersionString $APP_VERSION" \
  dist/ebook2kindle.app/Contents/Info.plist
/usr/libexec/PlistBuddy \
  -c "Add :CFBundleVersion string $APP_VERSION" \
  dist/ebook2kindle.app/Contents/Info.plist
codesign --force --deep --sign - dist/ebook2kindle.app

ditto -c -k --sequesterRsrc --keepParent \
  dist/ebook2kindle.app \
  dist/ebook2kindle.zip

rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/dist/ebook2kindle"

echo "Built ebook2kindle $APP_VERSION in dist/ebook2kindle.app and dist/ebook2kindle.zip"
