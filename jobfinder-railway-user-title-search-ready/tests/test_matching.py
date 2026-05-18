from src.israel_sources.models import IsraeliJob
from src.matching.matcher import JobMatcher
from src.matching.models import MatchResult
from src.matching.openai_matcher import extract_output_text, strip_json_fence
from src.matching.rule_based_matcher import RuleBasedMatcher


def sample_config():
    return {
        "search": {
            "keywords": ["Backend Developer"],
            "keyword_aliases": {"Backend Developer": ["Python Developer"]},
            "remote_types": ["remote", "hybrid", "onsite"],
            "employment_types": ["full_time"],
            "seniority": ["entry", "junior", "mid", "senior"],
            "years_experience": {"min": 0, "max": 5},
        },
        "filters": {
            "include": {"must_have_keywords": [], "nice_to_have_keywords": ["Python", "API"]},
            "exclude": {"keywords": []},
        },
        "matching": {
            "provider": "rule_based",
            "minimum_score": 65,
            "strong_match_score": 80,
            "possible_match_score": 60,
        },
    }


def sample_job():
    return IsraeliJob(
        source="drushim",
        source_job_id="123",
        title="Backend Developer",
        company="Example",
        location="Tel Aviv hybrid",
        description="Python API role, full time, hybrid, 2 years experience.",
        apply_url="https://example.com/apply",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    ).to_job(normalized_output_language="en")


def test_rule_based_matcher_returns_serializable_result():
    result = RuleBasedMatcher(sample_config()).match(sample_job(), "Python backend APIs cloud")
    data = result.to_dict()

    assert isinstance(result, MatchResult)
    assert result.score >= 60
    assert result.verdict in {"strong_match", "possible_match", "weak_match", "not_recommended"}
    assert result.used_openai is False
    assert data["job_fingerprint"]
    assert data["created_at"]


def test_job_matcher_recommended_filters_by_score():
    matcher = JobMatcher(sample_config())
    results = matcher.recommended([sample_job()], "Python backend APIs cloud")

    assert len(results) == 1
    assert results[0].score >= 65


def test_openai_response_helpers_extract_json_text():
    response = {"output": [{"content": [{"type": "output_text", "text": "```json\n{\"score\": 70}\n```"}]}]}

    assert extract_output_text(response).startswith("```json")
    assert strip_json_fence(extract_output_text(response)) == '{"score": 70}'
