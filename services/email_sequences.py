"""
Email Sequences  —  Stage 4 onboarding
=======================================
Five contextual emails, each sent once per user, triggered by how many days
have elapsed since account creation and by what the user has (or hasn't) done.

Sequence map
------------
  welcome   →  immediately on signup (called inline, not by cron)
  day_1     →  24 h after signup — "Your 3 quickest wins"
  day_3     →  3 d after signup  — "How do you compare?"
  day_7     →  7 d after signup  — "Your rankings haven't been checked"
  day_14    →  14 d after signup — Usage summary + upgrade nudge (free only)

Each email is skipped if:
  • user has already received it  (EmailSequenceLog row exists)
  • user has unsubscribed         (email_seq_unsubscribed == True)
  • the contextual condition says it doesn't make sense
    (e.g. day_14 is skipped for paying users)
"""

from __future__ import annotations

import os
import logging



from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from rq_app import queue
from rq import Retry

log = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
PRIMARY   = "#00A4C6"
ACCENT    = "#0DD3B6"
YEAR      = datetime.now().year


# ── Low-level email sender (re-uses existing email_service.py) ─────────────────




# ── Shared HTML primitives ────────────────────────────────────────────────────

# def _logo_html() -> str:
#     return f"""
#     <div style="text-align:center;margin-bottom:8px;">
#       <span style="display:inline-flex;align-items:center;gap:8px;">
#         <span style="display:inline-block;width:28px;height:28px;background:{PRIMARY};
#               border-radius:6px;text-align:center;line-height:28px;color:white;
#               font-weight:900;font-size:14px;">A
#         </span>
#         <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
#             <rect width="28" height="28" rx="6" fill={PRIMARY} />
#             <path d="M6 20 L11 12 L16 16 L21 8" stroke="white" strokeWidth="4"
#             strokeLinecap="round" strokeLinejoin="round" />
#             <circle cx="21" cy="8" r="3" fill={ACCENT} />
#         </svg>
#         <img src="{FRONTEND_URL}/logo2.svg" alt="OutAudits" />
#         <span style="font-weight:900;margin-left:8px;font-size:16px;color:#111;letter-spacing:-0.3px;">
#           OutAudits
#         </span>
#       </span>
#     </div>"""
def _logo_html() -> str:
    return f"""
    <div style="text-align:center;margin-bottom:8px;">
      <span style="display:inline-flex;align-items:center;gap:8px;">
        <img src="{FRONTEND_URL}/logo2.svg" alt="OutAudits" style="width:28px;height:auto;" />
        <span style="font-weight:900;margin-left:8px;font-size:16px;color:#111;letter-spacing:-0.3px;">
           OutAudits
        </span>
      </span>
    </div>"""


def _button(label: str, url: str, accent: bool = False) -> str:
    bg = ACCENT if accent else PRIMARY
    fg = "#111111" if accent else "#ffffff"
    return f"""
    <p style="text-align:center;margin:28px 0 0;">
      <a href="{url}" style="display:inline-block;padding:14px 32px;
         background:{bg};color:{fg};text-decoration:none;
         border-radius:6px;font-weight:700;font-size:14px;">
        {label}
      </a>
    </p>"""


def _score_color(score: Optional[int]) -> str:
    if score is None:
        return "#9CA3AF"
    return ACCENT if score >= 80 else "#F59E0B" if score >= 50 else "#EF4444"


