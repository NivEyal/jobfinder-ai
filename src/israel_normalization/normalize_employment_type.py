from src.israel_normalization.text import normalize_key


def normalize_employment_type(value: str) -> str:
    text = normalize_key(value)
    if any(term in text for term in ["full time", "fulltime", "משרה מלאה"]):
        return "full_time"
    if any(term in text for term in ["part time", "parttime", "משרה חלקית", "חצי משרה"]):
        return "part_time"
    if any(term in text for term in ["contract", "freelance", "פרילנס", "קבלן", "חוזה"]):
        return "contract"
    if any(term in text for term in ["temporary", "temp", "זמני", "משרה זמנית"]):
        return "temporary"
    if any(term in text for term in ["internship", "intern", "התמחות", "סטאז"]):
        return "internship"
    return ""
