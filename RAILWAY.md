# Railway Deployment

Deploy the repository root to Railway.

## Required Variables

```text
WORK_PREFERENCES_PATH=data_folder/work_preferences.yaml
OPENAI_API_KEY=your_new_openai_key
TAKBULL_WEBHOOK_SECRET=
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=JobFinder <apply@jobfinder.fit>
APPLICATION_REPLY_TO_EMAIL=support@jobfinder.fit
RESEND_API_URL=https://api.resend.com/emails
SUBSCRIPTION_ACTIVE=
```

Leave `SUBSCRIPTION_ACTIVE` empty in production. Setting it to `true` unlocks premium actions globally.

## Railway Settings

- Builder: Dockerfile
- Start command: `sh start.sh`
- Healthcheck path: `/api/status`
- Public domain: connect `jobfinder.fit`

## Takbull Webhook

After the Railway domain is live, set the Takbull webhook URL to:

```text
https://jobfinder.fit/webhooks/takbull
```

Use request type `POST` and data type `JSON`.

## User Search Flow

Users do not need the default keyword list to cover the world. In the app, they enter a job title such as:

```text
Backend Developer
Junior Economist
Data Analyst
QA Engineer
```

JobFinder writes that title into `search.keywords` and runs the pipeline against Israeli and global sources.
