import hashlib
import json
import os
import time
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, Optional

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


def _asset_ver(filename: str) -> str:
    try:
        content = Path(filename).read_bytes()
        return hashlib.md5(content).hexdigest()[:8]
    except OSError:
        return "1"


_CSS_VER = _asset_ver("assets/style.css")
_JS_VER  = _asset_ver("assets/app.js")

_config_cache: Dict[str, Any] = {}
_config_cache_mtime: float = 0.0

_STATUS_TTL = 5.0
_status_cache: Optional[Dict[str, Any]] = None
_status_cache_at: float = 0.0


def config_path() -> str:
    return os.getenv("WORK_PREFERENCES_PATH", DEFAULT_CONFIG_PATH)


def load_config() -> Dict[str, Any]:
    global _config_cache, _config_cache_mtime
    path = Path(config_path())
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return _config_cache or {}
    if mtime != _config_cache_mtime:
        try:
            _config_cache = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            _config_cache_mtime = mtime
        except Exception:
            pass
    return _config_cache


def get_status() -> Dict[str, Any]:
    global _status_cache, _status_cache_at
    now = time.monotonic()
    if _status_cache is not None and (now - _status_cache_at) < _STATUS_TTL:
        return _status_cache
    config = load_config()
    status_path = Path(config.get("output", {}).get("summary_dir", "data_folder/output")) / "automation_status.json"
    if status_path.exists():
        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
            _status_cache = data
            _status_cache_at = now
            return data
        except (json.JSONDecodeError, OSError):
            pass
    result = {
        "status": "לא רץ עדיין",
        "subscription_locked": is_subscription_locked(config),
        "subscription_pay_url": config.get("subscription", {}).get("pay_url", ""),
    }
    _status_cache = result
    _status_cache_at = now
    return result


def invalidate_status_cache() -> None:
    global _status_cache, _status_cache_at
    _status_cache = None
    _status_cache_at = 0.0


