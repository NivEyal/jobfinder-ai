from typing import Any, Dict, Iterable, List

from src.israel_sources.base import SearchQuery
from src.israel_sources.models import IsraeliJob
from src.israel_sources.registry import get_adapter, get_all_adapters


class IsraelSearchEngine:
    def __init__(self, sources: Iterable[str] | None = None, max_pages: int | None = None):
        self.adapters = [get_adapter(source) for source in sources] if sources else get_all_adapters()
        if max_pages is not None:
            for adapter in self.adapters:
                adapter.max_pages = max_pages

    def search(self, keywords: List[str], locations: List[str], limit: int = 25) -> List[IsraeliJob]:
        query = SearchQuery(keywords=keywords, locations=locations, limit=limit)
        jobs: List[IsraeliJob] = []
        for adapter in self.adapters:
            try:
                jobs.extend(adapter.search(query))
            except Exception:
                continue
            if len(jobs) >= limit:
                break
        return jobs[:limit]

    def search_from_plan(self, search_plan: Dict[str, Any]) -> List[IsraeliJob]:
        total_limit = search_plan.get("total_limit", 100)
        jobs_per_source = search_plan.get("jobs_per_source", 25)
        jobs: List[IsraeliJob] = []
        seen = set()

        for query_spec in search_plan.get("queries", []):
            query_jobs = self.search(
                keywords=query_spec.get("keywords", []),
                locations=query_spec.get("locations", []),
                limit=min(query_spec.get("limit", jobs_per_source), total_limit),
            )
            for job in query_jobs:
                key = (job.source, job.source_job_id)
                if key in seen:
                    continue
                seen.add(key)
                jobs.append(job)
                if len(jobs) >= total_limit:
                    return jobs
        return jobs

    def source_names(self) -> List[str]:
        return [adapter.source for adapter in self.adapters]
