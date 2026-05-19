# In this file, you can set the configurations of the app.

from src.utils.constants import ERROR

#config related to logging must have prefix LOG_
LOG_LEVEL = 'ERROR'
LOG_SELENIUM_LEVEL = ERROR
LOG_TO_FILE = False
LOG_TO_CONSOLE = False

MINIMUM_WAIT_TIME_IN_SECONDS = 60

JOB_APPLICATIONS_DIR = "job_applications"

# Step 1 runs in static mode: no LinkedIn, Easy Apply, or LLM configuration.
ENABLE_LINKEDIN_FLOW = False
ENABLE_EASY_APPLY_FLOW = False
ENABLE_LLM_FLOW = False
