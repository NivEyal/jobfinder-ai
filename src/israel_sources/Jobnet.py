from src.israel_sources.base import SearchQuery
from src.israel_sources.jsonld_adapter import JsonLdJobAdapter
from src.israel_sources.models import IsraeliJob

from datetime import datetime
from typing import List, Optional


class JobnetAdapter(JsonLdJobAdapter):
    source = "jobnet"
    base_url = "https://www.jobnet.co.il"

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        return self.make_url(
            "jobs",
            {
                "search": query.keyword_text or None,
                "location": query.location_text or None,
                "page": page if page > 1 else None,
            },
        )

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        if not payload:
            return []
        jobs: List[IsraeliJob] = []
        for block in self.split_blocks(r'<div\s+itemscope itemtype="https://schema.org/JobPosting"', payload):
            try:
                job_id = self.first_match(r"positionid=(\d+)", block)
                title = self.first_match(r'itemprop="title"[^>]*>(.*?)</h2>', block)
                if not job_id or not title:
                    continue
                company = self.first_match(r'itemprop="hiringOrganization"[^>]*>.*?<a[^>]*>(.*?)</a>', block)
                description = self.first_match(r'itemprop="description"[^>]*>(.*?)</div>', block)
                skills = self.first_match(r'itemprop="skills"[^>]*>(.*?)</div>', block)
                location = self.first_match(r'<strong>אזור:</strong>\s*(.*?)</div>', block)
                posted_at = self._parse_date(self.first_match(r'itemprop="datePosted"[^>]*>(.*?)</p>', block))
                jobs.append(
                    self.make_job(
                        source_job_id=job_id,
                        title=title,
                        company=company or "Jobnet",
                        location=location or (query.location_text if query else "") or "Israel",
                        description=" ".join(part for part in [description, skills] if part) or title,
                        apply_url=self.absolute_url(f"/jobs?positionid={job_id}"),
                        posted_at=posted_at,
                    )
                )
            except Exception:
                continue
        return jobs

    @staticmethod
    def _parse_date(value: str) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.strptime(value.strip(), "%d/%m/%Y")
        except ValueError:
            return None
