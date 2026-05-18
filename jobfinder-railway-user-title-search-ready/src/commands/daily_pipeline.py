import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from main import ConfigValidator, SearchPlanBuilder
from src.apply import ApplicationRequest, ApplicationResult, AutoApplyEngine
from src.israel_sources.search_engine import IsraelSearchEngine
from src.job import Job
from src.matching import JobMatcher, MatchResult
from src.resume_schemas.israeli_resume import IsraeliResume
from src.storage import JsonlStore, SQLiteStore
from src.subscription import SubscriptionGate


STATUS_LABELS_HE = {
    "active": "האוטומציה פעילה",
    "paused": "האוטומציה מושהית",
    "submitted": "נשלח",
    "dry_run_ready": "ממתין",
    "pending_approval": "דורש אישור",
    "requires_adapter": "דורש ידני",
    "requires_manual": "דורש ידני",
    "blocked": "נדחה על ידי חוקים",
    "failed": "נכשל",
    "saved_match": "ממתין",
    "payment_required": "נדרש מנוי",
}


@dataclass
class PipelineSummary:
    automation_status: str
    last_run_at: str
    next_run_at: str
    jobs_found_today: int
    applications_sent_today: int
    requires_approval: int
    daily_limit_used: int
    daily_limit: int
    matched_jobs: int
    rejected_by_rules: int
    requires_manual: int
    failed: int
    mode: str
    threshold: int
    subscription_required: bool = False
    subscription_locked: bool = False
    subscription_pay_url: str = ""
    subscription_message: str = ""
    inbox: List[Dict[str, Any]] = field(default_factory=list)

    def to_user_status(self) -> Dict[str, Any]:
        return {
            "status": STATUS_LABELS_HE.get(self.automation_status, self.automation_status),
            "last_run": self.last_run_at,
            "next_run": self.next_run_at,
            "jobs_found_today": self.jobs_found_today,
            "applications_sent_today": self.applications_sent_today,
            "requires_approval": self.requires_approval,
            "daily_limit": f"{self.daily_limit_used}/{self.daily_limit}",
            "subscription_required": self.subscription_required,
            "subscription_locked": self.subscription_locked,
            "subscription_pay_url": self.subscription_pay_url,
            "subscription_message": self.subscription_message,
            "buttons": [
                "הפעל / השהה",
                "הרץ עכשיו",
                "שנה שעה יומית",
                "בדוק לפני שליחה / שלח אוטומטית",
            ],
            "application_modes": [
                "אוטומטי מלא",
                "אישור לפני שליחה",
                "רק שמירת התאמות",
            ],
            "match_thresholds": [
                "רק משרות בציון 80+",
                "רק משרות בציון 70+",
                "רק משרות בציון 60+",
            ],
            "application_inbox": self.inbox,
        }


