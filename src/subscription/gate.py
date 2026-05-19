import os
import json
from pathlib import Path
from typing import Any, Dict


class SubscriptionGate:
    """Blocks premium pipeline actions after the user sees discovered jobs."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        subscription = self.config.get("subscription", {})
        self.enabled = bool(subscription.get("enabled", False))
        self.pay_url = subscription.get("pay_url", "")
        self.unlock_env = subscription.get("unlock_env", "SUBSCRIPTION_ACTIVE")
        self.status_path = Path(subscription.get("status_path", "data_folder/output/subscription_status.json"))
        self.reveal_after_jobs_count = int(subscription.get("reveal_after_jobs_count", 1))
        self.blocked_actions = subscription.get("blocked_actions", ["match_jobs", "auto_apply"])

    def is_unlocked(self, user: Dict[str, Any] | None = None) -> bool:
        if not self.enabled:
            return True
        if os.getenv(self.unlock_env, "").lower() in {"1", "true", "yes", "paid", "active"}:
            return True
        if self.status_path.exists():
            try:
                if bool(json.loads(self.status_path.read_text(encoding="utf-8")).get("active")):
                    return True
            except json.JSONDecodeError:
                pass
        user_subscription = (user or {}).get("subscription", {})
        return bool(user_subscription.get("active", False))

    def should_block(self, jobs_found: int, user: Dict[str, Any] | None = None) -> bool:
        if self.is_unlocked(user):
            return False
        return jobs_found >= self.reveal_after_jobs_count

    def status_payload(self, jobs_found: int) -> Dict[str, Any]:
        return {
            "subscription_required": self.enabled,
            "subscription_locked": self.enabled,
            "jobs_found_before_gate": jobs_found,
            "pay_url": self.pay_url,
            "message": "נמצאו משרות מתאימות. כדי להמשיך ל-Matching והגשות, יש להפעיל מנוי.",
            "blocked_actions": self.blocked_actions,
            "unlock": {
                "after_payment": "set user.subscription.active=true or set SUBSCRIPTION_ACTIVE=true",
                "unlock_env": self.unlock_env,
                "status_path": str(self.status_path),
            },
        }
