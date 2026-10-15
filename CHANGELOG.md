# Changelog

## v1.0.0 — 2026-10-15

- Fixed the standard macOS Command-W shortcut so it closes the app window.
- Added automatic offline minimalist covers using detected English or Chinese title and author metadata.
- Standardized every generated cover on a light background with dark text for grayscale Kindle visibility.
- Added a delivery-sidebar link to Amazon's official Send to Kindle website.
- Added semantic version metadata and a stable macOS bundle identifier to release builds.
- Removed the retired splash, generated iconset, stale local release copies, previews, and cache files.

## v1.0-beta.2 — 2026-09-23

- Added a Chinese usage guide and documented installation, release assets, and beta limitations.
- Removed generated builds, bytecode, and Finder metadata from source tracking; app downloads belong in GitHub Releases.
- Removed SMTP port stepper arrows and replaced the connection-security dropdown with two visible, mutually exclusive buttons.
- Preserve existing EPUBs using numbered output names and atomic publication of completed files.
- Preserve introductions and other opening text before the first chapter heading.
- Prevent duplicate SMTP submissions when connection cleanup fails after message acceptance.
- Added regression coverage for output collisions, interrupted writes, opening text, and SMTP cleanup failures.
- Replaced the Tkinter interface with a PySide6/Qt presentation layer.
- Added genuinely rounded cards, buttons, fields, tabs, badges, and progress indicators.
- Added a file queue with per-file conversion and delivery status.
- Moved conversion and email delivery onto background workers.
- Reworked Settings into a rounded segmented layout.
- Replaced styling spinboxes with sliders and live `em` values.
- Moved the styling sliders onto the main page for immediate adjustment.
- Removed the top title banner and relocated Settings to the delivery sidebar.
- Removed the legacy debug-details panel and logging adapter.
- Stabilized the primary action label to avoid layout shifts.
- Added reproducible build dependencies and separate public and development handoff READMEs.
- Added validated delivery configuration and structured per-book SMTP results.
- Added secure STARTTLS and implicit-TLS modes; plaintext SMTP authentication is no longer supported.
- Added typed delivery errors, message IDs, attachment preflight, and bounded transient retries.
- Moved SMTP passwords to the operating-system credential store with automatic legacy migration.
- Added mocked SMTP and delivery-worker coverage.

## Previous application

- TXT-to-EPUB conversion with encoding and language detection.
- Chinese and English chapter detection.
- Configurable paragraph indentation and spacing.
- SMTP-based Send to Kindle support with encrypted local password storage.
