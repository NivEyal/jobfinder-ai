from src.israel_sources.base import SearchQuery
from src.israel_sources.jsonld_adapter import JsonLdJobAdapter
from src.israel_sources.models import IsraeliJob

from typing import List


class IndeedIsraelAdapter(JsonLdJobAdapter):
    source = "indeed"
    base_url = "https://il.indeed.com"

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        return self.make_url(
            "jobs",
            {
                "q": query.keyword_text,
                "l": query.location_text or "Israel",
                "start": (page - 1) * 10 if page > 1 else None,
            },
        )

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        for block in self.split_blocks(r'<div[^>]+class="[^"]*job_seen_beacon', payload):
            job_id = self.first_match(r'data-jk="([^"]+)"', block)
            title = self.first_match(r'<span[^>]+title="([^"]+)"', block) or self.first_match(r'<h2[^>]*>(.*?)</h2>', block)
            if not job_id or not title:
                continue
            company = self.first_match(r'data-testid="company-name"[^>]*>(.*?)</span>', block)
            location = self.first_match(r'data-testid="text-location"[^>]*>(.*?)</div>', block)
            description = self.first_match(r'<ul[^>]*>(.*?)</ul>', block)
            jobs.append(
                self.make_job(
                    source_job_id=job_id,
                    title=title,
                    company=company or "Indeed",
                    location=location or (query.location_text if query else "") or "Israel",
                    description=description or title,
                    apply_url=self.absolute_url(f"/viewjob?jk={job_id}"),
                )
            )
        return jobs
