import json
import os
import threading
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.commands.daily_pipeline import DailyPipeline


APP_NAME = "JobFinder"
BRAND_TAGLINE = "מחברים אותך להזדמנות הבאה שלך"
DEFAULT_CONFIG_PATH = "data_folder/work_preferences.yaml"

app = FastAPI(title=APP_NAME)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


@app.get("/")
def root() -> HTMLResponse:
    config = load_config()
    return page(
        "JobFinder | מציאת עבודה והגשה חכמה",
        f"""
        <section class="hero">
          <div>
            <span class="eyebrow">AI job agent for Israel</span>
            <h1>JobFinder<br><span class="gradient">מוצא. מתאים. מגיש.</span></h1>
            <p>{BRAND_TAGLINE}. חיפוש משרות, דירוג התאמה, Application Inbox ומצב אישור לפני שליחה במקום אחד.</p>
            <div class="actions">
              <a class="button primary" href="/onboarding">התחל ב-2 דקות</a>
              <a class="button secondary" href="/dashboard">פתח דשבורד</a>
              <a class="button ghost" href="{config['subscription']['pay_url']}">הפעל מנוי</a>
            </div>
          </div>
          <div class="logo-panel"><img src="/assets/brand/jobfinder-logo.png" alt="JobFinder" /></div>
        </section>
        <section class="trust">
          <div>AI לא שולח בלי אישור במצב ברירת המחדל</div>
          <div>קורות החיים לא מפורסמים לציבור</div>
          <div>כל פעולה נרשמת בלוג</div>
        </section>
        """,
        landing=True,
    )


@app.get("/onboarding")
def onboarding() -> HTMLResponse:
    config = load_config()
    current_title = ", ".join(config.get("search", {}).get("keywords", [])[:3])
    return page(
        "JobFinder Onboarding",
        f"""
        <section class="onboarding">
          <div class="panel">
            <span class="eyebrow">Step 1 of 4</span>
            <h1>העלה קורות חיים ובחר טייטל לחיפוש.</h1>
            <p>JobFinder לא מנחש עבורך מקצועות. המשתמש מקליד את הטייטל הרצוי, והמערכת מחפשת לפי הטייטל הזה והקורות חיים שהועלו.</p>
            <form method="post" action="/upload-cv" enctype="multipart/form-data" class="dropzone">
              <label>טייטל לחיפוש</label>
              <input name="job_title" value="{escape(current_title)}" placeholder="לדוגמה: Junior Economist, Backend Developer" required />
              <strong>בחר קובץ קורות חיים</strong>
              <span>PDF, DOCX, YAML או TXT</span>
              <input type="file" name="resume" accept=".pdf,.doc,.docx,.yaml,.yml,.txt" required />
              <button class="primary" type="submit">שמור והתחל חיפוש</button>
            </form>
          </div>
          <div class="panel">
            <span class="eyebrow">User controlled search</span>
            <h2>מה המערכת עושה בפועל</h2>
            <div class="chips">
              <span>טייטל מהמשתמש</span><span>קורות חיים שהועלו</span><span>משרות מתאימות</span><span>הגשה בקליק</span>
            </div>
            <div class="timeline">
              <div><b>1</b><span>שומר את קורות החיים</span></div>
              <div><b>2</b><span>שומר את הטייטל שהמשתמש ביקש</span></div>
              <div><b>3</b><span>מחפש במקורות ישראליים וגלובליים</span></div>
              <div><b>4</b><span>מציג משרות ומאפשר הגשה מרוכזת</span></div>
            </div>
          </div>
        </section>
        """,
    )


@app.get("/login")
def login_page() -> HTMLResponse:
    return page(
        "כניסה ל-JobFinder",
        """
        <section class="panel narrow">
          <h1>כניסה ל-JobFinder</h1>
          <p>כניסה מהירה ל-MVP. בפרודקשן אפשר לחבר כאן Authentication מלא.</p>
          <form method="post" action="/login">
            <label>אימייל</label>
            <input name="email" type="email" value="candidate@example.com" required />
            <button class="primary" type="submit">המשך לדשבורד</button>
          </form>
        </section>
        """,
    )


@app.post("/login")
async def login(request: Request) -> RedirectResponse:
    form = await request.form()
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie("jobfinder_user", str(form.get("email", "")), httponly=True, samesite="lax")
    return response


