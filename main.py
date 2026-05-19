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
        cls._require_type(market, "include_remote_worldwide", bool, config_path)
        cls._require_list_of_strings(market, "languages", config_path)
        cls._validate_allowed_values(market["languages"], cls.LANGUAGES, "market.languages", config_path)

    @classmethod
    def _validate_search(cls, search: dict, config_path: Path):
        cls._require_list_of_strings(search, "keywords", config_path)
        if not search["keywords"]:
            raise ConfigError(f"search.keywords cannot be empty in {config_path}")
        cls._require_type(search, "keyword_aliases", dict, config_path)
        for key, aliases in search["keyword_aliases"].items():
            if not isinstance(key, str) or not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
                raise ConfigError(f"search.keyword_aliases must map strings to lists of strings in {config_path}")
        cls._require_type(search, "locations", dict, config_path)
        cls._require_list_of_strings(search["locations"], "israel", config_path)
        cls._require_list_of_strings(search["locations"], "worldwide", config_path)
        cls._require_list_of_strings(search, "remote_types", config_path)
        cls._require_list_of_strings(search, "employment_types", config_path)
        cls._require_list_of_strings(search, "seniority", config_path)
        cls._validate_allowed_values(search["remote_types"], cls.REMOTE_TYPES, "search.remote_types", config_path)
        cls._validate_allowed_values(search["employment_types"], cls.EMPLOYMENT_TYPES, "search.employment_types", config_path)
        cls._validate_allowed_values(search["seniority"], cls.SENIORITY_LEVELS, "search.seniority", config_path)
        cls._require_type(search, "years_experience", dict, config_path)
        cls._require_type(search["years_experience"], "min", int, config_path)
        cls._require_type(search["years_experience"], "max", int, config_path)
        cls._require_type(search, "salary", dict, config_path)
        cls._require_type(search["salary"], "currency", str, config_path)
        cls._require_type(search["salary"], "min", int, config_path)
        cls._require_type(search["salary"], "max", int, config_path)
        cls._require_type(search, "date_posted", str, config_path)
        cls._validate_allowed_values([search["date_posted"]], cls.DATE_FILTERS, "search.date_posted", config_path)

    @classmethod
    def _validate_sources(cls, sources: dict, config_path: Path):
        cls._require_list_of_strings(sources, "enabled", config_path)
        cls._validate_allowed_values(sources["enabled"], cls.KNOWN_SOURCES, "sources.enabled", config_path)
        cls._require_type(sources, "limits", dict, config_path)
        cls._require_type(sources["limits"], "total_jobs", int, config_path)
        cls._require_type(sources["limits"], "jobs_per_source", int, config_path)
        cls._require_type(sources["limits"], "max_pages", int, config_path)

    @classmethod
    def _validate_filters(cls, filters: dict, config_path: Path):
        for section in ["include", "exclude"]:
            cls._require_type(filters, section, dict, config_path)
        for key in ["must_have_keywords", "nice_to_have_keywords"]:
            cls._require_list_of_strings(filters["include"], key, config_path)
        for key in ["companies", "titles", "locations", "keywords"]:
            cls._require_list_of_strings(filters["exclude"], key, config_path)

    @classmethod
    def _validate_matching(cls, matching: dict, config_path: Path):
        cls._require_type(matching, "enabled", bool, config_path)
        cls._require_type(matching, "provider", str, config_path)
        cls._validate_allowed_values([matching["provider"]], {"openai", "rule_based"}, "matching.provider", config_path)
        cls._require_type(matching, "model", str, config_path)
        cls._require_type(matching, "api_key_env", str, config_path)
        cls._require_type(matching, "fallback", str, config_path)
        cls._validate_allowed_values([matching["fallback"]], {"rule_based"}, "matching.fallback", config_path)
        for key in [
            "minimum_score",
            "strong_match_score",
            "possible_match_score",
            "openai_max_jobs_per_run",
            "openai_max_workers",
            "max_description_chars",
            "timeout_seconds",
        ]:
            cls._require_type(matching, key, int, config_path)
        if not 0 <= matching["possible_match_score"] <= matching["strong_match_score"] <= 100:
            raise ConfigError(f"matching thresholds must be between 0 and 100 in {config_path}")

    @classmethod
    def _validate_apply(cls, apply_config: dict, config_path: Path):
        cls._require_type(apply_config, "enabled", bool, config_path)
        cls._require_type(apply_config, "dry_run", bool, config_path)
        cls._require_type(apply_config, "minimum_match_score", int, config_path)
        cls._require_type(apply_config, "require_resume_file", bool, config_path)
        cls._require_type(apply_config, "ledger_path", str, config_path)
        cls._require_list_of_strings(apply_config, "allowed_methods", config_path)
        cls._validate_allowed_values(
            apply_config["allowed_methods"],
            {"email", "form", "external"},
            "apply.allowed_methods",
            config_path,
        )
        for section in ["email", "form", "external"]:
            cls._require_type(apply_config, section, dict, config_path)
        for key in ["provider", "api_key_env", "api_url_env", "from_email_env", "reply_to_env"]:
            cls._require_type(apply_config["email"], key, str, config_path)
        cls._require_type(apply_config["email"], "timeout_seconds", int, config_path)
        cls._validate_allowed_values([apply_config["email"]["provider"]], {"resend"}, "apply.email.provider", config_path)
        cls._require_type(apply_config["form"], "timeout_seconds", int, config_path)
        cls._require_type(apply_config["form"], "submit_selector", str, config_path)
        cls._require_list_of_strings(apply_config["external"], "complex_indicators", config_path)

    @classmethod
    def _validate_storage(cls, storage: dict, config_path: Path):
        cls._require_type(storage, "enabled", bool, config_path)
        cls._require_type(storage, "backend", str, config_path)
        cls._validate_allowed_values([storage["backend"]], {"sqlite"}, "storage.backend", config_path)
        cls._require_type(storage, "sqlite_path", str, config_path)
        cls._require_type(storage, "jsonl_dir", str, config_path)
        cls._require_type(storage, "save_source_snapshots", bool, config_path)

    @classmethod
    def _validate_automation(cls, automation: dict, config_path: Path):
        cls._require_type(automation, "enabled", bool, config_path)
        cls._require_type(automation, "status", str, config_path)
        cls._validate_allowed_values([automation["status"]], {"active", "paused"}, "automation.status", config_path)
        cls._require_type(automation, "daily_time", str, config_path)
        cls._require_type(automation, "daily_application_limit", int, config_path)
        cls._require_type(automation, "application_mode", str, config_path)
        cls._validate_allowed_values(
            [automation["application_mode"]],
            {"full_auto", "approval_before_send", "save_matches_only"},
            "automation.application_mode",
            config_path,
        )
        cls._require_type(automation, "match_threshold", int, config_path)
        cls._validate_allowed_values([str(automation["match_threshold"])], {"60", "70", "80"}, "automation.match_threshold", config_path)
        cls._require_type(automation, "expire_after_days", int, config_path)

    @classmethod
    def _validate_subscription(cls, subscription: dict, config_path: Path):
        cls._require_type(subscription, "enabled", bool, config_path)
        cls._require_type(subscription, "pay_url", str, config_path)
        cls._require_type(subscription, "unlock_env", str, config_path)
        cls._require_type(subscription, "status_path", str, config_path)
        cls._require_type(subscription, "webhook_secret_env", str, config_path)
        cls._require_type(subscription, "reveal_after_jobs_count", int, config_path)
        cls._require_list_of_strings(subscription, "blocked_actions", config_path)

    @classmethod
    def _validate_users(cls, users: list, config_path: Path):
        for user in users:
            if not isinstance(user, dict):
                raise ConfigError(f"users must contain objects in {config_path}")
            for key in ["id", "name", "email", "phone"]:
                cls._require_type(user, key, str, config_path)
            cls._require_type(user, "active", bool, config_path)
            if "subscription" in user:
                cls._require_type(user["subscription"], "active", bool, config_path)

    @classmethod
    def _validate_output(cls, output: dict, config_path: Path):
        cls._require_type(output, "save_raw_results", bool, config_path)
        cls._require_type(output, "deduplicate", bool, config_path)
        cls._require_type(output, "sort_by", str, config_path)
        cls._require_type(output, "normalized_language", str, config_path)
        cls._validate_allowed_values([output["normalized_language"]], {"he", "en"}, "output.normalized_language", config_path)

    @classmethod
    def _require_type(cls, container: dict, key: str, expected_type: type, config_path: Path):
        if key not in container:
            raise ConfigError(f"Missing key '{key}' in {config_path}")
        if not isinstance(container[key], expected_type):
            raise ConfigError(f"'{key}' must be a {expected_type.__name__} in {config_path}")

    @classmethod
    def _require_list_of_strings(cls, container: dict, key: str, config_path: Path):
        if key not in container:
            raise ConfigError(f"Missing key '{key}' in {config_path}")
        if not isinstance(container[key], list) or not all(isinstance(item, str) for item in container[key]):
            raise ConfigError(f"'{key}' must be a list of strings in {config_path}")

    @classmethod
    def _validate_allowed_values(cls, values: List[str], allowed_values: set[str], field_name: str, config_path: Path):
        invalid_values = [value for value in values if value not in allowed_values]
        if invalid_values:
            raise ConfigError(
                f"Invalid values for {field_name} in {config_path}: {invalid_values}. "
                f"Expected values from {sorted(allowed_values)}"
            )