@app.get("/")
def root() -> HTMLResponse:
    config = load_config()
    pay_url = config.get("subscription", {}).get("pay_url", "#")
    return page(
        "JobFinder | מציאת עבודה והגשה חכמה",
        f"""
        <section class="hero">
          <div class="hero-content reveal">
            <span class="eyebrow">AI job agent for Israel</span>
            <h1>JobFinder<br><span class="gradient typewriter" data-texts='["מוצא. מתאים. מגיש.","מאיץ את החיפוש שלך.","AI לשוק העבודה הישראלי."]' data-base=""></span></h1>
            <p>{BRAND_TAGLINE}. חיפוש משרות, דירוג התאמה, Application Inbox ומצב אישור לפני שליחה במקום אחד.</p>
            <div class="bubbles"></div>
            <div class="actions">
              <a class="button primary" href="/onboarding">התחל ב-2 דקות</a>
              <a class="button secondary" href="/dashboard">פתח דשבורד</a>
              <a class="button ghost" href="{pay_url}">הפעל מנוי</a>
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
    try:
        form = await request.form()
        response = RedirectResponse("/dashboard", status_code=303)
        response.set_cookie("jobfinder_user", str(form.get("email", "")), httponly=True, samesite="lax")
        return response
    except Exception:
        return JSONResponse({"error": "bad request"}, status_code=400)


@app.get("/dashboard")
def dashboard() -> HTMLResponse:
    config = load_config()
    current = get_status()
    automation = config.get("automation", {})
    subscription = config.get("subscription", {})
    metrics = metric_grid([
        ("סטטוס", current.get("status", "לא רץ עדיין")),
        ("נמצאו היום", current.get("jobs_found_today", 0)),
        ("נשלחו היום", current.get("applications_sent_today", 0)),
        ("דורש אישור", current.get("requires_approval", 0)),
        ("מגבלת היום", current.get("daily_limit", f"0/{automation.get('daily_application_limit', 10)}")),
        ("מנוי", "פעיל" if not current.get("subscription_locked", True) else "נדרש"),
    ])
    pay_button = f"<a class='button secondary' href='{subscription.get('pay_url', '#')}'>הפעל מנוי</a>" if current.get("subscription_locked", True) else ""
    progress_value = current.get("daily_limit", f"0/{automation.get('daily_application_limit', 10)}")
    current_title = ", ".join(config.get("search", {}).get("keywords", [])[:3])
    search_html = _search_form_html(current_title, "הרץ עכשיו")
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
                {search_html}
                <form method="post" action="/api/apply-all"><button class="primary" type="submit">הגש לכל המתאימות</button></form>
                {pay_button}
              </div>
            </section>
            {metrics}
            <section class="panel progress-card">
              <div>
                <span class="eyebrow">Apply progress</span>
                <h2>{progress_value} מהמגבלה היומית נוצלו</h2>
                <p>{current.get("jobs_found_today", 0)} משרות נמצאו היום. {current.get("requires_approval", 0)} דורשות אישור לפני שליחה.</p>
              </div>
              <div class="progress"><span style="width:{progress_percent(progress_value)}%"></span></div>
            </section>
            <section class="grid two">
              <div class="panel">
                <span class="eyebrow">AI insights</span>
                <h2>מה כדאי לשפר עכשיו</h2>
                <ul class="insights">
                  <li><b>ATS:</b> הוסף פרויקט מדיד עם Excel/SQL כדי לשפר התאמה למשרות אנליסט.</li>
                  <li><b>Timing:</b> הרצה לפני 10:00 מכניסה אותך מוקדם יותר לזרם המועמדים.</li>
                  <li><b>Fit:</b> משרות עם ציון 70+ נשמרות לאישור לפני שליחה.</li>
                </ul>
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
    current = get_status()
    config = load_config()
    items = [item for item in current.get("application_inbox", []) if item.get("title")]
    current_title = ", ".join(config.get("search", {}).get("keywords", [])[:3])
    search_html = _search_form_html(current_title, "רענן התאמות")
    cards = "".join(job_card(item) for item in items) or f"""
        <div class="empty-state">
          <h2>Your AI agent is preparing new opportunities.</h2>
          <p>הרץ את הפייפליין כדי לראות משרות שנמצאו, ציוני התאמה והמלצות AI.</p>
          {search_html}
        </div>"""
    return page(
        "JobFinder Jobs",
        f"""
        <section class="app-layout">
          {sidebar("jobs")}
          <div class="workspace">
            <section class="toolbar">
              <div><span class="eyebrow">Matched jobs</span><h1>משרות שמתאימות לך</h1></div>
              {search_html}
            </section>
            <section class="job-list">{cards}</section>
          </div>
        </section>
        """,
    )


@app.get("/inbox")
def inbox() -> HTMLResponse:
    items = get_status().get("application_inbox", [])
    rows = "".join(
        f"<tr><td>{item.get('status_label', item.get('status', ''))}</td>"
        f"<td>{item.get('title', '')}</td><td>{item.get('company', '')}</td>"
        f"<td>{item.get('score', '')}</td>"
        f"<td><a href='{item.get('apply_url') or item.get('pay_url') or '#'}'>פתח</a></td></tr>"
        for item in items
    ) or "<tr><td colspan='5'>Your AI agent is preparing new opportunities.</td></tr>"
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
    automation = config.get("automation", {})
    title_value = ", ".join(config.get("search", {}).get("keywords", [])[:5])
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
              <input name="daily_time" value="{automation.get('daily_time', '')}" />
              <label>מצב הגשה</label>
              <select name="application_mode">
                {option('full_auto', 'אוטומטי מלא', automation.get('application_mode', ''))}
                {option('approval_before_send', 'אישור לפני שליחה', automation.get('application_mode', ''))}
                {option('save_matches_only', 'רק שמירת התאמות', automation.get('application_mode', ''))}
              </select>
              <label>סף התאמה</label>
              <select name="match_threshold">
                {option('80', 'רק משרות בציון 80+', str(automation.get('match_threshold', '')))}
                {option('70', 'רק משרות בציון 70+', str(automation.get('match_threshold', '')))}
                {option('60', 'רק משרות בציון 60+', str(automation.get('match_threshold', '')))}
              </select>
              <label>סטטוס</label>
              <select name="status">
                {option('active', 'פעיל', automation.get('status', ''))}
                {option('paused', 'מושהה', automation.get('status', ''))}
              </select>
              <button class="primary" type="submit">שמור הגדרות</button>
            </form>
          </div>
        </section>
        """,
    )


