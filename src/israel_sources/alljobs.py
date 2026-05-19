from src.israel_sources.base import SearchQuery
from src.israel_sources.jsonld_adapter import JsonLdJobAdapter
from src.israel_sources.models import IsraeliJob

import re
from typing import List


class AllJobsAdapter(JsonLdJobAdapter):
    source = "alljobs"
    base_url = "https://www.alljobs.co.il"
    max_pages = 2

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        return self.make_url(
            "m/p/jobs/search",
            {
                "page": page if page > 1 else None,
                "keywords": query.keyword_text or None,
            },
        )

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        for block in self.split_blocks(r'<div class="job-content-top"', payload):
            if len(jobs) >= query.limit:
                break
            try:
                job_id = self.first_match(r"JobID=(\d+)", block)
                title = self.first_match(r"<h2[^>]*>([^<]*)</h2>", block)
                if not job_id or not title:
                    continue
                company = self.first_match(r'<div class="T14">\s*<a[^>]*>([^<]*)</a>', block)
                location = self.first_match(r'job-content-top-location[^>]*>[^<]*</b>([^<]*)</div>', block)
                description = self.first_match(
                    rf'id="job-body-content{re.escape(job_id)}"[^>]*>([^<]*(?:<(?!/div)[^<]*)*)',
                    block,
                )
                jobs.append(
                    self.make_job(
                        source_job_id=job_id,
                        title=title,
                        company=company or "AllJobs",
                        location=location or (query.location_text if query else "") or "Israel",
                        description=description or title,
                        apply_url=self.absolute_url(f"/Search/UploadSingle.aspx?JobID={job_id}"),
                    )
                )
            except Exception:
                continue
        return jobs
