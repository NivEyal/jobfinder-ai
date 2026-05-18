from pathlib import Path

import pytest

from src.resume_schemas.israeli_resume import IsraeliResume, IsraeliResumeError


def test_israeli_resume_template_supports_hebrew_rtl_and_english_versions():
    resume = IsraeliResume.from_path(Path("data_folder/plain_text_resume.yaml"))

    assert resume.data["resume_metadata"]["default_language"] == "he"
    assert resume.version("he")["direction"] == "rtl"
    assert resume.version("en")["direction"] == "ltr"
    assert "כלכלן" in resume.render_text("he")
    assert "Entry-Level Economist" in resume.render_text("en")


def test_israeli_resume_requires_israeli_phone_but_not_linkedin():
    resume = IsraeliResume.from_path(Path("data_folder/plain_text_resume.yaml"))

    assert resume.data["personal_information"]["phone"].startswith("+972")
    assert "linkedin" in resume.data["personal_information"]
    assert resume.data["personal_information"]["linkedin"] == ""


def test_israeli_resume_rejects_non_israeli_phone():
    bad_yaml = Path("data_folder/plain_text_resume.yaml").read_text(encoding="utf-8").replace(
        "+972-50-123-4567", "+1-555-123-4567"
    )

    with pytest.raises(IsraeliResumeError):
        IsraeliResume.from_yaml(bad_yaml)