def _wrap(body: str, preview_text: str = "") -> str:
    """Wrap body HTML in the standard email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <title>OutAudits</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings>
  <o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background:#F4F6FA;font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Roboto,sans-serif;-webkit-font-smoothing:antialiased;">
  {f'<div style="display:none;max-height:0;overflow:hidden;color:#F4F6FA;">{preview_text}</div>' if preview_text else ""}
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F4F6FA;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width:600px;">

          <!-- Logo header -->
          <tr>
            <td style="padding:0 0 16px;">
              {_logo_html()}
            </td>
          </tr>

          <!-- Card -->
          <tr>
            <td style="background:#ffffff;border:1px solid #E5E7EB;
                       border-radius:8px;padding:40px 40px 36px;
                       color:#374151;font-size:15px;line-height:1.65;">
              {body}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 0 0;text-align:center;
                       font-size:12px;color:#9CA3AF;line-height:1.6;">
              © {YEAR} OutAudits &nbsp;·&nbsp;
              <a href="{FRONTEND_URL}/unsubscribe" style="color:#9CA3AF;">Unsubscribe</a>
              &nbsp;·&nbsp;
              <a href="{FRONTEND_URL}/dashboard" style="color:#9CA3AF;">Go to dashboard</a>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _h1(text: str) -> str:
    return f'<h1 style="margin:0 0 16px;font-size:24px;font-weight:900;color:#111;line-height:1.2;">{text}</h1>'


def _p(text: str, muted: bool = False) -> str:
    color = "#6B7280" if muted else "#374151"
    return f'<p style="margin:0 0 16px;color:{color};font-size:15px;line-height:1.65;">{text}</p>'


def _divider() -> str:
    return '<hr style="border:none;border-top:1px solid #F3F4F6;margin:28px 0;">'


def _issue_row(label: str, value: str, color: str = PRIMARY) -> str:
    return f"""
    <tr>
      <td style="padding:10px 0;border-bottom:1px solid #F3F4F6;
                 font-size:14px;color:#374151;">{label}</td>
      <td style="padding:10px 0;border-bottom:1px solid #F3F4F6;
                 font-size:14px;font-weight:700;color:{color};
                 text-align:right;">{value}</td>
    </tr>"""


# ── Sequence log helpers ───────────────────────────────────────────────────────

def _already_sent(slug: str, user_id: int, db: Session) -> bool:
    from db.models import EmailSequenceLog
    return db.query(EmailSequenceLog).filter(
        EmailSequenceLog.user_id == user_id,
        EmailSequenceLog.sequence_slug == slug,
    ).first() is not None


def _mark_sent(slug: str, user_id: int, subject: str, db: Session) -> None:
    from db.models import EmailSequenceLog
    log_row = EmailSequenceLog(
        user_id=user_id,
        sequence_slug=slug,
        sent_at=datetime.utcnow(),
        subject=subject,
    )
    db.add(log_row)
    db.commit()


def _send_and_log(
    slug: str,
    user_id: int,
    email: str,
    subject: str,
    html: str,
    text: str,
    db: Session,
) -> bool:
    from services.email_service import send_email
    """Send the email and record it. Returns True if sent."""
    try:
        queue.enqueue(send_email, email, subject, html, text, retry = Retry(max=3, interval=[10, 30, 60]) )
        # send_email(email, subject, html, text)
        _mark_sent(slug, user_id, subject, db)
        print("Sent sequence email slug=%s user_id=%s", slug, user_id)
        log.info("Sent sequence email slug=%s user_id=%s", slug, user_id)
        return True
    except Exception as exc:
        log.error("Failed to send slug=%s user_id=%s: %s", slug, user_id, exc)
        return False


# ── Data helpers ───────────────────────────────────────────────────────────────

def _domain(url: str) -> str:
    try:
        return urlparse(url if "://" in url else f"https://{url}").netloc.replace("www.", "")
    except Exception:
        return url


def _get_latest_audit(user_id: int, db: Session):
    from db.models import Audit
    from sqlalchemy import desc
    return (
        db.query(Audit)
        .filter(Audit.user_id == user_id, Audit.status == "completed")
        .order_by(desc(Audit.created_at))
        .first()
    )


def _get_latest_comparison(user_id: int, db: Session):
    from db.models import Comparison
    from sqlalchemy import desc
    return (
        db.query(Comparison)
        .filter(Comparison.user_id == user_id, Comparison.status == "completed")
        .order_by(desc(Comparison.created_at))
        .first()
    )


def _get_rank_tracking_count(user_id: int, db: Session) -> int:
    from db.models import RankTracking
    return db.query(RankTracking).filter(RankTracking.user_id == user_id).count()


def _extract_top_issues(audit_results: dict, max_issues: int = 3) -> list[dict]:
    """
    Pull the top N actionable issues from a Lighthouse audit results blob.
    Returns a list of {label, impact} dicts.
    """
    issues = []

    categories = audit_results.get("categories", {})
    for cat_key, cat in categories.items():
        score = cat.get("score", 1)
        if score is None or score > 0.7:   # only include poor categories
            continue
        label = cat.get("title", cat_key.replace("-", " ").title())
        pct   = int((score or 0) * 100)
        issues.append({
            "label":  f"{label} needs work",
            "impact": f"Score: {pct}/100",
            "color":  "#EF4444" if pct < 50 else "#F59E0B",
        })

    # Also pull individual audits that failed
    audits_section = audit_results.get("audits", {})
    for audit_key, audit_item in audits_section.items():
        if len(issues) >= max_issues * 2:
            break
        if audit_item.get("score") not in (0, None):
            continue
        title       = audit_item.get("title", "")
        description = audit_item.get("description", "")
        if not title:
            continue
        issues.append({
            "label":  title,
            "impact": description[:80] + "…" if len(description) > 80 else description,
            "color":  "#EF4444",
        })

    # Deduplicate labels and cap
    seen, unique = set(), []
    for i in issues:
        if i["label"] not in seen:
            seen.add(i["label"])
            unique.append(i)
        if len(unique) >= max_issues:
            break

    return unique


# ══════════════════════════════════════════════════════════════════════════════
# SEQUENCE TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

# ── WELCOME (slug: "welcome") ─────────────────────────────────────────────────

def send_welcome_email(
    user_id: int,
    email: str,
    name: Optional[str],
    audit_score: Optional[int],
    audit_url: Optional[str],
    domain: Optional[str],
    db: Session,
) -> bool:
    """
    Sent immediately on signup (called from the auth register endpoint,
    not from the cron).  Personalised to whether they came from an
    anonymous audit or signed up cold.
    """
    slug    = "welcome"
    display = name or email.split("@")[0]

    if audit_score is not None and domain:
        # ── Variant A: they came via anonymous audit ──────────────
        score_color = _score_color(audit_score)
        subject = f"Your {domain} audit is saved — score: {audit_score}/100"

        body = f"""
        {_h1(f"Welcome, {display} — your report is saved 🎉")}
        {_p(f"You just ran a full Lighthouse audit + 50-page crawl on <strong>{domain}</strong>.")}

        <div style="text-align:center;margin:24px 0;">
          <span style="display:inline-block;font-size:56px;font-weight:900;
                       line-height:1;color:{score_color};">{audit_score}</span>
          <span style="display:block;font-size:13px;color:#9CA3AF;margin-top:4px;">overall SEO score</span>
        </div>

        {_p("Your free account is set up and the report is waiting in your dashboard. Here's what to do next:")}

        <table width="100%" cellpadding="0" cellspacing="0"
               style="margin:0 0 20px;border:1px solid #F3F4F6;border-radius:6px;overflow:hidden;">
          {_issue_row("View your full report", "→ Dashboard", PRIMARY)}
          {_issue_row("Fix top issues", "Start with the red items", "#EF4444")}
          {_issue_row("Track your keywords", "Set up daily rank checks", ACCENT)}
        </table>

        {_button("Go to my dashboard", f"{FRONTEND_URL}/dashboard")}
        {_divider()}
        {_p("Reply to this email any time — we read every response.", muted=True)}
        """

        text = f"""Welcome, {display}!

