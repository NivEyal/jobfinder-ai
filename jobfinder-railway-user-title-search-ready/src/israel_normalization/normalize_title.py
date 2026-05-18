from src.israel_normalization.text import choose_language, clean_text, normalize_key


TITLE_ALIASES = {
    "software engineer": ("מהנדס תוכנה", "Software Engineer"),
    "software developer": ("מפתח תוכנה", "Software Developer"),
    "מפתח תוכנה": ("מפתח תוכנה", "Software Developer"),
    "מהנדס תוכנה": ("מהנדס תוכנה", "Software Engineer"),
    "backend developer": ("מפתח Backend", "Backend Developer"),
    "backend engineer": ("מהנדס Backend", "Backend Engineer"),
    "מפתח backend": ("מפתח Backend", "Backend Developer"),
    "frontend developer": ("מפתח Frontend", "Frontend Developer"),
    "frontend engineer": ("מהנדס Frontend", "Frontend Engineer"),
    "react developer": ("מפתח React", "React Developer"),
    "full stack": ("מפתח Full Stack", "Full Stack Developer"),
    "full stack developer": ("מפתח Full Stack", "Full Stack Developer"),
    "fullstack developer": ("מפתח Full Stack", "Full Stack Developer"),
    "qa engineer": ("מהנדס QA", "QA Engineer"),
    "qa tester": ("בודק תוכנה", "QA Tester"),
    "בודק תוכנה": ("בודק תוכנה", "QA Tester"),
    "devops engineer": ("מהנדס DevOps", "DevOps Engineer"),
    "platform engineer": ("מהנדס Platform", "Platform Engineer"),
    "data analyst": ("אנליסט נתונים", "Data Analyst"),
    "data engineer": ("מהנדס נתונים", "Data Engineer"),
    "product manager": ("מנהל מוצר", "Product Manager"),
    "product owner": ("Product Owner", "Product Owner"),
    "מנהל מוצר": ("מנהל מוצר", "Product Manager"),
}


def normalize_title(value: str, output_language: str = "he") -> str:
    text = clean_text(value)
    key = normalize_key(text)
    for alias, (he_value, en_value) in TITLE_ALIASES.items():
        if alias in key:
            return choose_language(he_value, en_value, output_language)
    return text
