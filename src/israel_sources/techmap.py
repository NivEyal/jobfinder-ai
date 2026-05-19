import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.israel_sources.base import IsraelSourceAdapter, SearchQuery
from src.israel_sources.models import IsraeliJob


TECHMAP_BASE_URL = "https://raw.githubusercontent.com/mluggy/techmap/main"
TECHMAP_CATEGORIES = [
    "admin",
    "business",
    "data-science",
    "design",
    "devops",
    "finance",
    "frontend",
    "hardware",
    "hr",
    "legal",
    "marketing",
    "procurement-operations",
    "product",
    "project-management",
    "qa",
    "sales",
    "security",
    "software",
    "support",
]

_CATEGORY_HINTS = {
    "finance": [
        "accountant",
        "accounting",
        "bookkeeper",
        "controller",
        "economist",
        "fp&a",
        "payroll",
        "כלכל",
        "חשב",
        "כספ",
    ],
    "software": ["backend", "back end", "full stack", "fullstack", "software", "developer", "engineer", "python", "java", "מפתח", "תוכנה"],
    "frontend": ["frontend", "front end", "react", "angular", "vue"],
    "data-science": ["data", "bi", "analyst", "machine learning", "ai", "ml", "אנליסט"],
    "devops": ["devops", "sre", "platform", "cloud", "kubernetes", "aws"],
    "qa": ["qa", "quality", "automation", "tester", "בדיקות", "בודק"],
    "product": ["product", "owner", "מוצר"],
    "design": ["designer", "ui", "ux", "עיצוב"],
    "marketing": ["marketing", "growth", "seo", "ppc", "שיווק"],
    "sales": ["sales", "account executive", "sdr", "bdr", "מכירות"],
    "support": ["support", "customer success", "service", "תמיכה"],
    "hr": ["hr", "recruiter", "talent", "people", "גיוס"],
    "legal": ["legal", "lawyer", "counsel", "משפט"],
    "security": ["security", "cyber", "soc", "siem", "סייבר"],
}


