import re

from src.israel_normalization.text import clean_text


LEGAL_SUFFIXES = [
    "בע\"מ",
    "בעמ",
    "Ltd.",
    "Ltd",
    "Limited",
    "Inc.",
    "Inc",
    "LLC",
]


def normalize_company(value: str, output_language: str = "he") -> str:
    text = clean_text(value)
    for suffix in LEGAL_SUFFIXES:
        text = re.sub(rf"\s*{re.escape(suffix)}$", "", text, flags=re.IGNORECASE)
    return text.strip()
