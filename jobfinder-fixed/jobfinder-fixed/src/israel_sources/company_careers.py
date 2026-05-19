from typing import Dict, Iterable, List

from src.israel_sources.base import SearchQuery
from src.israel_sources.jsonld_adapter import JsonLdJobAdapter
from src.israel_sources.models import IsraeliJob


DEFAULT_COMPANY_CAREERS: Dict[str, str] = {
    "monday": "https://monday.com/careers",
    "wix": "https://www.wix.com/jobs",
    "similarweb": "https://www.similarweb.com/corp/careers",
    "check-point": "https://careers.checkpoint.com",
}


class CompanyCareersAdapter(JsonLdJobAdapter):
    source = "company_careers"
    base_url = "https://www.google.com/search"

    def __init__(self, company_urls: Dict[str, str] | None = None):
        self.company_urls = company_urls or DEFAULT_COMPANY_CAREERS

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        company_terms = " OR ".join(f"site:{url}" for url in self.company_urls.values())
        return self.make_url(
            "",
            {
                "q": f"{query.keyword_text} jobs Israel {company_terms}".strip(),
            },
        )

    def search(self, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        for company, url in self.company_urls.items():
            try:
                payload = self.fetch(url)
            except Exception:
                continue
            parsed_jobs = self.parse_jobs(payload, query)
            jobs.extend(self._with_company_fallback(parsed_jobs, company, url))
            if len(jobs) >= query.limit:
                break
        return jobs[: query.limit]

    def _with_company_fallback(
        self,
        jobs: Iterable[IsraeliJob],
        company: str,
        company_url: str,
    ) -> List[IsraeliJob]:
        normalized: List[IsraeliJob] = []
        for job in jobs:
            normalized.append(
                self.make_job(
                    source_job_id=job.source_job_id,
                    title=job.title,
                    company=job.company or company,
                    location=job.location or "Israel",
                    description=job.description,
                    apply_url=job.apply_url or company_url,
                    apply_email=job.apply_email,
                    apply_method=job.apply_method,
                    posted_at=job.posted_at,
                )
            )
        return normalized
