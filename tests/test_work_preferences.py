from pathlib import Path

from main import ConfigValidator, SearchPlanBuilder
from src.israel_sources.search_engine import IsraelSearchEngine


def test_work_preferences_v4_validates_and_builds_broad_search_plan():
    config = ConfigValidator.validate_config(Path("data_folder/work_preferences.yaml"))
    plan = SearchPlanBuilder.build(config)

    assert config["version"] == 4
    assert config["market"]["primary_country"] == "Israel"
    assert config["market"]["include_worldwide"] is True
    assert "Software Engineer" in plan["keywords"]
    assert "מפתח תוכנה" in plan["keywords"]
    assert "Remote" in plan["locations"]
    assert "Tel Aviv" in plan["locations"]
    assert "Worldwide" in plan["locations"]
    assert plan["total_limit"] == 2500
    assert plan["jobs_per_source"] == 200
    assert plan["max_pages"] == 12
    assert plan["normalized_language"] == "he"
    assert config["matching"]["provider"] == "openai"
    assert config["matching"]["api_key_env"] == "OPENAI_API_KEY"
    assert config["matching"]["fallback"] == "rule_based"
    assert config["apply"]["enabled"] is True
    assert config["apply"]["dry_run"] is False
    assert "email" in config["apply"]["allowed_methods"]
    assert config["storage"]["backend"] == "sqlite"
    assert config["storage"]["sqlite_path"].endswith(".sqlite3")
    assert config["automation"]["status"] == "active"
    assert config["automation"]["daily_application_limit"] == 100
    assert config["automation"]["application_mode"] == "full_auto"
    assert config["automation"]["match_threshold"] == 70
    assert config["subscription"]["enabled"] is True
    assert config["subscription"]["pay_url"] == "https://paypage.takbull.co.il/2dBbl"
    assert config["users"][0]["active"] is True
    assert config["users"][0]["subscription"]["active"] is False
    assert plan["queries"]
    assert all(len(query["keywords"]) == 1 for query in plan["queries"])


def test_search_engine_accepts_configured_sources_and_pagination():
    config = ConfigValidator.validate_config(Path("data_folder/work_preferences.yaml"))
    plan = SearchPlanBuilder.build(config)
    engine = IsraelSearchEngine(sources=plan["sources"], max_pages=plan["max_pages"])

    assert engine.source_names() == [
        "drushim",
        "alljobs",
        "jobmaster",
        "gotfriends",
        "indeed",
        "jobnet",
        "company_careers",
        "remotive",
        "arbeitnow",
        "remoteok",
        "greenhouse",
        "lever",
    ]
    assert all(adapter.max_pages == 12 for adapter in engine.adapters)