class SearchPlanBuilder:
    """Builds broad, source-friendly search queries from the Israeli config."""

    @staticmethod
    def build(config: Dict[str, Any]) -> Dict[str, Any]:
        search = config["search"]
        market = config["market"]
        sources = config["sources"]
        keywords = SearchPlanBuilder.expand_keywords(search["keywords"], search.get("keyword_aliases", {}))
        locations = list(search["locations"]["israel"])
        if market["include_worldwide"]:
            locations.extend(search["locations"]["worldwide"])
        if market["include_remote_worldwide"] and "Remote" not in locations:
            locations.append("Remote")

        queries = []
        for keyword in keywords:
            queries.append(
                {
                    "keywords": [keyword],
                    "locations": SearchPlanBuilder.unique(locations),
                    "limit": sources["limits"]["jobs_per_source"],
                }
            )

        return {
            "keywords": keywords,
            "locations": SearchPlanBuilder.unique(locations),
            "queries": queries,
            "sources": sources["enabled"],
            "total_limit": sources["limits"]["total_jobs"],
            "jobs_per_source": sources["limits"]["jobs_per_source"],
            "max_pages": sources["limits"]["max_pages"],
            "normalized_language": config["output"]["normalized_language"],
        }

    @staticmethod
    def expand_keywords(keywords: List[str], aliases: Dict[str, List[str]]) -> List[str]:
        expanded = []
        reverse_aliases: Dict[str, List[str]] = {}
        for canonical, alias_values in aliases.items():
            for alias in alias_values:
                reverse_aliases.setdefault(alias, []).append(canonical)
                reverse_aliases[alias].extend(alias_values)
        for keyword in keywords:
            expanded.append(keyword)
            expanded.extend(aliases.get(keyword, []))
            expanded.extend(reverse_aliases.get(keyword, []))
        return SearchPlanBuilder.unique(expanded)

    @staticmethod
    def unique(values: List[str]) -> List[str]:
        return list(dict.fromkeys(value for value in values if value))