Your {domain} audit is saved — score {audit_score}/100.

View your dashboard: {FRONTEND_URL}/dashboard

Next steps:
1. Review your full report
2. Fix the red-flagged issues first
3. Set up daily rank tracking

Reply to this email any time — we read every response.
"""

    else:
        # ── Variant B: cold signup ────────────────────────────────
        subject = f"Welcome to OutAudits, {display} — start your free audit"

        body = f"""
        {_h1(f"Welcome, {display} 👋")}
        {_p("Your free OutAudits account is ready. Here's what you can do right now — no credit card, no setup:")}

        <table width="100%" cellpadding="0" cellspacing="0"
               style="margin:0 0 20px;border:1px solid #F3F4F6;border-radius:6px;overflow:hidden;">
          {_issue_row("⚡ Lighthouse audit", "Performance · SEO · Accessibility", PRIMARY)}
          {_issue_row("🗺️ 50-page deep crawl", "Missing H1s · broken links · thin content", PRIMARY)}
          {_issue_row("📊 Competitor comparison", "See where you win and where you lag", PRIMARY)}
          {_issue_row("🎯 Rank tracking", "Daily Google & Bing position checks", PRIMARY)}
        </table>

        {_p("You get <strong>10 free credits</strong> every month — enough to run your first audits today.")}

        {_button("Run my first free audit →", f"{FRONTEND_URL}/audit", accent=True)}
        {_divider()}
        {_p("Reply to this email any time — we read every response.", muted=True)}
        """

        text = f"""Welcome to OutAudits, {display}!

