import json
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from src.israel_sources.search_engine import IsraelSearchEngine
from src.logging import logger
from src.matching.matcher import JobMatcher
from src.resume_schemas.israeli_resume import IsraeliResume, IsraeliResumeError
from src.utils.constants import PLAIN_TEXT_RESUME_YAML, WORK_PREFERENCES_YAML


STATIC_COVER_LETTER_TEMPLATE = "cover_letter_template.txt"


class ConfigError(Exception):
    """Custom exception for configuration-related errors."""


class ConfigValidator:
    """Validates local, non-AI configuration files."""

    REQUIRED_SECTIONS = {
        "market": dict,
        "search": dict,
        "sources": dict,
        "filters": dict,
        "matching": dict,
        "apply": dict,
        "storage": dict,
        "automation": dict,
        "subscription": dict,
        "users": list,
        "output": dict,
    }
    REMOTE_TYPES = {"remote", "hybrid", "onsite"}
    EMPLOYMENT_TYPES = {"full_time", "part_time", "contract", "temporary", "internship"}
    LANGUAGES = {"he", "en", "mixed"}
    SENIORITY_LEVELS = {"internship", "junior", "entry", "mid", "senior", "lead", "management", "executive"}
    DATE_FILTERS = {"all_time", "month", "week", "24_hours"}
    KNOWN_SOURCES = {
        "drushim",
        "alljobs",
        "jobmaster",
        "gotfriends",
        "indeed",
        "Jobnet",
        "jobnet",
        "company_careers",
        "remotive",
        "arbeitnow",
        "remoteok",
        "greenhouse",
        "lever",
    }

    @staticmethod
    def load_yaml(yaml_path: Path) -> dict:
        """Load and parse a YAML file."""
        try:
            with open(yaml_path, "r", encoding="utf-8") as stream:
                return yaml.safe_load(stream) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Error reading YAML file {yaml_path}: {exc}") from exc
        except FileNotFoundError as exc:
            raise ConfigError(f"YAML file not found: {yaml_path}") from exc

    @classmethod
    def validate_config(cls, config_yaml_path: Path) -> dict:
        """Validate the Israeli-market search configuration YAML file."""
        parameters = cls.load_yaml(config_yaml_path)
        if parameters.get("version") != 4:
            raise ConfigError(f"work_preferences.yaml must use version: 4 in {config_yaml_path}")

        for section, expected_type in cls.REQUIRED_SECTIONS.items():
            if section not in parameters:
                raise ConfigError(f"Missing required section '{section}' in {config_yaml_path}")
            if not isinstance(parameters[section], expected_type):
                raise ConfigError(f"Section '{section}' must be a {expected_type.__name__} in {config_yaml_path}")

        cls._validate_market(parameters["market"], config_yaml_path)
        cls._validate_search(parameters["search"], config_yaml_path)
        cls._validate_sources(parameters["sources"], config_yaml_path)
        cls._validate_filters(parameters["filters"], config_yaml_path)
        cls._validate_matching(parameters["matching"], config_yaml_path)
        cls._validate_apply(parameters["apply"], config_yaml_path)
        cls._validate_storage(parameters["storage"], config_yaml_path)
        cls._validate_automation(parameters["automation"], config_yaml_path)
        cls._validate_subscription(parameters["subscription"], config_yaml_path)
        cls._validate_users(parameters["users"], config_yaml_path)
        cls._validate_output(parameters["output"], config_yaml_path)
        return parameters

    @classmethod
    def _validate_market(cls, market: dict, config_path: Path):
        cls._require_type(market, "primary_country", str, config_path)
        cls._require_type(market, "include_worldwide", bool, config_path)
