# Step 3: Expanded Job Model

`src/job.py` now models Israeli job data directly.

Fields:

- `source`
- `source_job_id`
- `canonical_url`
- `company`
- `title`
- `location`
- `region`
- `remote_type`: `remote`, `hybrid`, `onsite`
- `employment_type`: `full_time`, `part_time`, `contract`
- `seniority`
- `years_experience`
- `salary_min`
- `salary_max`
- `language`: `he`, `en`, `mixed`
- `apply_email`
- `apply_url`
- `fingerprint`
- `first_seen_at`
- `last_seen_at`
- `status`

The model keeps backward-compatible aliases:

- `role` maps to `title`
- `link` maps to `canonical_url`
- `id` maps to `fingerprint`

`IsraeliJob.to_job()` converts source-adapter output into the expanded `Job` model.