Your account is ready. Here's what you can do:

• ⚡ Lighthouse audit (performance, SEO, accessibility)
• 🗺️ 50-page deep crawl (missing H1s, broken links, thin content)
• 📊 Competitor comparison
• 🎯 Daily rank tracking

You get 10 free credits every month.

Run your first audit: {FRONTEND_URL}/audit

Reply to this email any time — we read every response.
"""

    return _send_and_log(slug, user_id, email, subject, _wrap(body, f"Your OutAudits account is ready"), text, db)


# ── DAY 1 (slug: "day_1") — "Your 3 quickest wins" ───────────────────────────

def _send_day1(user_id: int, email: str, name: Optional[str], db: Session) -> bool:
    slug    = "day_1"
    display = name or email.split("@")[0]
    audit   = _get_latest_audit(user_id, db)

    if audit and audit.results:
        domain    = _domain(audit.url)
        score     = audit.overall_score or 0
        issues    = _extract_top_issues(audit.results)
        score_col = _score_color(score)
        subject   = f"Your 3 quickest wins for {domain}"

        issue_rows = "".join(
            _issue_row(i["label"], i["impact"], i["color"]) for i in issues
        ) or _issue_row("No critical issues found", "Great work! 🎉", ACCENT)

        body = f"""
        {_h1(f"Your 3 quickest wins for {domain}")}
        {_p(f"Yesterday you ran an audit and scored <strong style='color:{score_col}'>{score}/100</strong>. Here are the fastest improvements you can make today:")}

        <table width="100%" cellpadding="0" cellspacing="0"
               style="margin:0 0 24px;border:1px solid #F3F4F6;border-radius:6px;overflow:hidden;">
          {issue_rows}
        </table>

        {_p("Each of these is a quick fix — most can be done in under 30 minutes. Fix them and re-run the audit to watch your score climb.")}

        {_button("View full report →", f"{FRONTEND_URL}/audit/{audit.job_id}")}
        {_divider()}
        {_p(f"Haven't set up rank tracking yet? See how {domain} ranks for your target keywords — daily, for free.", muted=True)}
        <p style="margin:8px 0 0;font-size:13px;">
          <a href="{FRONTEND_URL}/rank-tracking" style="color:{PRIMARY};font-weight:600;">
            Set up rank tracking →
          </a>
        </p>
        """

        text = f"""Your 3 quickest wins for {domain}

Your audit score: {score}/100

Top issues to fix:
{chr(10).join(f"• {i['label']}: {i['impact']}" for i in issues) or "No critical issues — great work!"}

View full report: {FRONTEND_URL}/audit/{audit.job_id}

