import re
from typing import Optional, Tuple

from src.israel_normalization.text import clean_text


def normalize_salary(value: str) -> Tuple[Optional[int], Optional[int]]:
    text = clean_text(value).lower()
    match = re.search(r"(\d{1,3})\s*[-–]\s*(\d{1,3})\s*(?:k|אלף|₪|שח|ils)?", text, flags=re.IGNORECASE)
    if not match:
        single = re.search(r"(?:שכר|salary).*?(\d{2,3})\s*(?:k|אלף|₪|שח|ils)?", text, flags=re.IGNORECASE)
        if not single:
            return None, None
        salary = _to_monthly_salary(int(single.group(1)))
        return salary, salary
    return _to_monthly_salary(int(match.group(1))), _to_monthly_salary(int(match.group(2)))


def _to_monthly_salary(value: int) -> int:
    if value < 1000:
        return value * 1000
    return value
