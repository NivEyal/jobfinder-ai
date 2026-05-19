import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterable, List

from src.israel_sources.base import IsraelSourceAdapter, SearchQuery
from src.israel_sources.models import IsraeliJob


COMEET_URLS = [
    "https://www.comeet.com/jobs/accessibe/D5.00B",
    "https://www.comeet.com/jobs/moonshot/87.005",
    "https://www.comeet.com/jobs/team8/61.003",
    "https://www.comeet.com/jobs/nexar/13.008",
    "https://www.comeet.com/jobs/liveu/90.00C",
    "https://www.comeet.com/jobs/infinidat/D6.003",
    "https://www.comeet.com/jobs/global-e/62.002",
    "https://www.comeet.com/jobs/razorlabs/A5.002",
    "https://www.comeet.com/jobs/buyme/B2.008",
    "https://www.comeet.com/jobs/scadafence/43.00E",
    "https://www.comeet.com/jobs/lili/A6.009",
    "https://www.comeet.com/jobs/p81/64.00C",
    "https://www.comeet.com/jobs/cynet/33.00D",
    "https://www.comeet.com/jobs/aquasec/91.001",
    "https://www.comeet.com/jobs/scylladb/E4.006",
    "https://www.comeet.com/jobs/fundguard/37.002",
    "https://www.comeet.com/jobs/onezerobank/36.00A",
    "https://www.comeet.com/jobs/workiz/F6.006",
    "https://www.comeet.com/jobs/guesty/10.000",
    "https://www.comeet.com/jobs/devalore/15.007",
    "https://www.comeet.com/jobs/guardknox/55.008",
    "https://www.comeet.com/jobs/viber/04.002",
    "https://www.comeet.com/jobs/upstream/E4.003",
    "https://www.comeet.com/jobs/easysend/D5.009",
    "https://www.comeet.com/jobs/biocatch/03.00E",
    "https://www.comeet.com/jobs/audiocodes/85.004",
    "https://www.comeet.com/jobs/zim/72.008",
    "https://www.comeet.com/jobs/silverfort/54.007",
    "https://www.comeet.com/jobs/komodor/96.005",
    "https://www.comeet.com/jobs/deepinstinct/72.00A",
    "https://www.comeet.com/jobs/incredibuild/66.00F",
    "https://www.comeet.com/jobs/final/C0.009",
    "https://www.comeet.com/jobs/optibus/D1.00C",
    "https://www.comeet.com/jobs/ilyon/42.00A",
    "https://www.comeet.com/jobs/ourcrowd/D3.00A",
    "https://www.comeet.com/jobs/vastdata/43.001",
    "https://www.comeet.com/jobs/immunai/37.009",
    "https://www.comeet.com/jobs/riverside-fm/66.009",
    "https://www.comeet.com/jobs/rapyd/73.00E",
    "https://www.comeet.com/jobs/safebreach/53.004",
    "https://www.comeet.com/jobs/jvp/35.00E",
    "https://www.comeet.com/jobs/Claroty/F2.004",
    "https://www.comeet.com/jobs/attenti/C2.00D",
    "https://www.comeet.com/jobs/autobrains/57.004",
    "https://www.comeet.com/jobs/paragon/76.006",
    "https://www.comeet.com/jobs/aiola/77.002",
    "https://www.comeet.com/jobs/365scores/B3.006",
    "https://www.comeet.com/jobs/paybox/18.004",
    "https://www.comeet.com/jobs/minutemedia/45.00A",
    "https://www.comeet.com/jobs/voyagerlabs/63.00A",
    "https://www.comeet.com/jobs/ai21/E6.001",
]


ISRAEL_CITY_TOKENS = {
    "israel",
    "il",
    "tlv",
    "tel aviv",
    "tel-aviv",
    "jerusalem",
    "haifa",
    "herzliya",
    "netanya",
    "raanana",
    "ramat gan",
    "petah tikva",
    "beer sheva",
    "yokneam",
    "rehovot",
    "ashdod",
    "bnei brak",
}


class ComeetAdapter(IsraelSourceAdapter):
    source = "comeet"
    base_url = "https://www.comeet.com"
    default_apply_method = "external_url"

    def __init__(self, urls: Iterable[str] | None = None):
        self.urls = list(urls or COMEET_URLS)

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        if not self.urls:
            return self.base_url
        return self.urls[(page - 1) % len(self.urls)]

    def sample_job(self) -> IsraeliJob:
        return self.make_job(
            source_job_id="comeet-sample",
            title="Software Engineer",
            company="Example Comeet Company",
            location="Tel Aviv, Israel",
            description="Static sample job used to validate the adapter contract.",
            apply_url=self.base_url,
        )

    def search(self, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        seen = set()
        urls = self.urls[: max(query.limit * 3, 20)]
        with ThreadPoolExecutor(max_workers=min(12, max(1, len(urls)))) as executor:
            futures = {executor.submit(self.fetch, url): url for url in urls}
            for future in as_completed(futures):
                try:
                    parsed = self.parse_jobs(future.result(), query)
                except Exception:
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

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        for item in self._position_items(payload):
            location = item.get("location") or {}
            location_text = self._location_text(location)
            if not self._is_israel_location(location, location_text):
                continue
            company = str(item.get("company_name") or item.get("company") or "Comeet")
            title = str(item.get("name") or item.get("title") or "")
            uid = str(item.get("uid") or item.get("id") or self.stable_id(company, title, location_text))
            apply_url = str(item.get("url_comeet_hosted_page") or item.get("url") or self.base_url)
            jobs.append(
                self.make_job(
                    source_job_id=f"{company}-{uid}",
                    title=title,
                    company=company,
                    location=location_text or "Israel",
                    description=str(item.get("description") or title),
                    apply_url=apply_url,
                )
            )
        return jobs

    @staticmethod
    def _position_items(payload: str) -> List[dict]:
        items: List[dict] = []
        pattern = re.compile(r"COMPANY_POSITIONS_DATA\s*=\s*(\[.*?\])\s*;?\s*(?:\n|$)", re.DOTALL)
        for match in pattern.finditer(payload or ""):
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                items.extend(item for item in data if isinstance(item, dict))
        return items

    @staticmethod
    def _location_text(location: Any) -> str:
        if isinstance(location, dict):
            parts = [location.get("name"), location.get("city"), location.get("country")]
            return ", ".join(str(part) for part in parts if part)
        return str(location or "")

    @staticmethod
    def _is_israel_location(location: Any, location_text: str) -> bool:
        values = [location_text]
        if isinstance(location, dict):
            values.extend(str(location.get(key) or "") for key in ["name", "city", "country"])
        text = " ".join(values).lower()
        return any(token in text for token in ISRAEL_CITY_TOKENS)
