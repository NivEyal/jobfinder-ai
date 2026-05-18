import json
from pathlib import Path

import yaml

from src.israel_sources.models import IsraeliJob
from src.matching.matcher import JobMatcher


def main() -> int:
    config = yaml.safe_load(Path("data_folder/work_preferences.yaml").read_text(encoding="utf-8"))
    resume_text = Path("data_folder/plain_text_resume.yaml").read_text(encoding="utf-8")
    job = IsraeliJob(
        source="smoke",
        source_job_id="matching-1",
        title="Backend Developer",
        company="Example",
        location="Tel Aviv hybrid",
        description="Backend role with Python, APIs, cloud, full time, hybrid, 2 years experience.",
        apply_url="https://example.com/apply",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    ).to_job(normalized_output_language=config["output"]["normalized_language"])

    result = JobMatcher(config).match(job, resume_text)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if 0 <= result.score <= 100 and result.verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
