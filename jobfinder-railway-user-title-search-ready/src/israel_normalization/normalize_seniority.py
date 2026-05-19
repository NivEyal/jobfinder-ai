import re
from typing import Optional

from src.israel_normalization.text import normalize_key


def normalize_seniority(value: str) -> str:
    text = normalize_key(value)
    if any(term in text for term in ["ללא ניסיון", "ללא נסיון", "0 1", "0-1", "entry", "graduate", "בוגר"]):
        return "entry"
    if any(term in text for term in ["junior", "מתחיל", "גוניור"]):
        return "junior"
    if any(term in text for term in ["senior", "sr", "בכיר", "מנוסה"]):
        return "senior"
    if any(term in text for term in ["team lead", "lead", "principal", "ראש צוות"]):
        return "lead"
    if any(term in text for term in ["manager", "director", "מנהל", "ניהולי"]):
        return "management"
    if any(term in text for term in ["intern", "internship", "סטודנט", "התמחות"]):
        return "internship"
    return ""


_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)")
_YEARS_EN_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs|year)", re.IGNORECASE)
_YEARS_HE_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s*(?:שנות|שנים|שנה)", re.IGNORECASE)


def normalize_years_experience(value: str) -> Optional[float]:
    text = normalize_key(value)
    if any(term in text for term in ["ללא ניסיון", "ללא נסיון", "no experience"]):
        return 0
    m = _RANGE_RE.search(text)
    if m:
        return float(m.group(1))
    m = _YEARS_EN_RE.search(text)
    if m:
        return float(m.group(1))
    m = _YEARS_HE_RE.search(text)
    if m:
        return float(m.group(1))
    return None
