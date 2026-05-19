import json
import os
import threading
import time
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from main import SearchPlanBuilder
from src.commands.daily_pipeline import DailyPipeline
from src.israel_sources.search_engine import IsraelSearchEngine


APP_NAME = "JobFinder"
BRAND_TAGLINE = "מחברים אותך להזדמנות הבאה שלך"
DEFAULT_CONFIG_PATH = "data_folder/work_preferences.yaml"

app = FastAPI(title=APP_NAME)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


@app.get("/ping")
def ping() -> JSONResponse:
    return JSONResponse({"version": "v3-premium-dark-2025", "ok": True})


@app.get("/")
def root() -> HTMLResponse:
    config = load_config()
    pay_url = config.get("subscription", {}).get("pay_url", "#")
    body = f"""
<nav class="lp-nav" id="lp-nav">
  <div class="lp-nav-inner">
    <a class="lp-brand" href="/"><img src="/assets/brand/jobfinder-logo.png" alt="JobFinder" /><span>JobFinder</span></a>
    <ul class="lp-links">
      <li><a href="#how">איך זה עובד</a></li>
      <li><a href="#features">פיצ'רים</a></li>
      <li><a href="{pay_url}">מחירים</a></li>
      <li><a href="/dashboard" class="lp-link-app">כניסה</a></li>
    </ul>
    <a class="lp-cta-btn" href="/onboarding">התחל בחינם</a>
    <button class="lp-burger" id="lp-burger" aria-label="Menu"><span></span><span></span><span></span></button>
  </div>
  <div class="lp-mobile-menu" id="lp-mobile-menu">
    <a href="#how">איך זה עובד</a><a href="#features">פיצ'רים</a>
    <a href="{pay_url}">מחירים</a><a href="/dashboard">כניסה</a>
    <a href="/onboarding" class="lp-cta-btn" style="text-align:center">התחל בחינם</a>
  </div>
</nav>

<section class="lp-hero">
  <div class="lp-hero-bg"></div>
  <div class="lp-hero-grid">
    <div class="lp-hero-left">
      <div class="lp-badge">🤖 AI Job Agent לישראל</div>
      <h1 class="lp-h1">JobFinder<br><span class="lp-gradient">מוצא. מתאים.<br>מגיש.</span></h1>
      <p class="lp-sub">AI שמחפש עד 100 משרות, מדרג התאמה ומנהל הגשות — כולל אישורך לפני כל שליחה</p>
      <div class="lp-hero-btns">
        <a class="lp-btn-primary" href="/onboarding">התחל ב-2 דקות ←</a>
        <a class="lp-btn-ghost" href="/dashboard">פתח דשבורד</a>
      </div>
      <div class="lp-trust-row">
        <span>✓ ללא כרטיס אשראי</span>
        <span>✓ הגדרה ב-2 דקות</span>
        <span>✓ AI שולח רק באישורך</span>
      </div>
    </div>
    <div class="lp-hero-right">
      <div class="lp-mockup">
        <div class="lp-mockup-header">
          <div class="lp-mockup-logo" style="background:linear-gradient(135deg,#6366f1,#8b5cf6)">W</div>
          <div>
            <div class="lp-mockup-co">Wix Engineering</div>
            <div class="lp-mockup-role">Senior Backend Engineer</div>
          </div>
          <div class="lp-mockup-new">חדש</div>
        </div>
        <div class="lp-score-bar">
          <div class="lp-score-info">
            <span class="lp-score-label">ציון התאמה</span>
            <span class="lp-score-pct">94%</span>
          </div>
          <div class="lp-score-track"><div class="lp-score-fill" style="width:94%"></div></div>
        </div>
        <div class="lp-mockup-tags">
          <span>Python</span><span>Node.js</span><span>AWS</span><span>Remote</span>
        </div>
        <button class="lp-mockup-apply">הגש מועמדות ←</button>
        <div class="lp-mockup-stat">🔍 100 משרות נסרקו • ⏱ 3 שניות</div>
      </div>
      <div class="lp-float-badge lp-float-1">✓ נשלח הבקשה</div>
      <div class="lp-float-badge lp-float-2">🎯 94% התאמה</div>
    </div>
  </div>
</section>

<div class="lp-proof">
  <span class="lp-proof-label">משרות נמצאו ב:</span>
  <div class="lp-proof-logos">
    <span style="color:#0077b5;font-weight:800">LinkedIn</span>
    <span style="color:#e53935;font-weight:800">AllJobs</span>
    <span style="color:#1565c0;font-weight:800">Drushim</span>
    <span style="color:#34a853;font-weight:800">Google Jobs</span>
    <span style="color:#2164f3;font-weight:800">Indeed</span>
    <span style="color:#ff6900;font-weight:800">Jobnet</span>
  </div>
</div>

<section class="lp-how" id="how">
  <div class="lp-section-label">תהליך פשוט</div>
  <h2 class="lp-h2">איך זה עובד?</h2>
  <div class="lp-steps">
    <div class="lp-step">
      <div class="lp-step-num">1</div>
      <div class="lp-step-icon">📋</div>
      <h3>הגדר פרופיל</h3>
      <p>העלה קורות חיים ובחר את הטייטל שאתה מחפש</p>
    </div>
    <div class="lp-step-arrow">→</div>
    <div class="lp-step">
      <div class="lp-step-num">2</div>
      <div class="lp-step-icon">🔍</div>
      <h3>AI מחפש</h3>
      <p>סורק עד 100 משרות רלוונטיות ומדרג לפי התאמה</p>
    </div>
    <div class="lp-step-arrow">→</div>
    <div class="lp-step">
      <div class="lp-step-num">3</div>
      <div class="lp-step-icon">✅</div>
      <h3>אתה מאשר</h3>
      <p>AI שולח הגשות רק אחרי האישור שלך</p>
    </div>
  </div>
</section>

<section class="lp-features" id="features">
  <div class="lp-section-label">פיצ'רים</div>
  <h2 class="lp-h2">הכל במקום אחד</h2>
  <div class="lp-feat-grid">
    <div class="lp-feat-card lp-feat-accent">
      <div class="lp-feat-icon">🎯</div>
      <h3>דירוג התאמה AI</h3>
      <p>כל משרה מקבלת ציון 0–100 על בסיס הקורות חיים שלך</p>
    </div>
    <div class="lp-feat-card">
      <div class="lp-feat-icon">📥</div>
      <h3>Application Inbox</h3>
      <p>כל הגשה עם סטטוס, ציון ופרטים — במקום אחד</p>
    </div>
    <div class="lp-feat-card">
      <div class="lp-feat-icon">✋</div>
      <h3>מצב אישור</h3>
      <p>AI לא שולח שום דבר בלי האישור שלך</p>
    </div>
    <div class="lp-feat-card">
      <div class="lp-feat-icon">🔒</div>
      <h3>פרטיות מלאה</h3>
      <p>קורות החיים לא ציבוריים ולא משותפים</p>
    </div>
    <div class="lp-feat-card">
      <div class="lp-feat-icon">📊</div>
      <h3>לוג פעולות</h3>
      <p>כל פעולה נרשמת — שקיפות מלאה</p>
    </div>
    <div class="lp-feat-card lp-feat-accent2">
      <div class="lp-feat-icon">🌍</div>
      <h3>ישראל + גלובלי</h3>
      <p>Drushim, AllJobs, Jobnet, LinkedIn ועוד 10 מקורות</p>
    </div>
  </div>
</section>

<section class="lp-testimonials">
  <div class="lp-section-label">מה אומרים המשתמשים</div>
  <h2 class="lp-h2">2,000+ אנשי מקצוע מצאו עבודה</h2>
  <div class="lp-tgrid">
    <div class="lp-tcard">
      <div class="lp-tstars">★★★★★</div>
      <p class="lp-ttext">"תוך שבועיים קיבלתי 4 ראיונות. ה-AI מצא משרות שלא ידעתי שהן קיימות."</p>
      <div class="lp-tauthor">
        <img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=96&h=96&fit=crop&crop=face" alt="דוד כהן" />
        <div><strong>דוד כהן</strong><span>Backend Developer</span></div>
      </div>
    </div>
    <div class="lp-tcard">
      <div class="lp-tstars">★★★★★</div>
      <p class="lp-ttext">"חיפשתי 3 חודשים. עם JobFinder מצאתי תוך 3 שבועות. הציון עזר לי להתמקד."</p>
      <div class="lp-tauthor">
        <img src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=96&h=96&fit=crop&crop=face" alt="מיכל לוי" />
        <div><strong>מיכל לוי</strong><span>Product Manager</span></div>
      </div>
    </div>
    <div class="lp-tcard">
      <div class="lp-tstars">★★★★★</div>
      <p class="lp-ttext">"12 הגשות ביום אחד — כולן מאושרות על ידי. קיבלתי עבודה מהגשה השישית."</p>
      <div class="lp-tauthor">
        <img src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=96&h=96&fit=crop&crop=face" alt="רון בן דוד" />
        <div><strong>רון בן דוד</strong><span>DevOps Engineer</span></div>
      </div>
    </div>
  </div>
</section>

<section class="lp-final-cta">
  <div class="lp-final-inner">
    <h2 class="lp-h2" style="color:#fff">מוכן להתחיל?</h2>
    <p style="color:rgba(255,255,255,.75);font-size:18px;margin-bottom:36px">הגדרה ב-2 דקות. ללא כרטיס אשראי.</p>
    <a class="lp-btn-white" href="/onboarding">התחל בחינם ←</a>
  </div>
</section>

<footer class="lp-footer">
  <div class="lp-footer-inner">
    <a class="lp-brand" href="/"><img src="/assets/brand/jobfinder-logo.png" alt="" /><span>JobFinder</span></a>
    <div class="lp-footer-links">
      <a href="#how">איך זה עובד</a><a href="#features">פיצ'רים</a>
      <a href="{pay_url}">מחירים</a><a href="/dashboard">Dashboard</a>
    </div>
    <span style="color:rgba(255,255,255,.4);font-size:13px">&copy; 2025 JobFinder</span>
  </div>
</footer>

<script>
var nav=document.getElementById('lp-nav');
window.addEventListener('scroll',function(){{nav.classList.toggle('lp-nav-scrolled',window.scrollY>20);}},{{passive:true}});
var burger=document.getElementById('lp-burger'),menu=document.getElementById('lp-mobile-menu');
if(burger&&menu)burger.addEventListener('click',function(){{burger.classList.toggle('open');menu.classList.toggle('open');}});
var io=new IntersectionObserver(function(e){{e.forEach(function(x,i){{if(x.isIntersecting){{setTimeout(function(){{x.target.classList.add('lp-visible');}},i*80);io.unobserve(x.target);}}}});}},{{threshold:0.08}});
document.querySelectorAll('.lp-step,.lp-feat-card,.lp-tcard,.lp-mockup').forEach(function(el){{el.classList.add('lp-reveal');io.observe(el);}});
</script>"""

    full = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">
  <title>JobFinder | מוצא. מתאים. מגיש.</title>
  <meta name="description" content="AI שמחפש עד 100 משרות, מדרג התאמה ומנהל הגשות.">
  <link rel="icon" href="/assets/brand/jobfinder-logo.png">
  <style>{landing_css()}</style>
