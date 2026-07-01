"""
Authenticated API - Complete FastAPI server with JWT auth, Google OAuth, and database
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta
import base64,os
from urllib.parse import urlparse
from sqlalchemy import desc, and_, func

# Database and models
from db.database import get_db, init_db
from db.models import ActivityType, User, Audit, Crawl, Comparison, KeywordAnalysis, BacklinkAnalysis, RefreshToken, Notification, RankTracking, RankHistory, TrackedKeyword, KeywordHistory 

# Authentication
from db.auth import (
    get_current_user, get_current_user_optional, check_and_consume_credits,
    authenticate_user, create_access_token, create_refresh_token, get_user_activity_history, log_activity, mark_notification_read, update_activity_status,
    verify_google_token, verify_token, get_password_hash, get_activity_stats, create_notification,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Schemas
from db.schemas import (
    ActivityListItem, CreateComparisonRequest, CreateComparisonResponse, UserRegister, UserLogin, GoogleAuthRequest, TokenResponse, RefreshTokenRequest,
    UserResponse, UserUpdate,
    NotificationItem,
    AuditRequest, AuditResponse, AuditStatus, CrawlRequest,
    ComparisonRequest, KeywordRequest, BacklinkRequest,
    AuditListItem, PaginatedResponse, SiteDataResponse, SiteHealthOverview, SiteRecommendation, ComparisonSummary, KeywordRanking, CrawlSummary, CrawlListItem,
    RankTrackingResponse, RankTrackingRequest, RankTrackingListItem, RankTrackingStatus, CreateTrackingRequest, CreateTrackingResponse
)

from db.payment_schemas import (
    CheckoutLinkRequest, CheckoutLinkResponse, SubscriptionStatus, 
    CancelSubscriptionResponse, PlanInfo, PlansResponse, TrialStatus,
    StartTrialResponse, TrialUpgradeOffer
)


from tasks import run_audit_task, run_crawl_task, run_comparison_task, run_keyword_analysis_task, run_rank_tracking_task, calculate_next_check, check_for_alerts, run_tracking_task, _next_check_time

#routes
from db.admin_routes import router as admin_router
from routes.embed_router import router as embed_router
from routes.tracking_routes import router as tracking_router
from services.visitor_tracking import track_visitor, get_visitor_analytics, mark_visitor_converted
from services import whop_service, email_service

import logging
from contextlib import asynccontextmanager
from db.migrations import run_migrations, check_migration_status
from fastapi import Request

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Startup Events
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    More reliable than @app.on_event decorators
    """
    # Startup
    logger.info("🚀 Starting AuditFlow API...")
    try:
        logger.info("📦 Running database migrations...")
        run_migrations()
        logger.info("✓ Migrations completed")
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        raise
    
    try:
        logger.info("🗄️  Initializing database...")
        init_db()
        logger.info("✓ Database initialized")
        print("✅ API ready to accept requests\n")
    except Exception as e:
        logger.warning(f"Database already initialized: {e}")
    
    logger.info("✅ API ready to accept requests\n")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AuditFlow API...")

