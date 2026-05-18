from src.israel_normalization.text import normalize_key


def normalize_remote_type(value: str) -> str:
    text = normalize_key(value)
    if any(term in text for term in ["hybrid", "היברידי", "היברידית", "יומיים מהבית", "יום מהבית"]):
        return "hybrid"
    if any(term in text for term in ["remote", "work from home", "wfh", "עבודה מהבית", "מרחוק", "מהבית"]):
        return "remote"
    if any(term in text for term in ["onsite", "on site", "office", "במשרד", "משרדי", "מהמשרד"]):
        return "onsite"
    return ""
