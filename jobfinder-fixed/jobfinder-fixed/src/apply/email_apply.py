import os
import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict

import httpx

from src.apply.application_guard import ApplicationGuard, ApplicationRequest, ApplicationResult


class EmailApplyEngine:
    """Applies by email when a job exposes an apply email address."""

    def __init__(self, config: Dict[str, Any] | None = None, guard: ApplicationGuard | None = None):
        self.config = config or {}
        self.guard = guard or ApplicationGuard(self.config)
        email_config = self.config.get("apply", {}).get("email", {})
        self.provider = email_config.get("provider", "resend")
        self.api_key_env = email_config.get("api_key_env", "RESEND_API_KEY")
        self.api_url_env = email_config.get("api_url_env", "RESEND_API_URL")
        self.from_email_env = email_config.get("from_email_env", "RESEND_FROM_EMAIL")
        self.reply_to_env = email_config.get("reply_to_env", "APPLICATION_REPLY_TO_EMAIL")
        self.timeout_seconds = int(email_config.get("timeout_seconds", 30))

    def apply(self, request: ApplicationRequest) -> ApplicationResult:
        blocked = self.guard.preflight(request, "email")
        if blocked:
            return blocked
        if not request.job.apply_email:
            return self.guard.blocked(request, "email", "job does not include apply_email")

        if self.guard.dry_run:
            result = self.result(request, "dry_run_ready", "email application prepared but not sent")
            self.guard.record(result, request)
            return result

        payload = self.build_payload(request)
        provider_message_id = self.send(payload)
        detail = "email sent"
        if provider_message_id:
            detail = f"email sent ({provider_message_id})"
        result = self.result(request, "submitted", detail)
        self.guard.record(result, request)
        return result

    def build_payload(self, request: ApplicationRequest) -> Dict[str, Any]:
        from_email = os.getenv(self.from_email_env)
        if not from_email:
            raise RuntimeError("Missing sender email. Set RESEND_FROM_EMAIL.")

        reply_to = os.getenv(self.reply_to_env) or request.candidate_email or from_email
        payload: Dict[str, Any] = {
            "from": from_email,
            "to": [request.job.apply_email or ""],
            "subject": f"Application for {request.job.title}",
            "text": request.message or default_message(request),
            "reply_to": reply_to,
            "attachments": [attachment_payload(request.resume_path)],
            "tags": [
                {"name": "source", "value": ascii_tag(request.job.source or "unknown")},
                {"name": "job_id", "value": ascii_tag(request.job.source_job_id or "unknown")},
            ],
        }
        if request.cover_letter_path and request.cover_letter_path.exists():
            payload["attachments"].append(attachment_payload(request.cover_letter_path))
        return payload

    def send(self, payload: Dict[str, Any]) -> str:
        if self.provider != "resend":
            raise RuntimeError(f"Unsupported email provider: {self.provider}")
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError("Missing Resend API key. Set RESEND_API_KEY.")
        api_url = os.getenv(self.api_url_env, "https://api.resend.com/emails")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key(payload),
        }
        response = httpx.post(api_url, headers=headers, json=payload, timeout=self.timeout_seconds)
        if response.status_code >= 400:
            raise RuntimeError(f"Resend email failed: {response.status_code} {response.text}")
        data = response.json()
        return str(data.get("id", ""))

    def result(self, request: ApplicationRequest, status: str, detail: str) -> ApplicationResult:
        return ApplicationResult(
            status=status,
            method="email",
            job_fingerprint=request.job.fingerprint,
            source=request.job.source,
            source_job_id=request.job.source_job_id,
            dry_run=self.guard.dry_run,
            detail=detail,
            target=request.job.apply_email or "",
        )


def default_message(request: ApplicationRequest) -> str:
    name = request.candidate_name or "Candidate"
    return (
        f"Hello,\n\n"
        f"I would like to apply for the {request.job.title} role at {request.job.company}.\n"
        f"My resume is attached.\n\n"
        f"Best regards,\n{name}\n"
    )


def attachment_payload(path: Path) -> Dict[str, str]:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "filename": path.name,
        "content": data,
        "content_type": content_type,
    }


def idempotency_key(payload: Dict[str, Any]) -> str:
    to = ",".join(payload.get("to", []))
    subject = payload.get("subject", "")
    return ascii_tag(f"jobfinder-{to}-{subject}")[:256]


def ascii_tag(value: str) -> str:
    cleaned = "".join(ch if ch.isascii() and (ch.isalnum() or ch in {"_", "-"}) else "-" for ch in value)
    return cleaned.strip("-")[:256] or "unknown"
