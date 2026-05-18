# Subscription Gate

The daily pipeline can show the user how many jobs were found, then block premium actions until a subscription is active.

Payment URL:

```text
https://paypage.takbull.co.il/2dBbl
```

## Flow

1. User fills the required details.
2. The app runs job discovery.
3. The app shows how many jobs were found.
4. If no subscription is active, the pipeline stops before matching and auto apply.
5. The user sees `payment_required` with the payment URL.
6. After payment is confirmed, unlock the user.

## Config

```yaml
subscription:
  enabled: true
  pay_url: https://paypage.takbull.co.il/2dBbl
  unlock_env: SUBSCRIPTION_ACTIVE
  reveal_after_jobs_count: 1
  blocked_actions:
    - match_jobs
    - auto_apply
```

Per-user unlock:

```yaml
users:
  - id: default
    subscription:
      active: true
```

Environment unlock:

```powershell
$env:SUBSCRIPTION_ACTIVE = "true"
```

## Output

When blocked, `automation_status.json` includes:

```json
{
  "subscription_required": true,
  "subscription_locked": true,
  "subscription_pay_url": "https://paypage.takbull.co.il/2dBbl",
  "subscription_message": "נמצאו משרות מתאימות. כדי להמשיך ל-Matching והגשות, יש להפעיל מנוי."
}
```

The Application Inbox receives a `payment_required` item.

## Payment verification

This implementation does not call a Takbull verification API. Unlocking is done by setting `user.subscription.active=true` after payment is confirmed, or by setting the configured environment variable.
