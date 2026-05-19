from dataclasses import fields
import argparse
import json

from src.israel_sources.base import SearchQuery
from src.israel_sources.models import IsraeliJob
from src.israel_sources.registry import get_all_adapters


EXPECTED_FIELDS = [field.name for field in fields(IsraeliJob)]


def validate_adapter_contract() -> None:
    adapters = get_all_adapters()
    if not adapters:
        raise AssertionError("No Israeli job source adapters registered.")

    for adapter in adapters:
        job = adapter.sample_job()
        if not isinstance(job, IsraeliJob):
            raise AssertionError(f"{adapter.source} did not return IsraeliJob.")

        data = job.to_dict()
        missing_fields = [field for field in EXPECTED_FIELDS if field not in data]
        if missing_fields:
            raise AssertionError(f"{adapter.source} missing fields: {missing_fields}")

        required_values = ["source", "source_job_id", "title", "company", "location", "description", "apply_url", "apply_method"]
        empty_values = [field for field in required_values if not data[field]]
        if empty_values:
            raise AssertionError(f"{adapter.source} returned empty values: {empty_values}")


def validate_live_search(keyword: str, location: str, min_total: int, min_sources: int) -> None:
    query = SearchQuery(keywords=[keyword], locations=[location], limit=50)
    report = {"total_jobs": 0, "sources_with_jobs": 0, "sources": {}}

    for adapter in get_all_adapters():
        try:
            jobs = adapter.search(query)
            sample = jobs[0].to_dict() if jobs else None
            report["sources"][adapter.source] = {
                "count": len(jobs),
                "sample": sample,
                "error": None,
            }
        except Exception as exc:
            jobs = []
            report["sources"][adapter.source] = {
                "count": 0,
                "sample": None,
                "error": f"{type(exc).__name__}: {exc}",
            }

        report["total_jobs"] += len(jobs)
        if jobs:
            report["sources_with_jobs"] += 1

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["total_jobs"] < min_total:
        raise AssertionError(f"Expected at least {min_total} live jobs, got {report['total_jobs']}.")
    if report["sources_with_jobs"] < min_sources:
        raise AssertionError(
            f"Expected live jobs from at least {min_sources} sources, got {report['sources_with_jobs']}."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Fetch real jobs from live Israeli sources.")
    parser.add_argument("--keyword", default="Software Engineer")
    parser.add_argument("--location", default="Israel")
    parser.add_argument("--min-total", type=int, default=20)
    parser.add_argument("--min-sources", type=int, default=4)
    args = parser.parse_args()

    validate_adapter_contract()
    if args.live:
        validate_live_search(args.keyword, args.location, args.min_total, args.min_sources)
    else:
        print("Israeli source adapter contract OK")