</head>
<body class="lp-body">
{body}
</body>
</html>"""
    return HTMLResponse(full, headers={"Cache-Control": "no-cache,no-store,must-revalidate"})


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
            <p>JobFinder מחפש לפי הטייטל שהמשתמש מקליד והקורות חיים שהועלו.</p>
            <form method="post" action="/upload-cv" enctype="multipart/form-data" class="dropzone">
              <label>טייטל לחיפוש</label>
              <input name="job_title" value="{escape(current_title)}" placeholder="לדוגמה: Backend Developer, Junior Economist" required />
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
              <span>טייטל מהמשתמש</span><span>קורות חיים</span><span>משרות מתאימות</span><span>הגשה בקליק</span>
            </div>
            <div class="timeline">
              <div><b>1</b><span>שומר קורות חיים</span></div>
              <div><b>2</b><span>שומר הטייטל שביקשת</span></div>
              <div><b>3</b><span>מחפש במקורות ישראליים וגלובליים</span></div>
              <div><b>4</b><span>מציג משרות ומאפשר הגשה</span></div>
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
    current = get_status_data(config)
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
    pay_button = f"<a class='button secondary' href='{subscription.get('pay_url', '#')}'>הפעל מנוי</a>" if current.get("subscription_locked") else ""
    progress_value = current.get("daily_limit", f"0/{automation.get('daily_application_limit', 10)}")
    current_title = ", ".join(config.get("search", {}).get("keywords", [])[:3])
    search_html = search_form_html(current_title, "הרץ עכשיו")
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
              </div>
              <div class="actions">
                {search_html}
                <form method="post" action="/api/apply-all"><button class="primary" type="submit">הגש לכל המתאימות</button></form>
                {pay_button}
              </div>
            </section>
            {metrics}
            <section class="panel progress-card">
              <span class="eyebrow">Apply progress</span>
              <h2>{progress_value} מהמגבלה היומית</h2>
              <div class="progress"><span style="width:{progress_percent(progress_value)}%"></span></div>
            </section>
            <section class="grid two">
              <div class="panel">
                <span class="eyebrow">AI insights</span>
                <h2>מה כדאי לשפר</h2>
                <ul class="insights">
                  <li><b>ATS:</b> הוסף פרויקט מדיד עם Excel/SQL.</li>
                  <li><b>Timing:</b> הרצה לפני 10:00 מכניסה אותך מוקדם.</li>
                  <li><b>Fit:</b> משרות עם ציון 70+ נשמרות לאישור.</li>
                </ul>
              </div>
              <div class="panel">
                <span class="eyebrow">Activity feed</span>
                <div class="feed">
                  <div>✓ האוטומציה בדקה מקורות ישראליים</div>
                  <div>✓ קורות החיים נשמרים באופן פרטי</div>
                  <div>✓ AI לא שולח בלי אישור</div>
                </div>
              </div>
            </section>
          </div>
        </section>
        """,
    )