Set up rank tracking: {FRONTEND_URL}/rank-tracking
"""
    else:
        # No audit yet — nudge them to run one
        subject = "One quick action to improve your SEO today"

        body = f"""
        {_h1(f"Hey {display} — one quick action for today")}
        {_p("You signed up yesterday but haven't run your first audit yet. It takes 90 seconds and shows you every SEO problem on your site — instantly.")}
        {_button("Run my free audit →", f"{FRONTEND_URL}/audit", accent=True)}
        {_divider()}
        {_p("No configuration needed. Just paste your URL and we'll handle the rest.", muted=True)}
        """

        text = f"""Hey {display} — one quick action for today

You signed up yesterday but haven't run your first audit yet.
It takes 90 seconds.

Run your free audit: {FRONTEND_URL}/audit
"""

    return _send_and_log(slug, user_id, email, subject, _wrap(body, subject), text, db)


# ── DAY 3 (slug: "day_3") — "How do you compare?" ───────────────────────────

def _send_day3(user_id: int, email: str, name: Optional[str], db: Session) -> bool:
    slug       = "day_3"
    
    display    = name or email.split("@")[0]
    audit      = _get_latest_audit(user_id, db)
    comparison = _get_latest_comparison(user_id, db)
    
    if comparison and comparison.score_gap is not None:
        # They already ran a comparison — show the result
        gap       = comparison.score_gap
        winning   = gap > 0
        gap_label = f"+{gap}" if winning else str(gap)
        gap_color = ACCENT if winning else "#EF4444"
        dom_target = _domain(comparison.target_url)
        dom_comp   = _domain(comparison.best_competitor_url or "competitor")
        subject    = f"You vs {dom_comp}: score gap is {gap_label}"

        status_html = (
            "You're ahead — keep the lead"
            if winning
            else "Close the gap with targeted fixes"
        )

        status_text = "you're ahead" if winning else "you're behind"
        body = f"""
        {_h1(f"You {'beat' if winning else 'trail'} {dom_comp} by {abs(gap)} points")}
        {_p(f"Your competitor comparison for <strong>{dom_target}</strong> is in.")}

        <div style="display:flex;gap:16px;margin:24px 0;text-align:center;">
          <div style="flex:1;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:6px;padding:20px;">
            <div style="font-size:40px;font-weight:900;color:{_score_color(comparison.target_score)};">
              {comparison.target_score or '—'}
            </div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:4px;">You</div>
          </div>
          <div style="display:flex;align-items:center;font-size:13px;color:#9CA3AF;">vs</div>
          <div style="flex:1;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:6px;padding:20px;">
            <div style="font-size:40px;font-weight:900;color:{_score_color(comparison.best_competitor_score)};">
              {comparison.best_competitor_score or '—'}
            </div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:4px;">{dom_comp}</div>
          </div>
        </div>

        <div style="text-align:center;margin-bottom:24px;">
          <span style="font-size:20px;font-weight:900;color:{gap_color};">
            {gap_label} points
          </span>
          <span style="font-size:13px;color:#9CA3AF;display:block;margin-top:4px;">
            {status_html}
          </span>
        </div>

        {_button("View full comparison →", f"{FRONTEND_URL}/compare/{comparison.job_id}")}
        {_divider()}
        {_p("Want to add another competitor? You can compare against up to 3 at once.", muted=True)}
        <p style="margin:8px 0 0;font-size:13px;">
          <a href="{FRONTEND_URL}/compare" style="color:{PRIMARY};font-weight:600;">
            Run another comparison →
          </a>
        </p>
        """
        
        text = f"""You vs {dom_comp}: score gap is {gap_label}

Your score: {comparison.target_score or '—'}
{dom_comp}: {comparison.best_competitor_score or '—'}
Gap: {gap_label} points ({status_text})

