import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.israel_sources.base import SearchQuery
from src.israel_sources.jsonld_adapter import JsonLdJobAdapter
from src.israel_sources.models import IsraeliJob


class DrushimAdapter(JsonLdJobAdapter):
    source = "drushim"
    base_url = "https://www.drushim.co.il"

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        return self.make_url(
            "api/jobs/search",
            {
                "searchterm": query.keyword_text,
                "area": query.location_text,
                "isAA": "true",
                "page": page,
            },
        )

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return super().parse_jobs(payload, query)

        jobs: List[IsraeliJob] = []
        for item in data.get("ResultList", []):
            job_content = item.get("JobContent") or {}
            job_info = item.get("JobInfo") or {}
            company = item.get("Company") or {}
            send_cv = item.get("SendCVButtonModel") or {}

            source_job_id = str(item.get("Code") or job_content.get("JobCode") or job_info.get("JobCode") or "")
            title = job_content.get("FullName") or job_content.get("Name") or ""
            description = " ".join(
                part
                for part in [
                    job_content.get("Description"),
                    job_content.get("Requirements"),
                    job_content.get("DeclarationAllGenders"),
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
                    apply_url=self.absolute_url(apply_url),
                    apply_method="external_url",
                    posted_at=self._parse_date(job_info.get("DisplayDate") or job_info.get("Date")),
                )
            )
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
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        text = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
