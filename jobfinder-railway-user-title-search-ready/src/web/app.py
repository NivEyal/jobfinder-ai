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