View full comparison: {FRONTEND_URL}/compare/{comparison.job_id}
"""

    elif audit:
        # They audited but haven't compared yet
        domain  = _domain(audit.url)
        subject = f"How does {domain} stack up against competitors?"

        body = f"""
        {_h1(f"How does {domain} stack up?")}
        {_p(f"You know your own score ({audit.overall_score or '—'}/100). But do you know how that compares to your top competitors?")}
        {_p("Our competitor comparison tool runs a side-by-side audit of you and up to 3 competitors and shows you exactly where you win and where they beat you.")}

        <table width="100%" cellpadding="0" cellspacing="0"
               style="margin:0 0 24px;border:1px solid #F3F4F6;border-radius:6px;overflow:hidden;">
          {_issue_row("Performance gap", "How much faster are they?", "#F59E0B")}
          {_issue_row("SEO gap", "Who has better on-page signals?", PRIMARY)}
          {_issue_row("Accessibility gap", "WCAG compliance comparison", ACCENT)}
        </table>

        {_button("Compare a competitor →", f"{FRONTEND_URL}/compare", accent=True)}
        {_divider()}
        {_p("Takes 2 minutes. No extra credits — it's included in your plan.", muted=True)}
        """

        text = f"""How does {domain} stack up against competitors?

You scored {audit.overall_score or '—'}/100. But how does that compare to your competitors?

Run a competitor comparison: {FRONTEND_URL}/compare

It shows you performance gap, SEO gap, and accessibility gap side-by-side.
Takes 2 minutes and uses 2 credits.
"""

    else:
        # No activity at all
        subject = f"Hey {display} — what are your competitors scoring?"

        body = f"""
        {_h1("What are your competitors scoring?")}
        {_p(f"Hi {display} — most websites have hidden SEO issues that competitors are already fixing.")}
        {_p("In 90 seconds you can see exactly how you compare: paste your URL and up to 3 competitors, and we'll run a full side-by-side analysis.")}
        {_button("Start free comparison →", f"{FRONTEND_URL}/compare", accent=True)}
        {_divider()}
        {_p("Uses 2 credits. You have 10 free credits on your plan.", muted=True)}
        """

        text = f"""Hey {display} — what are your competitors scoring?

In 90 seconds you can see exactly how you compare to competitors.

Start free comparison: {FRONTEND_URL}/compare
Uses 2 credits. You have 10 free credits on your plan.
"""

    return _send_and_log(slug, user_id, email, subject, _wrap(body, subject), text, db)


# ── DAY 7 (slug: "day_7") — rankings check-in ───────────────────────────────

def _send_day7(user_id: int, email: str, name: Optional[str], db: Session) -> bool:
    slug             = "day_7"
    display          = name or email.split("@")[0]
    tracking_count   = _get_rank_tracking_count(user_id, db)
    audit            = _get_latest_audit(user_id, db)
    domain           = _domain(audit.url) if audit else "your site"

    if tracking_count > 0:
        # They set up tracking — give a week-in recap nudge
        subject = f"One week in — how are your {domain} rankings moving?"

        body = f"""
        {_h1(f"One week of tracking {domain}")}
        {_p(f"You've been tracking rankings for a week now. Here's what to look for in your dashboard:")}

        <table width="100%" cellpadding="0" cellspacing="0"
               style="margin:0 0 24px;border:1px solid #F3F4F6;border-radius:6px;overflow:hidden;">
          {_issue_row("📈 Keywords climbing", "These are your quick wins — double down", ACCENT)}
          {_issue_row("📉 Keywords dropping", "Check for content changes or crawl issues", "#EF4444")}
          {_issue_row("🔴 Not in top 100", "May need fresh content or link building", "#F59E0B")}
        </table>

        {_p("If you see big drops, cross-reference with your last crawl — a missing H1 or broken internal link is often the culprit.")}

        {_button("View ranking dashboard →", f"{FRONTEND_URL}/rank-tracking")}
        {_divider()}
        {_p("Pro tip: set up email alerts for drops of 10+ positions so you catch issues the day they happen.", muted=True)}
        """

        text = f"""One week of tracking {domain}

You've been tracking rankings for a week.

Check your dashboard for:
• Keywords climbing (double down on these)
• Keywords dropping (investigate content/crawl issues)
• Keywords not in top 100 (need content or links)

View dashboard: {FRONTEND_URL}/rank-tracking

