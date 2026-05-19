import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_RETRY = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
_ADAPTER = HTTPAdapter(pool_connections=20, pool_maxsize=50, max_retries=_RETRY)
_SESSION = requests.Session()
_SESSION.mount("http://", _ADAPTER)
_SESSION.mount("https://", _ADAPTER)

from src.israel_sources.models import IsraeliJob


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


@dataclass(frozen=True)
class SearchQuery:
    keywords: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    limit: int = 25

    @property
    def keyword_text(self) -> str:
        return " ".join(self.keywords).strip()

    @property
    def location_text(self) -> str:
        return " ".join(self.locations).strip()


class IsraelSourceAdapter:
    source = ""
    base_url = ""
    default_apply_method = "external_url"

    max_pages = 3

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        raise NotImplementedError

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        return []

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def search(self, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        seen: set = set()
        pages = list(range(1, self.max_pages + 1))
        with ThreadPoolExecutor(max_workers=min(len(pages), 4)) as executor:
            futures = {
                executor.submit(self.fetch, self.build_search_url(query, page=p)): p
                for p in pages
            }
            for future in as_completed(futures):
                try:
                    payload = future.result()
                except Exception:
                    continue
                for job in self.parse_jobs(payload, query):
                    key = (job.source, job.source_job_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append(job)
                    if len(jobs) >= query.limit:
                        return jobs
        return jobs

    def fetch(self, url: str, timeout: int = 10) -> str:
        resp = _SESSION.get(url, headers=self._HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    def make_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        if params:
            clean_params = {key: value for key, value in params.items() if value not in (None, "", [])}
            if clean_params:
                url = f"{url}?{urlencode(clean_params, doseq=True)}"
        return url

    def absolute_url(self, url: str) -> str:
        return urljoin(self.base_url.rstrip("/") + "/", unescape(url or ""))

    def make_job(
        self,
        source_job_id: str,
        title: str,
        company: str,
        location: str,
        description: str,
        apply_url: str,
        apply_email: Optional[str] = None,
        apply_method: Optional[str] = None,
        posted_at: Optional[datetime] = None,
    ) -> IsraeliJob:
        normalized_apply_url = apply_url or self.base_url
        normalized_email = apply_email or self.extract_email(description)
        return IsraeliJob(
            source=self.source,
            source_job_id=source_job_id or self.stable_id(normalized_apply_url, title, company),
            title=self.clean_text(title),
            company=self.clean_text(company),
            location=self.clean_text(location),
            description=self.clean_text(description),
            apply_url=normalized_apply_url,
            apply_email=normalized_email,
            apply_method=apply_method or ("email" if normalized_email else self.default_apply_method),
            posted_at=posted_at,
        )

    def sample_job(self) -> IsraeliJob:
        return self.make_job(
            source_job_id=f"{self.source}-sample",
            title="Software Engineer",
            company="Example Company",
            location="Israel",
            description="Static sample job used to validate the adapter contract.",
            apply_url=self.build_search_url(SearchQuery(keywords=["Software Engineer"], locations=["Israel"], limit=1)),
        )

    @staticmethod
    def clean_text(value: Any) -> str:
        if value is None:
            return ""
        text = unescape(str(value))
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def first_match(cls, pattern: str, text: str, flags: int = re.IGNORECASE | re.DOTALL) -> str:
        match = re.search(pattern, text or "", flags)
        return cls.clean_text(match.group(1)) if match else ""

    @staticmethod
    def split_blocks(pattern: str, payload: str) -> List[str]:
        matches = list(re.finditer(pattern, payload, flags=re.IGNORECASE | re.DOTALL))
        blocks = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(payload)
            blocks.append(payload[match.start() : end])
        return blocks

    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        match = EMAIL_PATTERN.search(text or "")
        return match.group(0) if match else None

    @staticmethod
    def stable_id(*parts: str) -> str:
        raw = "|".join(part for part in parts if part)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def json_ld_blocks(payload: str) -> Iterable[Dict[str, Any]]:
        import json

        pattern = re.compile(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            flags=re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(payload):
            raw_json = unescape(match.group(1)).strip()
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        yield item
            elif isinstance(parsed, dict):
                graph = parsed.get("@graph")
                if isinstance(graph, list):
                    for item in graph:
                        if isinstance(item, dict):
                            yield item
                yield parsed
