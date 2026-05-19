import re
from typing import Any, Dict, Iterable, List, Set

from src.job import Job
from src.matching.models import MatchResult, verdict_for_score


TOKEN_RE = re.compile(r"[\w\u0590-\u05ff+#.-]+", re.UNICODE)


class RuleBasedMatcher:
    """Deterministic fallback matcher that works without external services."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        matching = self.config.get("matching", {})
        self.strong_threshold = int(matching.get("strong_match_score", 80))
        self.possible_threshold = int(matching.get("possible_match_score", 60))

    def match(self, job: Job, resume_text: str) -> MatchResult:
        resume_tokens = tokenize(resume_text)
        job_text = build_job_text(job)
        job_tokens = tokenize(job_text)

        search = self.config.get("search", {})
        filters = self.config.get("filters", {})
        include = filters.get("include", {})
        exclude = filters.get("exclude", {})

        preferred_keywords = expand_config_keywords(
            search.get("keywords", []),
            search.get("keyword_aliases", {}),
            include.get("nice_to_have_keywords", []),
        )
        must_have = include.get("must_have_keywords", [])
        excluded_keywords = {item.lower() for item in exclude.get("keywords", [])}

        score = 35
        reasons: List[str] = []
        matched_keywords: List[str] = []
        missing_requirements: List[str] = []

        matched_config_keywords = [
            keyword for keyword in preferred_keywords if keyword_matches(keyword, job_text, job_tokens, resume_tokens)
        ]
        if matched_config_keywords:
            keyword_points = min(25, 8 + len(matched_config_keywords) * 4)
            score += keyword_points
            matched_keywords.extend(matched_config_keywords[:12])
            reasons.append(f"Matched preferred keywords: {', '.join(matched_config_keywords[:5])}")

        resume_overlap = job_tokens.intersection(resume_tokens)
        if resume_overlap:
            overlap_points = min(20, len(resume_overlap) * 2)
            score += overlap_points
            reasons.append(f"Resume overlaps with {len(resume_overlap)} job terms")

        for keyword in must_have:
            if not keyword_matches(keyword, job_text, job_tokens, resume_tokens):
                score -= 18
                missing_requirements.append(keyword)

        if job.remote_type and job.remote_type in set(search.get("remote_types", [])):
            score += 8
            reasons.append(f"Remote type is allowed: {job.remote_type}")
        elif job.remote_type:
            score -= 6
            missing_requirements.append(f"remote_type:{job.remote_type}")

        if job.employment_type and job.employment_type in set(search.get("employment_types", [])):
            score += 7
            reasons.append(f"Employment type is allowed: {job.employment_type}")
        elif job.employment_type:
            score -= 6
            missing_requirements.append(f"employment_type:{job.employment_type}")

        if job.seniority and job.seniority in set(search.get("seniority", [])):
            score += 7
            reasons.append(f"Seniority is allowed: {job.seniority}")
        elif job.seniority:
            score -= 8
            missing_requirements.append(f"seniority:{job.seniority}")

        years = search.get("years_experience", {})
        if job.years_experience is not None and years:
            if years.get("min", 0) <= job.years_experience <= years.get("max", 99):
                score += 6
                reasons.append("Years of experience are inside the preferred range")
            else:
                score -= 8
                missing_requirements.append(f"years_experience:{job.years_experience}")

        if any(keyword in job_text.lower() for keyword in excluded_keywords):
            score -= 35
            missing_requirements.append("excluded_keyword")

        score = max(0, min(100, score))
        if not reasons:
            reasons.append("No strong signal found; scored with fallback rules")

        return MatchResult(
            job_fingerprint=job.fingerprint,
            source=job.source,
            source_job_id=job.source_job_id,
            score=score,
            verdict=verdict_for_score(score, self.strong_threshold, self.possible_threshold),
            confidence=0.55 if score >= self.possible_threshold else 0.4,
            reasons=reasons[:6],
            matched_keywords=unique(matched_keywords),
            missing_requirements=unique(missing_requirements),
            model="rule_based",
            used_openai=False,
        )


def build_job_text(job: Job) -> str:
    return " ".join(
        value
        for value in [
            job.title,
            job.company,
            job.location,
            job.region,
            job.remote_type,
            job.employment_type,
            job.seniority,
            job.description,
        ]
        if value
    )


def tokenize(text: str) -> Set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text or "") if len(token) > 1}


def keyword_matches(keyword: str, job_text: str, job_tokens: Set[str], resume_tokens: Set[str]) -> bool:
    lowered = (keyword or "").lower().strip()
    if not lowered:
        return False
    if lowered in job_text.lower():
        return True
    keyword_tokens = tokenize(lowered)
    return bool(keyword_tokens and keyword_tokens.issubset(job_tokens.union(resume_tokens)))


def expand_config_keywords(keywords: Iterable[str], aliases: Dict[str, List[str]], extras: Iterable[str]) -> List[str]:
    expanded: List[str] = []
    for keyword in keywords:
        expanded.append(keyword)
        expanded.extend(aliases.get(keyword, []))
    expanded.extend(extras)
    return unique(expanded)


def unique(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))
