import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from math import ceil
from typing import Any, Dict, List, Optional

from src.israel_sources.base import SearchQuery
from src.israel_sources.jsonld_adapter import JsonLdJobAdapter
from src.israel_sources.models import IsraeliJob


class DrushimAdapter(JsonLdJobAdapter):
    source = "drushim"
    base_url = "https://www.drushim.co.il"

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        params = {
            "searchterm": query.keyword_text,
            "isAA": "true",
            "page": page,
            "range": 3,
        }
        if query.location_text and len(query.locations) <= 2:
            params["area"] = query.location_text
        return self.make_url(
            "api/jobs/search",
            params,
        )

    max_pages = 12

    def search(self, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        seen: set = set()
        page_count = min(30, max(self.max_pages, ceil(max(query.limit, 1) / 10) + 6))
        pages = list(range(1, page_count + 1))
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.fetch, self.build_search_url(query, page=page), 20): page
                for page in pages
            }
            for future in as_completed(futures):
                try:
                    payload = future.result()
                except Exception:
                    continue
                parsed = self.parse_jobs(payload, query)
                if not parsed:
                    continue
                for job in parsed:
                    key = (job.source, job.source_job_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append(job)
                    if len(jobs) >= query.limit:
                        return jobs
        return jobs

    @staticmethod
    def is_economist_query(query: SearchQuery) -> bool:
        text = " ".join(query.keywords).lower()
        return any(term in text for term in ["כלכל", "economist", "financial analyst", "finance analyst"])

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return super().parse_jobs(payload, query)

        jobs: List[IsraeliJob] = []
        for item in data.get("ResultList", []):
            try:
                job_content = item.get("JobContent") or {}
                job_info = item.get("JobInfo") or {}
                company = item.get("Company") or {}
                send_cv = item.get("SendCVButtonModel") or {}

                title = str(job_content.get("FullName") or job_content.get("Name") or "")
                if not title:
                    continue

                source_job_id = str(item.get("Code") or job_content.get("JobCode") or job_info.get("JobCode") or "")
                description = " ".join(
                    part
                    for part in [
                        job_content.get("Description"),
                        job_content.get("Requirements"),
                        job_content.get("DeclarationAllGenders"),
                        self._taxonomy_text(job_content),
                    ]
                    if part
                )
                apply_url = send_cv.get("ExternalLink") or send_cv.get("ButtonLink") or job_info.get("Link") or ""
                jobs.append(
                    self.make_job(
                        source_job_id=source_job_id,
                        title=title,
                        company=company.get("CompanyDisplayName") or company.get("NameInHebrew") or "Drushim",
                        location=self._location(job_content),
                        description=description or title,
                        apply_url=self.absolute_url(apply_url) if apply_url else self.base_url,
                        apply_method="external_url",
                        posted_at=self._parse_date(job_info.get("DisplayDate") or job_info.get("Date")),
                    )
                )
            except Exception:
                continue
        return jobs

    @staticmethod
    def _location(job_content: Dict[str, Any]) -> str:
        addresses = job_content.get("Addresses") or []
        if addresses:
            cities = [address.get("City") for address in addresses if address.get("City")]
            if cities:
                return ", ".join(dict.fromkeys(cities))

        regions = job_content.get("Regions") or []
        if regions:
            return ", ".join(region.get("NameInHebrew") for region in regions if region.get("NameInHebrew"))

        zones = job_content.get("Zones") or []
        if zones:
            return ", ".join(zone.get("NameInHebrew") for zone in zones if zone.get("NameInHebrew"))

        return "Israel"

    @staticmethod
    def _taxonomy_text(job_content: Dict[str, Any]) -> str:
        names = []
        for group in ["Categories", "SubCategories", "Scopes"]:
            for item in job_content.get(group) or []:
                name = item.get("NameInHebrew")
                if name:
                    names.append(str(name))
        return " ".join(dict.fromkeys(names))

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        text = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
