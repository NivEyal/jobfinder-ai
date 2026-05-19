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

_SUFFIX_RE = re.compile(
    r"\s*(?:" + "|".join(re.escape(s) for s in LEGAL_SUFFIXES) + r")$",
    flags=re.IGNORECASE,
)


def normalize_company(value: str, output_language: str = "he") -> str:
    text = clean_text(value)
    text = _SUFFIX_RE.sub("", text)
    return text.strip()
