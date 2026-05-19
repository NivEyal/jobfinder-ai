import json
import os
import re
from typing import Any, Dict
from urllib import error, request

from src.job import Job
from src.matching.models import MatchResult, verdict_for_score
from src.matching.rule_based_matcher import RuleBasedMatcher


RESPONSES_API_URL = "https://api.openai.com/v1/responses"


class OpenAIMatcher:
    """OpenAI-powered matcher with a deterministic fallback."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        matching = self.config.get("matching", {})
        self.model = matching.get("model", "gpt-5-mini")
        self.api_key_env = matching.get("api_key_env", "OPENAI_API_KEY")
        self.max_description_chars = int(matching.get("max_description_chars", 4000))
        self.timeout_seconds = int(matching.get("timeout_seconds", 30))
        self.rule_based = RuleBasedMatcher(self.config)

    def match(self, job: Job, resume_text: str) -> MatchResult:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            return self.rule_based.match(job, resume_text)

        try:
            raw = self._call_openai(job, resume_text, api_key)
            return self._parse_result(raw, job)
        except Exception:
            return self.rule_based.match(job, resume_text)

    def _call_openai(self, job: Job, resume_text: str, api_key: str) -> str:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are a recruiting matcher for Israeli and worldwide jobs. "
                        "Score how well the candidate resume and preferences match the job. "
                        "Return only JSON with keys: score, verdict, confidence, reasons, "
                        "matched_keywords, missing_requirements. Verdict must be one of "
                        "strong_match, possible_match, weak_match, not_recommended."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "job": job.to_dict() | {"description": (job.description or "")[: self.max_description_chars]},
                            "resume": resume_text[:8000],
                            "preferences": {
                                "search": self.config.get("search", {}),
                                "filters": self.config.get("filters", {}),
                                "matching": self.config.get("matching", {}),
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            RESPONSES_API_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI matching request failed: HTTP {exc.code}: {details}") from exc
        return extract_output_text(response_data)

    def _parse_result(self, raw_text: str, job: Job) -> MatchResult:
        data = json.loads(strip_json_fence(raw_text))
        score = int(data.get("score", 0))
        matching = self.config.get("matching", {})
        strong_threshold = int(matching.get("strong_match_score", 80))
        possible_threshold = int(matching.get("possible_match_score", 60))
        verdict = verdict_for_score(score, strong_threshold, possible_threshold)
        return MatchResult(
            job_fingerprint=job.fingerprint,
            source=job.source,
            source_job_id=job.source_job_id,
            score=score,
            verdict=verdict,
            confidence=float(data.get("confidence", 0.75)),
            reasons=list(data.get("reasons", []))[:8],
            matched_keywords=list(data.get("matched_keywords", []))[:20],
            missing_requirements=list(data.get("missing_requirements", []))[:20],
            model=self.model,
            used_openai=True,
        )


def extract_output_text(response_data: Dict[str, Any]) -> str:
    if isinstance(response_data.get("output_text"), str):
        return response_data["output_text"]
    chunks = []
    for item in response_data.get("output", []):
        for content in item.get("content", []):
            if isinstance(content.get("text"), str):
                chunks.append(content["text"])
    if chunks:
        return "\n".join(chunks)
    raise ValueError("OpenAI response did not contain output text")


def strip_json_fence(text: str) -> str:
    text = (text or "").strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    return match.group(1).strip() if match else text