@app.post("/settings")
async def save_settings(request: Request) -> RedirectResponse:
    try:
        form = await request.form()
        config = load_config()
        job_title = str(form.get("job_title", "")).strip()
        if job_title:
            config.setdefault("search", {})["keywords"] = split_titles(job_title)
        automation = config.setdefault("automation", {})
        automation["daily_time"] = str(form.get("daily_time", automation.get("daily_time", "")))
        automation["application_mode"] = str(form.get("application_mode", automation.get("application_mode", "")))
        try:
            automation["match_threshold"] = int(form.get("match_threshold", automation.get("match_threshold", 70)))
        except (ValueError, TypeError):
            pass
        automation["status"] = str(form.get("status", automation.get("status", "active")))
        Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
        invalidate_status_cache()
        return RedirectResponse("/settings", status_code=303)
    except Exception:
        return JSONResponse({"error": "failed to save settings"}, status_code=500)


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
    try:
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
                config.setdefault("search", {})["keywords"] = split_titles(job_title)
            Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return RedirectResponse("/dashboard", status_code=303)
    except Exception:
        return JSONResponse({"error": "upload failed"}, status_code=500)


@app.post("/api/run-ui")
async def run_pipeline_ui(request: Request) -> RedirectResponse:
    try:
        form = await request.form()
        job_title = str(form.get("job_title", "")).strip()
        if job_title:
            update_search_titles(job_title)
        clear_cancel_flag()
        invalidate_status_cache()
        DailyPipeline(config_path=config_path()).run(max_jobs=100)
        invalidate_status_cache()
        return RedirectResponse("/dashboard", status_code=303)
    except Exception:
        return JSONResponse({"error": "pipeline failed"}, status_code=500)


@app.post("/api/apply-all")
def apply_all_ui() -> RedirectResponse:
    try:
        config = load_config()
        config.setdefault("automation", {})["application_mode"] = "full_auto"
        config["automation"]["daily_application_limit"] = 100
        config.setdefault("apply", {})["dry_run"] = False
        Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
        clear_cancel_flag()
        invalidate_status_cache()
        DailyPipeline(config_path=config_path()).run(max_jobs=100)
        invalidate_status_cache()
        return RedirectResponse("/dashboard", status_code=303)
    except Exception:
        return JSONResponse({"error": "apply-all failed"}, status_code=500)


