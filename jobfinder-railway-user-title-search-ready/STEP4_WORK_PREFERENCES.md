# Step 4: Israeli and Worldwide Work Preferences

`data_folder/work_preferences.yaml` now uses `version: 4`.

The new structure is designed for broad searches:

- Israeli locations are explicit and include major employment hubs.
- Worldwide and remote locations are included.
- Search terms are expanded with English and Hebrew aliases.
- Remote type, employment type, seniority, years of experience, salary, and language are all first-class filters.
- Sources have limits for total jobs, jobs per source, and pagination.

Important: the current implemented live sources are still the Step 2 Israeli adapters. The config now supports worldwide intent and remote-worldwide queries, but additional worldwide source adapters will be needed for truly global coverage beyond sources such as Indeed and company career pages.
