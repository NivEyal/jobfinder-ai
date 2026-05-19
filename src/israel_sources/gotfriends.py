import ssl

from src.israel_sources.base import SearchQuery
from src.israel_sources.jsonld_adapter import JsonLdJobAdapter
from src.israel_sources.models import IsraeliJob
from typing import List

_SSL_CTX = ssl._create_unverified_context()


class GotFriendsAdapter(JsonLdJobAdapter):
    source = "gotfriends"
    base_url = "https://www.gotfriends.co.il"
    max_pages = 2

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        keyword = (query.keyword_text or "").lower()
        if "full" in keyword or "software" in keyword or "engineer" in keyword:
            path = "jobslobby/software/full-stack-developer"
        elif "data" in keyword:
            path = "jobslobby/algorithm/data-scientist"
        else:
            path = "jobslobby/software"
        return self.make_url(path, {"page": page if page > 1 else None})

    def fetch(self, url: str, timeout: int = 20) -> str:
        from urllib.request import Request, urlopen
        request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "he,en;q=0.8"})
        with urlopen(request, timeout=timeout, context=_SSL_CTX) as response:
            return response.read().decode("utf-8", errors="replace")

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        for block in self.split_blocks(r'<div class="item">', payload):
            try:
                href = self.first_match(r'<a[^>]+href="([^"]+)"[^>]+class="position', block)
                title = self.first_match(r'<h2 class="title">(.*?)</h2>', block)
                if not href or not title:
                    continue
                job_id = self.first_match(r"מס&#x27; משרה:\s*([0-9]+)", block) or self.first_match(r"/([0-9]+)/", href)
                location = self.first_match(r'<span class="info-label">מיקום:</span>\s*<span class="info-data">(.*?)</span>', block)
                description = self.first_match(r'<div class="title_c">תיאור המשרה:</div>(.*?)(?:<div class="desc">|<div class="career_num"|$)', block)
                jobs.append(
                    self.make_job(
                        source_job_id=job_id,
                        title=title,
                        company="GotFriends",
                        location=location or (query.location_text if query else "") or "Israel",
                        description=description or title,
                        apply_url=self.absolute_url(href),
                    )
                )
            except Exception:
                continue
        return jobs
