from typing import Any, Callable, Dict
from urllib.parse import urlparse

from src.apply.application_guard import ApplicationGuard, ApplicationRequest, ApplicationResult


ExternalAdapter = Callable[[ApplicationRequest], ApplicationResult]


class ExternalApplyEngine:
    """Handles complex application flows through site-specific adapters."""

    def __init__(self, config: Dict[str, Any] | None = None, guard: ApplicationGuard | None = None):
        self.config = config or {}
        self.guard = guard or ApplicationGuard(self.config)
        self.adapters: Dict[str, ExternalAdapter] = {}

    def register(self, domain: str, adapter: ExternalAdapter):
        self.adapters[normalize_domain(domain)] = adapter

    def apply(self, request: ApplicationRequest) -> ApplicationResult:
        blocked = self.guard.preflight(request, "external")
        if blocked:
            return blocked

        domain = normalize_domain(urlparse(request.job.apply_url).netloc)
        adapter = self.adapters.get(domain)
        if adapter:
            result = adapter(request)
            self.guard.record(result, request)
            return result

        result = ApplicationResult(
            status="requires_adapter",
            method="external",
            job_fingerprint=request.job.fingerprint,
            source=request.job.source,
            source_job_id=request.job.source_job_id,
            dry_run=self.guard.dry_run,
            detail=f"complex external form needs a site-specific adapter for {domain}",
            target=request.job.apply_url,
        )
        self.guard.record(result, request)
        return result


def normalize_domain(domain: str) -> str:
    domain = (domain or "").lower().strip()
    return domain[4:] if domain.startswith("www.") else domain
