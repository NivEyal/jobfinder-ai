# Step 5: Hebrew and English Normalization

New package:

- `src/israel_normalization/normalize_location.py`
- `src/israel_normalization/normalize_title.py`
- `src/israel_normalization/normalize_company.py`
- `src/israel_normalization/normalize_seniority.py`
- `src/israel_normalization/normalize_remote_type.py`
- `src/israel_normalization/normalize_salary.py`

Also included:

- `normalize_employment_type.py` for values such as `משרה מלאה -> full_time`.
- `text.py` for shared text cleanup helpers.

Examples:

- `ת״א`, `תל אביב`, `Tel Aviv` -> `תל אביב` or `Tel Aviv` according to `output.normalized_language`.
- `היברידי`, `Hybrid` -> `hybrid`.
- `ללא ניסיון`, `Junior`, `0-1` -> `entry` or `junior` according to the phrase.
- `משרה מלאה` -> `full_time`.

Set `output.normalized_language` in `work_preferences.yaml` to `he` or `en`.