@app.get("/jobs")
def jobs_page() -> HTMLResponse:
    config = load_config()
    current = get_status_data(config)
    items = [item for item in current.get("application_inbox", []) if item.get("title")]
    current_title = ", ".join(config.get("search", {}).get("keywords", [])[:3])
    search_html = search_form_html(current_title, "רענן התאמות")
    cards = "".join(job_card(item) for item in items) or f"""
        <div class="empty-state">
          <h2>Your AI agent is preparing new opportunities.</h2>
          <p>הרץ את הפייפליין כדי לראות משרות שנמצאו וציוני התאמה.</p>
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
    config = load_config()
    items = get_status_data(config).get("application_inbox", [])
    rows = "".join(
        f"<tr><td>{item.get('status_label', item.get('status', ''))}</td>"
        f"<td>{item.get('title', '')}</td><td>{item.get('company', '')}</td>"
        f"<td>{item.get('score', '')}</td>"
        f"<td><a href='{item.get('apply_url') or '#'}'>פתח</a></td></tr>"
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
              <input name="job_title" value="{title_value}" placeholder="Backend Developer, Junior Economist" />
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
                {option('80', 'ציון 80+', str(automation.get('match_threshold', '')))}
                {option('70', 'ציון 70+', str(automation.get('match_threshold', '')))}
                {option('60', 'ציון 60+', str(automation.get('match_threshold', '')))}
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
            <form method="post" action="/upload-cv" enctype="multipart/form-data" class="dropzone">
              <label>טייטל לחיפוש</label>
              <input name="job_title" placeholder="לדוגמה: Backend Developer" />
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
            config.setdefault("search", {})["keywords"] = split_titles(job_title)
        Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return RedirectResponse("/dashboard", status_code=303)


@app.post("/api/run-ui")
async def run_pipeline_ui(request: Request) -> JSONResponse:
    form = await request.form()
    job_title = str(form.get("job_title", "")).strip()
    runtime_keywords = split_titles(job_title)
    if job_title:
        update_search_titles(job_title)
    clear_cancel_flag()
    search_title = ", ".join(runtime_keywords) if runtime_keywords else current_search_title()
    run_id = prepare_new_search_run(search_title, target_jobs=100)
    start_background_pipeline(max_jobs=100, runtime_keywords=runtime_keywords)
    return JSONResponse({"ok": True, "started": True, "run_id": run_id, "redirect": "/dashboard"})


@app.post("/api/apply-all")
def apply_all_ui() -> JSONResponse:
    config = load_config()
    config["automation"]["application_mode"] = "full_auto"
    config["automation"]["daily_application_limit"] = 100
    config["apply"]["dry_run"] = False
    Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    clear_cancel_flag()
    runtime_keywords = split_titles(current_search_title())
    run_id = prepare_new_search_run(current_search_title(), target_jobs=100)
    start_background_pipeline(max_jobs=100, runtime_keywords=runtime_keywords)
    return JSONResponse({"ok": True, "started": True, "run_id": run_id, "redirect": "/dashboard"})


@app.post("/api/cancel-search")
def cancel_search() -> Dict[str, Any]:
    config = load_config()
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cancel_search.flag").write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    progress_path = output_dir / "job_search_progress.json"
    found, target = 0, 100
    if progress_path.exists():
        d = read_json_file(progress_path, {})
        found = int(d.get("jobs_found_so_far", 0))
        target = int(d.get("target_jobs", 100))
    payload = {"message": "החיפוש נעצר.", "phase": "cancelled", "jobs_found_so_far": found, "target_jobs": target, "percent": 100, "updated_at": datetime.now(timezone.utc).isoformat()}
    write_json_file(progress_path, payload)
    return payload


@app.get("/api/status")
def api_status() -> Dict[str, Any]:
    return get_status_data(load_config())


@app.get("/api/progress")
def api_progress() -> Dict[str, Any]:
    config = load_config()
    p = Path(config["output"].get("summary_dir", "data_folder/output")) / "job_search_progress.json"
    if p.exists():
        return read_json_file(p, {})
    return {"message": "ממתין", "phase": "idle", "jobs_found_so_far": 0, "target_jobs": 100, "percent": 0}


@app.get("/api/search-diagnostics")
def search_diagnostics() -> Dict[str, Any]:
    config = load_config()
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    records = []
    p = output_dir / "search_diagnostics.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines()[-100:]:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
    return {"active_run": active_search_run(output_dir), "records": records}


@app.get("/api/debug-search")
def debug_search(title: str, limit: int = 10) -> Dict[str, Any]:
    runtime_keywords = split_titles(title)
    if not runtime_keywords:
        return {"ok": False, "error": "missing title", "jobs": []}
    config = load_config()
    config["search"] = dict(config["search"])
    config["search"]["keywords"] = runtime_keywords
    search_plan = SearchPlanBuilder.build(config)
    search_plan["total_limit"] = limit
    search_plan["jobs_per_source"] = min(limit, 5)
    search_plan["max_pages"] = 1
    engine = IsraelSearchEngine(sources=search_plan.get("sources", []), max_pages=1)
    jobs = engine.search_from_plan(search_plan)
    return {"ok": True, "count": len(jobs), "keywords": runtime_keywords, "jobs": [{"title": j.title, "company": j.company, "source": j.source} for j in jobs[:limit]]}


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
            sig = request.headers.get("x-takbull-signature", "")
            if sig != expected_secret:
                return JSONResponse({"ok": False, "error": "invalid signature"}, status_code=401)
        payment_status = detect_payment_status(payload)
        active = payment_status == "paid"
        user_id = extract_user_identifier(payload)
        record = {"active": active, "provider": "takbull", "payment_status": payment_status, "updated_at": datetime.now(timezone.utc).isoformat(), "user_identifier": user_id, "raw_payload": payload}
        status_path = Path(subscription.get("status_path", "data_folder/output/subscription_status.json"))
        write_json_file(status_path, record)
        return JSONResponse({"ok": True, "subscription_active": active, "payment_status": payment_status})
    except Exception:
        return JSONResponse({"ok": False, "error": "webhook processing failed"}, status_code=500)


# ─── Helpers ────────────────────────────────────────────────

def page(title: str, body: str, landing: bool = False) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">
  <title>{title}</title>
  <link rel="icon" href="/assets/brand/jobfinder-logo.png">
  <style>{css()}</style>
</head>
<body>
  {body}
  <div id="loading-overlay" class="loading-overlay" hidden>
    <div class="loading-card">
      <div class="spinner"></div>
      <strong>JobFinder מחפש עבורך עד 100 משרות מתאימות</strong>
      <span id="loading-message">זה יכול לקחת דקה או שתיים.</span>
      <div class="loading-progress"><span id="loading-progress-bar" style="width:0%"></span></div>
      <small id="loading-count">נמצאו 0 מתוך 100 משרות</small>
      <button id="cancel-search-button" class="secondary" type="button">עצור ושמור מה שנמצא</button>
    </div>
  </div>
  <script src="/assets/app.js"></script>
</body>
</html>"""
    return HTMLResponse(html, headers={"Cache-Control": "no-cache,no-store,must-revalidate"})


