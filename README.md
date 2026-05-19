# JobFinder

JobFinder is an Israel-ready job automation platform for finding, matching, tracking, and applying to jobs.

Brand line: **מחברים אותך להזדמנות הבאה שלך**

## What It Does

- Searches Israeli job sources.
- Searches global remote and company career sources.
- Normalizes Hebrew/English job data.
- Scores jobs against user preferences and resume.
- Blocks premium actions behind a subscription gate.
- Receives Takbull payment webhooks.
- Manages Application Inbox statuses.
- Stores jobs, runs, applications, logs, and snapshots in SQLite/JSONL.

## Product UX

The MVP includes a polished SaaS shell instead of a backend-only tool:

- Smooth onboarding with CV upload and extracted-profile confirmation.
- Dashboard with automation status, application progress, AI insights, and activity feed.
- Job cards with match scores, apply state, and transparent skill gaps.
- Application Inbox for sent, failed, pending, manual, and rule-blocked applications.
- Trust signals: human approval mode, visible run logs, data privacy copy, and subscription state.

## Job Coverage

Configured sources include Israeli boards plus global remote/company sources:

- Israeli: Drushim, AllJobs, JobMaster, GotFriends, Indeed Israel, Jobnet, company career pages.
- Global: Remotive, Arbeitnow, RemoteOK, Greenhouse public boards, Lever public postings.

No single crawler can reliably cover 90% of all jobs worldwide. To approach that level, add paid/partner sources such as LinkedIn/Indeed APIs, Adzuna, Google Talent-style feeds, and more ATS board lists. This project is structured so each new source can be added as another adapter returning the same `IsraeliJob` contract.

The default keywords are only starter examples. In the product flow, users type the job title they want, for example `Backend Developer`, `Junior Economist`, or `Data Analyst`. JobFinder saves that input to `search.keywords` and searches the enabled sources around the user's title.

## Web App

Run locally:

```bash
pip install -r requirements.txt
uvicorn src.web.app:app --reload
```

Open:

```text
http://localhost:8000
```

Main screens:

- `/` - branded JobFinder landing page
- `/onboarding` - smooth setup flow
- `/login` - MVP login
- `/dashboard` - automation status and actions
- `/jobs` - matched jobs and AI fit cards
- `/inbox` - Application Inbox
- `/settings` - daily time, match threshold, and apply mode
- `/upload-cv` - resume upload
- `/api/status` - JSON status
- `/webhooks/takbull` - Takbull payment webhook

Production webhook URL for Takbull:

```text
https://jobfinder.fit/webhooks/takbull
```

Takbull settings:

- URL: `https://jobfinder.fit/webhooks/takbull`
- Event: `עסקה חדשה`
- Request type: `POST`
- Data type: `JSON`

## Daily Pipeline

```bash
python -m src.commands.daily_pipeline
```

Quick smoke run:

```bash
python -m src.commands.daily_pipeline --max-jobs 1
```

The pipeline writes:

- `data_folder/output/automation_status.json`
- `data_folder/output/daily_summary.json`
- `data_folder/output/jobs_storage.sqlite3`
- `data_folder/output/jsonl/*.jsonl`

## Environment

Copy `.env.example` and configure deployment environment variables:

```text
OPENAI_API_KEY=
TAKBULL_WEBHOOK_SECRET=
WORK_PREFERENCES_PATH=data_folder/work_preferences.yaml
RESEND_API_KEY=
RESEND_FROM_EMAIL=JobFinder <apply@jobfinder.fit>
APPLICATION_REPLY_TO_EMAIL=
RESEND_API_URL=https://api.resend.com/emails
```

Do not commit real secrets.

## Production Email Apply

JobFinder uses Resend for production email applications. Gmail SMTP is not used.

Environment variables:

```text
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=JobFinder <apply@jobfinder.fit>
APPLICATION_REPLY_TO_EMAIL=support@jobfinder.fit
RESEND_API_URL=https://api.resend.com/emails
```

Setup steps:

1. Create a Resend account: https://resend.com
2. Add and verify `jobfinder.fit` or a sending subdomain such as `mail.jobfinder.fit`: https://resend.com/docs/dashboard/domains/introduction
3. Add the DNS records Resend gives you for SPF and DKIM. Add DMARC as well for better trust.
4. Create a Resend API key: https://resend.com/api-keys
5. In Bolt, add the environment variables above.
6. Use a real reply inbox for `APPLICATION_REPLY_TO_EMAIL`, because recruiters may reply there.

Resend requires a verified domain before sending to arbitrary recipients. In test mode, it may only allow sending to your own email address.

## Subscription Unlock

The subscription gate blocks matching and auto-apply after jobs are discovered.

Payment page:

```text
https://paypage.takbull.co.il/2dBbl
```

When Takbull sends a successful payment webhook, JobFinder writes:

```text
data_folder/output/subscription_status.json
```

The next pipeline/status check sees the subscription as active.

## Bolt Deployment

Use the project root as the deployment root.

Start command:

```bash
uvicorn src.web.app:app --host 0.0.0.0 --port $PORT
```

If Bolt supports Docker, use the included `Dockerfile`.

## Railway Deployment

Railway is supported with `railway.json`, `Dockerfile`, and `start.sh`.

Use:

```text
Start command: sh start.sh
Healthcheck path: /api/status
```

See `RAILWAY.md` for the full setup.

## Tests

```bash
python -m pytest tests -q
python -m compileall -q src main.py tests
```
