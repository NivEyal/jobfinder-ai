from datetime import datetime
from typing import Any, Dict, List, Optional

from src.israel_sources.base import IsraelSourceAdapter, SearchQuery
from src.israel_sources.models import IsraeliJob


class JsonLdJobAdapter(IsraelSourceAdapter):
    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        for block in self.json_ld_blocks(payload):
            for item in self._job_items(block):
                jobs.append(self._from_json_ld(item))
        return jobs

    def _job_items(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        item_type = item.get("@type")
        if item_type == "JobPosting" or (isinstance(item_type, list) and "JobPosting" in item_type):
            return [item]

        items = []
        for value in item.values():
            if isinstance(value, dict):
                items.extend(self._job_items(value))
            elif isinstance(value, list):
                for entry in value:
                    if isinstance(entry, dict):
                        items.extend(self._job_items(entry))
        return items

    def _from_json_ld(self, item: Dict[str, Any]) -> IsraeliJob:
        hiring_org = item.get("hiringOrganization") or {}
        location = item.get("jobLocation") or {}
        if isinstance(location, list):
            location = location[0] if location else {}

        address = location.get("address") if isinstance(location, dict) else {}
        if not isinstance(address, dict):
            address = {}

        apply_url = item.get("url") or item.get("sameAs") or self.base_url
        description = item.get("description") or ""
        posted_at = self._parse_date(item.get("datePosted") or item.get("validThrough"))

        return self.make_job(
            source_job_id=str(item.get("identifier") or ""),
            title=str(item.get("title") or ""),
            company=str(hiring_org.get("name") if isinstance(hiring_org, dict) else ""),
            location=", ".join(
                part
                for part in [
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                    address.get("addressCountry"),
                ]
                if part
            ),
            description=str(description),
            apply_url=str(apply_url),
            posted_at=posted_at,
        )

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        if not value:
            return None
        text = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
