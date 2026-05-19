# Step 6 - Job Matching

This step adds a matching layer for Israeli and worldwide jobs.

## What changed

- Added `src/matching/` with `JobMatcher`, `OpenAIMatcher`, `RuleBasedMatcher`, and `MatchResult`.
- Added matching settings to `data_folder/work_preferences.yaml`.
- Added unit tests and an offline smoke test.

## API key handling

Do not write an OpenAI key into YAML, Python files, logs, or ZIP artifacts.

Set the key only in the runtime environment:

```powershell
$env:OPENAI_API_KEY = "your_key_here"
```

If `OPENAI_API_KEY` is missing or the OpenAI request fails, matching falls back to the local rule-based matcher.

## Match result contract

Each match returns a serializable `MatchResult` with:

- `job_fingerprint`
- `source`
- `source_job_id`
- `score`
- `verdict`
- `confidence`
- `reasons`
- `matched_keywords`
- `missing_requirements`
- `model`
- `used_openai`
- `created_at`

`score` is always `0-100`.

`verdict` is one of `strong_match`, `possible_match`, `weak_match`, or `not_recommended`.

## Smoke test

```powershell
python -m src.matching.smoke_test
```

The smoke test is safe to run without an OpenAI key because it uses the fallback automatically.
