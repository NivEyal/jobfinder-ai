# Step 2: Israeli Source Adapters

This step adds a dedicated adapter layer for Israeli job sources.

Each adapter returns the same `IsraeliJob` structure:

```python
IsraeliJob(
    source,
    source_job_id,
    title,
    company,
    location,
    description,
    apply_url,
    apply_email,
    apply_method,
    posted_at,
)
```

Adapters live in `src/israel_sources`:

- `drushim.py`
- `alljobs.py`
- `jobmaster.py`
- `gotfriends.py`
- `indeed.py`
- `Jobnet.py`
- `company_careers.py`

On Windows, `drushim.py` and `Drushim.py` cannot both exist in the same folder. The registry therefore exposes both `drushim` and `Drushim` as source names that point to `drushim.py`.

## Validate

```bash
python -m src.israel_sources.smoke_test
```

This validates that every adapter can produce the required `IsraeliJob` contract.

Live validation:

```bash
python -m src.israel_sources.smoke_test --live --keyword "Software Engineer" --location Israel --min-total 20 --min-sources 4
```

The live test fetches real pages and prints a per-source report. Some sources may block server-side scraping; the test still fails unless enough real jobs are collected from live Israeli sources.
