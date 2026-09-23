from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from txt2epub import txt_to_epub
from userConfig.css_config import generate_css


def parse_args():
    parser = argparse.ArgumentParser(description="Convert one TXT file without launching the GUI.")
    parser.add_argument("input", type=Path, help="Input TXT file")
    parser.add_argument("output", nargs="?", type=Path, help="Output EPUB path")
    parser.add_argument("--title", help="Optional book title")
    parser.add_argument("--author", default="Unknown", help="Optional author name")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_path = (
        args.output.expanduser().resolve()
        if args.output
        else input_path.with_suffix(".epub")
    )

    result = txt_to_epub(
        input_txt=input_path,
        output_epub=output_path,
        css=generate_css(),
        title=args.title or input_path.stem,
        author=args.author,
    )
    print(f"Wrote {result.output_epub}")


if __name__ == "__main__":
    main()