@app.get("/dashboard")
def dashboard() -> HTMLResponse:
    config = load_config()
    current = status()
    metrics = metric_grid(
        [
            ("סטטוס", current.get("status", "לא רץ עדיין")),
            ("נמצאו היום", current.get("jobs_found_today", 0)),
            ("נשלחו היום", current.get("applications_sent_today", 0)),
            ("דורש אישור", current.get("requires_approval", 0)),
            ("מגבלת היום", current.get("daily_limit", f"0/{config['automation']['daily_application_limit']}")),
            ("מנוי", "פעיל" if not current.get("subscription_locked", True) else "נדרש"),
        ]
    )
    pay_button = ""
    if current.get("subscription_locked", True):
        pay_button = f"<a class='button secondary' href='{config['subscription']['pay_url']}'>הפעל מנוי</a>"
    progress_value = current.get("daily_limit", f"0/{config['automation']['daily_application_limit']}")
    jobs_found = current.get("jobs_found_today", 0)
    approval_count = current.get("requires_approval", 0)
    insights = ai_insights_html()
    return page(
        "JobFinder Dashboard",
        f"""
        <section class="app-layout">
          {sidebar("dashboard")}
          <div class="workspace">
            <section class="toolbar">
              <div>
                <span class="eyebrow">Your AI agent is active</span>
                <h1>הדשבורד שלך</h1>
                <p>JobFinder מחפש, מדרג ומכין הזדמנויות. אתה רואה התקדמות, סטטוס ומה דורש אישור.</p>
              </div>
              <div class="actions">
                {search_form("הרץ עכשיו")}
                <form method="post" action="/api/apply-all"><button class="primary" type="submit">הגש לכל המתאימות</button></form>
                {pay_button}
              </div>
            </section>
            {metrics}
            <section class="panel progress-card">
              <div>
                <span class="eyebrow">Apply progress</span>
                <h2>{progress_value} מהמגבלה היומית נוצלו</h2>
                <p>{jobs_found} משרות נמצאו היום. {approval_count} דורשות אישור לפני שליחה.</p>
              </div>
              <div class="progress"><span style="width:{progress_percent(progress_value)}%"></span></div>
            </section>
            <section class="grid two">
              <div class="panel">
                <span class="eyebrow">AI insights</span>
                <h2>מה כדאי לשפר עכשיו</h2>
                {insights}
              </div>
              <div class="panel">
                <span class="eyebrow">Activity feed</span>
                <div class="feed">
                  <div>✓ האוטומציה בדקה מקורות ישראליים</div>
                  <div>✓ קורות החיים נשמרים באופן פרטי</div>
                  <div>✓ AI לא שולח בלי אישור במצב הנוכחי</div>
                </div>
              </div>
            </section>
            <section class="trust">
              <div>קורות החיים שלך לא מפורסמים לציבור</div>
              <div>מצב אישור לפני שליחה פעיל</div>
              <div>כל פעולה נרשמת בלוג</div>
            </section>
          </div>
        </section>
        """,
    )


@app.get("/jobs")
def jobs_page() -> HTMLResponse:
    items = [item for item in status().get("application_inbox", []) if item.get("title")]
    cards = "".join(job_card(item) for item in items)
    if not cards:
        cards = """
        <div class="empty-state">
          <h2>Your AI agent is preparing new opportunities.</h2>
          <p>הרץ את הפייפליין כדי לראות משרות שנמצאו, ציוני התאמה והמלצות AI.</p>
          {search_form("מצא משרות עכשיו")}
        </div>
        """
    return page(
        "JobFinder Jobs",
        f"""
        <section class="app-layout">
          {sidebar("jobs")}
          <div class="workspace">
            <section class="toolbar">
              <div><span class="eyebrow">Matched jobs</span><h1>משרות שמתאימות לך</h1></div>
              {search_form("רענן התאמות")}
            </section>
            <section class="job-list">{cards}</section>
          </div>
        </section>
        """,
    )


@app.get("/inbox")
def inbox() -> HTMLResponse:
    items = status().get("application_inbox", [])
    if not items:
        rows = "<tr><td colspan='5'>Your AI agent is preparing new opportunities.</td></tr>"
    else:
        rows = "".join(
            "<tr>"
            f"<td>{item.get('status_label', item.get('status', ''))}</td>"
            f"<td>{item.get('title', '')}</td>"
            f"<td>{item.get('company', '')}</td>"
            f"<td>{item.get('score', '')}</td>"
            f"<td><a href='{item.get('apply_url') or item.get('pay_url') or '#'}'>פתח</a></td>"
            "</tr>"
            for item in items
        )
    return page(
        "Application Inbox",
        f"""
        <section class="app-layout">
          {sidebar("inbox")}
          <div class="workspace panel">
            <h1>Application Inbox</h1>
            <table>
              <thead><tr><th>מצב</th><th>משרה</th><th>חברה</th><th>ציון</th><th>קישור</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>
          </div>
        </section>
        """,
    )


