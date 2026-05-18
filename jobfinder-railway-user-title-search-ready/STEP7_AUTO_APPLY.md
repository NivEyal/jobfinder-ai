# Step 7 - Auto Apply

This step adds a guarded auto-apply layer split into three engines:

- `src/apply/email_apply.py`
- `src/apply/form_apply.py`
- `src/apply/external_apply.py`
- `src/apply/application_guard.py`

## Guardrails

Auto apply is controlled by `apply` in `data_folder/work_preferences.yaml`.

The default is:

```yaml
apply:
  enabled: true
  dry_run: true
```

`dry_run: true` means the system prepares an application result but does not send email and does not submit web forms.

The guard blocks:

- duplicate applications by job fingerprint
- missing resume files
- jobs below `minimum_match_score`
- disabled auto-apply mode

Applications are recorded in `data_folder/output/applications_ledger.json`.

## Email Apply

Email apply is the most stable channel for Israeli jobs.

If `job.apply_email` exists:

1. Attach the ready resume.
2. Attach the cover letter when present.
3. Send the configured message.

Production email delivery uses Resend API credentials from environment variables:

- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `APPLICATION_REPLY_TO_EMAIL`
- `RESEND_API_URL`

No email credentials are stored in project files.

## Simple Form Apply

Simple form apply uses Selenium for forms that look like:

- name
- email
- phone
- file upload
- message
- submit button

Complex URLs containing signals such as login, captcha, assessment, or questionnaire are not treated as simple forms.

## External Complex Apply

Complex forms are routed to `ExternalApplyEngine`.

If there is no site-specific adapter for a domain, the result is:

```text
requires_adapter
```

This is intentional. Real full auto-apply for complex Israeli job sites should be implemented with dedicated adapters per site or ATS, not one fragile generic bot.

## Smoke test

```powershell
python -m src.apply.smoke_test
```

This test runs in dry-run mode and does not send an application.
