from src.israel_sources.base import SearchQuery
from src.israel_sources.jsonld_adapter import JsonLdJobAdapter
from src.israel_sources.models import IsraeliJob

from typing import List


class JobMasterAdapter(JsonLdJobAdapter):
    source = "jobmaster"
    base_url = "https://www.jobmaster.co.il"

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        return self.make_url(
            "jobs/",
            {
                "currPage": page if page > 1 else None,
                "q": query.keyword_text or None,
            },
        )

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        if not payload:
            return []
        jobs: List[IsraeliJob] = []
        for block in self.split_blocks(r'<article[^>]+id="misra\d+"', payload):
            try:
                job_id = self.first_match(r'id="misra(\d+)"', block)
                href = self.first_match(r'class="CardHeader[^"]*"[^>]+href=[\'"]([^\'"]+)[\'"]', block)
                title = self.first_match(r'class="CardHeader[^"]*"[^>]+href=[\'"][^\'"]+[\'"][^>]*>(.*?)</a>', block)
                if not title:
                    title = self.first_match(r'class="CardHeader[^"]*"[^>]*>(.*?)</a>', block)
                if not job_id or not title:
                    continue
                company = self.first_match(r'class="font14 CompanyNameLink"[^>]*>\s*<span>(.*?)</span>', block)
                location = self.first_match(r'class="jobLocation"[^>]*>\s*<span>(.*?)</span>', block)
                description = self.first_match(r'class="jobShortDescription[^"]*"[^>]*>(.*?)</div>', block)
                jobs.append(
                    self.make_job(
                        source_job_id=job_id,
                        title=title,
                        company=company or "JobMaster",
                        location=location or (query.location_text if query else "") or "Israel",
                        description=description or title,
                        apply_url=self.absolute_url(href or f"/jobs/checknum.asp?key={job_id}"),
                        posted_at=None,
                    )
                )
            except Exception:
                continue
        return jobs
