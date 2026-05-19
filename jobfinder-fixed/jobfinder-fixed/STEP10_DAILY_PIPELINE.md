# Step 10 - One-Command Daily Pipeline

This step replaces separate operational commands with one daily automation command:

```powershell
python -m src.commands.daily_pipeline
```

## Pipeline steps

The command runs:

1. load active users
2. load user preferences
3. fetch jobs from Israeli sources
4. normalize jobs
5. dedupe jobs
6. score jobs per user
7. apply guardrails
8. auto apply where allowed
9. mark old jobs inactive
10. generate daily summary
11. write logs

## User-visible status

The pipeline writes:

- `data_folder/output/daily_summary.json`
- `data_folder/output/automation_status.json`
- JSONL logs under `data_folder/output/jsonl`
- SQLite rows in `data_folder/output/jobs_storage.sqlite3`

`automation_status.json` is designed for a simple UI:

```json
{
  "status": "האוטומציה פעילה",
  "last_run": "2026-05-18 08:17",
  "next_run": "2026-05-19 07:00",
  "jobs_found_today": 128,
  "applications_sent_today": 7,
  "requires_approval": 3,
  "daily_limit": "7/20"
}
```

## Controls

The summary exposes these UI actions:

- `הפעל / השהה`
- `הרץ עכשיו`
- `שנה שעה יומית`
- `בדוק לפני שליחה / שלח אוטומטית`

## Application modes

Configure in `work_preferences.yaml`:

```yaml
automation:
  application_mode: approval_before_send
```

Supported modes:

- `full_auto`
- `approval_before_send`
- `save_matches_only`

## Match threshold

Supported thresholds:

- `80`
- `70`
- `60`

## Application Inbox

The pipeline writes one inbox list with statuses:

- `נשלח`
- `נכשל`
- `דורש ידני`
- `נדחה על ידי חוקים`
- `ממתין`
- `דורש אישור`

## Quick smoke run

```powershell
python -m src.commands.daily_pipeline --max-jobs 1
```

`--max-jobs` limits the fetch stage itself, so it is safe for quick checks.
