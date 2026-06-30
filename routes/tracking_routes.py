from __future__ import annotations

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta
import base64,os

from sqlalchemy import desc, and_

# Database and models
from db.database import get_db, init_db
from db.models import RankTracking, RankHistory, TrackedKeyword,User, KeywordHistory, ActivityType

# Authentication
from db.auth import (
    get_current_user, get_current_user_optional, check_and_consume_credits,
    authenticate_user, create_access_token, create_refresh_token, get_user_activity_history, log_activity, mark_notification_read, update_activity_status,
    verify_google_token, verify_token, get_password_hash, get_activity_stats, create_notification,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Schemas
from db.schemas import (
    RankTrackingResponse, RankTrackingRequest, RankTrackingListItem, RankTrackingStatus, CreateTrackingRequest, CreateTrackingResponse
)



from tasks import  run_rank_tracking_task, calculate_next_check, check_for_alerts, run_tracking_task, _next_check_time



import logging

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rank-tracking", tags=["rank-tracking"])

# ──────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────────────────────

def _keyword_ids_for_campaign(job_id: str, user_id: int, db: Session):
    """Return the set of TrackedKeyword IDs belonging to a campaign, or None."""
    if not job_id:
        return None
    c = db.query(RankTracking).filter(
        RankTracking.job_id == job_id,
        RankTracking.user_id == user_id,
    ).first()
    if not c:
        return set()
    return {k.id for k in c.keywords_rel}

@router.post("", response_model=CreateTrackingResponse)
async def create_rank_tracking(
    req: CreateTrackingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not req.keywords:
        raise HTTPException(400, "At least one keyword required")
    if len(req.keywords) > 100:
        raise HTTPException(400, "Maximum 100 keywords per campaign")
 
    if not check_and_consume_credits(current_user, db, credits_needed=3):
        raise HTTPException(402, f"Insufficient credits ({current_user.credits_remaining} left)")
 
    job_id = str(uuid.uuid4())
 
    campaign = RankTracking(
        job_id=job_id,
        user_id=current_user.id,
        domain=req.domain,
        name=req.name or req.domain,
        engines=req.engines,
        country=req.country if req.country else None,
        frequency=req.frequency,
        is_scheduled=req.is_scheduled,
        status="pending",
        progress=0,
        next_check=_next_check_time(req.frequency) if req.is_scheduled else None,
    )
    db.add(campaign)
    db.flush()  # get campaign.id
 
    for kw_in in req.keywords:
        # re-use existing keyword row if same user+keyword+domain+engine+country
        existing = (
            db.query(TrackedKeyword)
            .filter(
                TrackedKeyword.user_id == current_user.id,
                TrackedKeyword.keyword == kw_in.keyword.strip().lower(),
                TrackedKeyword.domain == req.domain,
                TrackedKeyword.engine == req.engines[0],
                TrackedKeyword.country == req.country,
            )
            .first()
        )
        if existing:
            kw_obj = existing
        else:
            kw_obj = TrackedKeyword(
                user_id=current_user.id,
                keyword=kw_in.keyword.strip().lower(),
                domain=req.domain,
                engine=req.engines[0],
                country=req.country,
                search_volume=kw_in.search_volume,
                difficulty=kw_in.difficulty,
                group_name=kw_in.group_name,
                tags=kw_in.tags or [],
            )
            db.add(kw_obj)
            db.flush()
 
        campaign.keywords_rel.append(kw_obj)
 
    db.commit()
    log_activity(
        db,
        user_id=current_user.id,
        activity_type=ActivityType.RANK_TRACKING,
        activity_id=job_id,
        target=req.domain,
        status="pending"
    )
    
    create_notification(
    db=db,
    user_id=current_user.id,
    type="tracking",
    title="Kewyord tracking started",
    message=f"Your Rank Tracking Capmpaign for {req.domain} has been queued (job {job_id[:4]}).",
    metadata={"job_id": job_id, "url": str(req.domain)}
    )

    background_tasks.add_task(run_tracking_task, job_id, current_user.id)
    
    return CreateTrackingResponse(
        job_id=job_id,
        status="pending",
        message=f"Tracking started for {len(req.keywords)} keywords on {req.domain}",
    )

@router.get("/trackings")
async def list_rank_trackings(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's rank tracking jobs"""
    
    query = db.query(RankTracking).filter(RankTracking.user_id == current_user.id)
    total = query.count()
    
    trackings = query.order_by(desc(RankTracking.created_at))\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    print(trackings)
    
    return {
        'trackings': [{
            'job_id': t.job_id,
            'domain': t.domain,
            'keywords': [ kw.keyword for kw in t.keywords_rel],
            'status': t.status,
            'is_scheduled': t.is_scheduled,
            'frequency': t.frequency,
            'next_check': t.next_check,
            'created_at': t.created_at,
            'last_checked': t.last_checked
        } for t in trackings],
        'total': total,
        'page': page,
        'page_size': page_size
    }

@router.get("")
async def list_campaigns(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(RankTracking)
        .filter(RankTracking.user_id == current_user.id)
        .order_by(desc(RankTracking.created_at))
    )
    total = q.count()
    campaigns = q.offset((page - 1) * page_size).limit(page_size).all()
 
    def _enrich(c: RankTracking) -> dict:
        kws = c.keywords_rel
        positions = [k.current_position for k in kws if k.current_position]
        print(len(positions))
        avg_pos   = round(sum(positions) / len(positions), 1) if positions else None
        top10     = sum(1 for p in positions if p <= 10)
        top3      = sum(1 for p in positions if p <= 3)
        return {
            "job_id":        c.job_id,
            "name":          c.name,
            "domain":        c.domain,
            "status":        c.status,
            "progress":      c.progress,
            "engines":       c.engines,
            "frequency":     c.frequency,
            "is_scheduled":  c.is_scheduled,
            "keyword_count": len(kws),
            "avg_position":  avg_pos,
            "top10_count":   top10,
            "top3_count":    top3,
            "last_checked":  c.last_checked,
            "next_check":    c.next_check,
            "created_at":    c.created_at,
        }
 
    return {
        "campaigns": [_enrich(c) for c in campaigns],
        "total": total,
    }


@router.get("/kpis")
async def get_kpis(
    domain: Optional[str] = None,
    job_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all KPI data needed for the stat cards.
    Pass job_id to scope to a single campaign.
    """
    q = db.query(TrackedKeyword).filter(
        TrackedKeyword.user_id == current_user.id,
        TrackedKeyword.is_active == True,
    )
    if job_id:
        ids = _keyword_ids_for_campaign(job_id, current_user.id, db)
        if not ids:
            q = q.filter(False)
        else:
            q = q.filter(TrackedKeyword.id.in_(ids))
    elif domain:
        q = q.filter(TrackedKeyword.domain == domain)
 
    keywords: List[TrackedKeyword] = q.all()
 
    total = len(keywords)
    domains = len({k.domain for k in keywords})
 
    top3   = sum(1 for k in keywords if k.current_position and k.current_position <= 3)
    top10  = sum(1 for k in keywords if k.current_position and k.current_position <= 10)
    top100 = sum(1 for k in keywords if k.current_position and k.current_position <= 100)
 
    movers = [k for k in keywords if k.position_change is not None]
    gainer = max(movers, key=lambda k: k.position_change or 0, default=None)
    loser  = min(movers, key=lambda k: k.position_change or 0, default=None)
 
    def kw_snapshot(k: Optional[TrackedKeyword]):
        if not k:
            return None
        return {
            "keyword": k.keyword,
            "domain": k.domain,
            "change": k.position_change,
            "current": k.current_position,
            "previous": k.previous_position,
        }
    print("total kw:", total)
 
    return {
        "total_keywords": total,
        "total_domains": domains,
        "top3": top3,
        "top10": top10,
        "top100": top100,
        "not_ranking": total - top100,
        "biggest_gainer": kw_snapshot(gainer),
        "biggest_loser":  kw_snapshot(loser),
    }
 
 
# ── Keywords table endpoint ────────────────────────────────────────────────────
 
@router.get("/keywords")
async def list_keywords(
    domain: Optional[str] = None,
    job_id: Optional[str] = None,
    engine: Optional[str] = None,
    group_name: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = "position_change",   # position_change | current_position | keyword
    order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Paginated keyword list with filtering + sorting.
    Returns every column needed by the keyword table.
    Pass job_id to scope a single campaign.
    """
    q = db.query(TrackedKeyword).filter(
        TrackedKeyword.user_id == current_user.id,
        TrackedKeyword.is_active == True,
    )

    if job_id:
        ids = _keyword_ids_for_campaign(job_id, current_user.id, db)
        if not ids:
            q = q.filter(False)
        else:
            q = q.filter(TrackedKeyword.id.in_(ids))
 
    if domain:
        q = q.filter(TrackedKeyword.domain == domain)
    if engine:
        q = q.filter(TrackedKeyword.engine == engine)
    if group_name:
        q = q.filter(TrackedKeyword.group_name == group_name)
    if tag:
        q = q.filter(TrackedKeyword.tags.contains([tag]))
 
    sort_col = {
        "position_change":   TrackedKeyword.position_change,
        "current_position":  TrackedKeyword.current_position,
        "keyword":           TrackedKeyword.keyword,
        "search_volume":     TrackedKeyword.search_volume,
        "difficulty":        TrackedKeyword.difficulty,
    }.get(sort_by, TrackedKeyword.position_change)
 
    q = q.order_by(desc(sort_col) if order == "desc" else sort_col)
 
    total = q.count()
    rows: List[TrackedKeyword] = q.offset((page - 1) * page_size).limit(page_size).all()
 
    def trend(k: TrackedKeyword) -> str:
        if k.position_change is None:
            return "new"
        if k.position_change > 2:
            return "up"
        if k.position_change < -2:
            return "down"
        return "stable"
 
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "keywords": [
            {
                "id": k.id,
                "keyword": k.keyword,
                "domain": k.domain,
                "engine": k.engine,
                "country": k.country,
                "group_name": k.group_name,
                "tags": k.tags or [],
                "current_position": k.current_position,
                "previous_position": k.previous_position,
                "position_change": k.position_change,
                "best_position": k.best_position,
                "search_volume": k.search_volume,
                "difficulty": k.difficulty,
                "landing_url": k.landing_url,
                "last_checked_at": k.last_checked_at,
                "trend": trend(k),
            }
            for k in rows
        ],
    }
 
 
# ── Sparkline / mini-trend (last N data-points per keyword) ──────────────────
 
@router.get("/sparklines")
async def get_sparklines(
    domain: Optional[str] = None,
    job_id: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),   # how many keywords
    points: int = Query(10, ge=3, le=30),  # data-points each
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the last `points` history rows for the `limit` most-recently-checked
    keywords.  Used for the mini-trend cards on the dashboard.
    Pass job_id to scope a single campaign.
    """
    q = (
        db.query(TrackedKeyword)
        .filter(
            TrackedKeyword.user_id == current_user.id,
            TrackedKeyword.is_active == True,
            TrackedKeyword.last_checked_at.isnot(None),
        )
        .order_by(desc(TrackedKeyword.last_checked_at))
    )

    if job_id:
        ids = _keyword_ids_for_campaign(job_id, current_user.id, db)
        if not ids:
            q = q.filter(False)
        else:
            q = q.filter(TrackedKeyword.id.in_(ids))

    if domain:
        q = q.filter(TrackedKeyword.domain == domain)
 
    kws: List[TrackedKeyword] = q.limit(limit).all()
 
    result = []
    for kw in kws:
        hist = (
            db.query(KeywordHistory)
            .filter(KeywordHistory.keyword_id == kw.id)
            .order_by(desc(KeywordHistory.checked_at))
            .limit(points)
            .all()
        )
        # Reverse so oldest → newest
        data = [
            {"date": h.checked_at.isoformat(), "position": h.position}
            for h in reversed(hist)
        ]
        result.append(
            {
                "id": kw.id,
                "keyword": kw.keyword,
                "domain": kw.domain,
                "current_position": kw.current_position,
                "position_change": kw.position_change,
                "trend": (
                    "up" if (kw.position_change or 0) > 0
                    else "down" if (kw.position_change or 0) < 0
                    else "stable"
                ),
                "sparkline": data,
            }
        )
 
    return {"sparklines": result}
 
 
# ── Chart history (for the main line chart) ───────────────────────────────────
 
@router.get("/chart")
async def get_chart_data(
    keyword_ids: str = Query(..., description="Comma-separated keyword IDs"),
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns time-series history for selected keywords.
    Supports overlaying multiple keywords on the same chart.
    """
    ids = [int(x) for x in keyword_ids.split(",") if x.strip().isdigit()]
    if not ids:
        raise HTTPException(400, "Provide at least one keyword_id")
 
    since = datetime.utcnow() - timedelta(days=days)
 
    series = []
    for kid in ids:
        kw = db.query(TrackedKeyword).filter(
            TrackedKeyword.id == kid,
            TrackedKeyword.user_id == current_user.id,
        ).first()
        if not kw:
            continue

        print([r.job_id for r in kw.trackings])
 
        hist = (
            db.query(KeywordHistory)
            .filter(
                KeywordHistory.keyword_id == kid,
                KeywordHistory.checked_at >= since,
            )
            .order_by(KeywordHistory.checked_at)
            .all()
        )
 
        series.append(
            {
                "id": kw.id,
                "keyword": kw.keyword,
                "domain": kw.domain,
                "engine": kw.engine,
                "data": [
                    {"date": h.checked_at.isoformat()[:10], "position": h.position}
                    for h in hist
                ],
            }
        )
 
    return {"series": series, "days": days}
 
 
# ── Campaigns list ─────────────────────────────────────────────────────────────
 
# @router.get("")
# async def list_campaigns(
#     page: int = 1,
#     page_size: int = 20,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     q = (
#         db.query(RankTracking)
#         .filter(RankTracking.user_id == current_user.id)
#         .order_by(desc(RankTracking.created_at))
#     )
#     total = q.count()
#     campaigns = q.offset((page - 1) * page_size).limit(page_size).all()
 
#     return {
#         "campaigns": [
#             {
#                 "job_id": c.job_id,
#                 "name": c.name,
#                 "domain": c.domain,
#                 "status": c.status,
#                 "engines": c.engines,
#                 "frequency": c.frequency,
#                 "is_scheduled": c.is_scheduled,
#                 "keyword_count": len(c.keywords_rel),
#                 "last_checked": c.last_checked,
#                 "next_check": c.next_check,
#                 "created_at": c.created_at,
#             }
#             for c in campaigns
#         ],
#         "total": total,
#     }


#----old
# @router.post("/", response_model=RankTrackingResponse)
# async def create_rank_tracking(
#     request: RankTrackingRequest,
#     background_tasks: BackgroundTasks,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Start rank tracking (requires 1 credit per check)"""
    
#     # Check credits
#     if not check_and_consume_credits(current_user, db, credits_needed=1):
#         raise HTTPException(
#             status_code=status.HTTP_402_PAYMENT_REQUIRED,
#             detail=f"Insufficient credits. You have {current_user.credits_remaining} remaining."
#         )
    
#     # Validate inputs
#     if not request.keywords or len(request.keywords) == 0:
#         raise HTTPException(status_code=400, detail="At least one keyword required")
    
#     if len(request.keywords) > 50:
#         raise HTTPException(status_code=400, detail="Maximum 50 keywords allowed")
    
#     # Create tracking job
#     job_id = str(uuid.uuid4())
    
#     tracking = RankTracking(
#         job_id=job_id,
#         user_id=current_user.id,
#         domain=request.domain,
#         keywords=request.keywords,
#         engines=request.engines,
#         frequency=request.frequency,
#         is_scheduled=request.is_scheduled,
#         status="pending",
#         progress=0
#     )
    
#     if request.is_scheduled:
#         tracking.next_check = calculate_next_check(request.frequency)
    
#     db.add(tracking)
#     db.commit()
    
#     # Start background task
#     background_tasks.add_task(run_rank_tracking_task, job_id, current_user.id, db)
    
#     return RankTrackingResponse(
#         job_id=job_id,
#         status="pending",
#         message=f"Rank tracking started for {len(request.keywords)} keywords"
#     )


# ── Single campaign status ─────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=RankTrackingStatus)
async def get_rank_tracking_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get rank tracking status and results"""
    
    tracking = db.query(RankTracking).filter(
        and_(
            RankTracking.job_id == job_id,
            RankTracking.user_id == current_user.id
        )
    ).first()
    
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking job not found")

    # {
    #     'job_id':tracking.job_id,
    #     'domain':tracking.domain,
    #     'status':tracking.status,
    #     'engines':[eng for eng in tracking.engines],
    #     'progress':tracking.progress,
    #     'is_scheduled':tracking.is_scheduled,
    #     'frequency' : tracking.frequency,
    #     'last_checked':tracking.last_checked,
    #     'results':tracking.results,
    #     'error':tracking.error,
    #     'next_check':tracking.next_check,
    #     'created_at':tracking.created_at,
    # }
    return RankTrackingStatus(
        job_id=tracking.job_id,
        domain=tracking.domain,
        status=tracking.status,
        engines=tracking.engines,
        progress=tracking.progress,
        is_scheduled=tracking.is_scheduled,
        frequency = tracking.frequency,
        last_checked=tracking.last_checked,
        results=tracking.results,
        error=tracking.error,
        next_check=tracking.next_check,
        created_at=tracking.created_at,
    )


@router.get("/{job_id}/history")
async def get_rank_history(
    job_id: str,
    keyword: Optional[str] = None,
    engine: Optional[str] = None,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get historical rank data for charts"""
    
    tracking = db.query(RankTracking).filter(
        and_(
            RankTracking.job_id == job_id,
            RankTracking.user_id == current_user.id
        )
    ).first()
    
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking job not found")
    
    # Query history
    query = db.query(RankHistory).filter(
        RankHistory.tracking_id == tracking.id
    )
    
    if keyword:
        query = query.filter(RankHistory.keyword == keyword)
    
    if engine:
        query = query.filter(RankHistory.engine == engine)
    
    # Last N days
    since = datetime.utcnow() - timedelta(days=days)
    query = query.filter(RankHistory.checked_at >= since)
    
    history = query.order_by(RankHistory.checked_at).all()
    
    # Format for charts
    chart_data = {}
    
    for record in history:
        key = f"{record.keyword}_{record.engine}"
        
        if key not in chart_data:
            chart_data[key] = {
                'keyword': record.keyword,
                'engine': record.engine,
                'data': []
            }
        
        chart_data[key]['data'].append({
            'date': record.checked_at.isoformat(),
            'position': record.position,
            'change': record.position_change
        })
    
    return {
        'job_id': job_id,
        'domain': tracking.domain,
        'history': list(chart_data.values())
    }


@router.delete("/{job_id}")
async def delete_rank_tracking(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete rank tracking job and history"""
    
    tracking = db.query(RankTracking).filter(
        and_(
            RankTracking.job_id == job_id,
            RankTracking.user_id == current_user.id
        )
    ).first()
    
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking job not found")
    
    db.delete(tracking)
    db.commit()
    
    return {"message": "Rank tracking deleted"}



 
# ── Single campaign status ─────────────────────────────────────────────────────
 
# @router.get("/{job_id}")
# async def get_campaign(
#     job_id: str,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     c = db.query(RankTracking).filter(
#         RankTracking.job_id == job_id,
#         RankTracking.user_id == current_user.id,
#     ).first()
#     if not c:
#         raise HTTPException(404, "Campaign not found")
 
#     return {
#         "job_id": c.job_id,
#         "name": c.name,
#         "domain": c.domain,
#         "status": c.status,
#         "progress": c.progress,
#         "error": c.error,
#         "engines": c.engines,
#         "frequency": c.frequency,
#         "is_scheduled": c.is_scheduled,
#         "next_check": c.next_check,
#         "last_checked": c.last_checked,
#         "keywords": [
#             {
#                 "id": k.id,
#                 "keyword": k.keyword,
#                 "current_position": k.current_position,
#                 "position_change": k.position_change,
#             }
#             for k in c.keywords_rel
#         ],
#     }
 
 
# ── Refresh campaign ───────────────────────────────────────────────────────────
 
@router.post("/{job_id}/refresh")
async def refresh_campaign(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(RankTracking).filter(
        RankTracking.job_id == job_id,
        RankTracking.user_id == current_user.id,
    ).first()
    if not c:
        raise HTTPException(404, "Campaign not found")
 
    if not check_and_consume_credits(current_user, db, 1):
        raise HTTPException(402, "Insufficient credits")
 
    c.status = "pending"
    c.progress = 0
    db.commit()
    background_tasks.add_task(run_tracking_task, job_id, current_user.id)
    return {"message": "Refresh started"}
 
 
# ── Delete campaign ────────────────────────────────────────────────────────────
 
@router.delete("/{job_id}", status_code=204)
async def delete_campaign(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(RankTracking).filter(
        RankTracking.job_id == job_id,
        RankTracking.user_id == current_user.id,
    ).first()
    if not c:
        raise HTTPException(404, "Campaign not found")
    db.delete(c)
    db.commit()
 

@router.post("/{job_id}/refresh")
async def refresh_rank_tracking(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually refresh rank tracking (requires 1 credit)"""
    
    tracking = db.query(RankTracking).filter(
        and_(
            RankTracking.job_id == job_id,
            RankTracking.user_id == current_user.id
        )
    ).first()
    
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking job not found")
    
    # Check credits
    if not check_and_consume_credits(current_user, db, credits_needed=1):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits"
        )
    
    # Reset status
    tracking.status = "pending"
    tracking.progress = 0
    db.commit()
    
    # Start background task
    background_tasks.add_task(run_rank_tracking_task, job_id, current_user.id, db)
    
    return {"message": "Refresh started"}


