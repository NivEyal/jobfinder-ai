import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List
from unittest.mock import MagicMock, patch

from src.israel_sources.base import IsraelSourceAdapter, SearchQuery
from src.israel_sources.models import IsraeliJob
from src.israel_sources.registry import search_all_sources
from src.matching.rule_based_matcher import RuleBasedMatcher


SAMPLE_QUERY = SearchQuery(keywords=["Backend Developer"], locations=["Tel Aviv"], limit=5)


def _sample_config():
    return {
        "search": {
            "keywords": ["Backend Developer"],
            "keyword_aliases": {"Backend Developer": ["Python Developer"]},
            "remote_types": ["remote", "hybrid", "onsite"],
            "employment_types": ["full_time"],
            "seniority": ["entry", "junior", "mid", "senior"],
            "years_experience": {"min": 0, "max": 8},
        },
        "filters": {
            "include": {"must_have_keywords": [], "nice_to_have_keywords": ["Python", "API"]},
            "exclude": {"keywords": []},
        },
        "matching": {
            "provider": "rule_based",
            "minimum_score": 60,
            "strong_match_score": 80,
            "possible_match_score": 60,
        },
    }


def _sample_job():
    from src.israel_sources.models import IsraeliJob
    israeli = IsraeliJob(
        source="drushim",
        source_job_id="perf-001",
        title="Backend Developer",
        company="Tech Corp",
        location="Tel Aviv hybrid",
        description="Python Django REST API full time 3 years experience.",
        apply_url="https://example.com/apply",
        apply_email=None,
        apply_method="external_url",
        posted_at=None,
    )
    return israeli.to_job(normalized_output_language="en")


def _median_ms(times_ns):
    return statistics.median(times_ns) / 1_000_000


def _calls_per_second(times_ns):
    median_s = statistics.median(times_ns) / 1_000_000_000
    return 1.0 / median_s if median_s > 0 else float("inf")


def test_rule_based_matcher_calls_per_second():
    iterations = 1000
    matcher = RuleBasedMatcher(_sample_config())
    job = _sample_job()
    resume_text = "Python Django REST API backend developer cloud AWS microservices"
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        matcher.match(job, resume_text)
        times.append(time.perf_counter_ns() - t0)

    median = _median_ms(times)
    cps = _calls_per_second(times)
    assert median < 10, f"RuleBasedMatcher.match() too slow: {median:.3f}ms (expected <10ms)"
    assert cps > 100, f"RuleBasedMatcher.match() too slow: {cps:.0f} calls/sec (expected >100)"


def test_search_all_sources_with_mocked_adapters():
    class FastAdapter(IsraelSourceAdapter):
        source = "fast_mock"
        base_url = "https://mock.example.com"

        def build_search_url(self, query, page=1):
            return f"{self.base_url}/jobs?page={page}"

        def parse_jobs(self, payload, query):
            return []

        def search(self, query):
            return []

    fake_adapters = [FastAdapter() for _ in range(6)]
    iterations = 20
    times = []
    with patch("src.israel_sources.registry.get_all_adapters", return_value=fake_adapters):
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            search_all_sources(SAMPLE_QUERY)
            times.append(time.perf_counter_ns() - t0)

    median = _median_ms(times)
    assert median < 200, f"search_all_sources() too slow: {median:.3f}ms (expected <200ms)"


def test_parallel_vs_sequential():
    delay_s = 0.05
    num_adapters = 12

    class SlowAdapter(IsraelSourceAdapter):
        source = "slow_mock"
        base_url = "https://slow.example.com"

        def build_search_url(self, query, page=1):
            return f"{self.base_url}/jobs?page={page}"

        def parse_jobs(self, payload, query):
            return []

        def search(self, query):
            time.sleep(delay_s)
            return []

    adapters = [SlowAdapter() for _ in range(num_adapters)]

    seq_start = time.perf_counter()
    for adapter in adapters:
        adapter.search(SAMPLE_QUERY)
    seq_elapsed = time.perf_counter() - seq_start

    par_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_adapters) as executor:
        futures = [executor.submit(adapter.search, SAMPLE_QUERY) for adapter in adapters]
        for future in futures:
            future.result()
    par_elapsed = time.perf_counter() - par_start

    expected_seq_floor = delay_s * num_adapters * 0.8
    assert seq_elapsed >= expected_seq_floor, (
        f"Sequential too fast: {seq_elapsed:.3f}s (expected >={expected_seq_floor:.3f}s)"
    )
    assert par_elapsed < delay_s * 3, (
        f"Parallel too slow: {par_elapsed:.3f}s (expected <{delay_s * 3:.3f}s)"
    )
    speedup = seq_elapsed / par_elapsed
    assert speedup >= 4, (
        f"Speedup too low: {speedup:.1f}x (seq={seq_elapsed:.3f}s, par={par_elapsed:.3f}s, expected >=4x)"
    )
