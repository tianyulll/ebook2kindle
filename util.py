import tkinter as tk
import os
from pathlib import Path
import re
from txt2epub import txt_to_epub

# automatically close the message box in 5 seconds
def auto_close_messagebox(parent, title, message, duration=5000):
    msg_box = tk.Toplevel(parent)
    msg_box.title(title)
    tk.Label(msg_box, text=message).pack(padx=20, pady=20)
    msg_box.after(duration, msg_box.destroy)

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

def convert_format(file_path: str, output_display: tk.Text) -> str:
    input_path = Path(file_path)
    input_dir = input_path.parent

    # output: same folder, same stem, .epub
    output_path = input_dir / f"{input_path.stem}.epub"

    auto_title, auto_author = extract_metadata(input_path)

    # send-to-kindle accepts epub. No need conversion
    if input_path.suffix.lower() == ".epub":
        return str(input_path.resolve())

    try:
        res = txt_to_epub(
            input_txt=input_path,
            output_epub=output_path,
            title=auto_title,
            author=auto_author,
        )
        output_display.insert(tk.END, res)
        output_display.insert(tk.END, f"\n✅ Wrote: {res.output_epub}\n\n")
    except Exception as e:
        output_display.insert(tk.END, f"\n❌ Error converting {file_path}:\n{e}\n\n")

    output_display.yview_moveto(1.0)
    return str(output_path.resolve())
