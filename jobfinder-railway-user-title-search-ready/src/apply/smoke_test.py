import json
from pathlib import Path

import yaml

from src.apply import ApplicationRequest, AutoApplyEngine
from src.israel_sources.models import IsraeliJob
from src.matching.models import MatchResult


def main() -> int:
    config = yaml.safe_load(Path("data_folder/work_preferences.yaml").read_text(encoding="utf-8"))
    config["apply"]["ledger_path"] = "data_folder/output/apply_smoke_ledger.json"
    Path(config["apply"]["ledger_path"]).unlink(missing_ok=True)
    job = IsraeliJob(
        source="smoke",
        source_job_id="apply-1",
        title="Backend Developer",
        company="Example",
        location="Tel Aviv",
        description="Python backend role",
        apply_url="",
        apply_email="jobs@example.com",
        apply_method="email",
        posted_at=None,
    ).to_job(normalized_output_language=config["output"]["normalized_language"])
    match = MatchResult(
        job_fingerprint=job.fingerprint,
        source=job.source,
        source_job_id=job.source_job_id,
        score=90,
        verdict="strong_match",
        confidence=0.8,
    )
    request = ApplicationRequest(
        job=job,
        resume_path=Path("data_folder/plain_text_resume.yaml"),
        cover_letter_path=Path("data_folder/cover_letter_template.txt"),
        candidate_name="Candidate",
        candidate_email="candidate@example.com",
        candidate_phone="+972500000000",
        message="Please see my attached resume.",
        match_result=match,
    )
    result = AutoApplyEngine(config).apply(request)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.status in {"dry_run_ready", "submitted"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
