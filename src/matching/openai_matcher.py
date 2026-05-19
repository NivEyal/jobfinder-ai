import json
import os
import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from src.job import Job
from src.matching.models import MatchResult, verdict_for_score
from src.matching.rule_based_matcher import RuleBasedMatcher

CHAT_API_URL = "https://api.openai.com/v1/chat/completions"
_BATCH_SIZE = 8
_MAX_DESC_CHARS = 600
_TIMEOUT = 15
_MAX_RETRIES = 3
_CACHE_SIZE = 512


class _LRUCache:
    def __init__(self, maxsize: int):
        self._d: OrderedDict = OrderedDict()
        self._max = maxsize

    def get(self, key: str) -> Optional[MatchResult]:
        if key in self._d:
            self._d.move_to_end(key)
            return self._d[key]
        return None

    def put(self, key: str, value: MatchResult) -> None:
        self._d[key] = value
        self._d.move_to_end(key)
        if len(self._d) > self._max:
            self._d.popitem(last=False)


class OpenAIMatcher:
    """OpenAI-powered job matcher using Chat Completions with batch support and LRU cache."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        matching = self.config.get("matching", {})
        self.model = matching.get("model", "gpt-4o-mini")
        self.api_key_env = matching.get("api_key_env", "OPENAI_API_KEY")
        self.timeout = int(matching.get("timeout_seconds", _TIMEOUT))
        matching_config = self.config.get("matching", {})
        self.strong_threshold   = int(matching_config.get("strong_match_score",   80))
        self.possible_threshold = int(matching_config.get("possible_match_score", 60))
        self.rule_based = RuleBasedMatcher(self.config)
        self._cache = _LRUCache(_CACHE_SIZE)

    def _api_key(self) -> Optional[str]:
        return os.getenv(self.api_key_env)

    def match(self, job: Job, resume_text: str) -> MatchResult:
        cached = self._cache.get(job.fingerprint)
        if cached:
            return cached
        api_key = self._api_key()
        if not api_key:
            return self.rule_based.match(job, resume_text)
        try:
            results = self._batch_call([job], resume_text, api_key)
            result = results[0] if results else self.rule_based.match(job, resume_text)
            self._cache.put(job.fingerprint, result)
            return result
        except Exception:
            fallback = self.rule_based.match(job, resume_text)
            return fallback

    def match_batch(self, jobs: List[Job], resume_text: str) -> List[MatchResult]:
        if not jobs:
            return []
        api_key = self._api_key()
        if not api_key:
            return [self.rule_based.match(j, resume_text) for j in jobs]

        results: Dict[str, MatchResult] = {}
        uncached: List[Job] = []
        for job in jobs:
            cached = self._cache.get(job.fingerprint)
            if cached:
                results[job.fingerprint] = cached
            else:
                uncached.append(job)

        for i in range(0, len(uncached), _BATCH_SIZE):
            chunk = uncached[i:i + _BATCH_SIZE]
            try:
                chunk_results = self._batch_call(chunk, resume_text, api_key)
                for job, result in zip(chunk, chunk_results):
                    self._cache.put(job.fingerprint, result)
                    results[job.fingerprint] = result
            except Exception:
                for job in chunk:
                    results[job.fingerprint] = self.rule_based.match(job, resume_text)

        return [results.get(job.fingerprint, self.rule_based.match(job, resume_text)) for job in jobs]

    def _batch_call(self, jobs: List[Job], resume_text: str, api_key: str) -> List[MatchResult]:
        job_list = [
            {
                "index": i,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "description": (job.description or "")[:_MAX_DESC_CHARS],
                "remote_type": job.remote_type,
                "seniority": job.seniority,
                "employment_type": job.employment_type,
            }
            for i, job in enumerate(jobs)
        ]
        system_prompt = (
            "You are an expert Israeli job market recruiter and ATS specialist. "
            "You score how well a candidate's resume and preferences match each job. "
            f"Return a JSON array of exactly {len(jobs)} objects, one per job, in the same order. "
            "Each object must have these keys:\n"
            "  score (int 0-100), verdict (strong_match|possible_match|weak_match|not_recommended),\n"
            "  confidence (float 0-1), reasons (array of strings, max 5),\n"
            "  matched_keywords (array of strings, max 10),\n"
            "  missing_requirements (array of strings, max 8).\n"
            "Be strict but fair. Consider Israeli job market norms. Respond with JSON only, no prose."
        )
        user_content = json.dumps(
            {
                "jobs": job_list,
                "resume": resume_text[:6000],
                "preferences": {
                    "search":   self.config.get("search", {}),
                    "filters":  self.config.get("filters", {}),
                    "matching": self.config.get("matching", {}),
                },
            },
            ensure_ascii=False,
        )
        raw = self._call_chat(system_prompt, user_content, api_key)
        return self._parse_batch(raw, jobs)

    def _call_chat(self, system: str, user: str, api_key: str) -> str:
        import urllib.request as urlreq
        import urllib.error as urlerr

        payload = json.dumps(
            {
                "model": self.model,
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")

        for attempt in range(_MAX_RETRIES):
            req = urlreq.Request(
                CHAT_API_URL,
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urlreq.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]
            except urlerr.HTTPError as exc:
                if exc.code == 429 and attempt < _MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise

        raise RuntimeError("OpenAI: max retries reached")

    def _parse_batch(self, raw: str, jobs: List[Job]) -> List[MatchResult]:
        raw = _strip_fence(raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return [self.rule_based.match(j, "") for j in jobs]

        # Accept {"results": [...]} or a bare array
        if isinstance(data, dict):
            items = data.get("results") or data.get("jobs") or list(data.values())
            if items and isinstance(items[0], list):
                items = items[0]
        elif isinstance(data, list):
            items = data
        else:
            return [self.rule_based.match(j, "") for j in jobs]

        results = []
        for i, job in enumerate(jobs):
            item = items[i] if i < len(items) else {}
            if not isinstance(item, dict):
                item = {}
            try:
                score = max(0, min(100, int(item.get("score", 0))))
                results.append(MatchResult(
                    job_fingerprint=job.fingerprint,
                    source=job.source,
                    source_job_id=job.source_job_id,
                    score=score,
                    verdict=verdict_for_score(score, self.strong_threshold, self.possible_threshold),
                    confidence=float(item.get("confidence", 0.75)),
                    reasons=list(item.get("reasons", []))[:8],
                    matched_keywords=list(item.get("matched_keywords", []))[:20],
                    missing_requirements=list(item.get("missing_requirements", []))[:20],
                    model=self.model,
                    used_openai=True,
                ))
            except Exception:
                results.append(self.rule_based.match(job, ""))
        return results


def generate_ai_insights(
    matches: List[MatchResult],
    jobs: List[Job],
    resume_text: str,
    config: Dict[str, Any],
) -> List[str]:
    """Ask OpenAI to generate personalized career insights in Hebrew."""
    api_key_env = config.get("matching", {}).get("api_key_env", "OPENAI_API_KEY")
    api_key = os.getenv(api_key_env)
    if not api_key:
        return _fallback_insights(matches)

    model = config.get("matching", {}).get("model", "gpt-4o-mini")
    top = sorted(matches, key=lambda m: m.score, reverse=True)[:5]

    top_jobs_summary = [
        {
            "title": next((j.title for j in jobs if j.fingerprint == m.job_fingerprint), ""),
            "company": next((j.company for j in jobs if j.fingerprint == m.job_fingerprint), ""),
            "score": m.score,
            "matched": m.matched_keywords[:5],
            "missing": m.missing_requirements[:5],
            "reasons": m.reasons[:3],
        }
        for m in top
    ]
    search_keywords = config.get("search", {}).get("keywords", [])

    system = (
        "You are a senior Israeli job market career coach and ATS expert. "
        "Based on the candidate's top job matches, provide 4 short, specific, actionable insights in Hebrew. "
        "Each insight must be 1 sentence. Focus on: resume improvements, timing, keyword gaps, and market fit. "
        "Return a JSON object: {\"insights\": [\"...\", \"...\", \"...\", \"...\"]}. "
        "Only JSON, no prose."
    )
    user = json.dumps(
        {
            "resume_snippet": resume_text[:2000],
            "search_keywords": search_keywords,
            "top_matches": top_jobs_summary,
            "jobs_analyzed": len(matches),
            "top_score": top[0].score if top else 0,
        },
        ensure_ascii=False,
    )

    import urllib.request as urlreq
    import urllib.error as urlerr

    payload = json.dumps(
        {
            "model": model,
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")

    try:
        req = urlreq.Request(
            CHAT_API_URL,
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlreq.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(_strip_fence(content))
            return list(parsed.get("insights", []))[:6]
    except Exception:
        return _fallback_insights(matches)


def _fallback_insights(matches: List[MatchResult]) -> List[str]:
    top = sorted(matches, key=lambda m: m.score, reverse=True)[:5]
    openai_used = sum(1 for m in matches if m.used_openai)
    missing = list(dict.fromkeys(kw for m in top for kw in m.missing_requirements[:3]))
    reasons = list(dict.fromkeys(r for m in top for r in m.reasons[:3]))
    return [
        f"OpenAI ניתח {openai_used} מתוך {len(matches)} משרות; שאר המשרות דורגו עם fallback מקומי.",
        f"ציון ההתאמה הגבוה ביותר הוא {top[0].score if top else 0}.",
        f"דרישות שחוזרות במשרות מובילות: {', '.join(missing[:5]) or 'אין מספיק נתונים עדיין'}.",
        f"סיבות התאמה בולטות: {', '.join(reasons[:5]) or 'אין מספיק נתונים עדיין'}.",
    ]


def _strip_fence(text: str) -> str:
    text = (text or "").strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    return m.group(1).strip() if m else text


# Keep backward-compat helpers
def extract_output_text(response_data: Dict[str, Any]) -> str:
    if isinstance(response_data.get("output_text"), str):
        return response_data["output_text"]
    chunks = []
    for item in response_data.get("output", []):
        for content in item.get("content", []):
            if isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks) if chunks else ""


def strip_json_fence(text: str) -> str:
    return _strip_fence(text)