def sidebar(active: str) -> str:
    items = [("dashboard", "/dashboard", "Dashboard"), ("jobs", "/jobs", "Jobs"), ("inbox", "/inbox", "Inbox"), ("settings", "/settings", "Settings"), ("resume", "/upload-cv", "Resume")]
    links = "".join(f"<a class='{'active' if k == active else ''}' href='{h}'>{l}</a>" for k, h, l in items)
    return f"<aside class='side'>{links}</aside>"


def search_form_html(current_title: str, label: str) -> str:
    return f'<form class="search-inline" method="post" action="/api/run-ui"><input name="job_title" value="{escape(current_title)}" placeholder="Backend Developer, Economist..." /><button class="primary" type="submit">{escape(label)}</button></form>'


def split_titles(raw: str) -> list[str]:
    return [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]


def update_search_titles(raw: str) -> None:
    titles = split_titles(raw)
    if not titles:
        return
    config = load_config()
    config.setdefault("search", {})["keywords"] = titles
    Path(config_path()).write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")


def current_search_title() -> str:
    try:
        return ", ".join(load_config().get("search", {}).get("keywords", [])[:3])
    except Exception:
        return ""


def start_background_pipeline(max_jobs: int = 100, runtime_keywords: list[str] | None = None) -> None:
    def runner() -> None:
        try:
            DailyPipeline(config_path=config_path(), runtime_keywords=runtime_keywords).run(max_jobs=max_jobs)
        except Exception as exc:
            try:
                config = load_config()
                output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
                output_dir.mkdir(parents=True, exist_ok=True)
                write_json_file(output_dir / "job_search_progress.json", {"message": f"שגיאה: {exc}", "phase": "failed", "jobs_found_so_far": 0, "target_jobs": max_jobs, "percent": 100, "updated_at": datetime.now(timezone.utc).isoformat()})
            except Exception:
                pass
    threading.Thread(target=runner, daemon=True).start()


def prepare_new_search_run(search_title: str, target_jobs: int = 100) -> str:
    config = load_config()
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in ["automation_status.json", "daily_summary.json", "ai_insights.json", "search_diagnostics.jsonl"]:
        p = output_dir / f
        if p.exists():
            p.unlink()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    write_json_file(output_dir / "active_search_run.json", {"run_id": run_id, "search_title": search_title, "target_jobs": target_jobs, "started_at": datetime.now(timezone.utc).isoformat()})
    write_json_file(output_dir / "job_search_progress.json", {"message": "מתחיל חיפוש חדש.", "phase": "starting", "jobs_found_so_far": 0, "target_jobs": target_jobs, "percent": 1, "updated_at": datetime.now(timezone.utc).isoformat()})
    return run_id


def active_search_run(output_dir: Path) -> Dict[str, Any] | None:
    p = output_dir / "active_search_run.json"
    return read_json_file(p, None) if p.exists() else None


def clear_cancel_flag() -> None:
    try:
        config = load_config()
        f = Path(config["output"].get("summary_dir", "data_folder/output")) / "cancel_search.flag"
        if f.exists():
            f.unlink()
    except Exception:
        pass


def get_status_data(config: Dict[str, Any]) -> Dict[str, Any]:
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    p = output_dir / "automation_status.json"
    if p.exists():
        return read_json_file(p, {})
    return {"status": "לא רץ עדיין", "subscription_locked": is_subscription_locked(config), "subscription_pay_url": config.get("subscription", {}).get("pay_url", ""), "application_inbox": [], "jobs_found_today": 0, "applications_sent_today": 0, "requires_approval": 0, "daily_limit": f"0/{config.get('automation', {}).get('daily_application_limit', 10)}"}


def in_progress_status(config: Dict[str, Any], progress: Dict[str, Any]) -> Dict[str, Any]:
    return {**get_status_data(config), **progress}


def empty_fresh_status(config: Dict[str, Any], msg: str) -> Dict[str, Any]:
    return {**get_status_data(config), "status": msg}


def is_subscription_locked(config: Dict[str, Any]) -> bool:
    raw = config.get("subscription", {}).get("status_path", "")
    if not raw:
        return bool(config.get("subscription", {}).get("enabled", True))
    sp = Path(raw)
    if not sp.exists():
        return bool(config.get("subscription", {}).get("enabled", True))
    try:
        return not bool(read_json_file(sp, {}).get("active"))
    except Exception:
        return True


