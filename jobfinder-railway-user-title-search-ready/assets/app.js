/* ═══════════════════════════════════════════════════
   JobFinder — Premium Visual Effects & Interactions
   ═══════════════════════════════════════════════════ */

// ── Page progress bar ──
const pageProgress = document.getElementById("page-progress");
function showPageProgress(pct) {
  if (!pageProgress) return;
  pageProgress.style.width = pct + "%";
  pageProgress.style.opacity = pct >= 100 ? "0" : "1";
}
window.addEventListener("load", () => {
  showPageProgress(100);
  setTimeout(() => { if (pageProgress) pageProgress.style.opacity = "0"; }, 600);
});
showPageProgress(40);
setTimeout(() => showPageProgress(80), 200);

// ── Header scroll class ──
const header = document.querySelector("header");
window.addEventListener("scroll", () => {
  if (header) header.classList.toggle("scrolled", window.scrollY > 24);
}, { passive: true });

// ── Theme toggle ──
const THEME_KEY = "jf-theme";
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  const btn = document.getElementById("theme-toggle");
  if (btn) btn.textContent = t === "dark" ? "☀️" : "🌙";
}
(function initTheme() {
  const saved = localStorage.getItem(THEME_KEY) || "dark";
  applyTheme(saved);
  const btn = document.getElementById("theme-toggle");
  if (btn) btn.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  });
})();

// ── Mobile hamburger ──
const hamburger = document.querySelector(".hamburger");
const nav       = document.querySelector("nav");
if (hamburger && nav) {
  hamburger.addEventListener("click", () => {
    hamburger.classList.toggle("open");
    nav.classList.toggle("open");
  });
}

// ── Mouse spotlight / glow cursor ──
(function initSpotlight() {
  const el = document.getElementById("spotlight");
  if (!el) return;
  const isMobile = window.matchMedia("(pointer: coarse)").matches;
  if (isMobile) { el.style.display = "none"; return; }
  let mx = -9999, my = -9999;
  document.addEventListener("mousemove", (e) => {
    mx = e.clientX; my = e.clientY;
    el.style.left = mx + "px";
    el.style.top  = my + "px";
  }, { passive: true });
})();

// ── Particle canvas ──
(function initParticles() {
  const canvas = document.getElementById("particle-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let W, H, particles;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize, { passive: true });

  const COLORS = ["rgba(0,212,255,", "rgba(124,58,237,", "rgba(245,158,11,"];

  function makeParticle() {
    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    return {
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.8 + 0.4,
      vx: (Math.random() - .5) * .35,
      vy: (Math.random() - .5) * .35,
      a: Math.random(),
      va: (Math.random() * .008 + .003) * (Math.random() < .5 ? 1 : -1),
      color,
    };
  }

  const COUNT = Math.min(120, Math.floor((W * H) / 12000));
  particles = Array.from({ length: COUNT }, makeParticle);

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy; p.a += p.va;
      if (p.a <= 0 || p.a >= 1) p.va *= -1;
      if (p.x < -10) p.x = W + 10;
      if (p.x > W + 10) p.x = -10;
      if (p.y < -10) p.y = H + 10;
      if (p.y > H + 10) p.y = -10;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color + Math.max(0, Math.min(1, p.a)) + ")";
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }
  draw();
})();

// ── Typewriter effect ──
(function initTypewriter() {
  const el = document.querySelector(".typewriter");
  if (!el) return;
  const texts = el.dataset.texts ? JSON.parse(el.dataset.texts)
    : ["מוצא. מתאים. מגיש.", "מאיץ את החיפוש שלך.", "AI לשוק העבודה הישראלי."];
  let ti = 0, ci = 0, deleting = false;
  const base = el.dataset.base || "";

  function tick() {
    const target = texts[ti];
    if (!deleting) {
      el.textContent = base + target.slice(0, ci + 1);
      ci++;
      if (ci === target.length) { deleting = true; setTimeout(tick, 1800); return; }
    } else {
      el.textContent = base + target.slice(0, ci - 1);
      ci--;
      if (ci === 0) { deleting = false; ti = (ti + 1) % texts.length; }
    }
    setTimeout(tick, deleting ? 45 : 80);
  }
  tick();
})();

// ── Scroll reveal ──
(function initReveal() {
  const els = document.querySelectorAll(".reveal");
  if (!els.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e, i) => {
      if (e.isIntersecting) {
        setTimeout(() => e.target.classList.add("visible"), i * 80);
        io.unobserve(e.target);
      }
    });
  }, { threshold: .1 });
  els.forEach(el => io.observe(el));
})();

// ── Toast notifications ──
let _toastEl = null;
function getToastContainer() {
  if (_toastEl) return _toastEl;
  _toastEl = document.getElementById("toast-container");
  if (!_toastEl) {
    _toastEl = document.createElement("div");
    _toastEl.id = "toast-container";
    document.body.appendChild(_toastEl);
  }
  return _toastEl;
}

