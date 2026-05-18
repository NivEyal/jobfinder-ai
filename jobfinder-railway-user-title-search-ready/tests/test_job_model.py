from datetime import datetime, timezone

from src.israel_sources.models import IsraeliJob
from src.job import Job


def test_job_model_supports_israeli_market_fields():
    job = Job(
        source="drushim",
        source_job_id="123",
        canonical_url="https://example.com/job/123",
        company="Example Ltd.",
        title="Senior Software Engineer",
        location="Tel Aviv",
        region="center",
        remote_type="hybrid",
        employment_type="full_time",
        seniority="senior",
        years_experience=5,
        salary_min=30000,
        salary_max=40000,
        language="mixed",
        apply_email="jobs@example.com",
        apply_url="https://example.com/apply/123",
        first_seen_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
        last_seen_at=datetime(2026, 5, 18, tzinfo=timezone.utc),
        status="new",
        description="Hybrid full time role in Tel Aviv.",
    )

    data = job.to_dict()

    assert data["source"] == "drushim"
    assert data["source_job_id"] == "123"
    assert data["canonical_url"] == "https://example.com/job/123"
    assert data["company"] == "Example"
    assert data["title"] == "מהנדס תוכנה"
    assert data["location"] == "תל אביב"
    assert data["region"] == "center"
    assert data["remote_type"] == "hybrid"
    assert data["employment_type"] == "full_time"
    assert data["seniority"] == "senior"
    assert data["years_experience"] == 5
    assert data["salary_min"] == 30000
    assert data["salary_max"] == 40000
    assert data["language"] == "mixed"
    assert data["fingerprint"]
    assert data["first_seen_at"].startswith("2026-05-18")
    assert job.id == job.fingerprint
    assert job.role == job.title
    assert job.link == job.canonical_url


def test_job_can_be_created_from_israeli_job():
    israeli_job = IsraeliJob(
        source="gotfriends",
        source_job_id="153797",
        title="Full Stack AI Engineer",
        company="GotFriends",
        location='ת"א והמרכז',
        description="משרה היברידית, משרה מלאה, 3 שנות ניסיון, שכר 30-40 אלף",
        apply_url="https://www.gotfriends.co.il/jobslobby/software/full-stack-developer/153797/",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    )

    job = israeli_job.to_job()

    assert job.source == "gotfriends"
    assert job.source_job_id == "153797"
    assert job.title == "מפתח Full Stack"
    assert job.company == "GotFriends"
    assert job.region == "center"
    assert job.remote_type == "hybrid"
    assert job.employment_type == "full_time"
    assert job.years_experience == 3
    assert job.salary_min == 30000
    assert job.salary_max == 40000
    assert job.language == "mixed"
    assert job.apply_url == israeli_job.apply_url
    assert job.fingerprint


def test_job_can_be_normalized_to_english():
    israeli_job = IsraeliJob(
        source="drushim",
        source_job_id="1",
        title="מהנדס תוכנה",
        company="חברה לדוגמה בעמ",
        location="ת״א",
        description="היברידי, משרה מלאה, ללא ניסיון",
        apply_url="https://example.com",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    )

    job = israeli_job.to_job(normalized_output_language="en")

    assert job.title == "Software Engineer"
    assert job.location == "Tel Aviv"
    assert job.remote_type == "hybrid"
    assert job.employment_type == "full_time"
    assert job.seniority == "entry"
    assert job.years_experience == 0