class DailyPipeline:
    def __init__(
        self,
        config_path: str | Path = "data_folder/work_preferences.yaml",
        resume_path: str | Path = "data_folder/plain_text_resume.yaml",
        cover_letter_path: str | Path = "data_folder/cover_letter_template.txt",
    ):
        self.config_path = Path(config_path)
        self.profile_resume_path = Path(resume_path)
        self.cover_letter_path = Path(cover_letter_path)
        self.config = ConfigValidator.validate_config(self.config_path)
        IsraeliResume.from_path(self.profile_resume_path)
        self.resume_path = self.resolve_resume_path()
        storage_config = self.config["storage"]
        self.store = SQLiteStore(storage_config["sqlite_path"])
        self.jsonl = JsonlStore(storage_config["jsonl_dir"])
        self.subscription_gate = SubscriptionGate(self.config)

    def run(self, jobs_override: Iterable[Any] | None = None, max_jobs: int | None = None) -> PipelineSummary:
        now = datetime.now(timezone.utc)
        automation = self.config["automation"]
        active_users = self.load_active_users()
        if not automation["enabled"] or automation["status"] != "active":
            summary = self.empty_summary(now, "paused")
            return self.write_summary(summary)

        search_plan = SearchPlanBuilder.build(self.config)
        if max_jobs is not None:
            self.write_progress("מתחיל חיפוש משרות", jobs_found=0, target_jobs=max_jobs, percent=1, phase="starting")
        source_name = "pipeline"
        run_id = self.store.start_ingestion_run(source_name, search_plan)
        try:
            israeli_jobs = list(jobs_override) if jobs_override is not None else self.fetch_jobs(search_plan, max_jobs=max_jobs)
            if max_jobs is not None:
                israeli_jobs = israeli_jobs[:max_jobs]
            jobs = self.normalize_and_dedupe(israeli_jobs)
            saved = self.store.save_jobs(jobs)
            self.store.finish_ingestion_run(run_id, "success", jobs_found=len(jobs), jobs_saved=saved)
            if self.cancel_requested():
                self.write_progress("החיפוש נעצר. נשמרו המשרות שנמצאו עד עכשיו.", jobs_found=len(jobs), target_jobs=max_jobs or len(jobs), percent=100, phase="cancelled")
            else:
                self.write_progress("החיפוש הסתיים, מתחיל דירוג התאמות", jobs_found=len(jobs), target_jobs=max_jobs or len(jobs), percent=100, phase="matching")
        except Exception as exc:
            self.write_progress(f"שגיאה בחיפוש: {exc}", jobs_found=0, target_jobs=max_jobs or 0, percent=100, phase="failed")
            self.store.record_ingestion_error(source_name, search_plan, exc, run_id=run_id)
            self.store.finish_ingestion_run(run_id, "failed", jobs_found=0, jobs_saved=0)
            raise

        blocked_user = next((user for user in active_users if self.subscription_gate.should_block(len(jobs), user)), None)
        gate_payload = self.subscription_gate.status_payload(len(jobs)) if blocked_user else None

        inbox: List[Dict[str, Any]] = []
        sent = 0
        requires_approval = 0
        rejected = 0
        requires_manual = 0
        failed = 0
        matched_jobs = 0
        daily_limit_used = 0
        apply_attempts = 0
        daily_limit = automation["daily_application_limit"]
        threshold = automation["match_threshold"]
        throttle_every = int(automation.get("apply_throttle_every", 10))
        throttle_seconds = int(automation.get("apply_throttle_seconds", 3))

        for user in active_users:
            matcher = JobMatcher(self.user_config(user))
            apply_engine = AutoApplyEngine(self.user_config(user))
            resume_text = self.read_resume_text()
            for job in jobs:
                match = matcher.match(job, resume_text)
                if match.score < threshold:
                    rejected += 1
                    inbox.append(self.inbox_item(job, match, "blocked", "score below threshold"))
                    continue
                matched_jobs += 1
                if gate_payload and "auto_apply" in self.config["subscription"].get("blocked_actions", []):
                    requires_approval += 1
                    inbox.append(self.inbox_item(job, match, "payment_required", gate_payload["message"]))
                    continue
                if daily_limit_used >= daily_limit:
                    requires_approval += 1
                    inbox.append(self.inbox_item(job, match, "pending_approval", "daily limit reached"))
                    continue
                mode = automation["application_mode"]
                if mode == "save_matches_only":
                    inbox.append(self.inbox_item(job, match, "saved_match", "match saved only"))
                    continue
                if mode == "approval_before_send":
                    requires_approval += 1
                    inbox.append(self.inbox_item(job, match, "pending_approval", "approval required before sending"))
                    continue
                try:
                    apply_attempts += 1
                    result = apply_engine.apply(
                        ApplicationRequest(
                            job=job,
                            resume_path=self.resume_path,
                            cover_letter_path=self.cover_letter_path,
                            candidate_name=user.get("name", ""),
                            candidate_email=user.get("email", ""),
                            candidate_phone=user.get("phone", ""),
                            message=user.get("message", "Please see my attached resume."),
                            match_result=match,
                        )
                    )
                    inbox.append(self.inbox_item(job, match, result.status, result.detail, result))
                    if result.status == "submitted":
                        sent += 1
                        daily_limit_used += 1
                    elif result.status == "dry_run_ready":
                        daily_limit_used += 1
                    elif result.status in {"requires_adapter", "requires_manual"}:
                        requires_manual += 1
                    elif result.status == "blocked":
                        rejected += 1
                    elif result.status == "failed":
                        failed += 1
                    self.throttle_apply(apply_attempts, throttle_every, throttle_seconds)
                except Exception as exc:
                    failed += 1
                    self.store.record_ingestion_error("auto_apply", {"job": job.fingerprint}, exc)
                    inbox.append(self.inbox_item(job, match, "failed", str(exc)))
                    self.throttle_apply(apply_attempts, throttle_every, throttle_seconds)

        self.mark_old_jobs_inactive(days=automation["expire_after_days"])
        summary = PipelineSummary(
            automation_status=automation["status"],
            last_run_at=local_display_time(now),
            next_run_at=self.next_run_display(now),
            jobs_found_today=len(jobs),
            applications_sent_today=sent,
            requires_approval=requires_approval,
            daily_limit_used=daily_limit_used,
            daily_limit=daily_limit,
            matched_jobs=matched_jobs,
            rejected_by_rules=rejected,
            requires_manual=requires_manual,
            failed=failed,
            mode=automation["application_mode"],
            threshold=threshold,
            subscription_required=bool(gate_payload),
            subscription_locked=bool(gate_payload),
            subscription_pay_url=gate_payload["pay_url"] if gate_payload else "",
            subscription_message=gate_payload["message"] if gate_payload else "",
            inbox=inbox[:100],
        )
        return self.write_summary(summary)

    def load_active_users(self) -> List[Dict[str, Any]]:
        users = self.config.get("users", [])
        active = [user for user in users if user.get("active", True)]
        if active:
            return active
        personal = IsraeliResume.from_path(self.profile_resume_path).data["personal_information"]
        return [
            {
                "id": "default",
                "active": True,
                "name": f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip(),
                "email": personal.get("email", ""),
                "phone": personal.get("phone", ""),
            }
        ]

    def user_config(self, user: Dict[str, Any]) -> Dict[str, Any]:
        config = dict(self.config)
        config["apply"] = dict(self.config["apply"])
        config["apply"]["dry_run"] = self.config["automation"]["application_mode"] != "full_auto" or self.config["apply"]["dry_run"]
        return config

    def resolve_resume_path(self) -> Path:
        configured = self.config.get("output", {}).get("resume_upload_path", "")
        if configured and Path(configured).exists():
            return Path(configured)
        return self.profile_resume_path

    def read_resume_text(self) -> str:
        try:
            return self.resume_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            return IsraeliResume.from_path(self.profile_resume_path).render_text("en")

    @staticmethod
    def throttle_apply(apply_attempts: int, throttle_every: int, throttle_seconds: int) -> None:
        if throttle_every <= 0 or throttle_seconds <= 0:
            return
        if apply_attempts > 0 and apply_attempts % throttle_every == 0:
            time.sleep(throttle_seconds)

    def fetch_jobs(self, search_plan: Dict[str, Any], max_jobs: int | None = None) -> List[Any]:
        if max_jobs is not None:
            search_plan = dict(search_plan)
            search_plan["total_limit"] = max_jobs
            search_plan["jobs_per_source"] = min(search_plan.get("jobs_per_source", max_jobs), max_jobs)
            search_plan["max_pages"] = min(search_plan.get("max_pages", 3), 3)
            priority_sources = ["remotive", "arbeitnow", "remoteok", "greenhouse", "lever"]
            configured_sources = search_plan.get("sources", [])
            search_plan["sources"] = [
                source for source in priority_sources if source in configured_sources
            ] + [source for source in configured_sources if source not in priority_sources]
            search_plan["queries"] = [
                {**query, "limit": min(query.get("limit", max_jobs), max_jobs)}
                for query in search_plan.get("queries", [])
            ]
        engine = IsraelSearchEngine(
            sources=search_plan["sources"],
            max_pages=search_plan["max_pages"],
            progress_callback=self.search_progress_callback,
            cancel_callback=self.cancel_requested,
        )
        return engine.search_from_plan(search_plan)

    def cancel_requested(self) -> bool:
        output_dir = Path(self.config["output"].get("summary_dir", "data_folder/output"))
        return (output_dir / "cancel_search.flag").exists()

    def search_progress_callback(self, progress: Dict[str, Any]) -> None:
        self.write_progress(
            f"בודק מקור: {progress.get('source', '')}",
            jobs_found=int(progress.get("jobs_found_so_far", 0)),
            target_jobs=int(progress.get("target_jobs", 100)),
            percent=int(progress.get("percent", 1)),
            phase=str(progress.get("phase", "searching")),
            source=str(progress.get("source", "")),
        )

    def write_progress(
        self,
        message: str,
        jobs_found: int,
        target_jobs: int,
        percent: int,
        phase: str,
        source: str = "",
    ) -> None:
        output_dir = Path(self.config["output"].get("summary_dir", "data_folder/output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "message": message,
            "phase": phase,
            "source": source,
            "jobs_found_so_far": jobs_found,
            "target_jobs": target_jobs,
            "percent": max(0, min(100, percent)),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        (output_dir / "job_search_progress.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def normalize_and_dedupe(self, israeli_jobs: Iterable[Any]) -> List[Job]:
        normalized_language = self.config["output"]["normalized_language"]
        jobs: List[Job] = []
        seen = set()
        for israeli_job in israeli_jobs:
            job = israeli_job.to_job(normalized_output_language=normalized_language)
            if job.fingerprint in seen:
                continue
            seen.add(job.fingerprint)
            jobs.append(job)
        return jobs

    def mark_old_jobs_inactive(self, days: int):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.store.connect() as conn:
            conn.execute("UPDATE jobs SET status = 'expired' WHERE last_seen_at < ?", (cutoff,))

    def inbox_item(
        self,
        job: Job,
        match: MatchResult,
        status: str,
        detail: str,
        result: ApplicationResult | None = None,
    ) -> Dict[str, Any]:
        item = {
            "status": status,
            "status_label": STATUS_LABELS_HE.get(status, status),
            "title": job.title,
            "company": job.company,
            "source": job.source,
            "source_job_id": job.source_job_id,
            "score": match.score,
            "detail": detail,
            "apply_url": job.apply_url,
            "apply_email": job.apply_email,
        }
        if result:
            item["method"] = result.method
            item["target"] = result.target
        return item

    def empty_summary(self, now: datetime, status: str) -> PipelineSummary:
        automation = self.config["automation"]
        return PipelineSummary(
            automation_status=status,
            last_run_at=local_display_time(now),
            next_run_at=self.next_run_display(now),
            jobs_found_today=0,
            applications_sent_today=0,
            requires_approval=0,
            daily_limit_used=0,
            daily_limit=automation["daily_application_limit"],
            matched_jobs=0,
            rejected_by_rules=0,
            requires_manual=0,
            failed=0,
            mode=automation["application_mode"],
            threshold=automation["match_threshold"],
            inbox=[],
        )

    def next_run_display(self, now: datetime) -> str:
        hour, minute = [int(part) for part in self.config["automation"]["daily_time"].split(":")]
        local_now = now.astimezone()
        next_run = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= local_now:
            next_run += timedelta(days=1)
        return local_display_time(next_run)

    def write_summary(self, summary: PipelineSummary) -> PipelineSummary:
        output_dir = Path(self.config["output"].get("summary_dir", "data_folder/output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "daily_summary.json").write_text(
            json.dumps(asdict(summary), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / "automation_status.json").write_text(
            json.dumps(summary.to_user_status(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.jsonl.append("pipeline_runs", asdict(summary))
        return summary


def local_display_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full daily Israeli jobs pipeline.")
    parser.add_argument("--config", default="data_folder/work_preferences.yaml")
    parser.add_argument("--resume", default="data_folder/plain_text_resume.yaml")
    parser.add_argument("--cover-letter", default="data_folder/cover_letter_template.txt")
    parser.add_argument("--max-jobs", type=int, default=None)
    args = parser.parse_args()
    summary = DailyPipeline(args.config, args.resume, args.cover_letter).run(max_jobs=args.max_jobs)
    print(json.dumps(summary.to_user_status(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
