from typing import Any, Dict, Iterable, List

from src.job import Job
from src.matching.models import MatchResult
from src.matching.openai_matcher import OpenAIMatcher
from src.matching.rule_based_matcher import RuleBasedMatcher


class JobMatcher:
    """Chooses OpenAI matching when configured, with rule-based fallback."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        matching = self.config.get("matching", {})
        provider = matching.get("provider", "openai")
        self.provider = provider
        self.minimum_score = int(matching.get("minimum_score", 65))
        self.matcher = OpenAIMatcher(self.config) if provider == "openai" else RuleBasedMatcher(self.config)

    def match(self, job: Job, resume_text: str) -> MatchResult:
        return self.matcher.match(job, resume_text)

    def match_many(self, jobs: Iterable[Job], resume_text: str) -> List[MatchResult]:
        results = [self.match(job, resume_text) for job in jobs]
        return sorted(results, key=lambda result: result.score, reverse=True)

    def recommended(self, jobs: Iterable[Job], resume_text: str) -> List[MatchResult]:
        return [result for result in self.match_many(jobs, resume_text) if result.score >= self.minimum_score]
