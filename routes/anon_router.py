"""
Anonymous Audit Routes  —  no auth required
Runs a real Lighthouse audit + 50-page crawl, stores under a session token.
"""

from __future__ import annotations
import asyncio
from rq_app import queue
from rq import Retry

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/anon", tags=["anonymous"])

# How long the result lives before we bin it
EXPIRY_HOURS = 24


# ── Schema ─────────────────────────────────────────────────────────────────────

class StartAnonAuditRequest(BaseModel):
    url: str


class ClaimRequest(BaseModel):
    session_token: str
    user_id: int


# ── Background task ─────────────────────────────────────────────────────────────

def run_anon_audit(session_token: str) -> None:
    from db.database import SessionLocal
    from db.models import AnonymousAudit
    from auditor import WebsiteAuditor
    from apps.crawler import crawl_website

    db: Session = SessionLocal()
    try:
        row: AnonymousAudit = (
            db.query(AnonymousAudit)
            .filter(AnonymousAudit.session_token == session_token)
            .first()
        )
        if not row:
            return

        row.status = "running"
        row.stage = "audit"
        row.stage_label = "Running Lighthouse audit…"
        row.progress = 5
        db.commit()

        # ── STAGE 1: Lighthouse audit ──────────────────────────────
        try:
            auditor = WebsiteAuditor(row.url)
            audit_results = asyncio.run(auditor.run_full_audit())

            row.audit_score = audit_results.get("overall_score")
            row.audit_results = audit_results
            row.progress = 40
            row.stage_label = "Audit complete — starting crawl…"
            db.commit()
        except Exception as e:
            # Audit failure is non-fatal — still do the crawl
            row.audit_results = {"error": str(e)}
            row.progress = 40
            db.commit()

        # ── STAGE 2: 50-page crawl ─────────────────────────────────
        row.stage = "crawl"
        row.stage_label = "Crawling up to 50 pages…"
        db.commit()

        async def crawl_progress(pct: float, _status: str = '') -> None:
            # Map crawl 0-100 → overall 40-95
            row.progress = int(40 + pct * 0.55)
            row.stage_label = f"Crawling pages… ({row.progress}%)"
            db.commit()

        try:
            crawl_results = asyncio.run(crawl_website(
                url=row.url,
                max_pages=50,
                progress_callback=crawl_progress,
            ))
            row.crawl_results = crawl_results
            row.pages_crawled = crawl_results.get("summary", {}).get("total_pages_crawled", 0)
        except Exception as e:
            row.crawl_results = {"error": str(e)}

        # ── Done ───────────────────────────────────────────────────
        row.status = "completed"
        row.stage = "done"
        row.stage_label = "Analysis complete"
        row.progress = 100
        db.commit()

    except Exception as exc:
        try:
            row.status = "failed"
            row.error = str(exc)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── START ───────────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_anon_audit(
    req: StartAnonAuditRequest,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """
    Called from the public homepage — no authentication required.
    Returns a session_token the browser stores in localStorage.
    """
    from db.database import SessionLocal
    from db.models import AnonymousAudit

    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    token = secrets.token_hex(32)  # 64-char hex string

    db: Session = SessionLocal()
    try:
        row = AnonymousAudit(
            session_token=token,
            url=url,
            status="pending",
            progress=0,
            expires_at=datetime.utcnow() + timedelta(hours=EXPIRY_HOURS),
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    # background_tasks.add_task(run_anon_audit, token)
    queue.enqueue(run_anon_audit, token, retry = Retry(max=3, interval=[10, 30, 60]) )

    return {"session_token": token, "status": "pending"}


# ── POLL STATUS ─────────────────────────────────────────────────────────────────

@router.get("/status/{token}")
async def get_anon_status(token: str):
    """Lightweight poll endpoint — returns only progress data, not full results."""
    from db.database import SessionLocal
    from db.models import AnonymousAudit

    db: Session = SessionLocal()
    try:
        row: Optional[AnonymousAudit] = (
            db.query(AnonymousAudit)
            .filter(AnonymousAudit.session_token == token)
            .first()
        )
        if not row:
            raise HTTPException(404, "Session not found")

        return {
            "status":      row.status,
            "progress":    row.progress,
            "stage":       row.stage,
            "stage_label": row.stage_label,
        }
    finally:
        db.close()


# ── RESULTS ─────────────────────────────────────────────────────────────────────

@router.get("/results/{token}")
async def get_anon_results(token: str):
    """Returns full audit + crawl results once status == 'completed'."""
    from db.database import SessionLocal
    from db.models import AnonymousAudit

    db: Session = SessionLocal()
    try:
        row: Optional[AnonymousAudit] = (
            db.query(AnonymousAudit)
            .filter(AnonymousAudit.session_token == token)
            .first()
        )
        if not row:
            raise HTTPException(404, "Session not found")

        if row.status != "completed":
            raise HTTPException(400, f"Results not ready (status: {row.status})")

        if row.expires_at and row.expires_at < datetime.utcnow():
            raise HTTPException(410, "Results have expired")
        print(row.crawl_results)
        return {
            "url":           row.url,
            "audit_score":   row.audit_score,
            "audit_results": row.audit_results,
            "crawl_results": row.crawl_results,
            "pages_crawled": row.pages_crawled,
            "created_at":    row.created_at,
            "expires_at":    row.expires_at,
            "claimed":       row.claimed_by_user_id is not None,
        }
    finally:
        db.close()


# ── CLAIM on signup ─────────────────────────────────────────────────────────────

@router.post("/claim")
async def claim_anon_audit(req: ClaimRequest):
    """
    Called immediately after the user creates an account.
    Transfers the anonymous results to their permanent account.
    user_id comes from the auth middleware in the wrapping route.
    """
    from db.database import SessionLocal
    from db.models import AnonymousAudit, Audit, Crawl
    import uuid

    db: Session = SessionLocal()
    try:
        row: Optional[AnonymousAudit] = (
            db.query(AnonymousAudit)
            .filter(
                AnonymousAudit.session_token == req.session_token,
                AnonymousAudit.claimed_by_user_id == None,  # noqa: E711
            )
            .first()
        )
        if not row:
            return {"message": "Nothing to claim"}

        # Create a proper Audit record so it shows in the dashboard
        if row.audit_results:
            audit = Audit(
                job_id=str(uuid.uuid4()),
                user_id=req.user_id,
                url=row.url,
                status="completed",
                progress=100,
                overall_score=row.audit_score,
                results=row.audit_results,
                completed_at=datetime.utcnow(),
            )
            db.add(audit)

        # Create a proper Crawl record
        if row.crawl_results:
            crawl = Crawl(
                job_id=str(uuid.uuid4()),
                user_id=req.user_id,
                url=row.url,
                max_pages=50,
                status="completed",
                progress=100,
                pages_crawled=row.pages_crawled,
                results=row.crawl_results,
                completed_at=datetime.utcnow(),
            )
            db.add(crawl)

        print("claimed")    

        row.claimed_by_user_id = req.user_id
        row.claimed_at = datetime.utcnow()
        db.commit()

        return {"message": "Claimed", "audit_created": row.audit_results is not None}
    finally:
        db.close()


# ── CLEANUP (call from a daily cron) ───────────────────────────────────────────

@router.delete("/expire")
async def expire_old_sessions():
    """Delete anonymous audits older than EXPIRY_HOURS."""
    from db.database import SessionLocal
    from db.models import AnonymousAudit

    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow()
        deleted = (
            db.query(AnonymousAudit)
            .filter(
                AnonymousAudit.expires_at < cutoff,
                AnonymousAudit.claimed_by_user_id == None,  # noqa: E711
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return {"deleted": deleted}
    finally:
        db.close()