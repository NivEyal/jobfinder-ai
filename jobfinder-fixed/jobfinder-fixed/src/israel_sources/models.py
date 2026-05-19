from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from src.job import Job


@dataclass(frozen=True)
class IsraeliJob:
    source: str
    source_job_id: str
    title: str
    company: str
    location: str
    description: str
    apply_url: str
    apply_email: Optional[str]
    apply_method: str
    posted_at: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["posted_at"] = self.posted_at.isoformat() if self.posted_at else None
        return data

    def to_job(self, normalized_output_language: str = "he") -> Job:
        return Job.from_israeli_job(self, normalized_output_language=normalized_output_language)
