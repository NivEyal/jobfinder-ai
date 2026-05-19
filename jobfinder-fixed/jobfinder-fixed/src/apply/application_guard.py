import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.job import Job
from src.matching.models import MatchResult
from src.storage import JsonlStore, SQLiteStore


@dataclass
class ApplicationRequest:
    job: Job
    resume_path: Path
    cover_letter_path: Optional[Path] = None
    candidate_name: str = ""
    candidate_email: str = ""
    candidate_phone: str = ""
    message: str = ""
    match_result: Optional[MatchResult] = None


@dataclass
class ApplicationResult:
    status: str
    method: str
    job_fingerprint: str
    source: str
    source_job_id: str
    dry_run: bool = True
    detail: str = ""
    target: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


class ApplicationGuard:
    """Protects auto-apply from duplicates and low-confidence submissions."""

    def __init__(self, config: Dict[str, Any] | None = None, ledger_path: Path | None = None):
        self.config = config or {}
        apply_config = self.config.get("apply", {})
        self.enabled = bool(apply_config.get("enabled", False))
        self.dry_run = bool(apply_config.get("dry_run", True))
        self.minimum_match_score = int(apply_config.get("minimum_match_score", 65))
        self.require_resume_file = bool(apply_config.get("require_resume_file", True))
        self.ledger_path = ledger_path or Path(apply_config.get("ledger_path", "data_folder/output/applications_ledger.json"))
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        storage_config = self.config.get("storage", {})
        self.storage_enabled = bool(storage_config.get("enabled", True))
        self.sqlite_store = SQLiteStore(storage_config.get("sqlite_path", "data_folder/output/jobs_storage.sqlite3"))
        self.jsonl_store = JsonlStore(storage_config.get("jsonl_dir", "data_folder/output/jsonl"))

    def preflight(self, request: ApplicationRequest, method: str) -> ApplicationResult | None:
        if not self.enabled:
            return self.blocked(request, method, "auto apply is disabled")
        if self.require_resume_file and not request.resume_path.exists():
            return self.blocked(request, method, f"resume file not found: {request.resume_path}")
        if request.match_result and request.match_result.score < self.minimum_match_score:
            return self.blocked(
                request,
                method,
                f"match score {request.match_result.score} is below minimum {self.minimum_match_score}",
            )
        if self.has_applied(request.job.fingerprint):
            return self.blocked(request, method, "application already recorded")
        return None

    def record(self, result: ApplicationResult, request: ApplicationRequest | None = None):
        entries = self.load_ledger()
        entries.append(result.to_dict())
        self.ledger_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        if self.storage_enabled:
            if request:
                self.sqlite_store.save_job(request.job)
            self.sqlite_store.record_application(result, request.match_result if request else None)
            self.sqlite_store.log_application(
                "application_recorded",
                result.detail or result.status,
                result,
                level="info" if result.status != "blocked" else "warning",
            )
            self.jsonl_store.append("application_logs", result.to_dict())

    def has_applied(self, job_fingerprint: str) -> bool:
        if self.storage_enabled and self.sqlite_store.has_application(job_fingerprint):
            return True
        return any(entry.get("job_fingerprint") == job_fingerprint for entry in self.load_ledger())

    def load_ledger(self) -> list[dict]:
        if not self.ledger_path.exists():
            return []
        try:
            return json.loads(self.ledger_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def blocked(self, request: ApplicationRequest, method: str, detail: str) -> ApplicationResult:
        return ApplicationResult(
            status="blocked",
            method=method,
            job_fingerprint=request.job.fingerprint,
            source=request.job.source,
            source_job_id=request.job.source_job_id,
            dry_run=self.dry_run,
            detail=detail,
            target=request.job.apply_email or request.job.apply_url,
        )


class AutoApplyEngine:
    """Routes each job to email, simple form, or external-complex apply."""

    def __init__(self, config: Dict[str, Any] | None = None):
        from src.apply.email_apply import EmailApplyEngine
        from src.apply.external_apply import ExternalApplyEngine
        from src.apply.form_apply import FormApplyEngine

        self.config = config or {}
        self.guard = ApplicationGuard(self.config)
        self.email = EmailApplyEngine(self.config, self.guard)
        self.form = FormApplyEngine(self.config, self.guard)
        self.external = ExternalApplyEngine(self.config, self.guard)

    def apply(self, request: ApplicationRequest) -> ApplicationResult:
        if request.job.apply_email:
            return self.email.apply(request)
        if request.job.apply_url and self.form.looks_like_simple_form(request.job.apply_url):
            return self.form.apply(request)
        if request.job.apply_url:
            return self.external.apply(request)
        return self.guard.blocked(request, "none", "job has no apply email or apply url")
