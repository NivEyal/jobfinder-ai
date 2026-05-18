from src.israel_normalization.text import choose_language, clean_text, normalize_key


LOCATION_ALIASES = {
    "תא": ("תל אביב", "Tel Aviv", "center"),
    "ת א": ("תל אביב", "Tel Aviv", "center"),
    "תל אביב": ("תל אביב", "Tel Aviv", "center"),
    "tel aviv": ("תל אביב", "Tel Aviv", "center"),
    "tlv": ("תל אביב", "Tel Aviv", "center"),
    "רמת גן": ("רמת גן", "Ramat Gan", "center"),
    "ramat gan": ("רמת גן", "Ramat Gan", "center"),
    "גבעתיים": ("גבעתיים", "Givatayim", "center"),
    "givatayim": ("גבעתיים", "Givatayim", "center"),
    "פתח תקווה": ("פתח תקווה", "Petah Tikva", "center"),
    "petah tikva": ("פתח תקווה", "Petah Tikva", "center"),
    "הרצליה": ("הרצליה", "Herzliya", "sharon"),
    "herzliya": ("הרצליה", "Herzliya", "sharon"),
    "רעננה": ("רעננה", "Raanana", "sharon"),
    "raanana": ("רעננה", "Raanana", "sharon"),
    "כפר סבא": ("כפר סבא", "Kfar Saba", "sharon"),
    "kfar saba": ("כפר סבא", "Kfar Saba", "sharon"),
    "נתניה": ("נתניה", "Netanya", "sharon"),
    "netanya": ("נתניה", "Netanya", "sharon"),
    "חיפה": ("חיפה", "Haifa", "north"),
    "haifa": ("חיפה", "Haifa", "north"),
    "ירושלים": ("ירושלים", "Jerusalem", "jerusalem"),
    "jerusalem": ("ירושלים", "Jerusalem", "jerusalem"),
    "באר שבע": ("באר שבע", "Beer Sheva", "south"),
    "beer sheva": ("באר שבע", "Beer Sheva", "south"),
    "ashdod": ("אשדוד", "Ashdod", "south"),
    "אשדוד": ("אשדוד", "Ashdod", "south"),
    "remote": ("מרחוק", "Remote", "remote"),
    "worldwide": ("עולמי", "Worldwide", "worldwide"),
    "israel": ("ישראל", "Israel", "israel"),
}


REGION_LABELS = {
    "center": ("מרכז", "Center"),
    "sharon": ("שרון", "Sharon"),
    "north": ("צפון", "North"),
    "south": ("דרום", "South"),
    "jerusalem": ("ירושלים", "Jerusalem"),
    "remote": ("מרחוק", "Remote"),
    "worldwide": ("עולמי", "Worldwide"),
    "israel": ("ישראל", "Israel"),
}


def normalize_location(value: str, output_language: str = "he") -> str:
    text = clean_text(value)
    key = normalize_key(text)
    for alias, (he_value, en_value, _region) in LOCATION_ALIASES.items():
        if alias in key:
            return choose_language(he_value, en_value, output_language)
    return text


def normalize_region(location: str, output_language: str = "en") -> str:
    key = normalize_key(location)
    for alias, (_he_value, _en_value, region) in LOCATION_ALIASES.items():
        if alias in key:
            he_region, en_region = REGION_LABELS[region]
            return choose_language(he_region, en_region.lower(), output_language)
    return ""
