# Architecture

## Overview

`ebook2kindle` is a small desktop application with a Qt presentation layer and a Python conversion backend.

```text
main.py
  └─ gui.py                         Qt window, queue, workers, delivery flow
      ├─ userConfig/setting_ui.py  Qt settings dialog
      ├─ userConfig/setting.py     Persistent settings and password encryption
      ├─ userConfig/css_config.py  EPUB paragraph CSS
      ├─ util.py                   Conversion adapter and metadata extraction
      ├─ txt2epub.py               TXT parsing and EPUB generation
      └─ send2device.py            Validated SMTP transport and delivery results
```

## UI layer

- `gui.py` owns window state, drag-and-drop, queue rendering, inline styling controls, status updates, and background jobs.
- `ui_theme.py` contains the shared Qt stylesheet. Geometry such as corner radius and button sizing should be changed there rather than scattered through widgets.
- `userConfig/setting_ui.py` owns Kindle delivery and SMTP settings and validates/persists their values.

## Background work

Conversions and SMTP delivery run through `QRunnable` objects on `QThreadPool`. Workers communicate structured per-book results to the main thread through Qt signals. Widget access must remain on the main thread.

## Data and secrets

Settings are stored under `~/.ebook2kindle/settings.json` using atomic replacement and restrictive permissions. SMTP passwords are stored through the operating-system credential store. Existing Fernet-encrypted passwords are migrated to that store on first use.

## Packaging

`build.sh` uses PyInstaller to create:

- `dist/ebook2kindle.app`
- `dist/ebook2kindle.zip`

The intermediate `build/` directory and raw `dist/ebook2kindle/` folder are generated artifacts and are removed after packaging.