def metric_grid(items: list[tuple[str, Any]]) -> str:
    return "<section class='grid metrics'>" + "".join(f"<div class='metric'><span>{l}</span><strong>{v}</strong></div>" for l, v in items) + "</section>"


def job_card(item: Dict[str, Any]) -> str:
    score = item.get("score", 0) or 0
    status = item.get("status_label", item.get("status", ""))
    return (f'<article class="job-card"><div><span class="badge">{escape(status)}</span>'
            f'<div class="job-card-title">{escape(item.get("title", ""))}</div>'
            f'<div class="job-card-meta"><span>🏢 {escape(item.get("company", ""))}</span></div></div>'
            f'<div class="score"><strong>{score}</strong><span>match</span></div>'
            f'<a class="button secondary" href="{item.get("apply_url") or "#"}">פתח</a></article>')


def progress_percent(value: str) -> int:
    try:
        used, total = value.split("/")
        return max(0, min(100, int(int(used) / max(int(total), 1) * 100)))
    except Exception:
        return 0


def option(value: str, label: str, selected: str) -> str:
    return f"<option value='{value}'{' selected' if value == selected else ''}>{label}</option>"


def config_path() -> str:
    return os.getenv("WORK_PREFERENCES_PATH", DEFAULT_CONFIG_PATH)


def load_config() -> Dict[str, Any]:
    return yaml.safe_load(Path(config_path()).read_text(encoding="utf-8"))


