"""
Admin Routes - Dashboard and user management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from datetime import datetime, timedelta

from .database import get_db
from .models import User, Audit, Crawl, Comparison
from .auth import get_current_user
from .schemas import UserResponse, UserUpdate

from db.migrations import check_migration_status


router = APIRouter(prefix="/api/admin", tags=["admin"])


async def get_admin_user(current_user: User = Depends(get_current_user)):
    """Require admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.post("/add-admin")
async def add_admin_user(
    email: str,
    # current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a user as admin"""
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_admin = True
        db.commit()
        db.refresh(user)
        return UserResponse.model_validate(user)
    else:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/stats")
async def get_admin_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get platform statistics"""
    
    # User stats
    total_users = db.query(User).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    free_users = db.query(User).filter(User.plan == 'free').count()
    pro_users = db.query(User).filter(User.plan == 'pro').count()
    agency_users = db.query(User).filter(User.plan == 'agency').count()
    
    # Activity stats (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    recent_users = db.query(User).filter(
        User.created_at >= thirty_days_ago
    ).count()
    
    total_audits = db.query(Audit).count()
    recent_audits = db.query(Audit).filter(
        Audit.created_at >= thirty_days_ago
    ).count()
    
    total_crawls = db.query(Crawl).count()
    total_comparisons = db.query(Comparison).count()
    
    # Revenue (simplified - actual would come from Stripe)
    mrr = (pro_users * 29) + (agency_users * 199)
    
    return {
        "users": {
            "total": total_users,
            "verified": verified_users,
            "new_this_month": recent_users,
            "by_plan": {
                "free": free_users,
                "pro": pro_users,
                "agency": agency_users
            }
        },
        "audits": {
            "total": total_audits,
            "this_month": recent_audits
        },
        "features": {
            "crawls": total_crawls,
            "comparisons": total_comparisons
        },
        "revenue": {
            "mrr": mrr
        }
    }


@router.get("/users")
async def list_all_users(
    page: int = 1,
    page_size: int = 50,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    
    query = db.query(User).order_by(desc(User.created_at))
    total = query.count()
    
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "users": [UserResponse.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.patch("/users/{user_id}")
async def update_user_admin(
    user_id: int,
    request: UserUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    print(user_id, request.plan, request.credits_remaining, request.is_active, request.is_admin)
    if request.plan is not None:
        user.plan = request.plan
    if request.credits_remaining is not None:
        user.credits_remaining = request.credits_remaining
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.is_admin is not None:
        user.is_admin = request.is_admin

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete admin users"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user_id} deleted"}


@router.get("/activity")
async def get_recent_activity(
    limit: int = 100,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get recent platform activity"""
    
    recent_audits = db.query(Audit)\
        .join(User)\
        .order_by(desc(Audit.created_at))\
        .limit(limit)\
        .all()
    
    activity = []
    for audit in recent_audits:
        activity.append({
            "type": "audit",
            "user_email": audit.user.email,
            "url": audit.url,
            "status": audit.status,
            "score": audit.overall_score,
            "created_at": audit.created_at
        })
    
    return {"activity": activity}

@router.get("/migrations/status")
async def get_migration_status(admin_user: User = Depends(get_current_user)):
    """Get current database migration status (admin only)"""
    if not admin_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return check_migration_status()