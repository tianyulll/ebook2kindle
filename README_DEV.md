# ebook2kindle development handoff

This is the internal companion to `README.md`. It is written for maintainers and coding agents taking over the repository. Keep it current when architecture, build behavior, verification status, or known risks change.

## Current state

- The desktop UI is implemented with PySide6/Qt. Do not reintroduce Tkinter.
- TXT-to-EPUB conversion and SMTP delivery remain in the existing Python backend.
- Paragraph indent and spacing are edited directly on the main page and saved immediately.
- The Settings dialog is reserved for Kindle delivery and advanced SMTP configuration.
- The SMTP port is entered without stepper arrows; connection security uses two exclusive buttons. Switching modes updates standard ports (465/587) while preserving custom ports.
- SMTP delivery uses immutable validated configuration, secure TLS modes, one message per book, structured results, and one bounded transient retry.
- Conversion and delivery run through `QThreadPool`; UI widgets must only be touched on the main thread.
- The legacy debug-details panel and its text-widget adapter have been removed.
- Conversion preserves opening text before the first chapter. EPUBs are written to a temporary sibling and published with an atomic hard link; existing destinations get numbered alternatives such as `book (1).epub`. Filesystems without hard-link support fail safely rather than overwrite files.
- SMTP acceptance is recorded before connection cleanup, so QUIT errors cannot retry an already accepted message.

## Source map

```text
main.py
  └─ gui.py                         Main Qt window, queue, workers, delivery flow
      ├─ ui_theme.py                Shared Qt stylesheet and visual tokens
      ├─ userConfig/setting_ui.py  Delivery and SMTP settings dialog
      ├─ userConfig/setting.py     Persistent settings and password encryption
      ├─ userConfig/css_config.py  EPUB paragraph CSS generation
      ├─ util.py                   Conversion adapter and metadata extraction
      ├─ txt2epub.py               TXT parsing and EPUB generation
      └─ send2device.py            SMTP delivery
```

## UX invariants

- Keep controls and containers rounded; the visual system is centralized in `ui_theme.py`.
- The main action must remain the stable label **Convert books**. Explain send-after behavior with its tooltip and checkbox, not a changing button width or label.
- Styling sliders use tenths of an `em`: indent `0.0–6.0`, paragraph spacing `0.0–3.0`.
- Styling changes are persisted immediately and applied when a conversion begins.
- Settings must fit a 600 px-high macOS display without overlapping fields.
- Conversion errors belong in the Activity summary and per-file status, not a hidden debug console.

## Settings and secrets

Application state lives outside the repository under `~/.ebook2kindle/`:

- `settings.json` contains formatting and non-secret mail configuration.
- New SMTP passwords are stored in the operating-system credential store through `keyring`.
- Legacy `secret.key` and encrypted password values are migrated on first password use, then removed when migration completes.

Never print decrypted credentials. A blank password field in Settings preserves the credential-store entry.

## Local verification

The project Conda environment is `ebook` (Python 3.12). The verified environment includes EbookLib 0.20 and langdetect 1.0.9. Activate it with `conda activate ebook` before the commands below.

```bash
python -m pip install -r requirements.txt
python -B -m unittest discover -s test -p 'test*.py' -v
python test/run-convert.py --help
```

For UI changes, render or launch the app and inspect:

1. Empty and populated queues.
2. Main-page styling sliders and live value pills.
3. Disabled controls while a worker is running.
4. Both sections of the Settings dialog, including STARTTLS and implicit TLS selection.
5. Layout at the minimum supported window size.

## Build and release

```bash
PROJECT_PYTHON="$(command -v python)" ./build.sh
unzip -t dist/ebook2kindle.zip
```

The build produces `dist/ebook2kindle.app` and `dist/ebook2kindle.zip`, then removes the intermediate `build/` directory and raw onedir bundle. Generated artifacts are ignored by Git. The current Apple Silicon build requires macOS 13 or later; it has an ad-hoc signature, not a Developer ID signature or Apple notarization. See [Release procedure](docs/RELEASING.md) for versioned assets and checksums.

## Known gaps

- Live SMTP delivery has not been exercised with a dedicated non-production account; all current delivery verification uses mocked transports.
- The bundle still needs a clean-account macOS test.
- Provider-specific message-size limits are not yet configured.
- Windows packaging has not been established.

## Handoff checklist

Before ending a substantial change:

1. Update this file and `CHANGELOG.md` when behavior or architecture changes.
2. Run the unit tests and an import/compile check.
3. Visually inspect every UI surface affected by the change.
4. Rebuild both deliverables when runtime code changes.
5. Remove generated caches and confirm build intermediates are absent.
