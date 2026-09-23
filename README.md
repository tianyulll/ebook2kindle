# ebook2kindle

Convert plain-text books to Kindle-ready EPUB files, then optionally send them to a Kindle address.

[中文使用指南](docs/USAGE.zh-CN.md) · [Downloads / 下载](https://github.com/tianyulll/ebook2kindle/releases)

## Features

- Converts TXT files to EPUB and accepts existing EPUBs for delivery.
- Detects source encoding, language, and Chinese or English chapter headings.
- Supports batch drag-and-drop, queue management, and per-file progress.
- Provides adjustable paragraph indentation and spacing.
- Sends completed books through secure SMTP with per-book delivery status.
- Uses a native rounded Qt interface with background processing.

适配中文小说的 TXT 转 EPUB 工具，支持章节提取、段落排版和可选的 Kindle 邮件发送。

## Install

Download the macOS ZIP from [GitHub Releases](https://github.com/tianyulll/ebook2kindle/releases), extract it, and move `ebook2kindle.app` to Applications. The current binary is for **Apple Silicon (arm64), macOS 13 or later**. Intel Macs and Windows do not have a packaged build.

This beta is not Developer ID signed or notarized. If macOS blocks it, follow [Apple's instructions for opening an app from an unknown developer](https://support.apple.com/guide/mac-help/mh40616/mac) only after verifying the download's source. Release assets include a SHA-256 checksum.

To run or build from source with Python 3.12:

```bash
conda create -n ebook python=3.12 pip
conda activate ebook
python -m pip install -r requirements.txt
python main.py
# Build a macOS app:
PROJECT_PYTHON="$(command -v python)" ./build.sh
```

The build creates `dist/ebook2kindle.app` and `dist/ebook2kindle.zip`.
Generated builds are distributed as release attachments, not committed to Git.

## Use

Drop TXT or EPUB files into the app, review the queue, then choose **Convert books**. Enable **Send after conversion** when you also want to deliver successful conversions.

Converted EPUBs are saved beside the source TXT. Existing files are preserved; when a name is already taken, the app uses a numbered name such as `book (1).epub`.

For Kindle delivery:

1. Add the sender address to Amazon's approved personal document email list.
2. Enter the Kindle destination address in Settings.
3. For Gmail, use an app-specific password rather than the account password. Passwords are stored in the operating-system credential store.

Existing EPUBs also go through **Convert books** to prepare the queue; their contents are not converted or restyled. Then use **Send to Kindle**, or enable **Send after conversion** beforehand. A **Submitted** status means the mail provider accepted the message, not that it has appeared on the Kindle. Manually sending again submits all prepared books again.

Conversion happens locally. Sending uploads the EPUB through your configured mail provider to the destination address. Save TXT files in a writable folder on a filesystem with hard-link support (such as APFS); conversion fails safely on unsupported filesystems. Live SMTP and installation on a clean Mac have not yet been verified for this beta.

## Project documentation

- [Development and agent handoff notes](README_DEV.md)
- [Changelog](CHANGELOG.md)
- [中文使用指南](docs/USAGE.zh-CN.md)
- [Release procedure](docs/RELEASING.md)
