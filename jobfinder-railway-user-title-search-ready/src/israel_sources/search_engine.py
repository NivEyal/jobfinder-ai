from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import re
from html import unescape
from typing import Any, Callable, Dict, Iterable, List

from src.israel_sources.base import SearchQuery
from src.israel_sources.models import IsraeliJob
from src.israel_sources.registry import get_adapter, get_all_adapters


ProgressCallback = Callable[[Dict[str, Any]], None]
CancelCallback = Callable[[], bool]


class IsraelSearchEngine:
    def __init__(
        self,
        sources: Iterable[str] | None = None,
        max_pages: int | None = None,
        progress_callback: ProgressCallback | None = None,
        cancel_callback: CancelCallback | None = None,
    ):
        self.adapters = [get_adapter(source) for source in sources] if sources else get_all_adapters()
        self.progress_callback = progress_callback
        self.cancel_callback = cancel_callback
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
        max_workers = int(search_plan.get("max_workers", 10))
        max_tasks = int(search_plan.get("max_tasks", 80))
        jobs: List[IsraeliJob] = []
        seen = set()
        queries = search_plan.get("queries", [])
        tasks = []

        for query_spec in queries:
            query = SearchQuery(
                keywords=query_spec.get("keywords", []),
                locations=query_spec.get("locations", []),
                limit=min(query_spec.get("limit", jobs_per_source), total_limit),
            )
            for adapter in self.adapters:
                tasks.append((adapter, query))
                if len(tasks) >= max_tasks:
                    break
            if len(tasks) >= max_tasks:
                break

        total_steps = max(1, len(tasks))
        completed = 0
        executor = ThreadPoolExecutor(max_workers=max(1, max_workers))
        futures = {executor.submit(self.search_adapter, adapter, query): (adapter, query) for adapter, query in tasks}
        try:
            pending = set(futures)
            while pending and len(jobs) < total_limit:
                if self.cancel_requested():
                    self.emit_progress(search_plan, completed, total_steps, len(jobs), "", "cancelled")
                    break
                done, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                if not done:
                    continue
                for future in done:
                    completed += 1
                    adapter, query = futures[future]
                    try:
                        query_jobs = future.result()
                    except Exception as exc:
                        self.emit_progress(search_plan, completed, total_steps, len(jobs), adapter.source, f"error: {exc}")
                        continue
                    filtered_jobs = self.filter_jobs_by_query(query_jobs, query)
                    self.emit_source_result(search_plan, adapter.source, query, len(query_jobs), len(filtered_jobs))
                    for job in filtered_jobs:
                        key = (job.source, job.source_job_id)
                        if key in seen:
                            continue
                        seen.add(key)
                        jobs.append(job)
                        if len(jobs) >= total_limit:
                            self.emit_progress(search_plan, completed, total_steps, len(jobs), adapter.source, "complete")
                            return jobs[:total_limit]
                    self.emit_progress(search_plan, completed, total_steps, len(jobs), adapter.source, "searching")
            return jobs[:total_limit]
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def search_adapter(adapter: Any, query: SearchQuery) -> List[IsraeliJob]:
        return adapter.search(query)

    @classmethod
    def filter_jobs_by_query(cls, jobs: List[IsraeliJob], query: SearchQuery) -> List[IsraeliJob]:
        if not query.keywords:
            return jobs
        return [job for job in jobs if cls.job_matches_query(job, query)]

    @classmethod
    def job_matches_query(cls, job: IsraeliJob, query: SearchQuery) -> bool:
        title = cls.normalize_match_text(job.title or "")
        if not title:
            return False
        return any(cls.keyword_matches_title(keyword, title) for keyword in query.keywords if keyword)

    @classmethod
    def keyword_matches_title(cls, keyword: str, title: str) -> bool:
        normalized = cls.normalize_match_text(keyword)
        if not normalized:
            return True
        if normalized in title:
            return True
        keyword_tokens = cls.significant_tokens(normalized)
        title_tokens = set(cls.significant_tokens(title))
        if not keyword_tokens or not title_tokens:
            return False
        return all(token in title_tokens for token in keyword_tokens)

    @staticmethod
    def significant_tokens(value: str) -> List[str]:
        ignored = {"job", "jobs", "role", "remote", "hybrid", "full", "time", "משרה", "עבודה"}
        return [token for token in value.split() if token and token not in ignored]

    @staticmethod
    def normalize_match_text(value: str) -> str:
        text = unescape(value or "").lower()
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("-", " ")
        text = re.sub(r"[^\w\u0590-\u05ff+#.-]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def search_from_plan_serial(self, search_plan: Dict[str, Any]) -> List[IsraeliJob]:
        total_limit = search_plan.get("total_limit", 100)
        jobs_per_source = search_plan.get("jobs_per_source", 25)
        jobs: List[IsraeliJob] = []
        seen = set()
        queries = search_plan.get("queries", [])
        total_steps = max(1, len(queries) * max(1, len(self.adapters)))
        step = 0

        for query_spec in queries:
            if self.cancel_requested():
                self.emit_progress(search_plan, step, total_steps, len(jobs), "", "cancelled")
                return jobs
            query = SearchQuery(
                keywords=query_spec.get("keywords", []),
                locations=query_spec.get("locations", []),
                limit=min(query_spec.get("limit", jobs_per_source), total_limit),
            )
            for adapter in self.adapters:
                if self.cancel_requested():
                    self.emit_progress(search_plan, step, total_steps, len(jobs), adapter.source, "cancelled")
                    return jobs
                step += 1
                try:
                    query_jobs = adapter.search(query)
                except Exception as exc:
                    self.emit_progress(search_plan, step, total_steps, len(jobs), adapter.source, f"error: {exc}")
                    continue
                for job in self.filter_jobs_by_query(query_jobs, query):
                    key = (job.source, job.source_job_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append(job)
                    if len(jobs) >= total_limit:
                        self.emit_progress(search_plan, step, total_steps, len(jobs), adapter.source, "complete")
                        return jobs
                self.emit_progress(search_plan, step, total_steps, len(jobs), adapter.source, "searching")
                if len(jobs) >= total_limit:
                    return jobs
        return jobs

    def source_names(self) -> List[str]:
        return [adapter.source for adapter in self.adapters]

    def emit_progress(
        self,
        search_plan: Dict[str, Any],
        step: int,
        total_steps: int,
        found: int,
        source: str,
        status: str,
    ) -> None:
        if not self.progress_callback:
            return
        self.progress_callback(
            {
                "phase": "searching",
                "status": status,
                "source": source,
                "jobs_found_so_far": found,
                "target_jobs": search_plan.get("total_limit", 100),
                "step": step,
                "total_steps": total_steps,
                "percent": int(min(99, max(1, step / max(total_steps, 1) * 100))),
            }
        )

    def emit_source_result(
        self,
        search_plan: Dict[str, Any],
        source: str,
        query: SearchQuery,
        fetched_count: int,
        accepted_count: int,
    ) -> None:
        if not self.progress_callback:
            return
        self.progress_callback(
            {
                "phase": "searching",
                "status": "source_result",
                "source": source,
                "query": query.keyword_text,
                "fetched_count": fetched_count,
                "accepted_count": accepted_count,
                "jobs_found_so_far": None,
                "target_jobs": search_plan.get("total_limit", 100),
            }
        )

    def cancel_requested(self) -> bool:
        return bool(self.cancel_callback and self.cancel_callback())
