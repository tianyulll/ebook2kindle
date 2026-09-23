# Release procedure

Release binaries are GitHub attachments. Do not commit `dist/`, `build/`, Python bytecode, or `.DS_Store` files.

## Verify and package

Use the `ebook` Conda environment (Python 3.12) on the target architecture:

```bash
conda activate ebook
python -m pip install -r requirements.txt
python -B -m unittest discover -s test -p 'test*.py' -v
PROJECT_PYTHON="$(command -v python)" ./build.sh
unzip -tq dist/ebook2kindle.zip
```

Inspect the main window and both Settings pages, including their minimum sizes. Confirm the output-collision and SMTP retry regression tests pass. Record outstanding live-mail or clean-machine checks in the release notes.

For `v1.0-beta.2`, the existing artifact is arm64 and the bundled Qt requires macOS 13+. The app is ad-hoc signed by PyInstaller, without Developer ID signing or notarization. Do not describe it as universal, Intel-compatible, or notarized.

```bash
cp dist/ebook2kindle.zip dist/ebook2kindle-v1.0-beta.2-macos-arm64.zip
cd dist
shasum -a 256 ebook2kindle-v1.0-beta.2-macos-arm64.zip > SHA256SUMS.txt
shasum -a 256 -c SHA256SUMS.txt
```

## Publish

1. Update the changelog, English README, Chinese guide, and version-specific release notes.
2. Review and commit the intended source and documentation changes. Push the source commit; never force-push to publish a release.
3. Tag that exact commit `v1.0-beta.2`, then push the tag.
4. Create a GitHub **pre-release** targeting that tag, with the text from `docs/releases/v1.0-beta.2.md`.
5. Attach `ebook2kindle-v1.0-beta.2-macos-arm64.zip` and `SHA256SUMS.txt` before publishing. Preserve older releases and their assets.
6. Verify that the published release shows both attachments and the correct tag/commit.

With an authenticated GitHub CLI, steps 4–5 can be performed from the repository root:

```bash
gh release create v1.0-beta.2 \
  dist/ebook2kindle-v1.0-beta.2-macos-arm64.zip dist/SHA256SUMS.txt \
  --verify-tag --prerelease \
  --title "v1.0-beta.2 — Qt desktop update" \
  --notes-file docs/releases/v1.0-beta.2.md
```

Until Apple signing and clean-machine testing are established, keep the release marked as a pre-release and retain the installation caveats in its notes.
