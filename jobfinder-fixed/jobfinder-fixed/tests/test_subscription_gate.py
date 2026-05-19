from src.subscription import SubscriptionGate


def config():
    return {
        "subscription": {
            "enabled": True,
            "pay_url": "https://paypage.takbull.co.il/2dBbl",
            "unlock_env": "SUBSCRIPTION_ACTIVE",
            "reveal_after_jobs_count": 1,
            "blocked_actions": ["match_jobs", "auto_apply"],
        }
    }


def test_subscription_gate_blocks_after_jobs_are_found():
    gate = SubscriptionGate(config())

    assert gate.should_block(0, {"subscription": {"active": False}}) is False
    assert gate.should_block(3, {"subscription": {"active": False}}) is True
    assert gate.status_payload(3)["pay_url"] == "https://paypage.takbull.co.il/2dBbl"


def test_subscription_gate_unlocks_for_paid_user():
    gate = SubscriptionGate(config())

    assert gate.should_block(3, {"subscription": {"active": True}}) is False
