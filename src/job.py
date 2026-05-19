import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.israel_normalization import (
    normalize_company,
    normalize_employment_type,
    normalize_location,
    normalize_region,
    normalize_remote_type,
    normalize_salary,
    normalize_seniority,
    normalize_title,
    normalize_years_experience,
)
from src.logging import logger


REMOTE_TYPES = {"remote", "hybrid", "onsite", ""}
EMPLOYMENT_TYPES = {"full_time", "part_time", "contract", "temporary", "internship", ""}
LANGUAGES = {"he", "en", "mixed", ""}
NORMALIZED_OUTPUT_LANGUAGES = {"he", "en"}
STATUSES = {"new", "seen", "applied", "skipped", "expired", "closed", ""}


@dataclass
class Job:
    source: str = ""
    source_job_id: str = ""
    canonical_url: str = ""
    company: str = ""
    title: str = ""
    location: str = ""
    region: str = ""
    remote_type: str = ""
    employment_type: str = ""
    seniority: str = ""
    years_experience: Optional[float] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    language: str = ""
    apply_email: Optional[str] = None
    apply_url: str = ""
    fingerprint: str = ""
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "new"
    description: str = ""
    normalized_output_language: str = "he"

    # Existing application-output fields kept for backward compatibility.
    summarize_job_description: str = ""
    recruiter_link: str = ""
    resume_path: str = ""
    cover_letter_path: str = ""

    def __post_init__(self):
        self.normalized_output_language = self._validate_choice(
            "normalized_output_language", self.normalized_output_language, NORMALIZED_OUTPUT_LANGUAGES
        )
        source_text = f"{self.title} {self.location} {self.description}"

        self.company = normalize_company(self.company, self.normalized_output_language)
        self.title = normalize_title(self.title, self.normalized_output_language)
        self.location = normalize_location(self.location, self.normalized_output_language)
        self.region = self.region or normalize_region(self.location, "en")
        self.remote_type = self._validate_choice(
            "remote_type", self.remote_type or normalize_remote_type(source_text), REMOTE_TYPES
        )
        self.employment_type = self._validate_choice(
            "employment_type", self.employment_type or normalize_employment_type(source_text), EMPLOYMENT_TYPES
        )
        self.seniority = self.seniority or normalize_seniority(source_text)
        self.years_experience = (
            self.years_experience if self.years_experience is not None else normalize_years_experience(source_text)
        )
        salary_min, salary_max = normalize_salary(source_text)
        self.salary_min = self.salary_min if self.salary_min is not None else salary_min
        self.salary_max = self.salary_max if self.salary_max is not None else salary_max
        self.language = self._validate_choice("language", self.language or self.detect_language(), LANGUAGES)
        self.status = self._validate_choice("status", self.status, STATUSES) or "new"
        self.canonical_url = self.canonical_url or self.apply_url
        self.apply_url = self.apply_url or self.canonical_url
        self.fingerprint = self.fingerprint or self.build_fingerprint()

    @property
    def id(self) -> str:
        return self.fingerprint

    @property
    def role(self) -> str:
        return self.title

    @role.setter
    def role(self, value: str):
        self.title = normalize_title(value, self.normalized_output_language)
        self.fingerprint = self.build_fingerprint()

    @property
    def link(self) -> str:
        return self.canonical_url or self.apply_url

    @link.setter
    def link(self, value: str):
        self.canonical_url = value
        self.apply_url = self.apply_url or value
        self.fingerprint = self.build_fingerprint()

    @property
    def apply_method(self) -> str:
        if self.apply_email:
            return "email"
        if self.apply_url:
            return "external_url"
        return ""

    @classmethod
    def from_israeli_job(
        cls,
        israeli_job: Any,
        seen_at: Optional[datetime] = None,
        normalized_output_language: str = "he",
    ) -> "Job":
        seen_at = seen_at or datetime.now(timezone.utc)
        description = getattr(israeli_job, "description", "") or ""
        title = getattr(israeli_job, "title", "") or ""
        location = getattr(israeli_job, "location", "") or ""
        source_text = f"{title} {location} {description}"
        salary_min, salary_max = normalize_salary(source_text)
        return cls(
            source=getattr(israeli_job, "source", ""),
            source_job_id=getattr(israeli_job, "source_job_id", ""),
            canonical_url=getattr(israeli_job, "apply_url", ""),
            company=getattr(israeli_job, "company", ""),
            title=title,
            location=location,
            region=normalize_region(location, "en"),
            remote_type=normalize_remote_type(source_text),
            employment_type=normalize_employment_type(source_text),
            seniority=normalize_seniority(source_text),
            years_experience=normalize_years_experience(source_text),
            salary_min=salary_min,
            salary_max=salary_max,
            language=cls.detect_language_for_text(source_text),
            apply_email=getattr(israeli_job, "apply_email", None),
            apply_url=getattr(israeli_job, "apply_url", ""),
            first_seen_at=seen_at,
            last_seen_at=seen_at,
            status="new",
            description=description,
            normalized_output_language=normalized_output_language,
        )

    def mark_seen(self, seen_at: Optional[datetime] = None):
        self.last_seen_at = seen_at or datetime.now(timezone.utc)
        if self.status == "new":
            self.status = "seen"

    def build_fingerprint(self) -> str:
        parts = [
            self.source,
            self.source_job_id,
            self.company,
            self.title,
            self.canonical_url or self.apply_url,
        ]
        raw = "|".join(part.strip().lower() for part in parts if part)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["first_seen_at"] = self.first_seen_at.isoformat() if self.first_seen_at else None
        data["last_seen_at"] = self.last_seen_at.isoformat() if self.last_seen_at else None
        return data

    def formatted_job_information(self):
        logger.debug(f"Formatting job information for job: {self.title} at {self.company}")
        job_information = f"""
        # Job Description
        ## Job Information
        - Source: {self.source or 'Not available'}
        - Source Job ID: {self.source_job_id or 'Not available'}
        - Position: {self.title}
        - At: {self.company}
        - Location: {self.location}
        - Region: {self.region or 'Not available'}
        - Remote Type: {self.remote_type or 'Not available'}
        - Employment Type: {self.employment_type or 'Not available'}
        - Seniority: {self.seniority or 'Not available'}
        - Years Experience: {self.years_experience if self.years_experience is not None else 'Not available'}
        - Salary: {self.salary_min or 'Not available'} - {self.salary_max or 'Not available'}
        - Language: {self.language or 'Not available'}
        - Normalized Output Language: {self.normalized_output_language}
        - Apply URL: {self.apply_url or 'Not available'}
        - Apply Email: {self.apply_email or 'Not available'}
        - Status: {self.status}

        ## Description
        {self.description or 'No description provided.'}
        """
        formatted_information = job_information.strip()
        logger.debug(f"Formatted job information: {formatted_information}")
        return formatted_information

    def detect_language(self) -> str:
        return self.detect_language_for_text(f"{self.title} {self.description}")

    @staticmethod
    def detect_language_for_text(text: str) -> str:
        hebrew_chars = len(re.findall(r"[\u0590-\u05ff]", text or ""))
        latin_chars = len(re.findall(r"[A-Za-z]", text or ""))
        if hebrew_chars and latin_chars:
            return "mixed"
        if hebrew_chars:
            return "he"
        if latin_chars:
            return "en"
        return ""

    @staticmethod
    def infer_remote_type(text: str) -> str:
        return normalize_remote_type(text)

    @staticmethod
    def infer_employment_type(text: str) -> str:
        return normalize_employment_type(text)

    @staticmethod
    def infer_seniority(text: str) -> str:
        return normalize_seniority(text)

    @staticmethod
    def infer_years_experience(text: str) -> Optional[float]:
        return normalize_years_experience(text)

    @staticmethod
    def infer_salary(text: str) -> tuple[Optional[int], Optional[int]]:
        return normalize_salary(text)

    @staticmethod
    def infer_region(location: str) -> str:
        return normalize_region(location, "en")

    @staticmethod
    def _validate_choice(field_name: str, value: str, allowed_values: set[str]) -> str:
        if value not in allowed_values:
            raise ValueError(f"Invalid {field_name}: {value}. Expected one of {sorted(allowed_values)}")
        return value