function showToast(message, type = "info", duration = 4000) {
  const icons = { success: "✅", error: "❌", info: "ℹ️", gold: "🏆" };
  const container = getToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || "ℹ️"}</span><span>${message}</span>`;
  container.appendChild(toast);

  const remove = () => {
    toast.classList.add("removing");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
  };
  setTimeout(remove, duration);
  toast.addEventListener("click", remove);
  return toast;
}

// ── Confetti ──
function launchConfetti() {
  const canvas = document.createElement("canvas");
  canvas.id = "confetti-canvas";
  canvas.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:8888;";
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;

  const COLORS = ["#00d4ff","#7c3aed","#f59e0b","#10b981","#f43f5e","#a78bfa"];
  const pieces = Array.from({ length: 120 }, () => ({
    x:  Math.random() * canvas.width,
    y:  Math.random() * canvas.height - canvas.height,
    w:  Math.random() * 10 + 5,
    h:  Math.random() * 6 + 3,
    rot: Math.random() * 360,
    drot: (Math.random() - .5) * 8,
    vy: Math.random() * 4 + 2,
    vx: (Math.random() - .5) * 2,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    a: 1,
  }));

  let frame;
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = false;
    pieces.forEach(p => {
      p.y   += p.vy;
      p.x   += p.vx;
      p.rot += p.drot;
      if (p.y > canvas.height * .75) p.a -= .018;
      if (p.a > 0) {
        alive = true;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot * Math.PI / 180);
        ctx.globalAlpha = Math.max(0, p.a);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
        ctx.restore();
      }
    });
    if (alive) { frame = requestAnimationFrame(draw); }
    else { canvas.remove(); }
  }
  draw();
}

// ── Number counter animation ──
function animateCounter(el, from, to, duration = 1200) {
  const start = performance.now();
  function step(now) {
    const pct = Math.min(1, (now - start) / duration);
    const val = Math.round(from + (to - from) * easeOut(pct));
    el.textContent = val;
    if (pct < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

// Animate all metric counters on load
(function initCounters() {
  document.querySelectorAll(".metric strong").forEach(el => {
    const val = parseInt(el.textContent, 10);
    if (!isNaN(val) && val > 0) {
      animateCounter(el, 0, val, 1000 + Math.random() * 400);
    }
  });
})();

// ── Progress polling (original functionality) ──
let progressTimer = null;

function setProgress(data) {
  const count   = document.getElementById("loading-count");
  const bar     = document.getElementById("loading-progress-bar");
  const message = document.getElementById("loading-message");
  const found   = data.jobs_found_so_far || 0;
  const target  = data.target_jobs || 100;
  const percent = data.percent || Math.min(100, Math.round((found / Math.max(target,1)) * 100));

  if (count)   count.textContent   = `נמצאו ${found} מתוך ${target} משרות`;
  if (bar)     bar.style.width     = `${percent}%`;
  if (message && data.message) message.textContent = data.message;
}

async function pollProgress() {
  try {
    const r = await fetch("/api/progress", { cache: "no-store" });
    if (r.ok) setProgress(await r.json());
  } catch (_) {}
}

async function cancelSearch() {
  const btn = document.getElementById("cancel-search-button");
  if (btn) { btn.disabled = true; btn.textContent = "עוצר..."; }
  try {
    const r = await fetch("/api/cancel-search", { method: "POST" });
    if (r.ok) setProgress(await r.json());
  } catch (_) {}
}

function showLoading(form) {
  const overlay = document.getElementById("loading-overlay");
  if (overlay) overlay.hidden = false;
  setProgress({ jobs_found_so_far: 0, target_jobs: 100, percent: 1, message: "מתחיל חיפוש..." });
  if (progressTimer) clearInterval(progressTimer);
  progressTimer = setInterval(pollProgress, 1000);
  form.querySelectorAll("button").forEach(btn => {
    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.textContent = "טוען...";
  });
}

// ── Form submission with loading ──
document.querySelectorAll("form").forEach(form => {
  form.addEventListener("submit", async (event) => {
    const action = form.getAttribute("action") || "";
    const isAsync = action === "/api/run-ui" || action === "/api/apply-all";
    showLoading(form);
    if (!isAsync) return;
    event.preventDefault();
    try {
      const r = await fetch(action, { method: "POST", body: new FormData(form), redirect: "manual" });
      await pollProgress();
      // Confetti on apply-all
      if (action === "/api/apply-all") {
        launchConfetti();
        showToast("הגשות נשלחו בהצלחה! 🎉", "success");
      }
      window.location.href = r.headers.get("location") || "/dashboard";
    } catch (err) {
      const msg = document.getElementById("loading-message");
      if (msg) msg.textContent = "אירעה שגיאה. נסה שוב בעוד רגע.";
      if (progressTimer) clearInterval(progressTimer);
      showToast("אירעה שגיאה. נסה שוב.", "error");
    }
  });
});

// ── Cancel button ──
const cancelButton = document.getElementById("cancel-search-button");
if (cancelButton) cancelButton.addEventListener("click", cancelSearch);

// ── Job card hover: animate score ──
document.querySelectorAll(".job-card").forEach(card => {
  card.addEventListener("mouseenter", () => {
    const score = card.querySelector(".score strong");
    if (score && !score.dataset.animated) {
      score.dataset.animated = "1";
      const val = parseInt(score.textContent, 10);
      if (!isNaN(val)) animateCounter(score, 0, val, 600);
    }
  });
});

// ── Auto-add reveal class to main sections ──
document.querySelectorAll("main > section, .panel, .metric, .job-card").forEach((el, i) => {
  if (!el.classList.contains("reveal")) {
    el.classList.add("reveal");
    el.style.transitionDelay = (i * 50) + "ms";
  }
});

// Trigger reveals already in viewport on load
setTimeout(() => {
  document.querySelectorAll(".reveal").forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight) el.classList.add("visible");
  });
}, 100);

// ── Floating bubbles generation (hero) ──
(function initBubbles() {
  const container = document.querySelector(".bubbles");
  if (!container || container.children.length > 0) return;
  const roles = ["Backend Dev","Frontend","Full-Stack","Data Science","DevOps","QA","Product","UX Design","Mobile","Cloud"];
  roles.forEach((r, i) => {
    const b = document.createElement("span");
    b.className = "bubble";
    b.textContent = r;
    b.style.animationDelay = (i * 60) + "ms";
    container.appendChild(b);
  });
})();

// ── Expose utilities globally ──
window.JF = { showToast, launchConfetti, animateCounter, showLoading };
