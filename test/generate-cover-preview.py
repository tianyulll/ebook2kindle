#!/usr/bin/env python3
"""Generate a deterministic, offline EPUB cover preview from title metadata."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cover_generator import render_cover


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="The Last Light")
    parser.add_argument("--author", default="Avery Lin")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("cover-preview.png"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image = render_cover(args.title, args.author)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(args.output), "PNG"):
        raise OSError(f"Could not write cover preview to {args.output}")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
