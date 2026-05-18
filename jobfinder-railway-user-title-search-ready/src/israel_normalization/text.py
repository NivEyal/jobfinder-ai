import re
from typing import Optional


def clean_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("״", '"').replace("׳", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_key(value: Optional[str]) -> str:
    text = clean_text(value).lower()
    text = text.replace('"', "").replace("'", "")
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def choose_language(he_value: str, en_value: str, output_language: str = "he") -> str:
    if output_language == "en":
        return en_value
    return he_value
