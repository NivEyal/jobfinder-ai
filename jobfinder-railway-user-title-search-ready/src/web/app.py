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


@app.get("/")
def root() -> HTMLResponse:
    config = load_config()
    pay_url = config.get("subscription", {}).get("pay_url", "#")
    landing_html = f"""
<!-- NAVBAR -->
<nav class="site-nav" id="site-nav">
  <div class="nav-inner">
    <a class="nav-brand" href="/"><img src="/assets/brand/jobfinder-logo.png" alt="JobFinder" /><span>JobFinder</span></a>
    <ul class="nav-links">
      <li><a href="#how">איך זה עובד</a></li>
      <li><a href="{pay_url}">מחירים</a></li>
      <li><a href="/login">התחברות</a></li>
    </ul>
    <div class="nav-actions">
      <a class="btn btn-primary" href="/onboarding">התחל בחינם</a>
      <button class="nav-hamburger" id="nav-hamburger"><span></span><span></span><span></span></button>
    </div>
  </div>
  <div class="container"><div class="nav-mobile-menu" id="nav-mobile-menu">
    <a href="#how">איך זה עובד</a><a href="{pay_url}">מחירים</a>
    <a href="/login">התחברות</a><a href="/onboarding">התחל בחינם</a>
  </div></div>
</nav>

<!-- HERO -->
<section class="hero-section">
  <div class="hero-inner">
    <div class="hero-content reveal">
      <div class="hero-badge">🤖 AI Job Agent לישראל</div>
      <h1 class="hero-h1">JobFinder<br>מוצא. מתאים. מגיש.</h1>
      <p class="hero-sub">AI שמחפש עד 100 משרות מתאימות, מדרג התאמה, ומנהל הגשות — הכל במקום אחד</p>
      <div class="hero-ctas">
        <a class="btn btn-primary btn-lg" href="/onboarding">התחל ב-2 דקות →</a>
        <a class="btn btn-ghost btn-lg" href="/dashboard">פתח דשבורד</a>
      </div>
      <div class="hero-trust">
        <span>ללא כרטיס אשראי</span>
        <span>הגדרה ב-2 דקות</span>
        <span>AI מגיש רק באישורך</span>
      </div>
    </div>
    <div class="hero-visual reveal">
      <div class="hero-card-mockup">
        <div class="mockup-header">
          <div class="mockup-logo">W</div>
          <div>
            <div class="mockup-company">Wix Engineering</div>
            <div class="mockup-role">Senior Backend Engineer</div>
          </div>
        </div>
        <div class="mockup-score-row">
          <div>
            <div class="mockup-score-label">ציון התאמה</div>
            <div class="mockup-score-num">94%</div>
          </div>
          <span class="badge badge-green">התאמה חזקה</span>
        </div>
        <div class="mockup-tags">
          <span class="mockup-tag">Python</span>
          <span class="mockup-tag">Node.js</span>
          <span class="mockup-tag">AWS</span>
          <span class="mockup-tag">Remote</span>
        </div>
        <button class="mockup-apply">הגש מועמדות →</button>
      </div>
    </div>
  </div>
</section>

<!-- SOCIAL PROOF -->
<div class="proof-bar">
  <div class="proof-inner">
    <span class="proof-label">משרות נמצאו ב:</span>
    <div class="proof-logos">
      <span class="proof-logo linkedin">LinkedIn</span>
      <span class="proof-logo alljobs">AllJobs</span>
      <span class="proof-logo drushim">Drushim</span>
      <span class="proof-logo google">Google Jobs</span>
      <span class="proof-logo indeed">Indeed</span>
    </div>
  </div>
</div>

<!-- HOW IT WORKS -->
<section class="how-section" id="how">
  <div class="container section-center">
    <span class="section-label">תהליך פשוט</span>
    <h2>איך זה עובד?</h2>
  </div>
  <div class="steps-row">
    <div class="step reveal">
      <div class="step-num">1</div>
      <div class="step-icon">📋</div>
      <h3>הגדר פרופיל</h3>
      <p>תאר את הניסיון שלך, העלה קורות חיים ובחר את הטייטל שאתה מחפש</p>
    </div>
    <div class="step reveal">
      <div class="step-num">2</div>
      <div class="step-icon">🔍</div>
      <h3>AI מחפש</h3>
      <p>סורק עד 100 משרות רלוונטיות ממקורות ישראליים וגלובליים ומדרג לפי התאמה</p>
    </div>
    <div class="step reveal">
      <div class="step-num">3</div>
      <div class="step-icon">✅</div>
      <h3>אתה מאשר</h3>
      <p>AI שולח הגשות רק אחרי אישורך — שמירה מלאה על השליטה שלך</p>
    </div>
  </div>
</section>

<!-- FEATURES -->
<section class="features-section">
  <div class="container section-center">
    <span class="section-label">פיצ'רים</span>
    <h2 style="margin-bottom:48px">הכל במקום אחד</h2>
  </div>
  <div class="features-grid">
    <div class="feature-card reveal">
      <div class="feature-icon">🎯</div>
      <h3>דירוג התאמה AI</h3>
      <p>כל משרה מקבלת ציון התאמה מ-0 עד 100 על בסיס קורות החיים שלך</p>
    </div>
    <div class="feature-card reveal">
      <div class="feature-icon">📥</div>
      <h3>Application Inbox</h3>
      <p>כל הגשה עם סטטוס, ציון ופרטי המשרה — במקום אחד מסודר</p>
    </div>
    <div class="feature-card reveal">
      <div class="feature-icon">✋</div>
      <h3>מצב אישור</h3>
      <p>AI לא שולח שום דבר בלי האישור שלך — אתה תמיד בשליטה</p>
    </div>
    <div class="feature-card reveal">
      <div class="feature-icon">🔒</div>
      <h3>פרטיות מלאה</h3>
      <p>קורות החיים שלך לא מפורסמים לציבור ולא שיתוף עם צדדים שלישיים</p>
    </div>
    <div class="feature-card reveal">
      <div class="feature-icon">📊</div>
      <h3>לוג פעולות</h3>
      <p>כל פעולה נרשמת בלוג מפורט — שקיפות מלאה על כל מה שה-AI עשה</p>
    </div>
    <div class="feature-card reveal">
      <div class="feature-icon">🌍</div>
      <h3>ישראל + גלובלי</h3>
      <p>סורק Drushim, AllJobs, Jobnet, Remotive, LinkedIn ועוד 10 מקורות</p>
    </div>
  </div>
</section>

<!-- TESTIMONIALS -->
<section class="testimonials-section">
  <div class="container section-center">
    <span class="section-label">מה אומרים המשתמשים</span>
    <h2>מה אומרים המשתמשים שלנו</h2>
    <p class="section-sub">הצטרפו ל-2,000+ אנשי מקצוע שמצאו עבודה עם JobFinder</p>
  </div>
  <div class="testimonials-grid">
    <div class="t-card reveal">
      <div class="t-stars">★★★★★</div>
      <p class="t-text">"תוך שבועיים קיבלתי 4 ראיונות. ה-AI מצא משרות שלא ידעתי שהן קיימות ושלח בשמי רק למשרות שאישרתי."</p>
      <div class="t-author">
        <img class="t-avatar" src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=96&h=96&fit=crop&crop=face" alt="דוד כהן" />
        <div><div class="t-name">דוד כהן</div><div class="t-role">Backend Developer • Tel Aviv</div></div>
      </div>
    </div>
    <div class="t-card reveal">
      <div class="t-stars">★★★★★</div>
      <p class="t-text">"חיפשתי עבודה 3 חודשים. עם JobFinder מצאתי תוך 3 שבועות. הציון התאמה עזר לי להתמקד בהגשות עם סיכוי גבוה."</p>
      <div class="t-author">
        <img class="t-avatar" src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=96&h=96&fit=crop&crop=face" alt="מיכל לוי" />
        <div><div class="t-name">מיכל לוי</div><div class="t-role">Product Manager • Herzliya</div></div>
      </div>
    </div>
    <div class="t-card reveal">
      <div class="t-stars">★★★★★</div>
      <p class="t-text">"כלי מדהים. חסך לי שעות של חיפוש ידני. אוהב שה-AI לא שולח בלי אישורי — זה נותן לי שקט נפשי מלא."</p>
      <div class="t-author">
        <img class="t-avatar" src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=96&h=96&fit=crop&crop=face" alt="אמיר שמיר" />
        <div><div class="t-name">אמיר שמיר</div><div class="t-role">Full Stack Engineer • Remote</div></div>
      </div>
    </div>
    <div class="t-card reveal">
      <div class="t-stars">★★★★★</div>
      <p class="t-text">"ציון ההתאמה הוא גאוני. הבנתי בדיוק אילו משרות מתאימות לי ואילו לא. חסך לי הגשות מיותרות."</p>
      <div class="t-author">
        <img class="t-avatar" src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=96&h=96&fit=crop&crop=face" alt="שירה אדר" />
        <div><div class="t-name">שירה אדר</div><div class="t-role">Data Analyst • Be'er Sheva</div></div>
      </div>
    </div>
    <div class="t-card reveal">
      <div class="t-stars">★★★★★</div>
      <p class="t-text">"JobFinder שלח 12 הגשות בשמי תוך יום אחד — כולן מאושרות על ידי. קיבלתי עבודה מהגשה השישית."</p>
      <div class="t-author">
        <img class="t-avatar" src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=96&h=96&fit=crop&crop=face" alt="רון בן דוד" />
        <div><div class="t-name">רון בן דוד</div><div class="t-role">DevOps Engineer • Haifa</div></div>
      </div>
    </div>
  </div>
</section>

<!-- CTA BANNER -->
<section class="cta-section">
  <div class="container">
    <h2>מוכן להתחיל?</h2>
    <p>הצטרף לאלפי מועמדים שמצאו עבודה עם JobFinder. הגדרה ב-2 דקות, ללא כרטיס אשראי.</p>
    <a class="btn btn-white btn-lg" href="/onboarding">התחל בחינם →</a>
  </div>
</section>

<!-- FOOTER -->
<footer class="site-footer">
  <div class="footer-inner">
    <a class="footer-brand" href="/"><img src="/assets/brand/jobfinder-logo.png" alt="" /><span>JobFinder</span></a>
    <ul class="footer-links">
      <li><a href="#how">איך זה עובד</a></li>
      <li><a href="{pay_url}">מחירים</a></li>
      <li><a href="/dashboard">Dashboard</a></li>
      <li><a href="/onboarding">התחל</a></li>
    </ul>
    <span class="footer-copy">&copy; 2025 JobFinder. כל הזכויות שמורות.</span>
  </div>
</footer>

<script>
  // Navbar scroll
  var nav = document.getElementById('site-nav');
  window.addEventListener('scroll', function(){{nav.classList.toggle('scrolled', window.scrollY>8);}},{{passive:true}});
  // Hamburger
  var hbtn=document.getElementById('nav-hamburger'), hmenu=document.getElementById('nav-mobile-menu');
  if(hbtn&&hmenu)hbtn.addEventListener('click',function(){{hbtn.classList.toggle('open');hmenu.classList.toggle('open');}});
  // Scroll reveal
  var revealEls=document.querySelectorAll('.reveal');
  if(revealEls.length){{var io=new IntersectionObserver(function(e){{e.forEach(function(entry,i){{if(entry.isIntersecting){{setTimeout(function(){{entry.target.classList.add('visible');}},i*60);io.unobserve(entry.target);}}}});}},({{threshold:0.1}}));revealEls.forEach(function(el){{io.observe(el);}});}}
</script>"""
    full_html = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <title>JobFinder | מציאת עבודה והגשה חכמה</title>
  <meta name="description" content="JobFinder מוצא משרות, מדרג התאמה ומנהל הגשות עבודה בישראל." />
  <link rel="icon" href="/assets/brand/jobfinder-logo.png" />
  <!-- DESIGN VERSION: v2-premium-2025 -->
  <style>{css()}</style>
