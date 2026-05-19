import json
from pathlib import Path

from src.apply import ApplicationResult
from src.israel_sources.models import IsraeliJob
from src.storage import JsonlStore, SQLiteStore


def main() -> int:
    db_path = Path("data_folder/output/storage_smoke.sqlite3")
    jsonl_dir = Path("data_folder/output/storage_smoke_jsonl")
    db_path.unlink(missing_ok=True)
    store = SQLiteStore(db_path)
    jsonl = JsonlStore(jsonl_dir)
    job = IsraeliJob(
        source="smoke",
        source_job_id="storage-1",
        title="Junior Economist",
        company="Example",
        location="Tel Aviv",
        description="Entry economist role",
        apply_url="https://example.com/apply",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    ).to_job(normalized_output_language="en")
    store.save_job(job)
    run_id = store.start_ingestion_run("smoke", {"keyword": "Junior Economist"})
    store.finish_ingestion_run(run_id, "success", jobs_found=1, jobs_saved=1)
    result = ApplicationResult(
        status="dry_run_ready",
        method="form",
        job_fingerprint=job.fingerprint,
        source=job.source,
        source_job_id=job.source_job_id,
        dry_run=True,
        detail="storage smoke",
        target=job.apply_url,
    )
    store.record_application(result)
    store.log_application("smoke", "storage smoke application log", result)
    store.record_ingestion_error("smoke", {"keyword": "bad"}, "sample error")
    store.save_source_snapshot("smoke", "html", "<html></html>", "https://example.com")
    jsonl.append("application_logs", result.to_dict())
    counts = store.table_counts()
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    return 0 if all(counts[table] >= 1 for table in counts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