app = FastAPI(
    title="AuditFlow API",
    description="Complete SEO audit platform with authentication",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:3000", "https://auditflow-frontend.vercel.app", "https://outaudits.com"],
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(embed_router)
app.include_router(tracking_router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()


# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

#---------------------------------------------------------

@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register new user with email/password"""
    
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_verified=False,
        credits_remaining=10,
        credits_reset_date=datetime.utcnow() + timedelta(days=30)
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    create_notification(
            db=db,
            user_id=user.id,
            type="welcome",
            title="Welcome to OUTAUDITS",
            message=f"Add your agency settings to get started.",
            # metadata={"job_id": job_id, "url": str(req.domain)}
            )
    # email_service.send_welcome_email()
    
    # Mark visitor as converted
    from services.visitor_tracking import extract_ip_from_request
    ip_address = extract_ip_from_request(request)
    from db.models import Visitor
    visitor = db.query(Visitor).filter(Visitor.ip_address == ip_address).order_by(Visitor.visited_at.desc()).first()
    if visitor:
        visitor.converted = True
        visitor.converted_user_id = user.id
        db.commit()
        logger.info(f"[CONVERSION] Visitor {ip_address} converted to user {user.id}")
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(user.id, db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login with email/password"""
    
    user = authenticate_user(db, user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(user.id, db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/api/auth/google", response_model=TokenResponse)
async def google_auth(auth_data: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Authenticate with Google OAuth"""
    
    google_user = verify_google_token(auth_data.token)
    
    if not google_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )
    
    # Find or create user
    user = db.query(User).filter(User.google_id == google_user['google_id']).first()
    
    if not user:
        # Check if email exists
        user = db.query(User).filter(User.email == google_user['email']).first()
        
        if user:
            # Link Google account to existing user
            user.google_id = google_user['google_id']
        else:
            # Create new user
            user = User(
                email=google_user['email'],
                google_id=google_user['google_id'],
                full_name=google_user.get('name'),
                is_active=True,
                is_verified=google_user.get('email_verified', False),
                credits_remaining=10,
                credits_reset_date=datetime.utcnow() + timedelta(days=30)
            )
            db.add(user)
            
            create_notification(
            db=db,
            user_id=user.id,
            type="welcome",
            title="Welcome to OUTAUDITS",
            message=f"Add your agency settings to get started.",
            # metadata={"job_id": job_id, "url": str(req.domain)}
            )
            # email_service.send_welcome_email()
        
        db.commit()
        db.refresh(user)

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(user.id, db)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Get new access token using refresh token"""
    
    payload = verify_token(refresh_data.refresh_token, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = int(payload.get("sub"))
    
    # Verify refresh token exists in database and is not revoked
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_data.refresh_token,
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked"
        )
    
    # Create new access token
    access_token = create_access_token(data={"sub": str(user_id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,  # Keep same refresh token
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    if current_user.agency_url:
        print(current_user.agency_url)
    return current_user


@app.patch("/api/auth/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    print(user_update)
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    print(current_user.agency_name)
    db.refresh(current_user)
    
    return current_user


# ──────────────────────────────────────────────────────────────────────────────
# AUDIT ENDPOINTS (PROTECTED)
# ──────────────────────────────────────────────────────────────────────────────



@app.post("/api/audit", response_model=AuditResponse)
async def create_audit(
    request: AuditRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start new audit (requires authentication and credits)"""
    
    # Check credits
    if not check_and_consume_credits(current_user, db, credits_needed=1):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. You have {current_user.credits_remaining} credits remaining."
        )
    
    # Create audit record
    job_id = str(uuid.uuid4())
    audit = Audit(
        job_id=job_id,
        client_name=request.client_name,
        user_id=current_user.id,
        url=str(request.url),
        status="pending",
        progress=0
    )
    
    db.add(audit)
    db.commit()

    # Log activity
    log_activity(
        db,
        user_id=current_user.id,
        activity_type=ActivityType.AUDIT,
        activity_id=job_id,
        target=str(request.url),
        status="pending"
    )
    create_notification(
    db=db,
    user_id=current_user.id,
    type="audit",
    title="Audit started",
    message=f"Your audit for {request.url} has been queued (job {job_id}).",
    metadata={"job_id": job_id, "url": str(request.url)}
)
    
    
    # Start background task
    background_tasks.add_task(run_audit_task, job_id, str(request.url), current_user.id, db)
    
    return AuditResponse(
        job_id=job_id,
        status="pending",
        message=f"Audit started for {request.url}"
    )


@app.get("/api/audit/{job_id}", response_model=AuditStatus)
async def get_audit_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit status and results"""
    
    audit = db.query(Audit).filter(
        Audit.job_id == job_id,
        Audit.user_id == current_user.id
    ).first()
    
    if not audit or current_user.id != audit.user_id:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    update_activity_status(
        db,
        status=audit.status,
        activity_id=job_id,
    )
    
    
    
    return AuditStatus(
        job_id=audit.job_id,
        status=audit.status,
        progress=audit.progress,
        results=audit.results,
        error=audit.error
    )



@app.get("/api/audits")
async def list_audits(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's audit history"""
    
    query = db.query(Audit).filter(Audit.user_id == current_user.id)
    total = query.count()

    this_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    audits = query.order_by(Audit.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    audits_this_month = db.query(Audit).filter(Audit.user_id == current_user.id, Audit.created_at >= this_month).all()
    
    
    avg_score = 0
    total_score = 0
    for a in audits:
        if a.overall_score:
            total_score += a.overall_score

    if total_score != 0:
        avg_score = total_score/len(audits)     
        


    
    return PaginatedResponse(
        items=[AuditListItem.model_validate(a) for a in audits],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@app.get("/api/crawls")
async def list_craws(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's crawl history"""
    
    query = db.query(Crawl).filter(Crawl.user_id == current_user.id)
    total = query.count()
    
    crawls = query.order_by(Crawl.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    def count_issues(issues: dict) -> int:
        """
        Count the total number of issues across all categories in the issues dict.
        Handles dicts, lists, and empty values gracefully.
        """
        total = 0
        for category, value in issues.items():
            if isinstance(value, dict):
                # Count entries in dict
                total += len(value)
            elif isinstance(value, list):
                # Count entries in list
                total += len(value)
            else:
                # If it's something else (unlikely), skip
                continue
        return total

    total_pages_crawled = 0
    total_issues_found = 0


    for c in crawls:
        total_pages_crawled += c.results.get("summary").get("total_pages_crawled",0)
        total_issues_found += count_issues(c.results.get("issues",{}))

    metadata = {
        'total_pages_crawled' : total_pages_crawled,
        'total_issues_found' : total_issues_found,
    }

    
    
    return PaginatedResponse(
        items=[{
            "id": c.id,
            "job_id": c.job_id,
            "url": c.url,
            "status": c.status,
            "pages_crawled": c.results.get("summary").get("total_pages_crawled",0),
            "issues_found": count_issues(c.results.get("issues",{})),
            "created_at": c.created_at,
            "completed_at": c.completed_at,
            "results" : c.results,
        } for c in crawls],
        metadata = metadata,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

    

# Similar patterns for Crawl, Comparison, Keywords, Backlinks...
# (I'll create abbreviated versions to save space)



@app.post("/api/crawl", response_model=AuditResponse)
async def create_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start deep crawl (requires 2 credits)"""
    
    if not check_and_consume_credits(current_user, db, credits_needed=2):
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    job_id = str(uuid.uuid4())
    crawl = Crawl(
        job_id=job_id,
        user_id=current_user.id,
        url=str(request.url),
        client_name=str(request.client_name),
        max_pages=request.max_pages,
        status="pending"
    )
    db.add(crawl)
    db.commit()

    log_activity(
        db,
        user_id=current_user.id,
        activity_type=ActivityType.CRAWL,
        activity_id=job_id,
        target=str(request.url),
        status="pending"
    )
    create_notification(
    db=db,
    user_id=current_user.id,
    type="crawl",
    title=f"Crawl started!",
    message=f"Your audit for {request.url} has been queued (job).",
    metadata={"job_id": job_id, "url": str(request.url)}
)
    
    # TODO: Add background task
    background_tasks.add_task(run_crawl_task, job_id, str(request.url), current_user.id, db)
    
    return AuditResponse(job_id=job_id, status="pending", message="Crawl started")

@app.get("/api/crawl/{job_id}", response_model=AuditStatus)
async def get_crawl_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get crawl status and results"""

    crawl = db.query(Crawl).filter(
        Crawl.job_id == job_id,
        Crawl.user_id == current_user.id
    ).first()
    
    if not crawl:
        raise HTTPException(status_code=404, detail="Crawl not found")
    

    update_activity_status(
        db,
        status=crawl.status,
        activity_id=job_id,
    )

    
    return AuditStatus(
        job_id=crawl.job_id,
        status=crawl.status,
        progress=crawl.progress,
        results=crawl.results,
        error=crawl.error
    )

def _domain(url: str) -> str:
    try:
        netloc = urlparse(url if "://" in url else f"https://{url}").netloc
        return netloc.replace("www.", "") or url
    except Exception:
        return url
    
@app.post("/api/comparisons", response_model=CreateComparisonResponse, status_code=201)
async def create_comparison(
    req: CreateComparisonRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_and_consume_credits(current_user, db, credits_needed=2):
        raise HTTPException(402, f"Insufficient credits ({current_user.credits_remaining} left)")
 
    job_id = str(uuid.uuid4())
    comp = Comparison(
        job_id=job_id,
        user_id=current_user.id,
        target_url=req.target_url,
        competitor_urls=req.competitor_urls,
        client_name=req.client_name or _domain(req.target_url),
        status="pending",
        progress=0,
    )
    db.add(comp)
    db.commit()
 
    background_tasks.add_task(run_comparison_task, job_id)
 
    return CreateComparisonResponse(
        job_id=job_id,
        status="pending",
        message=f"Comparison started: {req.target_url} vs {len(req.competitor_urls)} competitors",
    )


@app.get("/api/comparisons/kpis")
async def get_comaprisons_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Stat cards:
      - total_comparisons
      - domains_analyzed (distinct target + competitor domains)
      - avg_score_gap (target - best competitor, averaged across completed runs)
      - strongest_win   { comparison with largest positive gap }
      - biggest_gap     { comparison with largest negative gap }
    """
    completed = (
        db.query(Comparison)
        .filter(Comparison.user_id == current_user.id, Comparison.status == "completed")
        .all()
    )
 
    total = db.query(func.count(Comparison.id)).filter(
        Comparison.user_id == current_user.id
    ).scalar() or 0
 
    domains = set()
    for c in completed:
        domains.add(_domain(c.target_url))
        for u in (c.competitor_urls or []):
            domains.add(_domain(u))
 
    gaps = [c.score_gap for c in completed if c.score_gap is not None]
    avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else None
 
    strongest = max(completed, key=lambda c: c.score_gap if c.score_gap is not None else -999, default=None)
    biggest_gap = min(completed, key=lambda c: c.score_gap if c.score_gap is not None else 999, default=None)
 
    def snapshot(c: Optional[Comparison]):
        if not c or c.score_gap is None:
            return None
        return {
            "job_id": c.job_id,
            "client_name": c.client_name,
            "target_domain": _domain(c.target_url),
            "competitor_domain": _domain(c.best_competitor_url) if c.best_competitor_url else None,
            "target_score": c.target_score,
            "competitor_score": c.best_competitor_score,
            "gap": c.score_gap,
        }
 
    return {
        "total_comparisons": total,
        "domains_analyzed": len(domains),
        "avg_score_gap": avg_gap,
        "strongest_win": snapshot(strongest) if (strongest and strongest.score_gap and strongest.score_gap > 0) else None,
        "biggest_gap": snapshot(biggest_gap) if (biggest_gap and biggest_gap.score_gap and biggest_gap.score_gap < 0) else None,
    }
 
 
# ── LIST ────────────────────────────────────────────────────────────────────────
 
@app.get("/api/comparisons")
async def list_comparisons(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Comparison).filter(Comparison.user_id == current_user.id)
    if status_filter:
        q = q.filter(Comparison.status == status_filter)
    q = q.order_by(desc(Comparison.created_at))
 
    total = q.count()
    rows: List[Comparison] = q.offset((page - 1) * page_size).limit(page_size).all()
 
    def card(c: Comparison) -> dict:
        return {
            "job_id": c.job_id,
            "client_name": c.client_name,
            "target_url": c.target_url,
            "target_domain": _domain(c.target_url),
            "competitor_urls": c.competitor_urls,
            "competitor_domains": [_domain(u) for u in (c.competitor_urls or [])],
            "status": c.status,
            "progress": c.progress,
            "target_score": c.target_score,
            "best_competitor_score": c.best_competitor_score,
            "best_competitor_url": c.best_competitor_url,
            "best_competitor_domain": _domain(c.best_competitor_url) if c.best_competitor_url else None,
            "avg_competitor_score": c.avg_competitor_score,
            "score_gap": c.score_gap,
            "created_at": c.created_at,
            "completed_at": c.completed_at,
        }
 
    return {
        "comparisons": [card(c) for c in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
 
 
# ── SINGLE STATUS ────────────────────────────────────────────────────────────────
 
@app.get("/api/comparisons/{job_id}")
async def get_comparison(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(Comparison).filter(
        Comparison.job_id == job_id,
        Comparison.user_id == current_user.id,
    ).first()
    if not c:
        raise HTTPException(404, "Comparison not found")
 
    return {
        "job_id": c.job_id,
        "name": c.name,
        "target_url": c.target_url,
        "competitor_urls": c.competitor_urls,
        "status": c.status,
        "progress": c.progress,
        "results": c.results,
        "error": c.error,
        "created_at": c.created_at,
        "completed_at": c.completed_at,
    }
 
 
# ── REFRESH ──────────────────────────────────────────────────────────────────────
 
@app.post("/api/comparisons/{job_id}/refresh")
async def refresh_comparison(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(Comparison).filter(
        Comparison.job_id == job_id,
        Comparison.user_id == current_user.id,
    ).first()
    if not c:
        raise HTTPException(404, "Comparison not found")
 
    if not check_and_consume_credits(current_user, db, 2):
        raise HTTPException(402, "Insufficient credits")
 
    c.status = "pending"
    c.progress = 0
    db.commit()
    background_tasks.add_task(run_comparison_task, job_id)
    return {"message": "Refresh started"}
 
 
# ── DELETE ───────────────────────────────────────────────────────────────────────
 
@app.delete("/api/comparisons/{job_id}", status_code=204)
async def delete_comparison(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(Comparison).filter(
        Comparison.job_id == job_id,
        Comparison.user_id == current_user.id,
    ).first()
    if not c:
        raise HTTPException(404, "Comparison not found")
    db.delete(c)
    db.commit()


# async def create_compare(
#     request: ComparisonRequest,
#     background_tasks: BackgroundTasks,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db)
# ):
#     """Start deep comparison (requires 2 credits)"""

#     print(request)
#     print(current_user)
#     print("Checking credits...")

#     if not check_and_consume_credits(current_user, db, credits_needed=2):
#         raise HTTPException(status_code=402, detail="Insufficient credits")

#     target_url = str(request.target_url)
#     competitor_urls = [str(url) for url in request.competitor_urls[:3]]  # Max 3 competitors
#     job_id = str(uuid.uuid4())
#     compare = Comparison(
#         job_id=job_id,
#         client_name=str(request.client_name),
#         user_id=current_user.id,
#         target_url=target_url,
#         competitor_urls=competitor_urls,
#         status="pending"
#     )
#     db.add(compare)
#     db.commit()

#     log_activity(
#         db,
#         user_id=current_user.id,
#         activity_type=ActivityType.COMPARISON,
#         activity_id=job_id,
#         target=target_url,
#         status="pending"
#     )
    
#     create_notification(
#     db=db,
#     user_id=current_user.id,
#     type="compare",
#     title="Comparison started",
#     message=f"Your Comparison for {target_url} has been queued (job {job_id[:4]}).",
#     metadata={"job_id": job_id, "url": str(target_url)}
# )

#     # TODO: Add background task
#     background_tasks.add_task(run_comparison_task, job_id, target_url, competitor_urls, current_user.id, db)

#     return AuditResponse(job_id=job_id, status="pending", message="Comparison started")



# ──────────────────────────────────────────────────────────────────────────────
# Scheduler (call this from a cron job or APScheduler)
# ──────────────────────────────────────────────────────────────────────────────

# async def run_scheduled_rank_checks(db: Session):
#     """Run all scheduled rank checks that are due"""
    
#     now = datetime.utcnow()
    
#     # Find all trackings due for check
#     due_trackings = db.query(RankTracking).filter(
#         and_(
#             RankTracking.is_scheduled == True,
#             RankTracking.next_check <= now,
#             RankTracking.status != "running"
#         )
#     ).all()
    
#     print(f"Found {len(due_trackings)} rank trackings due for check")
    
#     for tracking in due_trackings:
#         try:
#             # Check if user has credits
#             user = db.query(User).filter(User.id == tracking.user_id).first()
#             if not user or user.credits_remaining < 1:
#                 continue
            
#             # Run tracking
#             await run_rank_tracking_task(tracking.job_id, tracking.user_id, db)
            
#         except Exception as e:
#             print(f"Error running scheduled tracking {tracking.job_id}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# BILLING ENDPOINTS (Whop Payment Integration)
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/billing/checkout-link", response_model=CheckoutLinkResponse)
async def create_checkout_link_endpoint(
    request: CheckoutLinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Whop checkout link for plan upgrade
    
    Request body:
    - plan_tier: "pro" or "agency"
    
    Returns checkout URL for user to complete payment
    """
    
    plan_info = whop_service.get_plan_info(request.plan_tier)
    if not plan_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan tier: {request.plan_tier}"
        )
    
    # Check if user already has an active subscription at this tier
    if current_user.plan == request.plan_tier and current_user.subscription_status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have an active {request.plan_tier} subscription"
        )
    
    checkout_url = await whop_service.create_checkout_link(
        user_id=current_user.id,
        plan_tier=request.plan_tier,
        db=db
    )
    
    if not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout link. Please try again."
        )
    
    logger.info(f"Created checkout link for user {current_user.id}, plan {request.plan_tier}")
    
    return CheckoutLinkResponse(
        checkout_url=checkout_url,
        plan_tier=request.plan_tier
    )


@app.get("/api/billing/subscription", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription status"""
    
    return SubscriptionStatus(
        plan=current_user.plan,
        subscription_status=current_user.subscription_status or "inactive",
        subscription_started_at=current_user.subscription_started_at,
        subscription_renews_at=current_user.subscription_renews_at,
        credits_remaining=current_user.credits_remaining,
        whop_subscription_id=current_user.whop_subscription_id
    )


@app.post("/api/billing/cancel-subscription", response_model=CancelSubscriptionResponse)
async def cancel_subscription_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel user's active subscription"""
    
    if not current_user.whop_subscription_id or current_user.subscription_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel"
        )
    
    success = await whop_service.cancel_subscription(current_user.id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription. Please try again."
        )
    
    logger.info(f"Cancelled subscription for user {current_user.id}")
    
    return CancelSubscriptionResponse(
        success=True,
        message="Subscription cancelled successfully"
    )


@app.get("/api/billing/plans", response_model=PlansResponse)
async def get_plans():
    """Get all available plans and pricing"""
    
    plans_data = {}
    for tier, config in whop_service.get_all_plans().items():
        plans_data[tier] = PlanInfo(
            name=config["name"],
            price=config["price"],
            credits=config["credits"]
        )
    
    return PlansResponse(plans=plans_data)


@app.post("/api/billing/webhook")
async def whop_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Whop payment events
    
    Events handled:
    - order.completed: Payment successful
    - order.failed: Payment failed
    - subscription.cancelled: Subscription cancelled
    """
    from whop_sdk import Whop   
    


    # webhook_key must be base64-encoded — the SDK passes it
    # straight to the Standard Webhooks verifier, which expects b64.
    whopsdk = Whop(
        api_key=os.environ["WHOP_API_KEY"],
        webhook_key=base64.b64encode(os.environ["WHOP_WEBHOOK_SECRET"].encode()).decode(),
    )
    print("Webhook received")
    # Get raw body for signature verification
    
    

    # Verify webhook signature
    # if not whop_service.verify_webhook_signature(body, signature):
    #     logger.warning("Invalid webhook signature")
    #     raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        payload = await request.json()
        # print(payload)
        # Unwrap + verify signature in one call. Raises on invalid signatures.
        body = (await request.body()).decode()
        event = whopsdk.webhooks.unwrap(body, headers=dict(request.headers))
        data = event.data
        print("webhook: ",event.type, data)
        
        logger.info(f"Received Whop webhook: {event}")
        # checkout_config = whopsdk.checkout_configurations.retrieve(data.checkout_configuration.id)
        checkout_config = whopsdk.checkout_configurations.retrieve("ch_LWf3OIdrIMw2pZM")
        # checkout_config = whopsdk.checkout_configurations.retrieve("ch_pxBxsChgCIuqy1F")
        print(checkout_config)
        if event.type == "payment.succeeded":
            # Payment successful
            subscription_id = data.membership.id
            product_id = data.product.id
            customer_email = checkout_config.metadata.get('user_email', data.user.email)
            metadata = data.metadata

            trial = checkout_config.plan.trial_period_days if checkout_config.plan.trial_period_days else 0
            print(trial)

            print(subscription_id, product_id, customer_email, metadata)
            
            success = await whop_service.handle_payment_success(
                subscription_id=subscription_id,
                product_id=product_id,
                customer_email=customer_email,
                metadata=metadata,
                trial = trial,
                db=db
            )
            
            if success:
                return {"status": "success", "message": "Payment processed"}
            else:
                logger.error("Failed to process payment")
                return {"status": "error", "message": "Failed to process payment"}, 500
                
        elif event.type == "order.failed":
            # Payment failed
            customer_email = data.get("customer_email")
            reason = data.get("failure_reason", "Unknown")
            
            await whop_service.handle_payment_failed(
                customer_email=customer_email,
                reason=reason,
                db=db
            )
            
            return {"status": "success", "message": "Failure recorded"}
            
        elif event.type == "subscription.cancelled":
            # Subscription cancelled
            subscription_id = data.get("subscription_id")
            customer_email = data.get("customer_email")
            
            user = db.query(User).filter(User.email == customer_email).first()
            if user and user.whop_subscription_id == subscription_id:
                user.subscription_status = "cancelled"
                user.updated_at = datetime.utcnow()
                db.commit()
                logger.info(f"Subscription cancelled for user {user.id}")
            
            return {"status": "success", "message": "Cancellation recorded"}
        
        else:
            logger.info(f"Unhandled webhook event: {event}")
            return {"status": "success", "message": "Event received"}
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing webhook")


# ──────────────────────────────────────────────────────────────────────────────
# TRIAL MANAGEMENT ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/billing/start-trial", response_model=StartTrialResponse)
async def start_trial_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start 14-day free Pro plan trial
    - User can only use trial once per account
    - Trial grants 10,000 credits
    - After 14 days, user reverts to Free plan (20 credits)
    """
    
    success, message, trial_ends_at = await whop_service.start_free_trial(
        current_user.id, db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    logger.info(f"Trial started for user {current_user.id}")
    
    create_notification(
    db=db,
    user_id=current_user.id,
    type="trial-started",
    title="Your Free trial has been activated !",
    metadata={}
    )
    
    return StartTrialResponse(
        success=True,
        message=message,
        trial_ends_at=trial_ends_at,
        credits_granted=10000
    )


@app.get("/api/billing/trial-status", response_model=TrialStatus)
async def get_trial_status_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's trial status"""
    
    trial_status = whop_service.get_trial_status(current_user)
    
    return TrialStatus(
        trial_active=trial_status["trial_active"],
        trial_started_at=trial_status["trial_started_at"],
        trial_ends_at=trial_status["trial_ends_at"],
        trial_used=trial_status["trial_used"],
        days_remaining=trial_status["days_remaining"],
        plan=trial_status["plan"],
        credits_remaining=trial_status["credits_remaining"]
    )


@app.get("/api/billing/trial-upgrade-offer", response_model=TrialUpgradeOffer)
async def get_trial_upgrade_offer_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get upgrade offer after trial expires
    Users who expired trial get 30% discount if they upgrade within 3 days
    """
    
    offer = whop_service.get_trial_upgrade_offer(current_user)
    
    return TrialUpgradeOffer(
        trial_expired=offer["trial_expired"],
        offer_active=offer["offer_active"],
        discount_percent=offer["discount_percent"],
        offer_expires_at=offer["offer_expires_at"],
        plan_tier=offer["plan_tier"],
        discounted_price=offer["discounted_price"],
        original_price=offer["original_price"]
    )


# ──────────────────────────────────────────────────────────────────────────────
# Activity history endpoint
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/activities")
async def get_activities(
    limit: int = 10,
    days: Optional[int] = None,
    activity_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user activity history"""
    atype = ActivityType(activity_type) if activity_type else None
    activities = get_user_activity_history(db, current_user.id, limit=limit, days=days, activity_type=atype)
    
    return {
        "total": len(activities),
        "activities": [
            {
                "id": a.id,
                "type": a.activity_type,
                "activity_id": a.activity_id,
                "target": a.target,
                "status": a.status,
                "summary": a.summary,
                "created_at": a.created_at,
                "completed_at": a.completed_at,
                
            }
            for a in activities
        ]
    }

@app.get("/api/activities/stats")
async def get_activity_stats_endpoint(
    days: int = 30,
    current_month: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get activity statistics"""
    
    stats = get_activity_stats(db, current_user.id, days=days, current_month=current_month)
    return stats


# ──────────────────────────────────────────────────────────────────────────────
# Notifications endpoint
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/notifications")
async def list_notifications(
    page: int = 1, page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc())
    total = query.count()
    items = query.offset((page-1)*page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [NotificationItem.model_validate(n) for n in items]
    }

@app.post("/api/notifications/{notification_id}/mark-read")
async def mark_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = mark_notification_read(db, notification_id, current_user.id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "notification": NotificationItem.model_validate(n)}

# ──────────────────────────────────────────────────────────────────────────────
# VISITOR TRACKING ENDPOINTS (For conversion analysis)
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/track/visitor")
async def track_landing_page_visitor(
    request: Request,
    db: Session = Depends(get_db),
    page_url: Optional[str] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
):
    """
    Track a landing page visitor for conversion analysis
    
    No authentication required - called from landing page
    Captures: IP, Country, User Agent, Referrer, Timestamp
    
    Query params (optional):
    - page_url: URL being visited
    - utm_source: Traffic source (google, facebook, etc)
    - utm_medium: Traffic medium (cpc, organic, email, etc)
    - utm_campaign: Campaign name
    """
    
    visitor = await track_visitor(db, request, page_url=page_url)
    
    if visitor:
        return {
            "status": "tracked",
            "visitor_id": visitor.id,
            "ip": visitor.ip_address,
            "country": visitor.country,
            "timestamp": visitor.visited_at.isoformat(),
            "utm": {
                "source": utm_source,
                "medium": utm_medium,
                "campaign": utm_campaign
            }
        }
    else:
        return {"status": "error", "message": "Failed to track visitor"}


@app.get("/api/visitors/analytics")
async def get_visitors_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get visitor analytics and conversion metrics
    Admin/Owner only - see conversion trends by country, referrer, etc.
    """
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    analytics = get_visitor_analytics(db, days=days)
    
    return {
        "analytics": analytics,
        "period": f"Last {days} days",
        "generated_at": datetime.utcnow().isoformat()
    }


@app.get("/api/visitors/list")
async def list_visitors(
    page: int = 1,
    page_size: int = 50,
    country: Optional[str] = None,
    converted_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List tracked visitors with filtering options
    Admin only
    """
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from db.models import Visitor
    
    query = db.query(Visitor)
    
    if country:
        query = query.filter(Visitor.country_code == country.upper())
    
    if converted_only:
        query = query.filter(Visitor.converted == True)
    
    total = query.count()
    
    visitors = query.order_by(Visitor.visited_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return PaginatedResponse(
        items=[{
            "id": v.id,
            "ip": v.ip_address,
            "country": v.country,
            "country_code": v.country_code,
            "city": v.city,
            "referer": v.referer,
            "visited_at": v.visited_at.isoformat(),
            "converted": v.converted,
            "converted_user_id": v.converted_user_id
        } for v in visitors],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@app.post("/api/visitors/{visitor_id}/mark-converted")
async def mark_visitor_as_converted(
    visitor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a visitor as converted when they sign up
    Call this from your registration endpoint
    """
    
    from db.models import Visitor
    
    visitor = db.query(Visitor).filter(Visitor.id == visitor_id).first()
    
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    visitor.converted = True
    visitor.converted_user_id = current_user.id
    db.commit()
    
    return {
        "status": "success",
        "visitor_id": visitor.id,
        "converted": True,
        "user_id": current_user.id
    }


# ──────────────────────────────────────────────────────────────────────────────
# Site Data
# ──────────────────────────────────────────────────────────────────────────────

def generate_recommendations_from_crawl(crawl_results) -> List[SiteRecommendation]:
    """
    Generate a list of `SiteRecommendation` items based on crawl `results`.
    This inspects the `issues` section of crawl results and creates a
    short, prioritized recommendation for each issue category detected.
    """
    recs: List[SiteRecommendation] = []
    if not crawl_results:
        return recs

    issues = crawl_results.get("issues") if isinstance(crawl_results, dict) else None
    if not issues:
        return recs

    for category, value in issues.items():
        # Determine a sensible count for the category
        count = 0
        examples = None
        if isinstance(value, dict):
            # Try common keys that contain lists of problematic URLs/items
            for k in ("items", "pages", "urls", "examples", "instances"):
                if k in value and isinstance(value[k], list):
                    count = len(value[k])
                    examples = value[k][:3]
                    break
            if count == 0:
                # Fall back to top-level keys count
                count = len(value)
        elif isinstance(value, list):
            count = len(value)
            examples = value[:3]
        else:
            # Unknown shape — skip
            continue

        if count == 0:
            continue

        title = category.replace("_", " ").title()
        description = f"Found {count} {category.replace('_',' ')} issues."
        # if examples:
        #     # Keep examples short and human-friendly
        #     try:
        #         ex_str = ", ".join([str(x) for x in examples])
        #         description += f" Examples: {ex_str}"
        #     except Exception:
        #         pass

        priority = "high" if count > 50 else "medium" if count > 10 else "low"

        recs.append(
            SiteRecommendation(
                title=title,
                description=description,
                priority=priority
            )
        )

    return recs


@app.get("/api/sites/{site_url}/data", response_model=SiteDataResponse)
async def get_site_data(
    site_url: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive site data overview including:
    - Latest health scores (SEO, Core Web Vitals, performance, etc)
    - Latest recommendations/opportunities
    - Latest comparison report summary
    - Latest keyword rankings (mock data)
    
    Query params:
    - site_url: The website URL to get data for (e.g., "example.com")
    """
    
    # Normalize URL
    normalized_url = site_url.lower().strip()
    if not normalized_url.startswith(('http://', 'https://')):
        normalized_url = f"https://{normalized_url}"
    
    # Get latest audit for this site
    latest_audit = db.query(Audit).filter(
        Audit.user_id == current_user.id,
        Audit.url.ilike(f"%{site_url}%")
    ).order_by(Audit.created_at.desc()).first()
    
    if not latest_audit or not latest_audit.results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit found for {site_url}"
        )
    
    audit_results = latest_audit.results
    
    # Extract health scores
    health_overview = SiteHealthOverview(
        overall_score=audit_results.get("overall_score", 0),
        seo_score=audit_results.get("lighthouse", {}).get("categories", {}).get("seo", {}).get("score", 0),
        performance_score=audit_results.get("lighthouse", {}).get("categories", {}).get("performance", {}).get("score", 0),
        accessibility_score=audit_results.get("lighthouse", {}).get("categories", {}).get("accessibility", {}).get("score", 0),
        best_practices_score=audit_results.get("lighthouse", {}).get("categories", {}).get("best_practices", {}).get("score", 0),
        pwa_score=audit_results.get("lighthouse", {}).get("categories", {}).get("pwa", {}).get("score", 0),
        core_web_vitals=audit_results.get("lighthouse", {}).get("metrics", {}).get("coreWebVitals", {}),
        broken_links_count=audit_results.get("broken_links", {}).get("broken_count", 0),
        technical_seo=audit_results.get("technical_seo", {}),
        security={
            "https": audit_results.get("security", {}).get("https", False),
            "security_headers": audit_results.get("security", {}).get("security_headers", {})
        },
        content_quality={
            "score": audit_results.get("content_quality", {}).get("score", 0),
            "word_count": audit_results.get("content_quality", {}).get("word_count", 0),
            "reading_ease": audit_results.get("content_quality", {}).get("reading_ease_score", 0)
        }
    )
    
    # Extract recommendations and opportunities
    opportunities = audit_results.get("lighthouse", {}).get("opportunities", [])
    recommendations = []

    # Get latest crawl for this site
    latest_crawl = db.query(Crawl).filter(
        Crawl.user_id == current_user.id,
        Crawl.url.ilike(f"%{site_url}%")
    ).order_by(Crawl.created_at.desc()).first()

    crawl_summary = None
    if latest_crawl:
        crawl_summary = CrawlSummary(
            job_id=latest_crawl.job_id,
            pages_crawled=latest_crawl.pages_crawled,
            issues_found=latest_crawl.issues_found,
            completed_at=latest_crawl.completed_at,
            results_summary=(latest_crawl.results.get("summary") if latest_crawl.results else None),
            issues = (latest_crawl.results.get('issues') if latest_crawl.results else None)
        )    
        # Merge crawl-based recommendations
        try:
            crawl_recs = generate_recommendations_from_crawl(latest_crawl.results or {})
            if crawl_recs:
                # Append up to 5 crawl recommendations
                recommendations.extend(crawl_recs[:5])
        except Exception as e:
            logger.warning(f"Failed to generate crawl recommendations: {e}")
    
    for opp in opportunities[:5]:  # Top 5 opportunities
        recommendations.append(
            SiteRecommendation(
                title=opp.get("title", ""),
                description=opp.get("description", ""),
                savings_ms=round(opp.get("savings", {}).get("ms", 0)),
                priority="high" if opp.get("savings", {}).get("ms", 0) > 1000 else "medium"
            )
        )
    
    # Add content quality recommendations
    content_recs = audit_results.get("content_quality", {}).get("recommendations", [])
    for rec in content_recs[:3]:
        recommendations.append(
            SiteRecommendation(
                title="Content Quality",
                description=rec,
                priority="medium"
            )
        )
    
    
    # Get latest comparison report
    latest_comparison = db.query(Comparison).filter(
        Comparison.user_id == current_user.id,
        Comparison.target_url.ilike(f"%{site_url}%")
    ).order_by(Comparison.created_at.desc()).first()
    
    comparison_summary = None
    if latest_comparison and latest_comparison.results:
        comp_results = latest_comparison.results
        print(comp_results.get('overall_scores'))
        comparison_summary = ComparisonSummary(
            vs_competitors= comp_results.get('overall_scores').get('competitors', []),
            overall_scores = comp_results.get('overall_scores',{}),
            your_position="leader" if audit_results.get("overall_score", 0) >= 80 else "competitive" if audit_results.get("overall_score", 0) >= 60 else "needs_improvement",
            your_score=audit_results.get("overall_score", 0),
            average_competitor_score=comp_results.get("average_score", 0),
            key_advantages=comp_results.get("advantages", [])[:3],
            key_disadvantages=comp_results.get("disadvantages", [])[:3],
            comparison_date=latest_comparison.created_at.isoformat()
        )
    
    
    keywords  = db.query(TrackedKeyword).filter(
        TrackedKeyword.user_id == current_user.id,
        TrackedKeyword.is_active == True,
        TrackedKeyword.domain.ilike(f"%{site_url}%")).order_by(TrackedKeyword.created_at.desc()).all()

    keyword_rankings = [
        KeywordRanking(
            keyword = k.keyword,
            current_rank = k.current_position,
            previous_rank= k.previous_position,
            search_volume=4800,
            difficulty=62,
            trend="up" if k.position_change >= 0 else "down"
        ) for k in keywords
    ]
    
    logger.info(f"Fetched site data for {site_url} - User {current_user.id}")
    
    return SiteDataResponse(
        site_url=normalized_url,
        last_audit_date=latest_audit.created_at.isoformat(),
        health_overview=health_overview,
        recommendations=recommendations,
        comparison_summary=comparison_summary,
        top_keywords=keyword_rankings[:10],
        latest_crawl=crawl_summary
    )





# ──────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "AuditFlow API v2.0",
        "status": "online",
        "authenticated": True
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check with database connection test"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
        # users = db.query(User).all()
        # for user in users:
        #     print(f"User: {user.email}, Credits: {user.credits_remaining}")

    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)