# Project tracking

Last updated: 2026-09-23

## Current release status

| Area | Status | Notes |
| --- | --- | --- |
| TXT → EPUB conversion | Complete | Encoding, language, chapter splitting, and CSS retained |
| Batch queue | Complete | Add, remove, clear, progress, and per-file states |
| Kindle delivery | Complete | Validated per-book submission with STARTTLS/implicit TLS and structured results |
| Credential storage | Complete | OS credential store with legacy Fernet migration |
| Background processing | Complete | Qt thread-pool workers keep the UI responsive |
| Rounded Qt design | Complete | Main window and Settings visually verified |
| Styling controls | Complete | Main-page indent and spacing sliders with live `em` values |
| Legacy debug UI removal | Complete | Activity and per-file states provide user-facing feedback |
| macOS packaging | Complete | `.app` and ZIP produced by `build.sh` |
| Conversion data safety | Complete | Numbered outputs, atomic publication, opening text preserved |
| SMTP cleanup safety | Complete | Accepted submissions are not retried after QUIT errors |
| Release documentation | Complete | English installation notes, Chinese usage guide, and beta release notes |

## Verification checklist

- [x] Python modules compile.
- [x] Offscreen render of the empty queue.
- [x] Offscreen render of populated queue and statuses.
- [x] Offscreen render of all Settings sections.
- [x] Main-page styling values persist and feed conversion CSS.
- [x] Mocked STARTTLS and implicit-TLS submission.
- [x] Authentication, recipient, validation, retry, and partial-batch delivery cases.
- [x] End-to-end background TXT conversion.
- [x] PyInstaller app launch.
- [x] ZIP integrity check.
- [x] All 20 automated tests pass in the `ebook` Conda environment.
- [ ] Live SMTP delivery against a non-production test account.
- [ ] Test on a clean macOS account without the development environment.

## Next candidates

1. Add a lightweight conversion-history view.
2. Add explicit output-folder selection.
3. Add provider-specific attachment-size guidance and limits.
4. Add signing and notarization for public macOS distribution.
5. Consider Windows packaging after the macOS release is stable.

## Release procedure

See [RELEASING.md](RELEASING.md) for tag creation, versioned assets, checksums, and GitHub publication. Current release notes: [v1.0-beta.2](releases/v1.0-beta.2.md).

```bash
python -m pip install -r requirements.txt
PROJECT_PYTHON="$(command -v python)" ./build.sh
unzip -t dist/ebook2kindle.zip
```

After building, launch `dist/ebook2kindle.app` and verify drag-and-drop, conversion, Settings, and the disabled/enabled states of all actions.
