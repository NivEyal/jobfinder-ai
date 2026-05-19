from src.apply import ApplicationResult
from src.israel_sources.models import IsraeliJob
from src.storage import JsonlStore, SQLiteStore


def make_job():
    return IsraeliJob(
        source="jobmaster",
        source_job_id="123",
        title="Junior Economist",
        company="Example",
        location="Tel Aviv",
        description="Entry level economist role",
        apply_url="https://example.com/apply",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    ).to_job(normalized_output_language="en")


def test_sqlite_store_creates_required_tables_and_records_flow(tmp_path):
    store = SQLiteStore(tmp_path / "jobs.sqlite3")
    job = make_job()

    store.save_job(job)
    run_id = store.start_ingestion_run("jobmaster", {"keyword": "Junior Economist"})
    store.finish_ingestion_run(run_id, "success", jobs_found=1, jobs_saved=1)
    store.record_ingestion_error("jobmaster", {"keyword": "bad"}, "sample error")
    store.save_source_snapshot("jobmaster", "html", "<html></html>", "https://example.com")
    result = ApplicationResult(
        status="dry_run_ready",
        method="form",
        job_fingerprint=job.fingerprint,
        source=job.source,
        source_job_id=job.source_job_id,
        dry_run=True,
        detail="prepared",
        target=job.apply_url,
    )
    store.record_application(result)
    store.log_application("prepared", "application prepared", result)

    counts = store.table_counts()

    assert counts["jobs"] == 1
    assert counts["applications"] == 1
    assert counts["ingestion_runs"] == 1
    assert counts["ingestion_errors"] == 1
    assert counts["application_logs"] == 1
    assert counts["source_snapshots"] == 1
    assert store.has_application(job.fingerprint) is True


def test_jsonl_store_appends_readable_logs(tmp_path):
    store = JsonlStore(tmp_path / "jsonl")

    store.append("application_logs", {"event": "prepared", "job_fingerprint": "abc"})
    rows = store.read_all("application_logs")

    assert rows[0]["event"] == "prepared"
    assert rows[0]["job_fingerprint"] == "abc"
    assert rows[0]["created_at"]