@app.post("/api/cancel-search")
def cancel_search() -> JSONResponse:
    try:
        config = load_config()
        output_dir = Path(config.get("output", {}).get("summary_dir", "data_folder/output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "cancel_search.flag").write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
        progress_path = output_dir / "job_search_progress.json"
        found, target = 0, 100
        if progress_path.exists():
            try:
                d = json.loads(progress_path.read_text(encoding="utf-8"))
                found = int(d.get("jobs_found_so_far", 0))
                target = int(d.get("target_jobs", 100))
            except (json.JSONDecodeError, ValueError, OSError):
                pass
        payload = {
            "message": "החיפוש נעצר. נשמרו המשרות שנמצאו עד עכשיו.",
            "phase": "cancelled",
            "jobs_found_so_far": found,
            "target_jobs": target,
            "percent": 100,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        invalidate_status_cache()
        return JSONResponse(payload)
    except Exception:
        return JSONResponse({"error": "cancel failed"}, status_code=500)


@app.get("/api/status")
def api_status() -> JSONResponse:
    try:
        return JSONResponse(get_status())
    except Exception:
        return JSONResponse({"error": "status unavailable"}, status_code=500)


@app.get("/api/progress")
def api_progress() -> JSONResponse:
    try:
        config = load_config()
        progress_path = Path(config.get("output", {}).get("summary_dir", "data_folder/output")) / "job_search_progress.json"
        if progress_path.exists():
            try:
                return JSONResponse(json.loads(progress_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
    except Exception:
        pass
    return JSONResponse({"message": "ממתין להתחלת חיפוש", "phase": "idle", "jobs_found_so_far": 0, "target_jobs": 100, "percent": 0})


@app.post("/api/run")
def run_pipeline(max_jobs: int | None = None) -> JSONResponse:
    try:
        summary = DailyPipeline(config_path=config_path()).run(max_jobs=max_jobs)
        invalidate_status_cache()
        return JSONResponse(summary.to_user_status())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/webhooks/takbull")
async def takbull_webhook(request: Request) -> JSONResponse:
    try:
        payload = await parse_payload(request)
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    try:
        config = load_config()
        subscription = config.get("subscription", {})
        expected_secret = os.getenv(subscription.get("webhook_secret_env", "TAKBULL_WEBHOOK_SECRET"), "")
        if expected_secret:
            provided = request.headers.get("x-webhook-secret") or request.query_params.get("secret", "")
            if provided != expected_secret:
                return JSONResponse({"ok": False, "error": "invalid webhook secret"}, status_code=401)
        payment_status = detect_payment_status(payload)
        active = payment_status in {"paid", "approved", "success", "completed", "new_transaction"}
        record = {
            "active": active, "provider": "takbull", "payment_status": payment_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "user_identifier": extract_user_identifier(payload), "raw_payload": payload,
        }
        sp = Path(subscription["status_path"])
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        invalidate_status_cache()
        return JSONResponse({"ok": True, "subscription_active": active, "payment_status": payment_status})
    except Exception:
        return JSONResponse({"ok": False, "error": "webhook processing failed"}, status_code=500)


def page(title: str, body: str, landing: bool = False) -> HTMLResponse:
    nav_links = "" if landing else (
        "<a href='/dashboard'>Dashboard</a>"
        "<a href='/jobs'>Jobs</a>"
        "<a href='/inbox'>Inbox</a>"
        "<a href='/settings'>Settings</a>"
        "<a href='/upload-cv'>Resume</a>"
    )
    hamburger = "" if landing else "<button class='hamburger' id='hamburger' aria-label='Menu'><span></span><span></span><span></span></button>"
    theme_btn = "<button class='theme-toggle' id='theme-toggle' aria-label='Toggle theme'>🌙</button>"
    html = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <title>{title}</title>
  <meta name="description" content="JobFinder מוצא משרות, מדרג התאמה ומנהל הגשות עבודה בישראל." />
  <link rel="icon" href="/assets/brand/jobfinder-logo.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/assets/style.css?v={_CSS_VER}" />
</head>
<body>
  <div id="page-progress"></div>
  <canvas id="particle-canvas"></canvas>
  <div id="spotlight"></div>
  <div class="shell">
    <header id="site-header">
      <a class="brand" href="/">
        <img src="/assets/brand/jobfinder-logo.png" alt="JobFinder logo" />
        <span><span class="brand-text">JobFinder</span></span>
      </a>
      <nav id="main-nav">{nav_links}</nav>
      <div style="display:flex;align-items:center;gap:10px;">
        {theme_btn}
        {hamburger}
      </div>
    </header>
    <main>{body}</main>
    <footer>
      <span>JobFinder &copy; 2025</span>
      <span>{BRAND_TAGLINE}</span>
    </footer>
  </div>
  <div id="loading-overlay" class="loading-overlay" hidden>
    <div class="loading-card panel">
      <div class="spinner"></div>
      <strong>JobFinder מחפש עבורך עד 100 משרות מתאימות</strong>
      <span id="loading-message">זה יכול לקחת דקה או שתיים כי המערכת בודקת מקורות בישראל ובעולם.</span>
      <div class="loading-progress"><span id="loading-progress-bar" style="width:0%"></span></div>
      <small id="loading-count">נמצאו 0 מתוך 100 משרות</small>
      <button id="cancel-search-button" class="secondary" type="button">עצור ושמור מה שנמצא</button>
    </div>
  </div>
  <div id="toast-container"></div>
  <script>
    // Hamburger init before app.js
    var _h = document.getElementById('hamburger');
    var _n = document.getElementById('main-nav');
    if (_h && _n) _h.addEventListener('click', function() {{ _h.classList.toggle('open'); _n.classList.toggle('open'); }});
  </script>
  <script src="/assets/app.js?v={_JS_VER}"></script>
</body>
</html>"""
    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def sidebar(active: str) -> str:
    items = [("dashboard", "/dashboard", "Dashboard"), ("jobs", "/jobs", "Jobs"),
             ("inbox", "/inbox", "Applications"), ("resume", "/upload-cv", "Resume"), ("settings", "/settings", "Settings")]
    links = "".join(f"<a class='{'active' if k == active else ''}' href='{h}'>{l}</a>" for k, h, l in items)
    return f"<aside class='side'>{links}</aside>"


def _search_form_html(current_title: str, button_label: str) -> str:
    return (f'<form class="search-inline" method="post" action="/api/run-ui">'
            f'<input name="job_title" value="{escape(current_title)}" placeholder="Type a job title: Backend Developer, Economist, QA" />'
            f'<button class="primary" type="submit">{escape(button_label)}</button></form>')


def search_form(button_label: str) -> str:
    config = load_config()
    return _search_form_html(", ".join(config.get("search", {}).get("keywords", [])[:3]), button_label)


def split_titles(raw: str) -> list[str]:
    return [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]


def update_search_titles(raw: str) -> None:
    titles = split_titles(raw)
    if not titles:
        return
    config = load_config()
    config.setdefault("search", {})["keywords"] = titles
    Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")


def clear_cancel_flag() -> None:
    config = load_config()
    flag = Path(config.get("output", {}).get("summary_dir", "data_folder/output")) / "cancel_search.flag"
    if flag.exists():
        flag.unlink()


def metric_grid(items: list[tuple[str, Any]]) -> str:
    return "<section class='grid metrics'>" + "".join(
        f"<div class='metric'><span>{label}</span><strong>{value}</strong></div>" for label, value in items
    ) + "</section>"


def job_card(item: Dict[str, Any]) -> str:
    score = item.get("score", 0) or 0
    status = item.get("status", "")
    status_label = item.get("status_label", status)
    badge_cls = "badge-green" if status == "submitted" else "badge-blue" if status in ("saved_match","dry_run_ready") else "badge-gold" if status == "pending_approval" else "badge-purple"
    new_badge = '<span class="badge badge-new">חדש</span> ' if status in ("saved_match", "dry_run_ready") else ""
    return (
        f'<article class="job-card reveal">'
        f'<div class="job-card-main">'
        f'<div class="job-card-title">{new_badge}{escape(item.get("title", ""))}</div>'
        f'<div class="job-card-meta">'
        f'<span>🏢 {escape(item.get("company",""))}</span>'
        f'<span>📍 {escape(item.get("source",""))}</span>'
        f'</div>'
        f'<span class="badge {badge_cls}">{escape(status_label)}</span>'
        f'</div>'
        f'<div class="score"><strong>{score}</strong><span>match</span></div>'
        f'<a class="button secondary" href="{item.get("apply_url") or "#"}">פתח משרה</a>'
        f'</article>'
    )


def progress_percent(value: str) -> int:
    try:
        used, total = value.split("/")
        return max(0, min(100, int(int(used) / max(int(total), 1) * 100)))
    except (ValueError, AttributeError):
        return 0


def option(value: str, label: str, selected: str) -> str:
    return f"<option value='{value}'{' selected' if value == selected else ''}>{label}</option>"


async def parse_payload(request: Request) -> Dict[str, Any]:
    if "application/json" in request.headers.get("content-type", ""):
        return await request.json()
    return dict(await request.form())


def detect_payment_status(payload: Dict[str, Any]) -> str:
    text = " ".join(str(v).lower() for k in ["status", "transaction_status", "payment_status", "event", "event_type", "type"] if (v := payload.get(k)))
    if any(w in text for w in ["paid", "approved", "success", "completed", "מאושר", "שולם", "הצלחה"]):
        return "paid"
    if any(w in text for w in ["failed", "cancel", "declined", "refund", "נכשל", "בוטל", "זיכוי"]):
        return "failed"
    return "new_transaction"


def extract_user_identifier(payload: Dict[str, Any]) -> str:
    for key in ["email", "customer_email", "phone", "customer_phone", "user_id", "order_id", "transaction_id"]:
        if v := payload.get(key):
            return str(v)
    return ""


def is_subscription_locked(config: Dict[str, Any]) -> bool:
    raw = config.get("subscription", {}).get("status_path", "")
    if not raw:
        return bool(config.get("subscription", {}).get("enabled", True))
    sp = Path(raw)
    if not sp.exists():
        return bool(config.get("subscription", {}).get("enabled", True))
    try:
        return not bool(json.loads(sp.read_text(encoding="utf-8")).get("active"))
    except (json.JSONDecodeError, OSError):
        return True