class TechMapAdapter(IsraelSourceAdapter):
    source = "techmap"
    base_url = TECHMAP_BASE_URL
    default_apply_method = "external_url"
    max_pages = 1

    _cache: Dict[str, List[IsraeliJob]] = {}

    def build_search_url(self, query: SearchQuery, page: int = 1) -> str:
        category = self._category_candidates(query)[0]
        return f"{self.base_url}/jobs/{category}.csv"

    def search(self, query: SearchQuery) -> List[IsraeliJob]:
        jobs: List[IsraeliJob] = []
        seen: set = set()
        categories = self._category_candidates(query)

        with ThreadPoolExecutor(max_workers=min(8, len(categories))) as executor:
            futures = {executor.submit(self._fetch_category_jobs, category): category for category in categories}
            for future in as_completed(futures):
                for job in future.result():
                    if not self._matches_query(job.title, query):
                        continue
                    key = (job.source, job.source_job_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append(job)
                    if len(jobs) >= query.limit:
                        return jobs
        return jobs[: query.limit]

    def parse_jobs(self, payload: str, query: SearchQuery) -> List[IsraeliJob]:
        return list(self._jobs_from_csv(payload, category="techmap"))

    def sample_job(self) -> IsraeliJob:
        return self.make_job(
            source_job_id="techmap-sample",
            title="Backend Developer",
            company="Example TechMap Company",
            location="תל אביב-יפו",
            description="TechMap sample job used to validate the adapter contract.",
            apply_url="https://example.com/jobs/backend",
        )

    def _fetch_category_jobs(self, category: str) -> List[IsraeliJob]:
        if category in self._cache:
            return self._cache[category]

        payload = self.fetch(f"{self.base_url}/jobs/{category}.csv", timeout=12)
        jobs = list(self._jobs_from_csv(payload, category=category))
        self._cache[category] = jobs
        return jobs

    def _jobs_from_csv(self, payload: str, category: str) -> Iterable[IsraeliJob]:
        reader = csv.DictReader(io.StringIO((payload or "").lstrip("\ufeff")))
        for row in reader:
            apply_url = self._clean_url(row.get("url", ""))
            title = row.get("title", "").strip()
            company = row.get("company", "").strip()
            if not apply_url or not title:
                continue

            city = row.get("city", "").strip() or "Israel"
            industry = row.get("category", "").strip()
            level = row.get("level", "").strip()
            updated = self._parse_date(row.get("updated", ""))
            description = " | ".join(
                part
                for part in [
                    f"TechMap category: {category}",
                    f"Industry: {industry}" if industry else "",
                    f"Level: {level}" if level else "",
                    f"Company size: {row.get('size', '').strip()}" if row.get("size", "").strip() else "",
                ]
                if part
            )

            yield self.make_job(
                source_job_id=self.stable_id(apply_url),
                title=title,
                company=company or "Unknown",
                location=city,
                description=description,
                apply_url=apply_url,
                posted_at=updated,
            )

    def _category_candidates(self, query: Optional[SearchQuery]) -> List[str]:
        keyword_text = " ".join((query.keywords if query else []) or []).lower()
        matched = [
            category
            for category, hints in _CATEGORY_HINTS.items()
            if any(hint.lower() in keyword_text for hint in hints)
        ]
        if matched:
            return [category for category in TECHMAP_CATEGORIES if category in set(matched)]
        return TECHMAP_CATEGORIES

    def _matches_query(self, title: str, query: Optional[SearchQuery]) -> bool:
        keywords = (query.keywords if query else []) or []
        if not keywords:
            return True
        title_text = self.clean_text(title).lower().replace("-", " ")
        title_tokens = set(self._tokens(title_text))
        return any(self._keyword_matches(keyword, title_text, title_tokens) for keyword in keywords)

    def _keyword_matches(self, keyword: str, title_text: str, title_tokens: set) -> bool:
        keyword_text = self.clean_text(keyword).lower().replace("-", " ")
        if not keyword_text:
            return True

        required_groups = self._expanded_keyword_groups(keyword_text)
        if required_groups:
            return all(any(term in title_text for term in group) for group in required_groups)

        tokens = [token for token in self._tokens(keyword_text) if token not in {"job", "jobs", "role", "remote", "hybrid", "משרה", "עבודה"}]
        return bool(tokens) and all(token in title_tokens for token in tokens)

    @staticmethod
    def _tokens(value: str) -> List[str]:
        import re

        return re.findall(r"[a-z0-9+#.\u0590-\u05ff]+", value or "")

    def _expanded_keyword_groups(self, keyword_text: str) -> List[List[str]]:
        groups: List[List[str]] = []
        if ("data" in keyword_text and "analyst" in keyword_text) or "אנליסט נתונים" in keyword_text:
            groups.append(["data analyst", "bi analyst", "business intelligence analyst", "אנליסט נתונים"])
            return groups
        if any(term in keyword_text for term in ["כלכל", "economist", "economic"]):
            groups.append(["economist", "economic", "financial analyst", "fp&a analyst", "finance analyst", "כלכל"])
        if any(term in keyword_text for term in ["מתחיל", "junior", "entry", "entry level", "ללא ניסיון"]):
            groups.append(["junior", "entry", "assistant", "associate", "student", "graduate", "מתחיל", "סטודנט"])
        if any(term in keyword_text for term in ["analyst", "אנליסט"]):
            groups.append(["analyst", "אנליסט"])
        if "backend" in keyword_text:
            groups.append(["backend", "back end", "server"])
        if "frontend" in keyword_text or "front end" in keyword_text:
            groups.append(["frontend", "front end", "react", "web"])
        if "full stack" in keyword_text or "fullstack" in keyword_text:
            groups.append(["full stack", "fullstack", "full-stack"])
        if "devops" in keyword_text:
            groups.append(["devops", "sre", "platform engineer"])
        if "qa" in keyword_text or "בודק" in keyword_text:
            groups.append(["qa", "quality", "automation", "tester", "בדיקות", "בודק"])
        return groups

    @staticmethod
    def _parse_date(raw: str) -> Optional[datetime]:
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _clean_url(raw: str) -> str:
        raw = (raw or "").strip()
        if not raw:
            return ""
        parsed = urlparse(raw)
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.startswith("utm_")
        ]
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(query), ""))
