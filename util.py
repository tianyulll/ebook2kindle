from pathlib import Path
import re
from txt2epub import txt_to_epub

def extract_metadata(input_path: Path) -> tuple[str, str]:
    """
    Extract (title, author) using common Chinese ebook conventions.

    Rules (in order):

    Title:
      1) 《书名》 from filename
      2) 《书名》 from text (first ~2000 chars)

    Author:
      1) 作者: XXX from text (first ~2000 chars)
    """
    # Read only a small prefix of the file
    head = ""
    try:
        with input_path.open("r", encoding="utf-8", errors="ignore") as f:
            head = f.read(2000)
    except Exception:
        head = ""

    # -------- title --------
    title = None

    # Try filename first
    m = re.search(r"《([^》]+)》", input_path.stem)
    if m:
        title = m.group(1).strip()

    # Then try text
    if not title:
        m = re.search(r"《([^》]+)》", head)
        if m:
            title = m.group(1).strip()

    # Fallback
    if not title:
        title = input_path.stem

    # -------- author --------
    author = "Unknown"
    m = re.search(r"作者\s*[:：]\s*([^\n\r]+)", head)
    if m:
        author = m.group(1).strip()

    return title, author

def convert_format(file_path: str, css: str) -> str:
    input_path = Path(file_path)
    input_dir = input_path.parent

    # output: same folder, same stem, .epub
    output_path = input_dir / f"{input_path.stem}.epub"

    auto_title, auto_author = extract_metadata(input_path)

    # send-to-kindle accepts epub. No need conversion
    if input_path.suffix.lower() == ".epub":
        return str(input_path.resolve())

    result = txt_to_epub(
        input_txt=input_path,
        output_epub=output_path,
        css=css,
        title=auto_title,
        author=auto_author,
    )
    return str(result.output_epub.resolve())
