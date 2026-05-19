from pathlib import Path

from src.apply import ApplicationGuard, ApplicationRequest, AutoApplyEngine, EmailApplyEngine, ExternalApplyEngine, FormApplyEngine
from src.israel_sources.models import IsraeliJob
from src.matching.models import MatchResult


def config(tmp_path):
    return {
        "apply": {
            "enabled": True,
            "dry_run": True,
            "minimum_match_score": 65,
            "require_resume_file": True,
            "ledger_path": str(tmp_path / "ledger.json"),
            "allowed_methods": ["email", "form", "external"],
            "email": {
                "provider": "resend",
                "api_key_env": "RESEND_API_KEY",
                "api_url_env": "RESEND_API_URL",
                "from_email_env": "RESEND_FROM_EMAIL",
                "reply_to_env": "APPLICATION_REPLY_TO_EMAIL",
            },
            "form": {
                "timeout_seconds": 20,
                "submit_selector": "button[type='submit'], input[type='submit']",
            },
            "external": {"complex_indicators": ["captcha", "login"]},
        },
        "storage": {
            "enabled": True,
            "backend": "sqlite",
            "sqlite_path": str(tmp_path / "storage.sqlite3"),
            "jsonl_dir": str(tmp_path / "jsonl"),
            "save_source_snapshots": True,
        },
    }


def make_job(apply_email="jobs@example.com", apply_url="https://example.com/apply"):
    return IsraeliJob(
        source="drushim",
        source_job_id="123",
        title="Backend Developer",
        company="Example",
        location="Tel Aviv",
        description="Python backend role",
        apply_url=apply_url,
        apply_email=apply_email,
        apply_method="email" if apply_email else "external_url",
        posted_at=None,
    ).to_job(normalized_output_language="en")


def make_request(tmp_path, job=None, score=90):
    resume = tmp_path / "resume.yaml"
    resume.write_text("Python backend APIs", encoding="utf-8")
    job = job or make_job()
    match = MatchResult(
        job_fingerprint=job.fingerprint,
        source=job.source,
        source_job_id=job.source_job_id,
        score=score,
        verdict="strong_match",
        confidence=0.9,
    )
    return ApplicationRequest(
        job=job,
        resume_path=resume,
        candidate_name="Candidate",
        candidate_email="candidate@example.com",
        candidate_phone="+972500000000",
        message="Please see my resume.",
        match_result=match,
    )


def test_auto_apply_routes_email_and_records_dry_run(tmp_path):
    result = AutoApplyEngine(config(tmp_path)).apply(make_request(tmp_path))

    assert result.status == "dry_run_ready"
    assert result.method == "email"
    assert result.dry_run is True
    assert Path(config(tmp_path)["apply"]["ledger_path"]).exists()
    assert Path(config(tmp_path)["storage"]["sqlite_path"]).exists()


def test_guard_blocks_low_match_score(tmp_path):
    result = AutoApplyEngine(config(tmp_path)).apply(make_request(tmp_path, score=40))

    assert result.status == "blocked"
    assert "below minimum" in result.detail


def test_guard_blocks_duplicate_applications(tmp_path):
    engine = AutoApplyEngine(config(tmp_path))
    request = make_request(tmp_path)

    first = engine.apply(request)
    second = engine.apply(request)

    assert first.status == "dry_run_ready"
    assert second.status == "blocked"
    assert "already recorded" in second.detail


def test_email_apply_builds_resend_payload_with_attachment(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEND_FROM_EMAIL", "JobFinder <apply@jobfinder.fit>")
    request = make_request(tmp_path)

    payload = EmailApplyEngine(config(tmp_path)).build_payload(request)

    assert payload["from"] == "JobFinder <apply@jobfinder.fit>"
    assert payload["to"] == ["jobs@example.com"]
    assert payload["reply_to"] == "candidate@example.com"
    assert payload["attachments"][0]["filename"] == "resume.yaml"
    assert payload["attachments"][0]["content"]


def test_form_detector_separates_simple_and_complex_urls(tmp_path):
    form = FormApplyEngine(config(tmp_path), ApplicationGuard(config(tmp_path)))

    assert form.looks_like_simple_form("https://company.example/careers/apply/123") is True
    assert form.looks_like_simple_form("https://company.example/login/apply/123") is False


def test_external_apply_requires_site_specific_adapter(tmp_path):
    job = make_job(apply_email=None, apply_url="https://ats.example.com/questionnaire/123")
    result = ExternalApplyEngine(config(tmp_path), ApplicationGuard(config(tmp_path))).apply(make_request(tmp_path, job))

    assert result.status == "requires_adapter"
    assert result.method == "external"
