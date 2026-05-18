from typing import Any, Dict
from urllib.parse import urlparse

from src.apply.application_guard import ApplicationGuard, ApplicationRequest, ApplicationResult


SIMPLE_FORM_KEYWORDS = ("apply", "jobs", "career", "careers", "candidate")
COMPLEX_FORM_KEYWORDS = ("login", "signin", "captcha", "assessment", "questionnaire")


class FormApplyEngine:
    """Fills simple name/email/phone/file/message forms with Selenium."""

    def __init__(self, config: Dict[str, Any] | None = None, guard: ApplicationGuard | None = None):
        self.config = config or {}
        self.guard = guard or ApplicationGuard(self.config)
        form_config = self.config.get("apply", {}).get("form", {})
        self.timeout_seconds = int(form_config.get("timeout_seconds", 20))
        self.submit_selector = form_config.get("submit_selector", "button[type='submit'], input[type='submit']")

    def looks_like_simple_form(self, url: str) -> bool:
        lowered = (url or "").lower()
        if any(keyword in lowered for keyword in COMPLEX_FORM_KEYWORDS):
            return False
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc and any(keyword in lowered for keyword in SIMPLE_FORM_KEYWORDS))

    def apply(self, request: ApplicationRequest) -> ApplicationResult:
        blocked = self.guard.preflight(request, "form")
        if blocked:
            return blocked

        if self.guard.dry_run:
            result = self.result(request, "dry_run_ready", "simple form application prepared but not submitted")
            self.guard.record(result, request)
            return result

        try:
            self.submit_with_selenium(request)
        except ImportError as exc:
            return self.guard.blocked(request, "form", f"selenium is not installed: {exc}")

        result = self.result(request, "submitted", "simple form submitted")
        self.guard.record(result, request)
        return result

    def submit_with_selenium(self, request: ApplicationRequest):
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        driver = webdriver.Chrome()
        try:
            driver.get(request.job.apply_url)
            wait = WebDriverWait(driver, self.timeout_seconds)
            fill_first(driver, ["input[name*='name']", "input[id*='name']"], request.candidate_name)
            fill_first(driver, ["input[type='email']", "input[name*='mail']", "input[id*='mail']"], request.candidate_email)
            fill_first(driver, ["input[type='tel']", "input[name*='phone']", "input[id*='phone']"], request.candidate_phone)
            fill_first(driver, ["textarea", "textarea[name*='message']"], request.message)
            upload_first(driver, ["input[type='file']"], str(request.resume_path.resolve()))
            submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.submit_selector)))
            submit.click()
        finally:
            driver.quit()

    def result(self, request: ApplicationRequest, status: str, detail: str) -> ApplicationResult:
        return ApplicationResult(
            status=status,
            method="form",
            job_fingerprint=request.job.fingerprint,
            source=request.job.source,
            source_job_id=request.job.source_job_id,
            dry_run=self.guard.dry_run,
            detail=detail,
            target=request.job.apply_url,
        )


def fill_first(driver, selectors: list[str], value: str):
    if not value:
        return
    for selector in selectors:
        elements = driver.find_elements("css selector", selector)
        if elements:
            elements[0].clear()
            elements[0].send_keys(value)
            return


def upload_first(driver, selectors: list[str], path: str):
    for selector in selectors:
        elements = driver.find_elements("css selector", selector)
        if elements:
            elements[0].send_keys(path)
            return