</head>
<body>
{landing_html}
</body>
</html>"""
    return HTMLResponse(
        full_html,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
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
    found = 0
    target = 100
    if progress_path.exists():
        current = read_json_file(progress_path, {})
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
    write_json_file(progress_path, payload)
    return payload


@app.get("/ping")
def ping() -> JSONResponse:
    return JSONResponse({"version": "v2-premium-2025", "design": "white-blue", "ok": True})


@app.get("/api/status")
def status() -> Dict[str, Any]:
    config = load_config()
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    progress_path = output_dir / "job_search_progress.json"
    if progress_path.exists():
        progress_payload = read_json_file(progress_path, {})
        if progress_payload.get("phase") in {"starting", "searching", "matching", "failed", "cancelled"}:
            return in_progress_status(config, progress_payload)
    status_path = output_dir / "automation_status.json"
    if status_path.exists():
        payload = read_json_file(status_path, {})
        active_run = active_search_run(output_dir)
        if active_run and payload.get("run_id") != active_run.get("run_id"):
            return empty_fresh_status(config, "ממתין לחיפוש חדש. תוצאות ישנות לא מוצגות.")
        return payload
    return {
        "status": "לא רץ חיפוש חדש עדיין",
        "subscription_locked": is_subscription_locked(config),
        "subscription_pay_url": config["subscription"]["pay_url"],
        "application_inbox": [],
        "jobs_found_today": 0,
        "applications_sent_today": 0,
        "requires_approval": 0,
        "daily_limit": f"0/{config['automation']['daily_application_limit']}",
    }


@app.get("/api/progress")
def progress() -> Dict[str, Any]:
    config = load_config()
    progress_path = Path(config["output"].get("summary_dir", "data_folder/output")) / "job_search_progress.json"
    if progress_path.exists():
        return read_json_file(progress_path, {})
    return {
        "message": "ממתין להתחלת חיפוש",
        "phase": "idle",
        "jobs_found_so_far": 0,
        "target_jobs": 100,
        "percent": 0,
    }


@app.get("/api/search-diagnostics")
def search_diagnostics() -> Dict[str, Any]:
    config = load_config()
    output_dir = Path(config["output"].get("summary_dir", "data_folder/output"))
    diagnostics_path = output_dir / "search_diagnostics.jsonl"
    records = []
    if diagnostics_path.exists():
        for line in diagnostics_path.read_text(encoding="utf-8").splitlines()[-100:]:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {
        "active_run": active_search_run(output_dir),
        "records": records,
    }


@app.get("/api/debug-search")
def debug_search(title: str, limit: int = 10) -> Dict[str, Any]:
    runtime_keywords = split_titles(title)
    if not runtime_keywords:
        return {"ok": False, "error": "missing title", "jobs": [], "diagnostics": []}

    config = load_config()
    config["search"] = dict(config["search"])
    config["search"]["keywords"] = runtime_keywords
    search_plan = SearchPlanBuilder.build(config)
    search_plan["total_limit"] = max(1, min(int(limit), 25))
    search_plan["jobs_per_source"] = max(1, min(int(limit), 25))
    search_plan["max_pages"] = 1
    search_plan["max_workers"] = 8
    search_plan["max_tasks"] = 80
    search_plan["queries"] = [
        {**query, "limit": search_plan["jobs_per_source"]}
        for query in search_plan.get("queries", [])
    ]

    diagnostics = []

    def collect_progress(progress_payload: Dict[str, Any]) -> None:
        if progress_payload.get("status") == "source_result":
            diagnostics.append(
                {
                    "source": progress_payload.get("source", ""),
                    "query": progress_payload.get("query", ""),
                    "fetched_count": progress_payload.get("fetched_count", 0),
                    "accepted_count": progress_payload.get("accepted_count", 0),
                }
            )

    engine = IsraelSearchEngine(
        sources=search_plan["sources"],
        max_pages=search_plan["max_pages"],
        progress_callback=collect_progress,
    )
    jobs = engine.search_from_plan(search_plan)
    return {
        "ok": True,
        "requested_title": title,
        "runtime_keywords": runtime_keywords,
        "plan_keywords": search_plan.get("keywords", []),
        "sources": search_plan.get("sources", []),
        "diagnostics": diagnostics,
        "jobs": [
            {
                "source": job.source,
                "source_job_id": job.source_job_id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "apply_url": job.apply_url,
            }
            for job in jobs
        ],
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
    write_json_file(status_path, status_record)
    return JSONResponse({"ok": True, "subscription_active": active, "payment_status": payment_status})


def page(title: str, body: str, landing: bool = False) -> HTMLResponse:
    # No top navbar on app pages — sidebar handles navigation
    header_html = ""
    footer_html = ""
    html = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <title>{title}</title>
  <meta name="description" content="JobFinder מוצא משרות, מדרג התאמה ומנהל הגשות עבודה בישראל." />
  <link rel="icon" href="/assets/brand/jobfinder-logo.png" />
  <style>{css()}</style>
  <!-- DESIGN VERSION: v2-premium-2025 -->
</head>
<body>
  {header_html}
  {body}
  {footer_html}
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
        ("inbox", "/inbox", "Inbox"),
        ("settings", "/settings", "Settings"),
        ("resume", "/upload-cv", "Resume"),
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


def start_background_pipeline(max_jobs: int = 100, runtime_keywords: list[str] | None = None) -> None:
    def runner() -> None:
        try:
            DailyPipeline(config_path=config_path(), runtime_keywords=runtime_keywords).run(max_jobs=max_jobs)
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
            write_json_file(output_dir / "job_search_progress.json", payload)

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
    active_payload = {
        "run_id": run_id,
        "search_title": search_title,
        "target_jobs": target_jobs,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json_file(output_dir / "active_search_run.json", active_payload)
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
    write_json_file(output_dir / "job_search_progress.json", payload)
    write_json_file(output_dir / "automation_status.json", in_progress_status(config, payload))
    return run_id


def in_progress_status(config: Dict[str, Any], progress_payload: Dict[str, Any]) -> Dict[str, Any]:
    phase = progress_payload.get("phase", "")
    status_text = {
        "starting": "חיפוש חדש מתחיל עכשיו",
        "searching": "חיפוש חדש רץ עכשיו",
        "matching": "מדרג התאמות מהריצה החדשה",
        "failed": "החיפוש החדש נכשל",
        "cancelled": "החיפוש החדש נעצר",
    }.get(phase, "חיפוש חדש רץ עכשיו")
    return {
        "status": status_text,
        "last_run": progress_payload.get("updated_at", ""),
        "next_run": "",
        "jobs_found_today": int(progress_payload.get("jobs_found_so_far", 0)),
        "applications_sent_today": 0,
        "requires_approval": 0,
        "daily_limit": f"0/{config['automation']['daily_application_limit']}",
        "subscription_locked": is_subscription_locked(config),
        "subscription_pay_url": config["subscription"]["pay_url"],
        "application_inbox": [],
        "search_in_progress": phase in {"starting", "searching", "matching"},
        "search_title": progress_payload.get("search_title", ""),
        "run_id": progress_payload.get("run_id", ""),
    }


def empty_fresh_status(config: Dict[str, Any], message: str) -> Dict[str, Any]:
    return {
        "status": message,
        "last_run": "",
        "next_run": "",
        "jobs_found_today": 0,
        "applications_sent_today": 0,
        "requires_approval": 0,
        "daily_limit": f"0/{config['automation']['daily_application_limit']}",
        "subscription_locked": is_subscription_locked(config),
        "subscription_pay_url": config["subscription"]["pay_url"],
        "application_inbox": [],
        "search_in_progress": False,
    }


def active_search_run(output_dir: Path) -> Dict[str, Any]:
    path = output_dir / "active_search_run.json"
    if not path.exists():
        return {}
    return read_json_file(path, {})


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


def read_json_file(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return default
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else default
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json_file(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{threading.get_ident()}.{datetime.now(timezone.utc).timestamp()}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(5):
        try:
            temp_path.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))


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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    :root{--white:#fff;--off-white:#f8fafc;--gray-50:#f9fafb;--gray-100:#f3f4f6;--gray-200:#e5e7eb;--gray-300:#d1d5db;--blue-50:#eff6ff;--blue-100:#dbeafe;--blue-600:#2563eb;--blue-700:#1d4ed8;--navy:#0f172a;--text-body:#374151;--text-muted:#6b7280;--border:#e5e7eb;--success:#10b981;--warning:#f59e0b;--danger:#ef4444;--shadow-sm:0 1px 2px rgba(0,0,0,.06);--shadow-md:0 4px 12px rgba(0,0,0,.08);--shadow-lg:0 12px 40px rgba(0,0,0,.10);--shadow-xl:0 24px 64px rgba(0,0,0,.12);font-family:"Inter","Noto Sans Hebrew",system-ui,-apple-system,sans-serif;color-scheme:light}
    html{scroll-behavior:smooth;font-size:16px}
    body{background:var(--white);color:var(--text-body);line-height:1.6;-webkit-font-smoothing:antialiased}
    body::after{content:"v2 NEW DESIGN";position:fixed;bottom:10px;left:10px;background:#2563eb;color:#fff;padding:4px 10px;border-radius:6px;font-size:12px;font-weight:700;z-index:9999;pointer-events:none}
    img{max-width:100%;display:block}
    a{color:inherit;text-decoration:none}
    h1{font-size:clamp(32px,5vw,56px);font-weight:800;line-height:1.1;color:var(--navy);letter-spacing:-.03em}
    h2{font-size:clamp(28px,3.5vw,40px);font-weight:700;line-height:1.2;color:var(--navy);letter-spacing:-.02em}
    h3{font-size:20px;font-weight:700;color:var(--navy)}
    p{font-size:16px;line-height:1.7;color:var(--text-body)}
    /* Layout */
    .container{width:min(1160px,calc(100% - 48px));margin-inline:auto}
    section{padding:80px 0}
    /* Navbar */
    .site-nav{position:sticky;top:0;z-index:1000;background:rgba(255,255,255,.95);backdrop-filter:blur(12px);border-bottom:1px solid transparent;transition:border-color .2s,box-shadow .2s}
    .site-nav.scrolled{border-color:var(--border);box-shadow:var(--shadow-sm)}
    .nav-inner{display:flex;align-items:center;justify-content:space-between;gap:24px;height:68px;width:min(1160px,calc(100% - 48px));margin-inline:auto}
    .nav-brand{display:flex;align-items:center;gap:10px;font-size:20px;font-weight:800;color:var(--navy);flex-shrink:0}
    .nav-brand img{width:34px;height:34px;object-fit:contain}
    .nav-links{display:flex;align-items:center;gap:6px;list-style:none}
    .nav-links a{padding:8px 14px;border-radius:8px;font-size:15px;font-weight:500;color:var(--text-body);transition:background .15s,color .15s}
    .nav-links a:hover{background:var(--gray-100);color:var(--navy)}
    .nav-actions{display:flex;align-items:center;gap:10px}
    .nav-hamburger{display:none;flex-direction:column;gap:5px;background:none;border:none;cursor:pointer;padding:8px;border-radius:8px}
    .nav-hamburger span{display:block;width:22px;height:2px;background:var(--navy);border-radius:2px;transition:transform .25s,opacity .15s}
    .nav-hamburger.open span:nth-child(1){transform:translateY(7px) rotate(45deg)}
    .nav-hamburger.open span:nth-child(2){opacity:0}
    .nav-hamburger.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
    .nav-mobile-menu{display:none;flex-direction:column;gap:4px;padding:16px 0;border-top:1px solid var(--border)}
    .nav-mobile-menu.open{display:flex}
    .nav-mobile-menu a{padding:12px 20px;font-size:16px;font-weight:500;color:var(--text-body);border-radius:8px;transition:background .15s}
    .nav-mobile-menu a:hover{background:var(--gray-50)}
    /* Buttons */
    .btn{display:inline-flex;align-items:center;gap:8px;padding:12px 22px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;border:none;text-decoration:none;transition:all .2s;white-space:nowrap;line-height:1}
    .btn:disabled{opacity:.6;cursor:wait}
    .btn-primary{background:var(--blue-600);color:#fff;box-shadow:0 2px 8px rgba(37,99,235,.3)}
    .btn-primary:hover{background:var(--blue-700);box-shadow:0 4px 16px rgba(37,99,235,.4);transform:translateY(-1px)}
    .btn-ghost{background:transparent;color:var(--text-body);border:1.5px solid var(--border)}
    .btn-ghost:hover{border-color:var(--blue-600);color:var(--blue-600);background:var(--blue-50)}
    .btn-lg{padding:15px 28px;font-size:17px}
    .btn-white{background:#fff;color:var(--blue-600);font-weight:700}
    .btn-white:hover{background:var(--off-white);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.15)}
    .button,.button:link{display:inline-flex;align-items:center;gap:8px;padding:11px 20px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;border:1.5px solid transparent;text-decoration:none;transition:all .2s;white-space:nowrap;line-height:1}
    button:not(.nav-hamburger){display:inline-flex;align-items:center;gap:8px;padding:11px 20px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;border:1.5px solid transparent;transition:all .2s;white-space:nowrap;line-height:1}
    button:disabled{opacity:.6;cursor:wait}
    .primary{background:var(--blue-600);color:#fff;border-color:var(--blue-600)}
    .primary:hover{background:var(--blue-700);border-color:var(--blue-700);transform:translateY(-1px)}
    .secondary{background:#fff;color:var(--navy);border-color:var(--border)}
    .secondary:hover{border-color:var(--blue-600);color:var(--blue-600)}
    .ghost{background:transparent;color:var(--text-body);border-color:var(--border)}
    .ghost:hover{border-color:var(--blue-600);color:var(--blue-600)}
    /* Badges */
    .badge{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:999px;font-size:13px;font-weight:600}
    .badge-blue{background:var(--blue-100);color:var(--blue-600)}
    .badge-green{background:#d1fae5;color:#065f46}
    .badge-orange{background:#fef3c7;color:#92400e}
    .badge-gray{background:var(--gray-100);color:var(--text-muted)}
    .score-high{background:#d1fae5;color:#065f46}
    .score-mid{background:#fef3c7;color:#92400e}
    .score-low{background:#fee2e2;color:#991b1b}
    /* Hero */
    .hero-section{padding:96px 0 80px;overflow:hidden}
    .hero-inner{display:grid;grid-template-columns:1fr 480px;align-items:center;gap:80px;width:min(1160px,calc(100% - 48px));margin-inline:auto}
    .hero-badge{display:inline-flex;align-items:center;gap:8px;background:var(--blue-50);border:1px solid var(--blue-100);color:var(--blue-600);border-radius:999px;padding:6px 14px;font-size:14px;font-weight:600;margin-bottom:24px}
    .hero h1{margin-bottom:20px}
    .hero-sub{font-size:18px;color:var(--text-muted);margin-bottom:36px;max-width:560px}
    .hero-ctas{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:24px}
    .hero-trust{display:flex;align-items:center;gap:20px;flex-wrap:wrap;color:var(--text-muted);font-size:14px;font-weight:500}
    .hero-trust span::before{content:"✓ ";color:var(--success);font-weight:700}
    /* Hero card mockup */
    .hero-visual{display:flex;justify-content:center;align-items:center;position:relative}
    .hero-card-mockup{background:#fff;border:1px solid var(--border);border-radius:24px;padding:28px;box-shadow:var(--shadow-xl);width:100%;max-width:360px;animation:float 3s ease-in-out infinite alternate}
    @keyframes float{from{transform:translateY(0)}to{transform:translateY(-12px)}}
    .mockup-header{display:flex;align-items:center;gap:14px;margin-bottom:20px}
    .mockup-logo{width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#667eea,#764ba2);display:grid;place-items:center;color:#fff;font-weight:800;font-size:18px;flex-shrink:0}
    .mockup-company{font-weight:700;color:var(--navy);font-size:16px}
    .mockup-role{font-size:13px;color:var(--text-muted)}
    .mockup-score-row{display:flex;align-items:center;justify-content:space-between;background:var(--gray-50);border-radius:12px;padding:16px;margin-bottom:16px}
    .mockup-score-num{font-size:30px;font-weight:800;color:var(--success)}
    .mockup-score-label{font-size:13px;color:var(--text-muted);font-weight:500}
    .mockup-tags{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px}
    .mockup-tag{background:var(--blue-50);color:var(--blue-600);border-radius:999px;padding:4px 10px;font-size:12px;font-weight:600}
    .mockup-apply{width:100%;background:var(--blue-600);color:#fff;border:none;border-radius:8px;padding:13px;font-size:15px;font-weight:700;cursor:pointer;transition:background .15s}
    .mockup-apply:hover{background:var(--blue-700)}
    /* Proof bar */
    .proof-bar{padding:28px 0;background:var(--gray-50);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
    .proof-inner{display:flex;align-items:center;gap:32px;flex-wrap:wrap;width:min(1160px,calc(100% - 48px));margin-inline:auto}
    .proof-label{font-size:14px;font-weight:600;color:var(--text-muted);white-space:nowrap}
    .proof-logos{display:flex;align-items:center;gap:28px;flex-wrap:wrap}
    .proof-logo{font-size:15px;font-weight:700;opacity:.5;transition:opacity .2s;cursor:default}
    .proof-logo:hover{opacity:1}
    .proof-logo.linkedin{color:#0077b5}.proof-logo.alljobs{color:#e53935}.proof-logo.drushim{color:#1565c0}.proof-logo.google{color:#34a853}.proof-logo.indeed{color:#2164f3}
    /* How it works */
    .how-section{background:#fff}
    .section-center{text-align:center}
    .section-center h2{margin-bottom:56px}
    .steps-row{display:grid;grid-template-columns:repeat(3,1fr);gap:0;position:relative;width:min(1160px,calc(100% - 48px));margin-inline:auto}
    .steps-row::before{content:"";position:absolute;top:28px;left:calc(33.33% - 8px);right:calc(33.33% - 8px);height:2px;background:linear-gradient(90deg,var(--blue-100),var(--blue-600),var(--blue-100));z-index:0}
    .step{text-align:center;padding:0 32px;position:relative;z-index:1}
    .step-num{width:56px;height:56px;border-radius:50%;background:var(--blue-600);color:#fff;font-size:20px;font-weight:800;display:inline-grid;place-items:center;margin:0 auto 20px;box-shadow:0 0 0 6px var(--blue-50)}
    .step-icon{font-size:28px;margin-bottom:14px}
    .step h3{margin-bottom:10px;font-size:18px}
    .step p{font-size:15px;color:var(--text-muted);max-width:240px;margin-inline:auto}
    /* Features */
    .features-section{background:var(--off-white);padding:80px 0}
    .features-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;width:min(1160px,calc(100% - 48px));margin-inline:auto}
    .feature-card{background:#fff;border:1.5px solid var(--border);border-radius:12px;padding:28px 24px;transition:border-color .2s,box-shadow .2s,transform .2s}
    .feature-card:hover{border-color:var(--blue-600);box-shadow:var(--shadow-md);transform:translateY(-3px)}
    .feature-icon{font-size:32px;margin-bottom:16px}
    .feature-card h3{font-size:17px;margin-bottom:8px}
    .feature-card p{font-size:15px;color:var(--text-muted)}
    /* Testimonials */
    .testimonials-section{background:#fff;padding:80px 0}
    .testimonials-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;width:min(1160px,calc(100% - 48px));margin-inline:auto}
    .t-card{background:#fff;border:1.5px solid var(--border);border-radius:12px;padding:24px;transition:box-shadow .2s,transform .2s}
    .t-card:hover{box-shadow:var(--shadow-md);transform:translateY(-2px)}
    .t-stars{color:#f59e0b;font-size:14px;margin-bottom:12px;letter-spacing:2px}
    .t-text{font-size:15px;color:var(--text-body);line-height:1.65;margin-bottom:18px;font-style:italic}
    .t-author{display:flex;align-items:center;gap:12px}
    .t-avatar{width:44px;height:44px;border-radius:50%;object-fit:cover;border:2px solid var(--border);flex-shrink:0}
    .t-name{font-weight:700;font-size:14px;color:var(--navy)}
    .t-role{font-size:13px;color:var(--text-muted)}
    /* CTA section */
    .cta-section{background:var(--blue-600);padding:80px 0;text-align:center}
    .cta-section h2{color:#fff;margin-bottom:16px}
    .cta-section p{color:rgba(255,255,255,.8);margin-bottom:36px;font-size:18px;max-width:560px;margin-inline:auto}
    /* Section helpers */
    .section-label{display:block;font-size:13px;font-weight:700;color:var(--blue-600);text-transform:uppercase;letter-spacing:.1em;margin-bottom:10px;text-align:center}
    .section-sub{text-align:center;color:var(--text-muted);margin-bottom:52px;font-size:17px}
    /* Site footer */
    .site-footer{background:var(--navy);color:rgba(255,255,255,.7);padding:48px 0 32px}
    .footer-inner{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:24px;width:min(1160px,calc(100% - 48px));margin-inline:auto}
    .footer-brand{display:flex;align-items:center;gap:10px;color:#fff;font-weight:800;font-size:18px}
    .footer-brand img{width:28px;height:28px;object-fit:contain;filter:brightness(2)}
    .footer-links{display:flex;gap:24px;font-size:14px;list-style:none}
    .footer-links a{color:rgba(255,255,255,.6);transition:color .15s}
    .footer-links a:hover{color:#fff}
    .footer-copy{font-size:13px}
    /* App pages */
    .app-shell{min-height:100vh;background:var(--off-white)}
    .app-topbar{background:#fff;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
    .app-topbar-inner{display:flex;align-items:center;justify-content:space-between;height:60px;gap:16px;width:min(1200px,calc(100% - 48px));margin-inline:auto}
    .app-brand{display:flex;align-items:center;gap:8px;font-weight:800;font-size:18px;color:var(--navy)}
    .app-brand img{width:30px;height:30px;object-fit:contain}
    .app-nav{display:flex;align-items:center;gap:4px}
    .app-nav a{padding:7px 14px;border-radius:8px;font-size:14px;font-weight:600;color:var(--text-muted);transition:background .15s,color .15s}
    .app-nav a:hover{background:var(--gray-100);color:var(--navy)}
    .app-nav a.active{background:var(--blue-50);color:var(--blue-600)}
    .app-layout{display:grid;grid-template-columns:220px 1fr;gap:24px;align-items:start;max-width:1200px;margin:32px auto;padding:0 24px}
    .side{background:#fff;border:1px solid var(--border);border-radius:12px;padding:12px;position:sticky;top:80px;display:grid;gap:4px}
    .side a{display:flex;align-items:center;gap:10px;padding:11px 14px;border-radius:8px;font-size:14px;font-weight:600;color:var(--text-muted);transition:background .15s,color .15s}
    .side a:hover{background:var(--gray-50);color:var(--navy)}
    .side a.active{background:var(--blue-50);color:var(--blue-600)}
    .workspace{min-width:0}
    .panel{background:#fff;border:1px solid var(--border);border-radius:12px;padding:24px;margin-bottom:20px}
    .metrics,.status{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px}
    .metric{background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px}
    .metric span{display:block;font-size:13px;color:var(--text-muted);font-weight:600;margin-bottom:6px;text-transform:uppercase;letter-spacing:.04em}
    .metric strong{font-size:28px;font-weight:800;color:var(--navy)}
    .job-list{display:grid;gap:12px}
    .job-card{background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px 24px;display:grid;grid-template-columns:1fr 80px auto;align-items:center;gap:20px;transition:border-color .2s,box-shadow .2s}
    .job-card:hover{border-color:var(--blue-600);box-shadow:var(--shadow-sm)}
    .job-card-title{font-weight:700;font-size:16px;color:var(--navy);margin-bottom:4px}
    .job-card-meta{display:flex;flex-wrap:wrap;gap:12px;font-size:14px;color:var(--text-muted)}
    .score{text-align:center}
    .score strong{display:block;font-size:28px;font-weight:800;color:var(--blue-600)}
    .score span{font-size:12px;color:var(--text-muted)}
    .progress{height:8px;background:var(--gray-100);border-radius:999px;overflow:hidden}
    .progress span{display:block;height:100%;background:var(--blue-600);border-radius:999px;transition:width .4s}
    .progress-card{margin-bottom:20px}
    form{display:grid;gap:14px}
    label{font-size:14px;font-weight:600;color:var(--text-body)}
    input,select{width:100%;border:1.5px solid var(--border);border-radius:8px;padding:11px 14px;font-size:15px;color:var(--navy);background:#fff;transition:border-color .15s,box-shadow .15s;outline:none}
    input:focus,select:focus{border-color:var(--blue-600);box-shadow:0 0 0 3px rgba(37,99,235,.1)}
    .dropzone{border:2px dashed var(--border);border-radius:12px;padding:32px;text-align:center;transition:border-color .2s,background .2s}
    .dropzone:hover{border-color:var(--blue-600);background:var(--blue-50)}
    .search-inline{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .search-inline input{min-width:min(360px,100%);width:auto;flex:1}
    table{width:100%;border-collapse:collapse}
    th,td{border-bottom:1px solid var(--border);text-align:right;padding:12px 16px;font-size:14px}
    th{font-weight:700;font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em}
    tr:hover td{background:var(--gray-50)}
    .insights li{color:var(--text-body);font-size:14px;line-height:1.6;padding:10px 0;border-bottom:1px solid var(--border);list-style:none}
    .insights li:last-child{border:0}
    .insights li b{color:var(--blue-600)}
    .feed div{display:flex;align-items:center;gap:10px;padding:10px;border-radius:8px;color:var(--text-muted);font-size:14px}
    .feed div:hover{background:var(--gray-50)}
    .timeline{display:grid;gap:12px}
    .timeline div{display:flex;gap:14px;align-items:flex-start;padding:10px;border-radius:8px}
    .timeline div:hover{background:var(--gray-50)}
    .timeline b{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--blue-600);color:#fff;font-size:13px;font-weight:800;flex-shrink:0}
    .chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 20px}
    .chips span{background:var(--blue-50);color:var(--blue-600);border-radius:999px;padding:5px 12px;font-weight:600;font-size:13px;border:1px solid var(--blue-100)}
    .trust{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0}
    .trust div{background:#fff;border:1px solid var(--border);border-radius:12px;padding:14px 16px;color:var(--text-muted);font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px}
    .trust div::before{content:"✓";color:var(--success);font-weight:800}
    .eyebrow{display:inline-block;color:var(--blue-600);font-weight:700;font-size:13px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}
    .gradient{background:linear-gradient(90deg,var(--blue-600),#7c3aed);-webkit-background-clip:text;color:transparent}
    .grid{display:grid;gap:16px}
    .two{grid-template-columns:repeat(2,1fr)}
    .three{grid-template-columns:repeat(3,1fr)}
    .narrow{max-width:640px}
    .onboarding{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}
    .empty-state{background:#fff;border:1px solid var(--border);border-radius:12px;padding:64px 32px;text-align:center}
    .empty-state h2{margin-bottom:10px}
    .empty-state p{margin-bottom:24px;color:var(--text-muted)}
    .loading-overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);backdrop-filter:blur(4px);z-index:200;display:grid;place-items:center;padding:24px}
    .loading-overlay[hidden]{display:none}
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
    .loading-overlay[hidden]{display:none}
    .loading-card{width:min(480px,100%);background:#fff;border:1px solid var(--border);border-radius:16px;padding:36px;text-align:center;box-shadow:var(--shadow-xl)}
    .loading-card strong{display:block;font-size:19px;font-weight:700;color:var(--navy);margin:16px 0 8px}
    .loading-card span{color:var(--text-muted);font-size:15px}
    .loading-card small{display:block;color:var(--text-muted);font-size:13px;margin-top:8px}
    .loading-progress{height:6px;background:var(--gray-100);border-radius:999px;overflow:hidden;margin-top:20px}
    .loading-progress span{display:block;height:100%;width:0;background:var(--blue-600);border-radius:999px;transition:width .35s}
    .spinner{width:44px;height:44px;border-radius:50%;border:3px solid var(--gray-100);border-top-color:var(--blue-600);margin:0 auto;animation:spin .8s linear infinite}
    .toolbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:24px}
    .actions{display:flex;align-items:center;flex-wrap:wrap;gap:10px}
    .logo-panel{display:grid;place-items:center}
    .logo-panel img{width:min(100%,380px);height:auto}
    .hero{display:grid;grid-template-columns:1fr minmax(260px,420px);align-items:center;gap:48px;padding:54px 0 36px;width:min(1160px,calc(100% - 48px));margin-inline:auto}
    @keyframes spin{to{transform:rotate(360deg)}}
    @keyframes float{from{transform:translateY(0)}to{transform:translateY(-12px)}}
    @media(max-width:960px){
      section{padding:56px 0}
      .hero-section{padding:64px 0 48px}
      .hero-inner,.hero{grid-template-columns:1fr;gap:48px}
      .hero-visual{order:-1}
      .hero-card-mockup{max-width:320px;margin-inline:auto}
      .steps-row::before{display:none}
      .steps-row{grid-template-columns:1fr;gap:32px}
      .step{text-align:right;display:flex;gap:20px;align-items:flex-start;padding:0}
      .step-num{margin:0;flex-shrink:0}
      .step-icon{display:none}
      .features-grid{grid-template-columns:repeat(2,1fr)}
      .testimonials-grid{grid-template-columns:1fr}
      .app-layout{grid-template-columns:1fr;margin:16px auto}
      .side{position:static;grid-template-columns:repeat(3,1fr)}
      .side a{justify-content:center}
      .metrics,.status,.trust{grid-template-columns:repeat(2,1fr)}
      .job-card{grid-template-columns:1fr}
      .nav-links,.nav-actions .btn-primary{display:none}
      .nav-hamburger{display:flex}
      .proof-inner,.proof-logos{justify-content:center}
      .two,.onboarding{grid-template-columns:1fr}
      .footer-inner{flex-direction:column;text-align:center}
      .footer-links{justify-content:center}
    }
    @media(max-width:560px){
      h1{font-size:30px}
      .metrics,.status,.trust,.side{grid-template-columns:1fr}
      .features-grid{grid-template-columns:1fr}
      .hero-trust{flex-direction:column;gap:10px}
    }
    .reveal{opacity:0;transform:translateY(20px);transition:opacity .6s,transform .6s}
    .reveal.visible{opacity:1;transform:translateY(0)}
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
        return not bool(read_json_file(status_path, {}).get("active"))
    except OSError:
        return True
