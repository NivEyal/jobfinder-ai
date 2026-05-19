# Step 8 - Storage and Logs

This step adds durable storage for search and application operations.

## Storage backends

The default backend is SQLite:

```yaml
storage:
  enabled: true
  backend: sqlite
  sqlite_path: data_folder/output/jobs_storage.sqlite3
  jsonl_dir: data_folder/output/jsonl
  save_source_snapshots: true
```

JSONL logs are written beside SQLite for simple inspection and debugging.

## SQLite tables

The schema includes:

- `jobs`
- `applications`
- `ingestion_runs`
- `ingestion_errors`
- `application_logs`
- `source_snapshots`

This makes it possible to know:

- which jobs were already seen
- which applications were prepared or submitted
- which source runs succeeded or failed
- which errors happened per source/query
- which application events happened per job
- which source payloads were captured for debugging

## Auto Apply integration

`ApplicationGuard` now records every prepared/submitted application into:

- the previous JSON ledger
- SQLite `applications`
- SQLite `application_logs`
- JSONL `application_logs.jsonl`

Duplicate detection checks SQLite first, then falls back to the old JSON ledger.

## Smoke test

```powershell
python -m src.storage.smoke_test
```

The smoke test creates every required table and writes at least one row to each.
