from src.israel_normalization.normalize_employment_type import normalize_employment_type
from src.israel_normalization.normalize_location import normalize_location, normalize_region
from src.israel_normalization.normalize_remote_type import normalize_remote_type
from src.israel_normalization.normalize_salary import normalize_salary
from src.israel_normalization.normalize_seniority import normalize_seniority, normalize_years_experience
from src.israel_normalization.normalize_title import normalize_title


def test_location_normalization_hebrew_and_english():
    assert normalize_location("ת״א") == "תל אביב"
    assert normalize_location("תל אביב") == "תל אביב"
    assert normalize_location("Tel Aviv") == "תל אביב"
    assert normalize_location("ת״א", output_language="en") == "Tel Aviv"
    assert normalize_region("Tel Aviv") == "center"


def test_remote_seniority_and_employment_normalization():
    assert normalize_remote_type("היברידי") == "hybrid"
    assert normalize_remote_type("Hybrid") == "hybrid"
    assert normalize_remote_type("עבודה מהבית") == "remote"
    assert normalize_seniority("ללא ניסיון") == "entry"
    assert normalize_seniority("Junior") == "junior"
    assert normalize_seniority("0-1") == "entry"
    assert normalize_employment_type("משרה מלאה") == "full_time"
    assert normalize_employment_type("part time") == "part_time"


def test_salary_years_and_title_normalization():
    assert normalize_salary("שכר 30-40 אלף") == (30000, 40000)
    assert normalize_years_experience("3 שנות ניסיון") == 3
    assert normalize_title("Software Engineer") == "מהנדס תוכנה"
    assert normalize_title("מהנדס תוכנה", output_language="en") == "Software Engineer"
