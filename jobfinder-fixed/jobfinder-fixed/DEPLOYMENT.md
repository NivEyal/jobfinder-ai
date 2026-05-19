# Deployment

## Domain

Point `jobfinder.fit` to the deployment provider.

Required Takbull webhook:

```text
https://jobfinder.fit/webhooks/takbull
```

## Bolt

Deployment root: repository root.

Install:

```bash
pip install -r requirements.txt
```

Start:

```bash
uvicorn src.web.app:app --host 0.0.0.0 --port $PORT
```

Health check:

```text
/
```

## Railway

Railway is supported with `railway.json`, `Dockerfile`, and `start.sh`.

Recommended Railway settings:

```text
Builder: Dockerfile
Start command: sh start.sh
Healthcheck path: /api/status
```

See `RAILWAY.md` for the full variable list and webhook setup.

After deployment, verify:

```text
https://jobfinder.fit/
https://jobfinder.fit/dashboard
https://jobfinder.fit/api/status
```

## Required Environment Variables

```text
WORK_PREFERENCES_PATH=data_folder/work_preferences.yaml
TAKBULL_WEBHOOK_SECRET=
OPENAI_API_KEY=
RESEND_API_KEY=
RESEND_FROM_EMAIL=JobFinder <apply@jobfinder.fit>
APPLICATION_REPLY_TO_EMAIL=
RESEND_API_URL=https://api.resend.com/emails
```

`TAKBULL_WEBHOOK_SECRET` is optional unless you configure Takbull to send a matching `x-webhook-secret` header or `?secret=` query parameter.

## GitHub Checklist

- Commit source files.
- Do not commit `.env`.
- Do not commit `data_folder/output/`.
- Do not commit SQLite files.
- Confirm `assets/brand/jobfinder-logo.png` is committed.
- Confirm `.env.example`, `Procfile`, `Dockerfile`, and `start.sh` are committed.
