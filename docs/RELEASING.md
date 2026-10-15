# Release procedure

Release binaries are GitHub attachments. Do not commit `dist/`, `build/`, Python bytecode, or `.DS_Store` files.

## Choose the version

Use semantic versions in `VERSION`, changelog headings, tags, release notes, and asset names. Stable versions use `MAJOR.MINOR.PATCH` and tags such as `v1.0.0`; pre-release suffixes are reserved for builds that should be marked as GitHub pre-releases.

## Verify and package

Use the `ebook` Conda environment (Python 3.12) on the target architecture:

```bash
conda activate ebook
python -m pip install -r requirements.txt
python -B -m unittest discover -s test -p 'test*.py' -v
PROJECT_PYTHON="$(command -v python)" ./build.sh
unzip -tq dist/ebook2kindle.zip
codesign --verify --deep --strict dist/ebook2kindle.app
```

Confirm that `CFBundleShortVersionString` and `CFBundleVersion` match `VERSION`. Inspect the main window and both Settings pages, including their minimum sizes. Convert English and Chinese TXT samples and inspect the embedded light-background covers on a grayscale display. Verify that the Amazon Send to Kindle link opens the official HTTPS page. Confirm the output-collision and SMTP retry regression tests pass. Record outstanding live-mail or clean-machine checks in the release notes.

The v1.0.0 artifact is arm64 and the bundled Qt requires macOS 13+. The app is ad-hoc signed by PyInstaller, without Developer ID signing or notarization. Do not describe it as universal, Intel-compatible, or notarized.

```bash
cp dist/ebook2kindle.zip dist/ebook2kindle-v1.0.0-macos-arm64.zip
cd dist
shasum -a 256 ebook2kindle-v1.0.0-macos-arm64.zip > SHA256SUMS.txt
shasum -a 256 -c SHA256SUMS.txt
```

## Publish

1. Update `VERSION`, the changelog, English README, Chinese guide, and version-specific release notes.
2. Review and commit the intended source and documentation changes. Push the source commit; never force-push to publish a release.
3. Tag that exact commit `v1.0.0`, then push the tag.
4. Create a normal GitHub release targeting that tag, with the text from `docs/releases/v1.0.0.md`. Do not mark a stable release as a pre-release.
5. Attach `ebook2kindle-v1.0.0-macos-arm64.zip` and `SHA256SUMS.txt` before publishing. Preserve older releases and their assets.
6. Verify that the published release shows both attachments and the correct tag/commit.

With an authenticated GitHub CLI, steps 4–5 can be performed from the repository root:

```bash
gh release create v1.0.0 \
  dist/ebook2kindle-v1.0.0-macos-arm64.zip dist/SHA256SUMS.txt \
  --verify-tag --latest \
  --title "ebook2kindle v1.0.0" \
  --notes-file docs/releases/v1.0.0.md
```

Retain the signing, architecture, and verification caveats in stable release notes until those constraints change.