@app.get("/settings")
def settings_page() -> HTMLResponse:
    config = load_config()
    automation = config["automation"]
    search = config["search"]
    title_value = ", ".join(search.get("keywords", [])[:5])
    return page(
        "הגדרות JobFinder",
        f"""
        <section class="app-layout">
          {sidebar("settings")}
          <div class="workspace panel narrow">
            <h1>הגדרות אוטומציה</h1>
            <form method="post" action="/settings">
              <label>Primary job title search</label>
              <input name="job_title" value="{title_value}" placeholder="Backend Developer, Junior Economist, Data Analyst" />
              <label>שעה יומית</label>
              <input name="daily_time" value="{automation['daily_time']}" />
              <label>מצב הגשה</label>
              <select name="application_mode">
                {option('full_auto', 'אוטומטי מלא', automation['application_mode'])}
                {option('approval_before_send', 'אישור לפני שליחה', automation['application_mode'])}
                {option('save_matches_only', 'רק שמירת התאמות', automation['application_mode'])}
              </select>
              <label>סף התאמה</label>
              <select name="match_threshold">
                {option('80', 'רק משרות בציון 80+', str(automation['match_threshold']))}
                {option('70', 'רק משרות בציון 70+', str(automation['match_threshold']))}
                {option('60', 'רק משרות בציון 60+', str(automation['match_threshold']))}
              </select>
              <label>סטטוס</label>
              <select name="status">
                {option('active', 'פעיל', automation['status'])}
                {option('paused', 'מושהה', automation['status'])}
              </select>
              <button class="primary" type="submit">שמור הגדרות</button>
            </form>
          </div>
        </section>
        """,
    )


@app.post("/settings")
async def save_settings(request: Request) -> RedirectResponse:
    form = await request.form()
    path = Path(config_path())
    config = load_config()
    job_title = str(form.get("job_title", "")).strip()
    if job_title:
        config["search"]["keywords"] = split_titles(job_title)
    config["automation"]["daily_time"] = str(form.get("daily_time", config["automation"]["daily_time"]))
    config["automation"]["application_mode"] = str(form.get("application_mode", config["automation"]["application_mode"]))
    config["automation"]["match_threshold"] = int(form.get("match_threshold", config["automation"]["match_threshold"]))
    config["automation"]["status"] = str(form.get("status", config["automation"]["status"]))
    path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return RedirectResponse("/settings", status_code=303)


@app.get("/upload-cv")
def upload_cv_page() -> HTMLResponse:
    return page(
        "העלאת קורות חיים",
        f"""
        <section class="app-layout">
          {sidebar("resume")}
          <div class="workspace panel narrow">
            <h1>העלאת קורות חיים</h1>
            <p>הקובץ יישמר וישמש כקובץ ההגשה בפועל. ב-Railway production מומלץ לחבר Volume כדי שהקובץ יישאר גם אחרי redeploy.</p>
            <form method="post" action="/upload-cv" enctype="multipart/form-data" class="dropzone">
              <label>טייטל לחיפוש</label>
              <input name="job_title" placeholder="לדוגמה: Junior Economist, Backend Developer" />
              <strong>בחר קובץ קורות חיים</strong>
              <input type="file" name="resume" accept=".pdf,.doc,.docx,.yaml,.yml,.txt" required />
              <button class="primary" type="submit">העלה קובץ</button>
            </form>
          </div>
        </section>
        """,
    )


