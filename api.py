"""
Authenticated API - Complete FastAPI server with JWT auth, Google OAuth, and database
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta

# Database and models
from db.database import get_db, init_db
from db.models import ActivityType, User, Audit, Crawl, Comparison, KeywordAnalysis, BacklinkAnalysis, RefreshToken

# Authentication
from db.auth import (
    get_current_user, get_current_user_optional, check_and_consume_credits,
    authenticate_user, create_access_token, create_refresh_token, get_user_activity_history, log_activity, update_activity_status,
    verify_google_token, verify_token, get_password_hash, get_activity_stats,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Schemas
from db.schemas import (
    ActivityListItem, UserRegister, UserLogin, GoogleAuthRequest, TokenResponse, RefreshTokenRequest,
    UserResponse, UserUpdate,
    AuditRequest, AuditResponse, AuditStatus, CrawlRequest,
    ComparisonRequest, KeywordRequest, BacklinkRequest,
    AuditListItem, PaginatedResponse
)

# Audit engines
from auditor import WebsiteAuditor
from apps.crawler import crawl_website
from apps.competitor import compare_competitors
from apps.keywords import analyze_keywords
from apps.backlinks import analyze_backlinks, find_competitor_gaps

from tasks import run_audit_task, run_crawl_task, run_comparison_task, run_keyword_analysis_task

#routes
from db.admin_routes import router as admin_router

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AuditFlow API",
    description="Complete SEO audit platform with authentication",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://auditflow-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()


# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
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
    return current_user


@app.patch("/api/auth/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
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
    
    audits = query.order_by(Audit.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return PaginatedResponse(
        items=[AuditListItem.model_validate(a) for a in audits],
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


@app.post("/api/compare", response_model=AuditResponse)
async def create_compare(
    request: ComparisonRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start deep comparison (requires 2 credits)"""

    print(request)
    print(current_user)
    print("Checking credits...")

    if not check_and_consume_credits(current_user, db, credits_needed=2):
        raise HTTPException(status_code=402, detail="Insufficient credits")

    target_url = str(request.target_url)
    competitor_urls = [str(url) for url in request.competitor_urls[:3]]  # Max 3 competitors
    job_id = str(uuid.uuid4())
    compare = Comparison(
        job_id=job_id,
        user_id=current_user.id,
        target_url=target_url,
        competitor_urls=competitor_urls,
        status="pending"
    )
    db.add(compare)
    db.commit()

    log_activity(
        db,
        user_id=current_user.id,
        activity_type=ActivityType.COMPARISON,
        activity_id=job_id,
        target=target_url,
        status="pending"
    )

    # TODO: Add background task
    background_tasks.add_task(run_comparison_task, job_id, target_url, competitor_urls, current_user.id, db)

    return AuditResponse(job_id=job_id, status="pending", message="Comparison started")

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