class FileManager:
    """Handles local static application files."""

    REQUIRED_FILES = [WORK_PREFERENCES_YAML, PLAIN_TEXT_RESUME_YAML, STATIC_COVER_LETTER_TEMPLATE]

    @staticmethod
    def validate_data_folder(app_data_folder: Path) -> Tuple[Path, Path, Path, Path]:
        if not app_data_folder.is_dir():
            raise FileNotFoundError(f"Data folder not found: {app_data_folder}")

        missing_files = [file for file in FileManager.REQUIRED_FILES if not (app_data_folder / file).exists()]
        if missing_files:
            raise FileNotFoundError(f"Missing files in data folder: {', '.join(missing_files)}")

        output_folder = app_data_folder / "output"
        output_folder.mkdir(exist_ok=True)

        return (
            app_data_folder / WORK_PREFERENCES_YAML,
            app_data_folder / PLAIN_TEXT_RESUME_YAML,
            app_data_folder / STATIC_COVER_LETTER_TEMPLATE,
            output_folder,
        )

    @staticmethod
    def get_uploads(plain_text_resume_file: Path, cover_letter_template_file: Path) -> Dict[str, Path]:
        IsraeliResume.from_path(plain_text_resume_file)
        return {
            "resume": plain_text_resume_file,
            "cover_letter_template": cover_letter_template_file,
        }


