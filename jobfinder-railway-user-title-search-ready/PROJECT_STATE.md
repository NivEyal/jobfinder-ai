# JobFinder Project State

This file tracks product decisions and fixes so future point fixes stay consistent.

## Current Production Direction

- Deployment target: Railway.
- Repo root on GitHub currently contains the app inside `jobfinder-railway-user-title-search-ready/`.
- Railway Root Directory must point to `jobfinder-railway-user-title-search-ready`.
- Runtime command: `sh start.sh`.
- Healthcheck path: `/api/status`.

## Search Model

- The default keywords in `data_folder/work_preferences.yaml` are only starter examples.
- The product must rely on the user's typed job title, not guessed professions extracted from the CV.
- User title input is written into `search.keywords`.
- Dashboard run must not hard-limit search to 5 jobs.

## CV Handling

- Uploaded resume files are saved under `data_folder/output/uploads`.
- The saved path is written to `output.resume_upload_path`.
- Auto Apply attaches the uploaded resume when the file exists.
- Matching still falls back to `data_folder/plain_text_resume.yaml` when the uploaded file is binary PDF/DOCX and cannot be read as text.
- Railway production should use a Volume mounted to `data_folder/output` if uploaded resumes must survive redeploys.

## Apply Mode

- Daily application limit is 100.
- Default apply mode is `full_auto`.
- `apply.dry_run` is `false` for production behavior.
- Button `/api/apply-all` runs one-click application for up to 100 matched jobs.
- Subscription gate should show matched jobs but block `auto_apply` until payment is active.

## Subscription

- Payment URL: `https://paypage.takbull.co.il/2dBbl`.
- Takbull webhook URL: `https://jobfinder.fit/webhooks/takbull`.
- `SUBSCRIPTION_ACTIVE=true` globally unlocks premium actions and should not be used in production.

## Latest Fix Batch

- Removed fake static "AI extracted profile" chips from onboarding.
- Added explicit job title input to onboarding/upload/search forms.
- Removed `max_jobs=5` from dashboard run.
- Added one-click "apply all suitable jobs" endpoint and button.
- Changed daily limit from `20` to `100`.
- Changed subscription behavior from blocking matching to blocking auto apply only.
- Persisted uploaded resume path in config for subsequent pipeline runs.
- UI search/apply actions now start a background pipeline instead of blocking the HTTP request.
- `/api/progress` exposes live progress from `data_folder/output/job_search_progress.json`.
- `/api/cancel-search` writes `cancel_search.flag`; search checks it between sources and stops with saved jobs.
- AI insights are generated from real match results in `ai_insights.json`; OpenAI is used for top matches up to `matching.openai_max_jobs_per_run`.
- Performance patch: source search runs in parallel with early shutdown at the target limit.
- UI search uses fast mode: priority global sources first, `max_pages=1`, `max_workers=12`, `max_tasks=36`, target 100 jobs.
- Fetch timeout is 8 seconds instead of 20.
- Matching uses local prefiltering first, then parallel OpenAI only for the strongest jobs (`openai_max_workers=6`).
- Auto-apply remains sequential with throttle to avoid duplicate or spammy submissions.
