"""
ai_visibility_routes.py — API routes for the AI Visibility audit module.

Mirrors the existing /audit route pattern: create a job row, enqueue a
Celery task that runs the async engine in ai_visibility.py, poll for
status, return results. Wire this router into your FastAPI app with:

    from ai_visibility_routes import router as ai_visibility_router
    app.include_router(ai_visibility_router, prefix="/api/ai-visibility", tags=["ai-visibility"])

NOTE ON IMPORTS: this file assumes the following already exist in your
project and adjusts import paths accordingly — update the `# ADAPT`
lines to match your actual module names:
    - get_db()            -> your SQLAlchemy session dependency
    - get_current_user()  -> your auth dependency returning a User
    - celery_app          -> your configured Celery() instance
    - models.User, models.AiVisibilityAudit
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

# ADAPT: import your actual dependencies / celery app / models module
from sqlalchemy import func, desc
from typing import List
from datetime import datetime, timedelta

from db.database import get_db
from db.models import User, AiVisibilityAudit
from db.auth import get_current_user


from rq_app import queue
from rq import Retry

from tasks import run_ai_visibility_task, run_ai_visibility_layer2_task

router = APIRouter(prefix="/api/ai-visibility", tags=["ai-visibility"])


# ─────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────
class Layer2Request(BaseModel):
    brand_queries: list
    perplexity_key: str | None = None
    brave_key: str | None = None

class AiVisibilityAuditRequest(BaseModel):
    url: HttpUrl
    client_name: str | None = None
    layer2: bool = False  # opt-in live citation check (Pro/Agency, costs credits)


class AiVisibilityAuditResponse(BaseModel):
    job_id: str
    status: str


# ─────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────

@router.post("/audit", response_model=AiVisibilityAuditResponse)
def create_ai_visibility_audit(
    payload: AiVisibilityAuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ADAPT: plug into your existing credit-check logic, e.g.:
    # if current_user.credits_remaining <= 0:
    #     raise HTTPException(402, "No credits remaining")

    if payload.layer2:
        # ADAPT: gate behind plan check, e.g.
        # if current_user.plan == "free":
        #     raise HTTPException(403, "Layer 2 live citation check requires Pro or Agency")
        pass

    job_id = str(uuid.uuid4())
    audit = AiVisibilityAudit(
        job_id=job_id,
        user_id=current_user.id,
        url=str(payload.url),
        client_name=payload.client_name,
        status="pending",
        layer2_enabled=payload.layer2,
    )
    db.add(audit)
    db.commit()

    queue.enqueue(run_ai_visibility_task, job_id, str(payload.url),current_user.id, retry = Retry(max=3, interval=[10, 30, 60]) )

    return AiVisibilityAuditResponse(job_id=job_id, status="pending")


@router.get("/audit/{job_id}")
def get_ai_visibility_audit(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    audit = (
        db.query(AiVisibilityAudit)
        .filter(
            AiVisibilityAudit.job_id == job_id,
            AiVisibilityAudit.user_id == current_user.id,
        )
        .first()
    )
    if not audit:
        raise HTTPException(404, "Audit not found")

    return {
        "job_id": audit.job_id,
        "url": audit.url,
        "client_name": "audit.client_name",
        "status": audit.status,
        "progress": audit.progress,
        "overall_score": audit.overall_score,
        "sub_scores": {
            "entity_clarity": audit.entity_score,
            "eeat": audit.eeat_score,
            "content_structure": audit.structure_score,
            "crawlability": audit.crawlability_score,
        },
        "layer2_enabled": audit.layer2_enabled,
        "layer2_completed": audit.layer2_complete,
        "results": audit.results,
        "error": audit.error,
        "created_at": audit.created_at,
        "completed_at": audit.completed_at,
    }

@router.post("/{job_id}/layer2")
def start_layer2(job_id: str, req: Layer2Request, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(AiVisibilityAudit).filter(AiVisibilityAudit.job_id == job_id, AiVisibilityAudit.user_id == current_user.id).first()
    if not row:
        raise HTTPException(404, "Job not found")
    # Enqueue Layer-2 job (runs live citations)
    queue.enqueue(
        run_ai_visibility_layer2_task,
        job_id,
        req.brand_queries,
        req.perplexity_key,
        req.brave_key,
        retry=Retry(max=3, interval=[10,30,60]),
    )
    row.layer2_enabled = True
    row.stage_label = "Layer-2 queued"
    db.commit()
    return {"message": "Layer-2 citation check queued"}

@router.get("/history")
def list_ai_visibility_audits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
):
    audits = (
        db.query(AiVisibilityAudit)
        .filter(AiVisibilityAudit.user_id == current_user.id)
        .order_by(AiVisibilityAudit.created_at.desc())
        .limit(limit)
        .all()
    )
    print(len(audits))
    return [
        {
            "job_id": a.job_id,
            "url": a.url,
            "status": a.status,
            "overall_score": a.overall_score,
            "created_at": a.created_at,
        }
        for a in audits
    ]

@router.get("/kpis")
def ai_visibility_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    KPIs for the current user's AI Visibility audits.
    Returns counts, averages, monthly buckets (12 months), top domains.
    """
    
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_30 = now - timedelta(days=30)
    last_12_months = now.replace(day=1) - timedelta(days=365)

    # Base query
    base_q = db.query(AiVisibilityAudit).filter(AiVisibilityAudit.user_id == current_user.id)

    total = base_q.count()
    completed = base_q.filter(AiVisibilityAudit.status == "completed").count()
    audits_this_month = base_q.filter(AiVisibilityAudit.created_at >= month_start).count()
    audits_last_30 = base_q.filter(AiVisibilityAudit.created_at >= last_30).count()

    # Average overall score (only completed rows with non-null score)
    avg_score = db.query(func.avg(AiVisibilityAudit.overall_score)).filter(
        AiVisibilityAudit.user_id == current_user.id,
        AiVisibilityAudit.overall_score != None
    ).scalar()
    avg_score = round(float(avg_score), 1) if avg_score is not None else None

    # Median (simple approach: fetch ordered values and compute median in Python)
    scores = [
        r[0] for r in db.query(AiVisibilityAudit.overall_score)
                    .filter(AiVisibilityAudit.user_id == current_user.id, AiVisibilityAudit.overall_score != None)
                    .order_by(AiVisibilityAudit.overall_score)
                    .all()
    ]
    median = None
    if scores:
        n = len(scores)
        if n % 2 == 1:
            median = float(scores[n//2])
        else:
            median = float((scores[n//2 - 1] + scores[n//2]) / 2)

    # Percent layer2 enabled
    layer2_count = base_q.filter(AiVisibilityAudit.layer2_enabled == True).count()
    pct_layer2 = round((layer2_count / total) * 100, 1) if total else 0.0

    # Percent cited by Perplexity / Brave (only of completed audits)
    perp_count = base_q.filter(AiVisibilityAudit.perplexity_cited == True).count()
    brave_count = base_q.filter(AiVisibilityAudit.brave_cited == True).count()
    pct_perp = round((perp_count / completed) * 100, 1) if completed else 0.0
    pct_brave = round((brave_count / completed) * 100, 1) if completed else 0.0

    # Monthly buckets (last 12 months) — attempt DB-side grouping, fallback to Python
    monthly = []
    try:
        # Postgres: date_trunc month aggregation
        rows = db.query(
            func.date_trunc('month', AiVisibilityAudit.created_at).label('month'),
            func.count(AiVisibilityAudit.id),
            func.avg(AiVisibilityAudit.overall_score)
        ).filter(AiVisibilityAudit.user_id == current_user.id,
                 AiVisibilityAudit.created_at >= last_12_months
        ).group_by('month').order_by('month').all()

        for m, cnt, avg in rows:
            monthly.append({"month": m.strftime("%Y-%m"), "count": int(cnt), "avg_score": round(float(avg), 1) if avg is not None else None})
    except Exception:
        # Fallback: fetch rows and bucket in Python
        from collections import defaultdict
        buckets = defaultdict(list)
        rows = base_q.filter(AiVisibilityAudit.created_at >= last_12_months).all()
        for r in rows:
            key = r.created_at.strftime("%Y-%m")
            buckets[key].append(r.overall_score)
        for m in sorted(buckets.keys()):
            vals = [v for v in buckets[m] if v is not None]
            monthly.append({"month": m, "count": len(buckets[m]), "avg_score": round(sum(vals)/len(vals),1) if vals else None})

    # top domains
    top = (
        db.query(AiVisibilityAudit.domain, func.count(AiVisibilityAudit.id).label("cnt"), func.avg(AiVisibilityAudit.overall_score).label("avg"))
        .filter(AiVisibilityAudit.user_id == current_user.id)
        .group_by(AiVisibilityAudit.domain)
        .order_by(desc("cnt"))
        .limit(5)
        .all()
    )
    top_domains = [{"domain": d, "count": int(c), "avg_score": round(float(a),1) if a is not None else None} for d, c, a in top]

    return {
        "total_audits": total,
        "completed_audits": completed,
        "audits_this_month": audits_this_month,
        "audits_last_30_days": audits_last_30,
        "avg_overall_score": avg_score,
        "median_overall_score": median,
        "pct_layer2_enabled": pct_layer2,
        "pct_perplexity_cited": pct_perp,
        "pct_brave_cited": pct_brave,
        "monthly": monthly,
        "top_domains": top_domains,
    }

# ─────────────────────────────────────────────────────────────────────────
# Celery task
# ─────────────────────────────────────────────────────────────────────────

# @celery_app.task(name="ai_visibility.run_audit")
# def run_ai_visibility_audit_task(job_id: str) -> None:
#     """Celery entrypoint. Runs the async Layer 1 engine synchronously
#     inside the worker, then (if requested) the Layer 2 live check."""
#     from database import SessionLocal  # ADAPT: your session factory

#     db = SessionLocal()
#     try:
#         audit = db.query(models.AiVisibilityAudit).filter_by(job_id=job_id).first()
#         if not audit:
#             return

#         audit.status = "running"
#         audit.progress = 10
#         db.commit()

#         results = asyncio.run(run_ai_visibility_audit(audit.url))

#         if results.get("error"):
#             audit.status = "failed"
#             audit.error = results["error"]
#             db.commit()
#             return

#         audit.progress = 80

#         # Layer 2 — optional, only if requested. Implement as a separate
#         # module (e.g. ai_visibility_layer2.py) calling Perplexity/Brave
#         # APIs with 3-5 brand queries and checking for domain citations.
#         if audit.layer2_enabled:
#             try:
#                 from ai_visibility_layer2 import run_layer2_citation_check  # ADAPT: build this next
#                 layer2_results = run_layer2_citation_check(audit.url, audit.client_name)
#                 results["layer2"] = layer2_results
#                 results["layer2_run"] = True
#                 audit.cited_by_perplexity = layer2_results.get("perplexity", {}).get("cited")
#                 audit.cited_by_brave = layer2_results.get("brave", {}).get("cited")
#                 audit.layer2_completed = True
#             except ImportError:
#                 results["layer2_run"] = False
#                 results["layer2_note"] = "Layer 2 module not yet implemented."

#         audit.overall_score = results["overall_score"]
#         audit.entity_clarity_score = results["sub_scores"]["entity_clarity"]
#         audit.eeat_score = results["sub_scores"]["eeat"]
#         audit.content_structure_score = results["sub_scores"]["content_structure"]
#         audit.crawlability_score = results["sub_scores"]["crawlability"]
#         audit.results = results
#         audit.status = "completed"
#         audit.progress = 100
#         audit.completed_at = datetime.utcnow()
#         db.commit()

#         # ADAPT: deduct credit, log Activity row, etc. — mirror your
#         # existing run_audit_task pattern here.

#     except Exception as exc:  # noqa: BLE001
#         audit = db.query(models.AiVisibilityAudit).filter_by(job_id=job_id).first()
#         if audit:
#             audit.status = "failed"
#             audit.error = str(exc)
#             db.commit()
#     finally:
#         db.close()