import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote_plus

from src.israel_sources.base import IsraelSourceAdapter, SearchQuery
from src.israel_sources.models import IsraeliJob


def parse_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def keyword_matches(job: IsraeliJob, query: SearchQuery) -> bool:
    if not query.keywords:
        return True
    haystack = f"{job.title} {job.company} {job.location} {job.description}".lower()
    return any(keyword.lower() in haystack for keyword in query.keywords if keyword)


class RemotiveAdapter(IsraelSourceAdapter):
    source = "remotive"
    base_url = "https://remotive.com"
    default_apply_method = "external_url"

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        search = quote_plus(query.keyword_text or "software")
        return f"https://remotive.com/api/remote-jobs?search={search}"

    def search(self, query: SearchQuery) -> List[IsraeliJob]:
        payload = self.fetch(self.build_search_url(query))
        jobs = self.parse_jobs(payload, query)
        return jobs[: query.limit]

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []
        jobs = []
        for item in data.get("jobs", []):
            job = self.make_job(
                source_job_id=str(item.get("id") or ""),
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=item.get("candidate_required_location", "Remote"),
                description=item.get("description", ""),
                apply_url=item.get("url", ""),
                posted_at=parse_datetime(item.get("publication_date")),
            )
            jobs.append(job)
        return jobs


class ArbeitnowAdapter(IsraelSourceAdapter):
    source = "arbeitnow"
    base_url = "https://www.arbeitnow.com"
    default_apply_method = "external_url"

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        return f"https://www.arbeitnow.com/api/job-board-api?page={page}"

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []
        jobs = []
        for item in data.get("data", []):
            location = item.get("location") or ("Remote" if item.get("remote") else "Worldwide")
            job = self.make_job(
                source_job_id=str(item.get("slug") or item.get("url") or ""),
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                location=location,
                description=item.get("description", ""),
                apply_url=item.get("url", ""),
                posted_at=parse_datetime(item.get("created_at")),
            )
            if keyword_matches(job, query):
                jobs.append(job)
        return jobs


class RemoteOkAdapter(IsraelSourceAdapter):
    source = "remoteok"
    base_url = "https://remoteok.com"
    default_apply_method = "external_url"

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        search = quote_plus(query.keyword_text or "software")
        return f"https://remoteok.com/remote-{search}-jobs.json"

    def search(self, query: SearchQuery) -> List[IsraeliJob]:
        payload = self.fetch(self.build_search_url(query))
        jobs = self.parse_jobs(payload, query)
        return jobs[: query.limit]

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []
        jobs = []
        for item in data:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            tags = " ".join(item.get("tags") or [])
            description = item.get("description") or item.get("position") or tags
            job = self.make_job(
                source_job_id=str(item.get("id")),
                title=item.get("position", ""),
                company=item.get("company", ""),
                location=item.get("location") or "Remote",
                description=description,
                apply_url=item.get("url") or item.get("apply_url") or self.base_url,
                posted_at=parse_datetime(item.get("date") or item.get("epoch")),
            )
            jobs.append(job)
        return jobs


class GreenhouseAdapter(IsraelSourceAdapter):
    source = "greenhouse"
    base_url = "https://boards-api.greenhouse.io"
    default_apply_method = "external_url"
    boards = [
        "airbnb",
        "cloudflare",
        "datadog",
        "doordash",
        "github",
        "monday",
        "openai",
        "stripe",
        "wix",
    ]

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        board = self.boards[(page - 1) % len(self.boards)]
        return f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []
        jobs = []
        for item in data.get("jobs", []):
            offices = item.get("offices") or []
            locations = [office.get("name", "") for office in offices if isinstance(office, dict)]
            location = ", ".join(location for location in locations if location) or item.get("location", {}).get("name", "")
            job = self.make_job(
                source_job_id=str(item.get("id") or item.get("absolute_url") or ""),
                title=item.get("title", ""),
                company=data.get("name", "") or self.first_match(r"/boards/([^/]+)/", item.get("absolute_url", "")),
                location=location or "Worldwide",
                description=item.get("content", ""),
                apply_url=item.get("absolute_url", ""),
                posted_at=parse_datetime(item.get("updated_at")),
            )
            if keyword_matches(job, query):
                jobs.append(job)
        return jobs


class LeverAdapter(IsraelSourceAdapter):
    source = "lever"
    base_url = "https://api.lever.co"
    default_apply_method = "external_url"
    companies = ["anduril", "brex", "canva", "figma", "netlify", "ramp", "vercel", "zapier"]

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        company = self.companies[(page - 1) % len(self.companies)]
        return f"https://api.lever.co/v0/postings/{company}?mode=json"

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        jobs = []
        for item in data:
            categories = item.get("categories") or {}
            company = item.get("company") or self.first_match(r"/([^/]+)/[^/]+$", item.get("hostedUrl", ""))
            description = "\n".join(extract_lever_text(item.get("lists") or []))
            job = self.make_job(
                source_job_id=str(item.get("id") or item.get("hostedUrl") or ""),
                title=item.get("text", ""),
                company=company,
                location=categories.get("location", "Worldwide"),
                description=description or item.get("descriptionPlain", ""),
                apply_url=item.get("hostedUrl", ""),
                posted_at=parse_datetime(item.get("createdAt")),
            )
            if keyword_matches(job, query):
                jobs.append(job)
        return jobs


def extract_lever_text(lists: Iterable[Dict[str, Any]]) -> List[str]:
    output = []
    for section in lists:
        if not isinstance(section, dict):
            continue
        output.append(str(section.get("text", "")))
        for content in section.get("content", []) or []:
            if isinstance(content, dict):
                output.append(str(content.get("text", "")))
            else:
                output.append(str(content))
    return [text for text in output if text]
