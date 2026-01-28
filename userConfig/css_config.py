from __future__ import annotations


def _clamp(x: float, lo: float, hi: float) -> float:
    try:
        x = float(x)
    except Exception:
        x = lo
    return max(lo, min(hi, x))


def generate_css(
    text_indent_em: float = 1.0,
    paragraph_spacing_em: float = 0.3,
) -> str:
    """
    Based on your Kindle-friendly template, with user-tunable:
      - p { text-indent: Xem; }
      - p + p { margin-top: Yem; }
    """
    text_indent_em = _clamp(text_indent_em, 0.0, 6.0)
    paragraph_spacing_em = _clamp(paragraph_spacing_em, 0.0, 3.0)

    return f"""\
html, body {{ margin: 0; padding: 0; text-align: left; }}
p {{ margin: 0; padding: 0; text-indent: {text_indent_em:.2f}em; }}
p + p {{ margin-top: {paragraph_spacing_em:.2f}em; }}
div, section {{ margin: 0; padding: 0; }}
h1 {{ margin: 0.8em 0; font-weight: 600; text-indent: 0; }}
* {{ word-break: break-word; overflow-wrap: anywhere; }}
"""
