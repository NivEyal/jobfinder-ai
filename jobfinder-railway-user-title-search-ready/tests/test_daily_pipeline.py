from pathlib import Path

import yaml

from src.commands.daily_pipeline import DailyPipeline
from src.israel_sources.models import IsraeliJob


def make_config(tmp_path, mode="approval_before_send", threshold=60):
    config = yaml.safe_load(Path("data_folder/work_preferences.yaml").read_text(encoding="utf-8"))
    config["matching"]["provider"] = "rule_based"
    config["storage"]["sqlite_path"] = str(tmp_path / "pipeline.sqlite3")
    config["storage"]["jsonl_dir"] = str(tmp_path / "jsonl")
    config["apply"]["ledger_path"] = str(tmp_path / "applications_ledger.json")
    config["automation"]["application_mode"] = mode
    config["automation"]["match_threshold"] = threshold
    config["automation"]["daily_application_limit"] = 2
    config["users"][0]["subscription"]["active"] = True
    config["output"]["summary_dir"] = str(tmp_path / "output")
    path = tmp_path / "work_preferences.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def make_jobs():
    return [
        IsraeliJob(
            source="jobmaster",
            source_job_id="eco-1",
            title="כלכלן/ית מתחיל/ה",
            company="Example Finance",
            location="תל אביב",
            description="כלכלן מתחיל ללא ניסיון, Excel, בקרה תקציבית, משרה מלאה.",
            apply_url="https://example.com/apply/eco-1",
            apply_email=None,
            apply_method="external_url",
            posted_at=None,
        ),
        IsraeliJob(
            source="jobmaster",
            source_job_id="eco-2",
            title="כלכלן/ית מתחיל/ה למחלקת כספים",
            company="Example Retail",
            location="רמת גן",
            description="תפקיד כלכלה ובקרה תקציבית לבוגר כלכלה, Excel ודוחות.",
            apply_url="https://example.com/apply/eco-2",
            apply_email=None,
            apply_method="external_url",
            posted_at=None,
        ),
    ]


def test_daily_pipeline_generates_user_status_and_inbox(tmp_path):
    pipeline = DailyPipeline(config_path=make_config(tmp_path), resume_path="data_folder/plain_text_resume.yaml")
    summary = pipeline.run(jobs_override=make_jobs())
    user_status = summary.to_user_status()

    assert user_status["status"] == "האוטומציה פעילה"
    assert user_status["jobs_found_today"] == 2
    assert user_status["requires_approval"] >= 1
    assert user_status["daily_limit"].endswith("/2")
    assert "הרץ עכשיו" in user_status["buttons"]
    assert any(item["status"] in {"pending_approval", "blocked"} for item in user_status["application_inbox"])
    assert (tmp_path / "output" / "daily_summary.json").exists()
    assert (tmp_path / "output" / "automation_status.json").exists()


def test_daily_pipeline_full_auto_uses_dry_run_apply_and_daily_limit(tmp_path):
    pipeline = DailyPipeline(config_path=make_config(tmp_path, mode="full_auto", threshold=60), resume_path="data_folder/plain_text_resume.yaml")
    summary = pipeline.run(jobs_override=make_jobs())

    assert summary.daily_limit == 2
    assert summary.jobs_found_today == 2
    assert summary.applications_sent_today <= 2
    assert (tmp_path / "pipeline.sqlite3").exists()


def test_daily_pipeline_subscription_gate_blocks_after_showing_jobs(tmp_path):
    config_path = make_config(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["users"][0]["subscription"]["active"] = False
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    pipeline = DailyPipeline(config_path=config_path, resume_path="data_folder/plain_text_resume.yaml")

    summary = pipeline.run(jobs_override=make_jobs())
    user_status = summary.to_user_status()

    assert user_status["jobs_found_today"] == 2
    assert user_status["subscription_locked"] is True
    assert user_status["subscription_pay_url"] == "https://paypage.takbull.co.il/2dBbl"
    assert user_status["application_inbox"][0]["status"] == "payment_required"
    assert summary.matched_jobs == 2


def test_daily_pipeline_runtime_keywords_override_config(tmp_path):
    config_path = make_config(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["search"]["keywords"] = ["Software Engineer"]
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    pipeline = DailyPipeline(
        config_path=config_path,
        resume_path="data_folder/plain_text_resume.yaml",
        runtime_keywords=["Junior Economist"],
    )

    assert pipeline.config["search"]["keywords"] == ["Junior Economist"]


def test_apply_throttle_sleeps_after_every_batch(monkeypatch):
    calls = []
    monkeypatch.setattr("src.commands.daily_pipeline.time.sleep", lambda seconds: calls.append(seconds))

    DailyPipeline.throttle_apply(9, throttle_every=10, throttle_seconds=3)
    DailyPipeline.throttle_apply(10, throttle_every=10, throttle_seconds=3)
    DailyPipeline.throttle_apply(20, throttle_every=10, throttle_seconds=3)

    assert calls == [3, 3]