@app.post("/upload-cv")
async def upload_cv(request: Request) -> RedirectResponse:
    form = await request.form()
    resume = form.get("resume")
    uploads_dir = Path("data_folder/output/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    if hasattr(resume, "filename") and hasattr(resume, "read"):
        target = uploads_dir / Path(resume.filename or "resume").name
        target.write_bytes(await resume.read())
        config = load_config()
        config.setdefault("output", {})["resume_upload_path"] = str(target).replace("\\", "/")
        job_title = str(form.get("job_title", "")).strip()
        if job_title:
            config["search"]["keywords"] = split_titles(job_title)
        Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return RedirectResponse("/dashboard", status_code=303)


@app.post("/api/run-ui")
async def run_pipeline_ui(request: Request) -> JSONResponse:
    form = await request.form()
    job_title = str(form.get("job_title", "")).strip()
    if job_title:
        update_search_titles(job_title)
    clear_cancel_flag()
    run_id = prepare_new_search_run(job_title or current_search_title(), target_jobs=100)
    start_background_pipeline(max_jobs=100)
    return JSONResponse({"ok": True, "started": True, "run_id": run_id, "redirect": "/dashboard"})


@app.post("/api/apply-all")
def apply_all_ui() -> JSONResponse:
    config = load_config()
    config["automation"]["application_mode"] = "full_auto"
    config["automation"]["daily_application_limit"] = 100
    config["apply"]["dry_run"] = False
    Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    clear_cancel_flag()
    run_id = prepare_new_search_run(current_search_title(), target_jobs=100)
    start_background_pipeline(max_jobs=100)
    return JSONResponse({"ok": True, "started": True, "run_id": run_id, "redirect": "/dashboard"})


@app.post("/api/cancel-search")
def cancel_search() -> Dict[str, Any]:
    config = load_config()
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cancel_search.flag").write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    progress_path = output_dir / "job_search_progress.json"
    found = 0
    target = 100
    if progress_path.exists():
        current = json.loads(progress_path.read_text(encoding="utf-8"))
        found = int(current.get("jobs_found_so_far", 0))
        target = int(current.get("target_jobs", 100))
    payload = {
        "message": "החיפוש נעצר. נשמרו המשרות שנמצאו עד עכשיו.",
        "phase": "cancelled",
        "jobs_found_so_far": found,
        "target_jobs": target,
        "percent": 100,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


@app.get("/api/status")
def status() -> Dict[str, Any]:
    config = load_config()
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    progress_path = output_dir / "job_search_progress.json"
    if progress_path.exists():
        progress_payload = json.loads(progress_path.read_text(encoding="utf-8"))
        if progress_payload.get("phase") in {"starting", "searching", "matching"}:
            return in_progress_status(config, progress_payload)
    status_path = output_dir / "automation_status.json"
    if status_path.exists():
        return json.loads(status_path.read_text(encoding="utf-8"))
    return {
        "status": "לא רץ עדיין",
        "subscription_locked": is_subscription_locked(config),
        "subscription_pay_url": config["subscription"]["pay_url"],
    }


@app.get("/api/progress")
def progress() -> Dict[str, Any]:
    config = load_config()
    progress_path = Path(config["output"].get("summary_dir", "data_folder/output")) / "job_search_progress.json"
    if progress_path.exists():
        return json.loads(progress_path.read_text(encoding="utf-8"))
    return {
        "message": "ממתין להתחלת חיפוש",
        "phase": "idle",
        "jobs_found_so_far": 0,
        "target_jobs": 100,
        "percent": 0,
    }


@app.post("/api/run")
def run_pipeline(max_jobs: int | None = None) -> Dict[str, Any]:
    summary = DailyPipeline(config_path=config_path()).run(max_jobs=max_jobs)
    return summary.to_user_status()


@app.post("/webhooks/takbull")
async def takbull_webhook(request: Request) -> JSONResponse:
    payload = await parse_payload(request)
    config = load_config()
    subscription = config["subscription"]
    expected_secret = os.getenv(subscription.get("webhook_secret_env", "TAKBULL_WEBHOOK_SECRET"), "")
    if expected_secret:
        provided_secret = request.headers.get("x-webhook-secret") or request.query_params.get("secret", "")
        if provided_secret != expected_secret:
            return JSONResponse({"ok": False, "error": "invalid webhook secret"}, status_code=401)

    payment_status = detect_payment_status(payload)
    active = payment_status in {"paid", "approved", "success", "completed", "new_transaction"}
    status_record = {
        "active": active,
        "provider": "takbull",
        "payment_status": payment_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "user_identifier": extract_user_identifier(payload),
        "raw_payload": payload,
    }
    status_path = Path(subscription["status_path"])
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status_record, ensure_ascii=False, indent=2), encoding="utf-8")
    return JSONResponse({"ok": True, "subscription_active": active, "payment_status": payment_status})


def page(title: str, body: str, landing: bool = False) -> HTMLResponse:
    nav = "" if landing else "<nav><a href='/dashboard'>Dashboard</a><a href='/jobs'>Jobs</a><a href='/inbox'>Inbox</a><a href='/settings'>Settings</a><a href='/upload-cv'>Resume</a></nav>"
    html = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <meta name="description" content="JobFinder מוצא משרות, מדרג התאמה ומנהל הגשות עבודה בישראל." />
  <link rel="icon" href="/assets/brand/jobfinder-logo.png" />
  <style>{css()}</style>
