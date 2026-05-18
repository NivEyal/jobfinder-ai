from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


VERDICTS = {"strong_match", "possible_match", "weak_match", "not_recommended"}


@dataclass
class MatchResult:
    job_fingerprint: str
    source: str
    source_job_id: str
    score: int
    verdict: str
    confidence: float
    reasons: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    missing_requirements: List[str] = field(default_factory=list)
    model: str = "rule_based"
    used_openai: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        self.score = max(0, min(100, int(round(self.score))))
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        if self.verdict not in VERDICTS:
            self.verdict = verdict_for_score(self.score)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


def verdict_for_score(score: int, strong_threshold: int = 80, possible_threshold: int = 60) -> str:
    if score >= strong_threshold:
        return "strong_match"
    if score >= possible_threshold:
        return "possible_match"
    if score >= 40:
        return "weak_match"
    return "not_recommended"
