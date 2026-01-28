from pathlib import Path
from txt2epub import txt_to_epub

# ---- EDIT THESE TWO PATHS ----
INPUT_TXT = "/Users/tylu/Downloads/《你也想养小恶龙吗》作者：凤箫声醉.txt"
OUTPUT_EPUB = "/Users/tylu/Downloads/tmp.epub"

# Optional metadata
TITLE = None          # None -> uses filename stem
AUTHOR = "Unknown"    # change if you want
LANGUAGE = None       # None -> your function defaults/detects

def main():
    inp = Path(INPUT_TXT)
    out = Path(OUTPUT_EPUB)
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Converting:\n  IN : {inp}\n  OUT: {out}")

    epub_path = txt_to_epub(
        input_txt=str(inp),
        output_epub=str(out),
        title=TITLE,
        author=AUTHOR,
        language=LANGUAGE,
    )

    print(f"[OK] Wrote EPUB: {epub_path}")

if __name__ == "__main__":
    main()