Pro tip: enable email alerts for drops of 10+ positions.
"""

    else:
        # No tracking yet
        subject = f"{domain}'s rankings haven't been checked — set up takes 30 seconds"

        body = f"""
        {_h1(f"{domain}'s rankings haven't been checked yet")}
        {_p(f"Hi {display} — it's been a week since you signed up, but you haven't set up rank tracking yet.")}
        {_p("Rank tracking is the fastest way to know when Google moves your pages — up or down — so you can act the same day instead of finding out weeks later.")}

        <table width="100%" cellpadding="0" cellspacing="0"
               style="margin:0 0 24px;border:1px solid #F3F4F6;border-radius:6px;overflow:hidden;">
          {_issue_row("Daily checks", "Google + Bing positions, every 24 h", PRIMARY)}
          {_issue_row("Email alerts", "Notified instantly on drops of 10+ positions", "#EF4444")}
          {_issue_row("Historical charts", "See the trend, not just today's snapshot", ACCENT)}
          {_issue_row("Up to 50 keywords", "Track your whole content strategy", PRIMARY)}
        </table>

        {_button("Set up rank tracking →", f"{FRONTEND_URL}/rank-tracking", accent=True)}
        {_divider()}
        {_p("Takes 30 seconds. Uses 1 credit per campaign run.", muted=True)}
        """

        text = f"""{domain}'s rankings haven't been checked yet

Hi {display} — it's been a week since you signed up.

Rank tracking shows you when Google moves your pages — up or down — daily.

Features:
• Daily checks on Google + Bing
• Email alerts on drops of 10+ positions
• Historical trend charts
• Up to 50 keywords per campaign

Set up rank tracking: {FRONTEND_URL}/rank-tracking
Takes 30 seconds. Uses 1 credit per campaign.
"""

    return _send_and_log(slug, user_id, email, subject, _wrap(body, subject), text, db)


# ── DAY 14 (slug: "day_14") — usage summary + upgrade nudge ─────────────────

def _send_day14(user_id: int, email: str, name: Optional[str], plan: str, credits_remaining: int, credits_limit: int, db: Session) -> bool:
    slug    = "day_14"
    display = name or email.split("@")[0]

    # Skip for paying users — they already converted
    if plan != "free":
        log.info("Skipping day_14 for paying user user_id=%s plan=%s", user_id, plan)
        return False

    credits_used = credits_limit - credits_remaining
    audit        = _get_latest_audit(user_id, db)
    domain       = _domain(audit.url) if audit else "your site"
    subject      = f"Your OutAudits summary — {credits_used} of {credits_limit} credits used"

    # Usage bar HTML (approximate pixel widths)
    used_pct = min(int((credits_used / max(credits_limit, 1)) * 100), 100)

    body = f"""
    {_h1(f"Two weeks in — here's your usage summary")}
    {_p(f"Hi {display}, you've been on OutAudits for two weeks. Here's a quick look at what you've done:")}

    <table width="100%" cellpadding="0" cellspacing="0"
           style="margin:0 0 24px;border:1px solid #F3F4F6;border-radius:6px;overflow:hidden;">
      {_issue_row("Credits used", f"{credits_used} / {credits_limit}", PRIMARY if credits_used < credits_limit else "#EF4444")}
      {_issue_row("Credits remaining", str(credits_remaining), ACCENT if credits_remaining > 3 else "#EF4444")}
      {_issue_row("Current plan", plan.title(), "#9CA3AF")}
    </table>

    <!-- Usage bar -->
    <div style="margin:0 0 24px;">
      <div style="background:#F3F4F6;border-radius:4px;height:8px;overflow:hidden;">
        <div style="background:{'#EF4444' if used_pct > 80 else PRIMARY};
                    width:{used_pct}%;height:8px;border-radius:4px;
                    transition:width .5s;"></div>
      </div>
      <p style="font-size:12px;color:#9CA3AF;margin:6px 0 0;">
        {used_pct}% of monthly credits used
      </p>
    </div>

    {_p("On the <strong>Pro plan</strong> you get <strong>100 credits every month</strong> — 10× your current limit — plus:")}

    <table width="100%" cellpadding="0" cellspacing="0"
           style="margin:0 0 24px;border:1px solid #F3F4F6;border-radius:6px;overflow:hidden;">
      {_issue_row("100 credits / month", "vs 10 on free", ACCENT)}
      {_issue_row("Unlimited crawl pages", "Up from 50", ACCENT)}
      {_issue_row("White-label PDF reports", "Your logo, your branding", ACCENT)}
      {_issue_row("Email alerts", "Rank drops, audit issues", ACCENT)}
      {_issue_row("Priority support", "Response within 4 hours", ACCENT)}
    </table>

    {_button("Upgrade to Pro — $29/month →", f"{FRONTEND_URL}/dashboard/billing", accent=True)}
    {_divider()}
    {_p("Questions? Just reply to this email.", muted=True)}
    """

    text = f"""Two weeks in — your OutAudits summary