def prepare_static_application_package(parameters: dict):
    """Prepare static application files without LinkedIn, Easy Apply, or LLM flows."""
    output_dir = Path(parameters["outputFileDirectory"])
    uploads = parameters["uploads"]
    search_plan = SearchPlanBuilder.build(parameters)
    search_engine = IsraelSearchEngine(sources=search_plan["sources"], max_pages=search_plan["max_pages"])
    matcher = JobMatcher(parameters) if parameters.get("matching", {}).get("enabled", True) else None

    shutil.copy2(uploads["resume"], output_dir / "resume_ready_to_send.yaml")
    shutil.copy2(uploads["cover_letter_template"], output_dir / "cover_letter_template.txt")

    sources_path = output_dir / "israeli_sources.json"
    with open(sources_path, "w", encoding="utf-8") as sources_file:
        json.dump(
            {
                "step": 2,
                "search_engine": "IsraelSearchEngine",
                "sources": search_engine.source_names(),
                "search_plan": search_plan,
                "matching": {
                    "enabled": parameters["matching"]["enabled"],
                    "provider": parameters["matching"]["provider"],
                    "model": parameters["matching"]["model"],
                    "api_key_env": parameters["matching"]["api_key_env"],
                    "fallback": parameters["matching"]["fallback"],
                    "minimum_score": parameters["matching"]["minimum_score"],
                    "matcher_class": matcher.__class__.__name__ if matcher else None,
                },
                "apply": {
                    "enabled": parameters["apply"]["enabled"],
                    "dry_run": parameters["apply"]["dry_run"],
                    "minimum_match_score": parameters["apply"]["minimum_match_score"],
                    "allowed_methods": parameters["apply"]["allowed_methods"],
                    "ledger_path": parameters["apply"]["ledger_path"],
                },
                "storage": {
                    "enabled": parameters["storage"]["enabled"],
                    "backend": parameters["storage"]["backend"],
                    "sqlite_path": parameters["storage"]["sqlite_path"],
                    "jsonl_dir": parameters["storage"]["jsonl_dir"],
                    "save_source_snapshots": parameters["storage"]["save_source_snapshots"],
                },
                "automation": {
                    "enabled": parameters["automation"]["enabled"],
                    "status": parameters["automation"]["status"],
                    "daily_time": parameters["automation"]["daily_time"],
                    "daily_application_limit": parameters["automation"]["daily_application_limit"],
                    "application_mode": parameters["automation"]["application_mode"],
                    "match_threshold": parameters["automation"]["match_threshold"],
                },
                "subscription": {
                    "enabled": parameters["subscription"]["enabled"],
                    "pay_url": parameters["subscription"]["pay_url"],
                    "unlock_env": parameters["subscription"]["unlock_env"],
                    "status_path": parameters["subscription"]["status_path"],
                    "webhook_secret_env": parameters["subscription"]["webhook_secret_env"],
                    "reveal_after_jobs_count": parameters["subscription"]["reveal_after_jobs_count"],
                    "blocked_actions": parameters["subscription"]["blocked_actions"],
                },
                "job_contract": [
                    "source",
                    "source_job_id",
                    "title",
                    "company",
                    "location",
                    "description",
                    "apply_url",
                    "apply_email",
                    "apply_method",
                    "posted_at",
                ],
            },
            sources_file,
            ensure_ascii=False,
            indent=2,
        )

    summary_path = output_dir / "step1_static_mode_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as summary:
        summary.write("Step 1 complete: static Israeli-market application mode is enabled.\n")
        summary.write("Step 2 complete: Israeli source adapters are registered.\n")
        summary.write("Step 4 complete: Israeli/worldwide work preferences config is active.\n")
        summary.write("Step 6 complete: matching is enabled with OpenAI plus rule-based fallback.\n")
        summary.write("Step 7 complete: auto-apply engines are configured with guardrails and dry-run default.\n")
        summary.write("Step 8 complete: SQLite and JSONL storage are configured for jobs, applications, runs, errors, logs, and snapshots.\n")
        summary.write("Step 9 complete: Israeli bilingual resume template is active with Hebrew RTL and English LTR versions.\n")
        summary.write("Step 10 complete: daily_pipeline command is configured for one-command automation.\n")
        summary.write("Subscription gate enabled: users see jobs found before premium actions are blocked.\n")
        summary.write("OpenAI key handling: set OPENAI_API_KEY in the runtime environment; no key is stored in files.\n")
        summary.write("Disabled assumptions: LinkedIn, Easy Apply, LLM answers, and AI-tailored resumes.\n")
        summary.write("Use the prepared resume file and fixed cover-letter template for future application flows.\n")

    logger.info(f"Static application package prepared at: {output_dir}")


def main():
    """Main entry point for the static, non-AI job application workflow."""
    try:
        data_folder = Path("data_folder")
        config_file, plain_text_resume_file, cover_letter_template_file, output_folder = FileManager.validate_data_folder(
            data_folder
        )

        config = ConfigValidator.validate_config(config_file)
        config["uploads"] = FileManager.get_uploads(plain_text_resume_file, cover_letter_template_file)
        config["outputFileDirectory"] = output_folder

        prepare_static_application_package(config)

    except ConfigError as ce:
        logger.error(f"Configuration error: {ce}")
    except IsraeliResumeError as ire:
        logger.error(f"Israeli resume template error: {ire}")
    except FileNotFoundError as fnf:
        logger.error(f"File not found: {fnf}")
        logger.error("Ensure all required files are present in the data folder.")
    except RuntimeError as re:
        logger.error(f"Runtime error: {re}")
        logger.debug(traceback.format_exc())
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