</head>
<body>
  <div class="shell">
    <header>
      <a class="brand" href="/"><img src="/assets/brand/jobfinder-logo.png" alt="JobFinder logo" /><span>JobFinder</span></a>
      {nav}
    </header>
    <main>{body}</main>
    <footer>JobFinder | {BRAND_TAGLINE}</footer>
  </div>
  <div id="loading-overlay" class="loading-overlay" hidden>
    <div class="loading-card">
      <div class="spinner"></div>
      <strong>JobFinder מחפש עבורך עד 100 משרות מתאימות</strong>
      <span id="loading-message">זה יכול לקחת דקה או שתיים כי המערכת בודקת מקורות בישראל ובעולם.</span>
      <div class="loading-progress"><span id="loading-progress-bar" style="width:0%"></span></div>
      <small id="loading-count">נמצאו 0 מתוך 100 משרות</small>
      <button id="cancel-search-button" class="secondary" type="button">עצור ושמור מה שנמצא</button>
    </div>
  </div>
  <script>
    let progressTimer = null;
    function setProgress(data) {{
      const count = document.getElementById("loading-count");
      const bar = document.getElementById("loading-progress-bar");
      const message = document.getElementById("loading-message");
      const found = data.jobs_found_so_far || 0;
      const target = data.target_jobs || 100;
      const percent = data.percent || Math.min(100, Math.round((found / Math.max(target, 1)) * 100));
      if (count) count.textContent = `נמצאו ${{found}} מתוך ${{target}} משרות`;
      if (bar) bar.style.width = `${{percent}}%`;
      if (message && data.message) message.textContent = data.message;
    }}
    async function pollProgress() {{
      try {{
        const response = await fetch("/api/progress", {{ cache: "no-store" }});
        if (response.ok) setProgress(await response.json());
      }} catch (error) {{}}
    }}
    async function cancelSearch() {{
      const button = document.getElementById("cancel-search-button");
      if (button) {{
        button.disabled = true;
        button.textContent = "עוצר...";
      }}
      try {{
        const response = await fetch("/api/cancel-search", {{ method: "POST" }});
        if (response.ok) setProgress(await response.json());
      }} catch (error) {{}}
    }}
    function showLoading(form) {{
      const overlay = document.getElementById("loading-overlay");
      if (overlay) overlay.hidden = false;
      setProgress({{ jobs_found_so_far: 0, target_jobs: 100, percent: 1, message: "מתחיל חיפוש..." }});
      if (progressTimer) clearInterval(progressTimer);
      progressTimer = setInterval(pollProgress, 1000);
      form.querySelectorAll("button").forEach((button) => {{
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.textContent = "טוען...";
      }});
    }}
    document.querySelectorAll("form").forEach((form) => {{
      form.addEventListener("submit", async (event) => {{
        const action = form.getAttribute("action") || "";
        const asyncAction = action === "/api/run-ui" || action === "/api/apply-all";
        showLoading(form);
        if (!asyncAction) return;
        event.preventDefault();
        try {{
          const response = await fetch(action, {{
            method: "POST",
            body: new FormData(form),
            redirect: "manual"
          }});
          const data = await response.json().catch(() => ({{}}));
          const done = setInterval(async () => {{
            await pollProgress();
            try {{
              const progressResponse = await fetch("/api/progress", {{ cache: "no-store" }});
              const progressData = await progressResponse.json();
              if (["complete", "cancelled", "failed"].includes(progressData.phase)) {{
                clearInterval(done);
                if (progressTimer) clearInterval(progressTimer);
                window.location.href = data.redirect || "/dashboard";
              }}
            }} catch (error) {{}}
          }}, 1200);
        }} catch (error) {{
          const message = document.getElementById("loading-message");
          if (message) message.textContent = "אירעה שגיאה. נסה שוב בעוד רגע.";
          if (progressTimer) clearInterval(progressTimer);
        }}
      }});
    }});
    const cancelButton = document.getElementById("cancel-search-button");
    if (cancelButton) cancelButton.addEventListener("click", cancelSearch);
  </script>