Hi {display},

Credits used: {credits_used} / {credits_limit}
Credits remaining: {credits_remaining}
Current plan: {plan.title()}

Upgrade to Pro for 100 credits/month (10× more), unlimited crawls,
white-label PDF reports, and email alerts — $29/month.

Upgrade: {FRONTEND_URL}/dashboard/billing

Questions? Reply to this email.
"""

    return _send_and_log(slug, user_id, email, subject, _wrap(body, subject), text, db)


# ══════════════════════════════════════════════════════════════════════════════
# CRON PROCESSOR  —  called once per hour by the scheduler
# ══════════════════════════════════════════════════════════════════════════════

def process_sequences(db: Session) -> dict:
    """
    Iterate over all eligible users and send whichever sequence emails are due.
    Designed to be idempotent — safe to call multiple times; the EmailSequenceLog
    unique-per-slug constraint prevents double-sends.

    Returns a summary dict for logging.
    """
    from db.models import User
    print("processing emails")

    now = datetime.utcnow()
    summary = {"processed": 0, "sent": 0, "skipped": 0, "errors": 0}

    # test_sent = _send_day1(1, "alexngaikama913@gmail.com", "Ngaikam Alex", db)
    
    users: list[User] = (
        db.query(User)
        .filter(
            User.is_active == True,
            User.email_seq_unsubscribed == False,
        )
        .all()
    )

    for user in users:
        print(user.email)
        summary["processed"] += 1
        age_days = (now - user.created_at).days

        # Each check is: is it time? → is it already sent? → send it.
        try:
            # ── day_1: send after 1 day ──────────────────────────
            if age_days >= 1 and not _already_sent("day_1", user.id, db):
                sent = _send_day1(user.id, user.email, user.full_name, db)
                summary["sent" if sent else "skipped"] += 1

            # ── day_3: send after 3 days ─────────────────────────
            if age_days >= 3 and not _already_sent("day_3", user.id, db):
                sent = _send_day3(user.id, user.email, user.full_name, db)
                summary["sent" if sent else "skipped"] += 1

            # ── day_7: send after 7 days ─────────────────────────
            if age_days >= 7 and not _already_sent("day_7", user.id, db):
                sent = _send_day7(user.id, user.email, user.full_name, db)
                summary["sent" if sent else "skipped"] += 1

            # ── day_14: send after 14 days, free users only ───────
            if age_days >= 14 and not _already_sent("day_14", user.id, db):
                plan_credits = {"free": 10, "pro": 100, "agency": 1000}
                limit        = plan_credits.get(user.plan, 10)
                sent = _send_day14(
                    user.id, user.email, user.full_name,
                    user.plan, user.credits_remaining, limit, db,
                )
                summary["sent" if sent else "skipped"] += 1

        except Exception as exc:
            log.error("Error processing sequences for user_id=%s: %s", user.id, exc)
            summary["errors"] += 1

    log.info("Email sequence run complete: %s", summary)
    return summary
