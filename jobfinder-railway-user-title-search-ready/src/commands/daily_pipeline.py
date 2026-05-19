import argparse
import json
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
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
from src.matching.rule_based_matcher import RuleBasedMatcher
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