</body>
</html>"""
    return HTMLResponse(html)


def sidebar(active: str) -> str:
    items = [
        ("dashboard", "/dashboard", "Dashboard"),
        ("jobs", "/jobs", "Jobs"),
        ("inbox", "/inbox", "Applications"),
        ("resume", "/upload-cv", "Resume"),
        ("settings", "/settings", "Settings"),
    ]
    links = "".join(f"<a class='{'active' if key == active else ''}' href='{href}'>{label}</a>" for key, href, label in items)
    return f"<aside class='side'>{links}</aside>"


def search_form(button_label: str) -> str:
    config = load_config()
    current_title = ", ".join(config.get("search", {}).get("keywords", [])[:3])
    return f"""
    <form class="search-inline" method="post" action="/api/run-ui">
      <input name="job_title" value="{escape(current_title)}" placeholder="Type a job title: Backend Developer, Economist, QA" />
      <button class="primary" type="submit">{escape(button_label)}</button>
    </form>
    """


def split_titles(raw_value: str) -> list[str]:
    titles = [title.strip() for title in raw_value.replace("\n", ",").split(",")]
    return [title for title in titles if title]


def update_search_titles(raw_value: str) -> None:
    titles = split_titles(raw_value)
    if not titles:
        return
    path = Path(config_path())
    config = load_config()
    config["search"]["keywords"] = titles
    path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")


def start_background_pipeline(max_jobs: int = 100) -> None:
    def runner() -> None:
        try:
            DailyPipeline(config_path=config_path()).run(max_jobs=max_jobs)
        except Exception as exc:
            config = load_config()
            output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
            output_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "message": f"שגיאה בהרצה: {exc}",
                "phase": "failed",
                "jobs_found_so_far": 0,
                "target_jobs": max_jobs,
                "percent": 100,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            (output_dir / "job_search_progress.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()


def prepare_new_search_run(search_title: str, target_jobs: int = 100) -> str:
    config = load_config()
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in ["automation_status.json", "daily_summary.json", "ai_insights.json", "search_diagnostics.jsonl"]:
        path = output_dir / filename
        if path.exists():
            path.unlink()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    payload = {
        "message": "מתחיל חיפוש חדש. תוצאות ישנות נוקו ולא יוצגו.",
        "phase": "starting",
        "source": "",
        "jobs_found_so_far": 0,
        "target_jobs": target_jobs,
        "percent": 1,
        "run_id": run_id,
        "search_title": search_title,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "job_search_progress.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_id


def in_progress_status(config: Dict[str, Any], progress_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "חיפוש חדש רץ עכשיו",
        "last_run": progress_payload.get("updated_at", ""),
        "next_run": "",
        "jobs_found_today": int(progress_payload.get("jobs_found_so_far", 0)),
        "applications_sent_today": 0,
        "requires_approval": 0,
        "daily_limit": f"0/{config['automation']['daily_application_limit']}",
        "subscription_locked": is_subscription_locked(config),
        "subscription_pay_url": config["subscription"]["pay_url"],
        "application_inbox": [],
        "search_in_progress": True,
        "search_title": progress_payload.get("search_title", ""),
        "run_id": progress_payload.get("run_id", ""),
    }


def ai_insights_html() -> str:
    config = load_config()
    insights_path = Path(config["output"].get("summary_dir", "data_folder/output")) / "ai_insights.json"
    if not insights_path.exists():
        return """
        <ul class="insights">
          <li><b>OpenAI:</b> עדיין אין ניתוח אמיתי. הרץ חיפוש כדי להפעיל OpenAI Matching.</li>
          <li><b>Model:</b> המערכת תשתמש במודל שמוגדר ב-work_preferences.yaml.</li>
          <li><b>Speed:</b> OpenAI מופעל על המשרות המובילות, ושאר המשרות מדורגות מהר יותר מקומית.</li>
        </ul>
        """
    data = json.loads(insights_path.read_text(encoding="utf-8"))
    items = "".join(f"<li>{escape(str(item))}</li>" for item in data.get("insights", [])[:5])
    meta = f"<li><b>Model:</b> {escape(str(data.get('model', '')))} | OpenAI used: {data.get('openai_used', 0)}</li>"
    return f"<ul class='insights'>{meta}{items}</ul>"


def clear_cancel_flag() -> None:
    config = load_config()
    flag = Path(config["output"].get("summary_dir", "data_folder/output")) / "cancel_search.flag"
    if flag.exists():
        flag.unlink()


def current_search_title() -> str:
    config = load_config()
    return ", ".join(config.get("search", {}).get("keywords", [])[:3])


def metric_grid(items: list[tuple[str, Any]]) -> str:
    return "<section class='grid metrics'>" + "".join(
        f"<div class='metric'><span>{label}</span><strong>{value}</strong></div>" for label, value in items
    ) + "</section>"


def job_card(item: Dict[str, Any]) -> str:
    score = item.get("score", "")
    return f"""
    <article class="job-card">
      <div><span class="badge">{item.get('status_label', item.get('status', ''))}</span><h2>{item.get('title', '')}</h2><p>{item.get('company', '')}</p></div>
      <div class="score"><strong>{score}</strong><span>match</span></div>
      <a class="button secondary" href="{item.get('apply_url') or '#'}">פתח משרה</a>
    </article>
    """


def progress_percent(value: str) -> int:
    try:
        used, total = value.split("/")
        return max(0, min(100, int(int(used) / max(int(total), 1) * 100)))
    except (ValueError, AttributeError):
        return 0


def css() -> str:
    return """
    :root { color-scheme: light; --ink:#0b1736; --muted:#566174; --blue:#128ff2; --violet:#7c2df2; --line:#dbe5f2; --bg:#f7f9fc; --ok:#0f9f6e; --warn:#b7791f; font-family: Arial, "Noto Sans Hebrew", sans-serif; }
    body { margin:0; background:radial-gradient(circle at top,#fff 0,var(--bg) 62%); color:var(--ink); }
    .shell { min-height:100vh; display:grid; grid-template-rows:auto 1fr auto; }
    header, main, footer { width:min(1180px, calc(100% - 32px)); margin:0 auto; }
    header { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:18px 0; }
    nav { display:flex; gap:14px; flex-wrap:wrap; }
    nav a, .brand, .tile { color:var(--ink); text-decoration:none; }
    .brand { display:flex; align-items:center; gap:12px; font-weight:800; font-size:22px; }
    .brand img { width:54px; height:54px; object-fit:contain; }
    .hero { display:grid; grid-template-columns:1fr minmax(260px,420px); align-items:center; gap:48px; padding:54px 0 36px; }
    h1 { font-size:clamp(36px,6vw,76px); line-height:1; margin:0 0 18px; letter-spacing:0; }
    h2 { margin:0 0 12px; }
    p { font-size:18px; line-height:1.6; color:var(--muted); margin:0 0 24px; max-width:720px; }
    .eyebrow { display:inline-block; color:var(--blue); font-weight:800; margin-bottom:10px; }
    .gradient { background:linear-gradient(90deg,var(--blue),var(--violet)); -webkit-background-clip:text; color:transparent; }
    .actions, .toolbar { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; }
    .search-inline { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
    .search-inline input { min-width:min(360px, 100%); }
    .button, button { border:0; border-radius:8px; padding:13px 18px; font-size:16px; font-weight:700; cursor:pointer; text-decoration:none; display:inline-block; }
    button:disabled { opacity:.72; cursor:wait; }
    .primary { color:#fff; background:linear-gradient(90deg,var(--blue),var(--violet)); }
    .secondary, .ghost { color:var(--ink); background:#fff; border:1px solid var(--line); }
    .logo-panel { display:grid; place-items:center; }
    .logo-panel img { width:min(100%,420px); height:auto; }
    .app-layout { display:grid; grid-template-columns:220px 1fr; gap:18px; align-items:start; }
    .side { position:sticky; top:16px; display:grid; gap:8px; background:#fff; border:1px solid var(--line); border-radius:8px; padding:12px; }
    .side a { color:var(--muted); text-decoration:none; padding:12px; border-radius:8px; font-weight:700; }
    .side a.active, .side a:hover { color:var(--ink); background:#eef6ff; }
    .workspace { min-width:0; }
    .grid { display:grid; gap:12px; margin:18px 0 42px; }
    .metrics, .status { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:18px 0 28px; }
    .two, .onboarding { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; }
    .metric, .panel, .tile, .job-card, .empty-state { background:#fff; border:1px solid var(--line); border-radius:8px; padding:18px; }
    .metric span, .tile span { display:block; color:var(--muted); font-size:14px; margin-bottom:6px; }
    .metric strong, .tile strong { font-size:22px; }
    .narrow { max-width:620px; }
    form { display:grid; gap:12px; }
    input, select { border:1px solid var(--line); border-radius:8px; padding:12px; font-size:16px; background:#fff; }
    .dropzone { border:1px dashed var(--blue); border-radius:8px; padding:20px; background:#f5fbff; }
    .chips { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 20px; }
    .chips span, .badge { background:#eef6ff; color:#1465b7; border-radius:999px; padding:7px 10px; font-weight:700; font-size:13px; }
    .timeline, .feed, .insights { display:grid; gap:10px; color:var(--muted); }
    .timeline div { display:flex; gap:10px; align-items:center; }
    .timeline b { display:grid; place-items:center; width:28px; height:28px; border-radius:50%; background:linear-gradient(90deg,var(--blue),var(--violet)); color:#fff; }
    .progress { height:12px; background:#edf2f7; border-radius:999px; overflow:hidden; }
    .progress span { display:block; height:100%; background:linear-gradient(90deg,var(--blue),var(--violet)); }
    .trust { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:18px 0 28px; }
    .trust div { background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px; color:var(--muted); }
    .job-list { display:grid; gap:12px; }
    .job-card { display:grid; grid-template-columns:1fr 90px auto; align-items:center; gap:14px; }
    .score { text-align:center; }
    .score strong { display:block; font-size:30px; }
    .score span { color:var(--muted); }
    table { width:100%; border-collapse:collapse; }
    th, td { border-bottom:1px solid var(--line); text-align:right; padding:12px; }
    footer { padding:24px 0; color:var(--muted); border-top:1px solid var(--line); margin-top:42px; }
    .loading-overlay { position:fixed; inset:0; background:rgba(11,23,54,.42); z-index:50; display:grid; place-items:center; padding:24px; }
    .loading-overlay[hidden] { display:none; }
    .loading-card { width:min(460px,100%); background:#fff; border:1px solid var(--line); border-radius:8px; padding:24px; text-align:center; box-shadow:0 24px 80px rgba(11,23,54,.22); }
    .loading-card strong { display:block; font-size:22px; margin:14px 0 8px; }
    .loading-card span { color:var(--muted); line-height:1.5; }
    .loading-card small { display:block; color:var(--muted); margin-top:10px; }
    .loading-card button { margin-top:16px; }
    .loading-progress { height:12px; background:#edf2f7; border-radius:999px; overflow:hidden; margin-top:16px; }
    .loading-progress span { display:block; height:100%; width:0; background:linear-gradient(90deg,var(--blue),var(--violet)); transition:width .35s ease; }
    .spinner { width:42px; height:42px; border-radius:50%; border:4px solid #dbe5f2; border-top-color:var(--blue); margin:0 auto; animation:spin .9s linear infinite; }
    @keyframes spin { to { transform:rotate(360deg); } }
    @media (max-width:900px) { .hero,.two,.onboarding,.app-layout { grid-template-columns:1fr; } .metrics,.status,.trust { grid-template-columns:1fr 1fr; } .side { position:static; grid-template-columns:repeat(3,1fr); } .job-card { grid-template-columns:1fr; } }
    @media (max-width:560px) { .metrics,.status,.trust,.side { grid-template-columns:1fr; } header { align-items:flex-start; flex-direction:column; } }
    """


def option(value: str, label: str, selected: str) -> str:
    selected_attr = " selected" if value == selected else ""
    return f"<option value='{value}'{selected_attr}>{label}</option>"


def config_path() -> str:
    return os.getenv("WORK_PREFERENCES_PATH", DEFAULT_CONFIG_PATH)


def load_config() -> Dict[str, Any]:
    return yaml.safe_load(Path(config_path()).read_text(encoding="utf-8"))


async def parse_payload(request: Request) -> Dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return await request.json()
    form = await request.form()
    return dict(form)


def detect_payment_status(payload: Dict[str, Any]) -> str:
    candidates = [payload.get(key) for key in ["status", "transaction_status", "payment_status", "event", "event_type", "type"]]
    text = " ".join(str(item).lower() for item in candidates if item)
    if any(word in text for word in ["paid", "approved", "success", "completed", "מאושר", "שולם", "הצלחה"]):
        return "paid"
    if any(word in text for word in ["failed", "cancel", "declined", "refund", "נכשל", "בוטל", "זיכוי"]):
        return "failed"
    return "new_transaction"


def extract_user_identifier(payload: Dict[str, Any]) -> str:
    for key in ["email", "customer_email", "phone", "customer_phone", "user_id", "order_id", "transaction_id"]:
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def is_subscription_locked(config: Dict[str, Any]) -> bool:
    status_path = Path(config["subscription"]["status_path"])
    if not status_path.exists():
        return bool(config["subscription"].get("enabled", True))
    try:
        return not bool(json.loads(status_path.read_text(encoding="utf-8")).get("active"))
    except json.JSONDecodeError:
        return True
