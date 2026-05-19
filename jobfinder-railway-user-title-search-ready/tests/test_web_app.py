import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.web.app import app, prepare_new_search_run, search_diagnostics, split_titles, status


def test_home_page_is_branded_jobfinder():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "JobFinder" in response.text
    assert "/assets/brand/jobfinder-logo.png" in response.text
    assert "https://paypage.takbull.co.il/2dBbl" in response.text


def test_product_pages_load():
    client = TestClient(app)

    for path in ["/onboarding", "/dashboard", "/jobs", "/inbox", "/settings", "/upload-cv", "/login"]:
        response = client.get(path)
        assert response.status_code == 200
        assert "JobFinder" in response.text


def test_dashboard_contains_magic_ux_signals():
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "AI insights" in response.text
    assert "Activity feed" in response.text
    assert "מצב אישור לפני שליחה פעיל" in response.text
    assert "Type a job title" in response.text


def test_user_job_title_input_is_split_into_search_titles():
    assert split_titles("Backend Developer, Junior Economist\nData Analyst") == [
        "Backend Developer",
        "Junior Economist",
        "Data Analyst",
    ]


def test_railway_config_is_present():
    railway = json.loads(Path("railway.json").read_text(encoding="utf-8"))

    assert railway["build"]["builder"] == "DOCKERFILE"
    assert railway["deploy"]["startCommand"] == "sh start.sh"
    assert railway["deploy"]["healthcheckPath"] == "/api/status"


def test_cancel_search_endpoint_writes_progress(tmp_path, monkeypatch):
    config = tmp_path / "work_preferences.yaml"
    config.write_text(
        """
version: 4
output:
  summary_dir: "{tmp}/output"
subscription:
  enabled: true
  pay_url: https://paypage.takbull.co.il/2dBbl
  status_path: "{tmp}/output/subscription_status.json"
""".format(tmp=str(tmp_path).replace("\\", "/")),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORK_PREFERENCES_PATH", str(config))
    client = TestClient(app)

    response = client.post("/api/cancel-search")

    assert response.status_code == 200
    assert response.json()["phase"] == "cancelled"
    assert (tmp_path / "output" / "cancel_search.flag").exists()


def test_new_search_run_clears_stale_dashboard_results(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "automation_status.json").write_text(
        json.dumps(
            {
                "status": "old",
                "jobs_found_today": 99,
                "application_inbox": [{"title": "Old Sales Manager"}],
                "subscription_locked": False,
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "daily_summary.json").write_text("{}", encoding="utf-8")
    (output_dir / "ai_insights.json").write_text("{}", encoding="utf-8")
    config = tmp_path / "work_preferences.yaml"
    config.write_text(
        """
version: 4
automation:
  daily_application_limit: 100
output:
  summary_dir: "{tmp}/output"
subscription:
  enabled: true
  pay_url: https://paypage.takbull.co.il/2dBbl
  status_path: "{tmp}/output/subscription_status.json"
""".format(tmp=str(tmp_path).replace("\\", "/")),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORK_PREFERENCES_PATH", str(config))

    run_id = prepare_new_search_run("Backend Developer", target_jobs=100)
    current = status()

    assert run_id
    assert (output_dir / "automation_status.json").exists()
    assert not (output_dir / "daily_summary.json").exists()
    assert not (output_dir / "ai_insights.json").exists()
    assert (output_dir / "active_search_run.json").exists()
    assert current["search_in_progress"] is True
    assert current["jobs_found_today"] == 0
    assert current["application_inbox"] == []
    assert current["search_title"] == "Backend Developer"


def test_status_refuses_stale_results_when_active_run_exists(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "active_search_run.json").write_text(
        json.dumps({"run_id": "new-run", "search_title": "Backend Developer"}),
        encoding="utf-8",
    )
    (output_dir / "automation_status.json").write_text(
        json.dumps(
            {
                "run_id": "old-run",
                "status": "old complete",
                "jobs_found_today": 50,
                "application_inbox": [{"title": "Old Sales Manager"}],
                "subscription_locked": False,
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "work_preferences.yaml"
    config.write_text(
        """
version: 4
automation:
  daily_application_limit: 100
output:
  summary_dir: "{tmp}/output"
subscription:
  enabled: true
  pay_url: https://paypage.takbull.co.il/2dBbl
  status_path: "{tmp}/output/subscription_status.json"
""".format(tmp=str(tmp_path).replace("\\", "/")),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORK_PREFERENCES_PATH", str(config))

    current = status()

    assert current["jobs_found_today"] == 0
    assert current["application_inbox"] == []
    assert "ישנות לא מוצגות" in current["status"]


def test_search_diagnostics_returns_records(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "active_search_run.json").write_text(
        json.dumps({"run_id": "run-1", "search_title": "Backend Developer"}),
        encoding="utf-8",
    )
    (output_dir / "search_diagnostics.jsonl").write_text(
        json.dumps({"source": "jobmaster", "query": "Backend Developer", "fetched_count": 3, "accepted_count": 2})
        + "\n",
        encoding="utf-8",
    )
    config = tmp_path / "work_preferences.yaml"
    config.write_text(
        """
version: 4
output:
  summary_dir: "{tmp}/output"
subscription:
  enabled: true
  pay_url: https://paypage.takbull.co.il/2dBbl
  status_path: "{tmp}/output/subscription_status.json"
""".format(tmp=str(tmp_path).replace("\\", "/")),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORK_PREFERENCES_PATH", str(config))

    payload = search_diagnostics()

    assert payload["active_run"]["run_id"] == "run-1"
    assert payload["records"][0]["source"] == "jobmaster"


def test_takbull_webhook_unlocks_subscription(tmp_path, monkeypatch):
    config = tmp_path / "work_preferences.yaml"
    config.write_text(
        """
version: 4
output:
  summary_dir: "{tmp}/output"
subscription:
  enabled: true
  pay_url: https://paypage.takbull.co.il/2dBbl
  status_path: "{tmp}/output/subscription_status.json"
  webhook_secret_env: TAKBULL_WEBHOOK_SECRET
""".format(tmp=str(tmp_path).replace("\\", "/")),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORK_PREFERENCES_PATH", str(config))
    client = TestClient(app)

    response = client.post("/webhooks/takbull", json={"status": "paid", "email": "user@example.com"})

    assert response.status_code == 200
    assert response.json()["subscription_active"] is True