def read_json_file(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def parse_payload(request: Request) -> Dict[str, Any]:
    if "application/json" in request.headers.get("content-type", ""):
        return await request.json()
    return dict(await request.form())


def detect_payment_status(payload: Dict[str, Any]) -> str:
    text = " ".join(str(v).lower() for k in ["status", "transaction_status", "payment_status", "event"] if (v := payload.get(k)))
    if any(w in text for w in ["paid", "approved", "success", "completed"]):
        return "paid"
    if any(w in text for w in ["failed", "cancel", "declined", "refund"]):
        return "failed"
    return "new_transaction"


def extract_user_identifier(payload: Dict[str, Any]) -> str:
    for k in ["email", "customer_email", "phone", "user_id", "order_id"]:
        if v := payload.get(k):
            return str(v)
    return ""


def search_form(button_label: str) -> str:
    return search_form_html(current_search_title(), button_label)


def landing_css() -> str:
    return """
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:16px;scroll-behavior:smooth}
body.lp-body{font-family:'Inter','Noto Sans Hebrew',system-ui,sans-serif;background:#06080f;color:#e2e8f0;-webkit-font-smoothing:antialiased;overflow-x:hidden;direction:rtl}
/* NAV */
.lp-nav{position:sticky;top:0;z-index:999;background:rgba(6,8,15,.8);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.06);transition:all .3s}
.lp-nav-scrolled{background:rgba(6,8,15,.95);box-shadow:0 4px 30px rgba(0,0,0,.5)}
.lp-nav-inner{display:flex;align-items:center;gap:24px;height:68px;max-width:1180px;margin:0 auto;padding:0 24px}
.lp-brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:20px;color:#fff;margin-left:auto}
.lp-brand img{width:34px;height:34px;object-fit:contain;filter:drop-shadow(0 0 8px rgba(99,102,241,.6))}
.lp-links{display:flex;list-style:none;gap:4px;margin-right:auto}
.lp-links a{padding:8px 14px;border-radius:8px;font-size:14px;font-weight:500;color:#94a3b8;transition:all .2s}
.lp-links a:hover,.lp-link-app{color:#fff}
.lp-links .lp-link-app:hover{background:rgba(255,255,255,.06)}
.lp-cta-btn{display:inline-flex;align-items:center;padding:10px 22px;border-radius:8px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-weight:700;font-size:14px;white-space:nowrap;transition:all .25s;border:none;cursor:pointer;text-decoration:none;box-shadow:0 4px 20px rgba(99,102,241,.35)}
.lp-cta-btn:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(99,102,241,.5)}
.lp-burger{display:none;flex-direction:column;gap:5px;background:none;border:none;cursor:pointer;padding:8px}
.lp-burger span{display:block;width:22px;height:2px;background:#94a3b8;border-radius:2px;transition:all .25s}
.lp-burger.open span:nth-child(1){transform:translateY(7px) rotate(45deg)}
.lp-burger.open span:nth-child(2){opacity:0}
.lp-burger.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
.lp-mobile-menu{display:none;flex-direction:column;gap:8px;padding:16px 24px;border-top:1px solid rgba(255,255,255,.06);background:rgba(6,8,15,.98)}
.lp-mobile-menu.open{display:flex}
.lp-mobile-menu a{padding:12px 16px;color:#94a3b8;border-radius:8px;font-size:15px;font-weight:500;transition:all .2s}
.lp-mobile-menu a:hover{background:rgba(255,255,255,.05);color:#fff}
/* HERO */
.lp-hero{position:relative;padding:100px 0 80px;overflow:hidden}
.lp-hero-bg{position:absolute;inset:0;background:radial-gradient(ellipse 80% 60% at 50% -10%,rgba(99,102,241,.18) 0,transparent 70%),radial-gradient(ellipse 60% 40% at 80% 60%,rgba(139,92,246,.10) 0,transparent 60%);pointer-events:none}
.lp-hero-grid{display:grid;grid-template-columns:1fr 1fr;align-items:center;gap:64px;max-width:1180px;margin:0 auto;padding:0 24px}
.lp-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.3);color:#a5b4fc;border-radius:999px;padding:7px 16px;font-size:13px;font-weight:600;margin-bottom:28px;letter-spacing:.02em}
.lp-h1{font-size:clamp(40px,5.5vw,68px);font-weight:900;line-height:1.05;color:#fff;letter-spacing:-.04em;margin-bottom:22px}
.lp-gradient{background:linear-gradient(135deg,#6366f1 0%,#a855f7 50%,#06b6d4 100%);-webkit-background-clip:text;color:transparent;background-size:200% 200%;animation:grad 5s ease infinite}
@keyframes grad{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.lp-sub{font-size:18px;line-height:1.7;color:#94a3b8;margin-bottom:36px;max-width:520px}
.lp-hero-btns{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:28px}
.lp-btn-primary{display:inline-flex;align-items:center;gap:8px;padding:15px 30px;border-radius:10px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-weight:700;font-size:16px;transition:all .25s;box-shadow:0 6px 24px rgba(99,102,241,.4);text-decoration:none;border:none;cursor:pointer}
.lp-btn-primary:hover{transform:translateY(-3px);box-shadow:0 12px 40px rgba(99,102,241,.55)}
.lp-btn-ghost{display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:10px;background:rgba(255,255,255,.05);color:#e2e8f0;font-weight:600;font-size:16px;border:1px solid rgba(255,255,255,.12);transition:all .25s;text-decoration:none}
.lp-btn-ghost:hover{background:rgba(255,255,255,.09);border-color:rgba(255,255,255,.25);color:#fff}
.lp-trust-row{display:flex;align-items:center;gap:20px;flex-wrap:wrap;color:#64748b;font-size:14px;font-weight:500}
.lp-trust-row span{color:#10b981}
/* MOCKUP */
.lp-hero-right{position:relative;display:flex;justify-content:center}
.lp-mockup{background:rgba(15,18,30,.9);border:1px solid rgba(255,255,255,.10);border-radius:24px;padding:28px;max-width:380px;width:100%;backdrop-filter:blur(20px);box-shadow:0 30px 80px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,255,255,.08);animation:float 4s ease-in-out infinite alternate}
@keyframes float{from{transform:translateY(0) rotate(-.5deg)}to{transform:translateY(-14px) rotate(.5deg)}}
.lp-mockup-header{display:flex;align-items:center;gap:14px;margin-bottom:20px}
.lp-mockup-logo{width:48px;height:48px;border-radius:14px;display:grid;place-items:center;color:#fff;font-weight:800;font-size:20px;flex-shrink:0}
.lp-mockup-co{font-weight:700;color:#f1f5f9;font-size:16px}
.lp-mockup-role{font-size:13px;color:#64748b;margin-top:2px}
.lp-mockup-new{margin-right:auto;background:rgba(16,185,129,.15);color:#10b981;border:1px solid rgba(16,185,129,.3);border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700}
.lp-score-bar{background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.15);border-radius:14px;padding:16px;margin-bottom:16px}
.lp-score-info{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.lp-score-label{font-size:13px;color:#64748b;font-weight:500}
.lp-score-pct{font-size:28px;font-weight:900;background:linear-gradient(135deg,#6366f1,#06b6d4);-webkit-background-clip:text;color:transparent}
.lp-score-track{height:6px;background:rgba(255,255,255,.06);border-radius:999px;overflow:hidden}
.lp-score-fill{height:100%;background:linear-gradient(90deg,#6366f1,#06b6d4);border-radius:999px;box-shadow:0 0 12px rgba(99,102,241,.6)}
.lp-mockup-tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px}
.lp-mockup-tags span{background:rgba(99,102,241,.12);color:#a5b4fc;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:600;border:1px solid rgba(99,102,241,.2)}
.lp-mockup-apply{width:100%;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:10px;padding:13px;font-size:15px;font-weight:700;cursor:pointer;margin-bottom:12px;transition:opacity .2s}
.lp-mockup-apply:hover{opacity:.9}
.lp-mockup-stat{font-size:12px;color:#475569;text-align:center}
.lp-float-badge{position:absolute;background:rgba(15,18,30,.95);border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:10px 16px;font-size:13px;font-weight:600;color:#e2e8f0;box-shadow:0 8px 32px rgba(0,0,0,.4);backdrop-filter:blur(12px);white-space:nowrap}
.lp-float-1{top:-12px;left:-20px;animation:fb1 3s ease-in-out infinite alternate}
.lp-float-2{bottom:20px;right:-20px;animation:fb2 4s ease-in-out infinite alternate}
@keyframes fb1{from{transform:translateY(0)}to{transform:translateY(-8px)}}
@keyframes fb2{from{transform:translateY(0)}to{transform:translateY(8px)}}
/* PROOF */
.lp-proof{padding:28px 24px;background:rgba(255,255,255,.02);border-top:1px solid rgba(255,255,255,.05);border-bottom:1px solid rgba(255,255,255,.05);display:flex;align-items:center;justify-content:center;gap:32px;flex-wrap:wrap}
.lp-proof-label{font-size:14px;font-weight:600;color:#475569;white-space:nowrap}
.lp-proof-logos{display:flex;align-items:center;gap:28px;flex-wrap:wrap;justify-content:center}
.lp-proof-logos span{font-size:15px;font-weight:800;opacity:.45;transition:opacity .2s;cursor:default}
.lp-proof-logos span:hover{opacity:.9}
/* HOW IT WORKS */
.lp-how{padding:100px 24px;max-width:1180px;margin:0 auto;text-align:center}
.lp-section-label{display:block;font-size:13px;font-weight:700;color:#6366f1;text-transform:uppercase;letter-spacing:.12em;margin-bottom:12px}
.lp-h2{font-size:clamp(30px,4vw,46px);font-weight:800;color:#fff;letter-spacing:-.03em;margin-bottom:56px;line-height:1.15}
.lp-steps{display:flex;align-items:flex-start;justify-content:center;gap:0}
.lp-step{text-align:center;padding:0 40px;flex:1;max-width:280px}
.lp-step-arrow{font-size:28px;color:#334155;padding-top:28px;flex-shrink:0}
.lp-step-num{width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-size:22px;font-weight:900;display:inline-grid;place-items:center;margin:0 auto 18px;box-shadow:0 0 0 8px rgba(99,102,241,.12)}
.lp-step-icon{font-size:30px;margin-bottom:16px}
.lp-step h3{font-size:19px;font-weight:700;color:#f1f5f9;margin-bottom:10px}
.lp-step p{font-size:15px;color:#64748b;line-height:1.65;max-width:220px;margin:0 auto}
/* FEATURES */
.lp-features{padding:100px 24px;background:rgba(255,255,255,.015)}
.lp-features .lp-h2{text-align:center}
.lp-features .lp-section-label{display:block;text-align:center}
.lp-feat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:1180px;margin:0 auto}
.lp-feat-card{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:30px 26px;transition:all .3s;position:relative;overflow:hidden}
.lp-feat-card::before{content:"";position:absolute;inset:-1px;border-radius:16px;background:linear-gradient(135deg,rgba(99,102,241,.3),rgba(139,92,246,.3));opacity:0;transition:opacity .3s;z-index:0}
.lp-feat-card:hover{transform:translateY(-5px);border-color:rgba(99,102,241,.4);box-shadow:0 20px 60px rgba(0,0,0,.4)}
.lp-feat-card:hover::before{opacity:1}
.lp-feat-card>*{position:relative;z-index:1}
.lp-feat-accent{background:linear-gradient(135deg,rgba(99,102,241,.12),rgba(139,92,246,.08));border-color:rgba(99,102,241,.25)}
.lp-feat-accent2{background:linear-gradient(135deg,rgba(6,182,212,.08),rgba(99,102,241,.06));border-color:rgba(6,182,212,.2)}
.lp-feat-icon{font-size:34px;margin-bottom:18px}
.lp-feat-card h3{font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:10px}
.lp-feat-card p{font-size:15px;color:#64748b;line-height:1.65}
/* TESTIMONIALS */
.lp-testimonials{padding:100px 24px;max-width:1180px;margin:0 auto;text-align:center}
.lp-tgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:0}
.lp-tcard{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:28px;text-align:right;transition:all .3s}
.lp-tcard:hover{border-color:rgba(99,102,241,.3);transform:translateY(-4px);box-shadow:0 20px 50px rgba(0,0,0,.4)}
.lp-tstars{color:#f59e0b;font-size:15px;margin-bottom:14px;letter-spacing:2px}
.lp-ttext{font-size:15px;color:#94a3b8;line-height:1.7;margin-bottom:20px;font-style:italic}
.lp-tauthor{display:flex;align-items:center;gap:12px}
.lp-tauthor img{width:44px;height:44px;border-radius:50%;object-fit:cover;border:2px solid rgba(99,102,241,.3);flex-shrink:0}
.lp-tauthor strong{display:block;font-size:14px;font-weight:700;color:#f1f5f9}
.lp-tauthor span{font-size:13px;color:#475569}
/* FINAL CTA */
.lp-final-cta{padding:100px 24px;background:linear-gradient(135deg,rgba(99,102,241,.15),rgba(139,92,246,.10));border-top:1px solid rgba(99,102,241,.2);border-bottom:1px solid rgba(99,102,241,.2);text-align:center}
.lp-final-inner{max-width:680px;margin:0 auto}
.lp-btn-white{display:inline-flex;align-items:center;gap:8px;padding:16px 36px;border-radius:10px;background:#fff;color:#4f46e5;font-weight:800;font-size:17px;transition:all .25s;box-shadow:0 8px 30px rgba(0,0,0,.2);text-decoration:none}
.lp-btn-white:hover{transform:translateY(-3px);box-shadow:0 16px 50px rgba(0,0,0,.3)}
/* FOOTER */
.lp-footer{padding:48px 24px 32px;background:#06080f;border-top:1px solid rgba(255,255,255,.06)}
.lp-footer-inner{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:20px;max-width:1180px;margin:0 auto}
.lp-footer-links{display:flex;gap:24px}
.lp-footer-links a{font-size:14px;color:#475569;transition:color .2s}
.lp-footer-links a:hover{color:#94a3b8}
/* REVEAL ANIMATION */
.lp-reveal{opacity:0;transform:translateY(28px);transition:opacity .65s cubic-bezier(.22,1,.36,1),transform .65s cubic-bezier(.22,1,.36,1)}
.lp-visible{opacity:1;transform:translateY(0)}
/* RESPONSIVE */
@media(max-width:900px){
  .lp-nav-inner{padding:0 16px}
  .lp-links,.lp-cta-btn{display:none}
  .lp-burger{display:flex}
  .lp-hero{padding:72px 0 56px}
  .lp-hero-grid{grid-template-columns:1fr;gap:48px;text-align:center;padding:0 20px}
  .lp-brand{margin-right:auto;margin-left:unset}
  .lp-sub,.lp-trust-row{margin-inline:auto;justify-content:center}
  .lp-hero-right{order:-1}
  .lp-mockup{max-width:320px;margin:0 auto}
  .lp-float-badge{display:none}
  .lp-steps{flex-direction:column;align-items:center;gap:32px}
  .lp-step-arrow{display:none}
  .lp-step{max-width:100%;padding:0}
  .lp-feat-grid{grid-template-columns:1fr 1fr}
  .lp-tgrid{grid-template-columns:1fr}
  .lp-footer-inner{flex-direction:column;align-items:center;text-align:center}
}
@media(max-width:560px){
  .lp-h1{font-size:36px}
  .lp-feat-grid{grid-template-columns:1fr}
  .lp-proof{gap:20px}
  .lp-hero-btns{flex-direction:column;align-items:stretch}
  .lp-btn-primary,.lp-btn-ghost{justify-content:center}
}
"""


def css() -> str:
    return """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--white:#fff;--off:#f8fafc;--gray-50:#f9fafb;--gray-100:#f3f4f6;--blue-50:#eff6ff;--blue-100:#dbeafe;--blue-600:#2563eb;--blue-700:#1d4ed8;--navy:#0f172a;--body:#374151;--muted:#6b7280;--border:#e5e7eb;--ok:#10b981;--warn:#f59e0b;--line:#e5e7eb}
html{scroll-behavior:smooth;font-size:16px}
body{font-family:'Inter','Noto Sans Hebrew',system-ui,sans-serif;background:var(--off);color:var(--body);line-height:1.6;-webkit-font-smoothing:antialiased;direction:rtl}
a{color:inherit;text-decoration:none}
h1{font-size:clamp(28px,4vw,42px);font-weight:800;line-height:1.15;color:var(--navy);letter-spacing:-.02em}
h2{font-size:clamp(22px,3vw,32px);font-weight:700;line-height:1.2;color:var(--navy);letter-spacing:-.015em}
h3{font-size:18px;font-weight:700;color:var(--navy)}
p{font-size:16px;line-height:1.7;color:var(--body)}
img{max-width:100%;display:block}
.app-layout{display:grid;grid-template-columns:220px 1fr;gap:24px;max-width:1200px;margin:28px auto;padding:0 24px;align-items:start}
.side{background:#fff;border:1px solid var(--border);border-radius:12px;padding:12px;position:sticky;top:20px;display:grid;gap:4px}
.side a{display:flex;align-items:center;padding:11px 14px;border-radius:8px;font-size:14px;font-weight:600;color:var(--muted);transition:all .15s}
.side a:hover{background:var(--gray-50);color:var(--navy)}
.side a.active{background:var(--blue-50);color:var(--blue-600)}
.workspace{min-width:0}
.panel{background:#fff;border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:20px}
.metrics,.status{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px}
.metric{background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px}
.metric span{display:block;font-size:12px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.metric strong{font-size:28px;font-weight:800;color:var(--navy)}
.job-list{display:grid;gap:12px}
.job-card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px 24px;display:grid;grid-template-columns:1fr 80px auto;align-items:center;gap:20px;transition:border-color .2s,box-shadow .2s}
.job-card:hover{border-color:var(--blue-600);box-shadow:0 4px 12px rgba(37,99,235,.08)}
.job-card-title{font-weight:700;font-size:16px;color:var(--navy);margin-bottom:4px}
.job-card-meta{font-size:14px;color:var(--muted)}
.score{text-align:center}
.score strong{display:block;font-size:28px;font-weight:800;color:var(--blue-600)}
.score span{font-size:12px;color:var(--muted)}
.badge{display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;background:var(--blue-50);color:var(--blue-600)}
.toolbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:24px}
.actions{display:flex;align-items:center;flex-wrap:wrap;gap:10px}
.button,.button:link{display:inline-flex;align-items:center;gap:8px;padding:10px 18px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;border:1.5px solid transparent;text-decoration:none;transition:all .2s;white-space:nowrap;line-height:1}
button{display:inline-flex;align-items:center;gap:8px;padding:10px 18px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;border:1.5px solid transparent;transition:all .2s;white-space:nowrap;line-height:1}
button:disabled{opacity:.6;cursor:wait}
.primary{background:var(--blue-600);color:#fff;border-color:var(--blue-600)}
.primary:hover{background:var(--blue-700);border-color:var(--blue-700);transform:translateY(-1px)}
.secondary{background:#fff;color:var(--navy);border-color:var(--border)}
.secondary:hover{border-color:var(--blue-600);color:var(--blue-600)}
.ghost{background:transparent;color:var(--muted);border-color:var(--border)}
.ghost:hover{border-color:var(--blue-600);color:var(--blue-600)}
.eyebrow{display:inline-block;color:var(--blue-600);font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
.progress{height:8px;background:var(--gray-100);border-radius:999px;overflow:hidden;margin-top:12px}
.progress span{display:block;height:100%;background:var(--blue-600);border-radius:999px;transition:width .4s}
.progress-card{margin-bottom:20px}
.grid{display:grid;gap:16px;margin-bottom:20px}
.two{grid-template-columns:repeat(2,1fr)}
.narrow{max-width:640px}
.onboarding{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}
.empty-state{background:#fff;border:1px solid var(--border);border-radius:12px;padding:64px 32px;text-align:center}
.empty-state h2{margin-bottom:10px}
.empty-state p{margin-bottom:24px;color:var(--muted)}
form{display:grid;gap:14px}
label{font-size:14px;font-weight:600;color:var(--body)}
input,select{width:100%;border:1.5px solid var(--border);border-radius:8px;padding:11px 14px;font-size:15px;color:var(--navy);background:#fff;outline:none;transition:border-color .15s,box-shadow .15s}
input:focus,select:focus{border-color:var(--blue-600);box-shadow:0 0 0 3px rgba(37,99,235,.1)}
.dropzone{border:2px dashed var(--border);border-radius:12px;padding:28px;text-align:center;transition:all .2s}
.dropzone:hover{border-color:var(--blue-600);background:var(--blue-50)}
.search-inline{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.search-inline input{min-width:min(320px,100%);width:auto;flex:1}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 20px}
.chips span{background:var(--blue-50);color:var(--blue-600);border-radius:999px;padding:5px 12px;font-weight:600;font-size:13px;border:1px solid var(--blue-100)}
.trust{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0}
.trust div{background:#fff;border:1px solid var(--border);border-radius:10px;padding:14px;color:var(--muted);font-size:14px;font-weight:600;display:flex;align-items:center;gap:8px}
.trust div::before{content:"✓";color:var(--ok);font-weight:800}
.timeline{display:grid;gap:10px}
.timeline div{display:flex;gap:14px;align-items:flex-start;padding:10px;border-radius:8px}
.timeline div:hover{background:var(--gray-50)}
.timeline b{width:28px;height:28px;border-radius:50%;background:var(--blue-600);color:#fff;font-size:13px;font-weight:800;display:grid;place-items:center;flex-shrink:0}
.feed{display:grid;gap:8px}
.feed div{padding:10px;border-radius:8px;color:var(--muted);font-size:14px}
.feed div:hover{background:var(--gray-50)}
.insights{display:grid;gap:0;list-style:none}
.insights li{font-size:14px;color:var(--body);padding:10px 0;border-bottom:1px solid var(--border);line-height:1.6}
.insights li:last-child{border:0}
.insights li b{color:var(--blue-600)}
table{width:100%;border-collapse:collapse}
th,td{border-bottom:1px solid var(--border);text-align:right;padding:12px 16px;font-size:14px}
th{font-weight:700;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
tr:hover td{background:var(--gray-50)}
.loading-overlay{position:fixed;inset:0;background:rgba(0,0,0,.55);backdrop-filter:blur(6px);z-index:200;display:grid;place-items:center;padding:24px}
.loading-overlay[hidden]{display:none}
.loading-card{background:#fff;border:1px solid var(--border);border-radius:16px;padding:36px;width:min(480px,100%);text-align:center;box-shadow:0 24px 80px rgba(0,0,0,.12)}
.loading-card strong{display:block;font-size:18px;font-weight:700;color:var(--navy);margin:16px 0 8px}
.loading-card span{color:var(--muted);font-size:15px}
.loading-card small{display:block;color:var(--muted);font-size:13px;margin-top:8px}
.loading-progress{height:6px;background:var(--gray-100);border-radius:999px;overflow:hidden;margin-top:20px}
.loading-progress span{display:block;height:100%;width:0;background:var(--blue-600);border-radius:999px;transition:width .35s}
.spinner{width:44px;height:44px;border:3px solid var(--gray-100);border-top-color:var(--blue-600);border-radius:50%;margin:0 auto;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:900px){.app-layout{grid-template-columns:1fr;margin:16px auto}.side{position:static;grid-template-columns:repeat(3,1fr)}.side a{justify-content:center}.metrics,.status,.trust{grid-template-columns:repeat(2,1fr)}.job-card{grid-template-columns:1fr}.two,.onboarding{grid-template-columns:1fr}}
@media(max-width:560px){.metrics,.status,.trust,.side{grid-template-columns:1fr}}
"""
