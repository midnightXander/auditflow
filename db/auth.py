"""
Authentication - JWT tokens and Google OAuth integration
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
from dotenv import load_dotenv
import hashlib
from .database import get_db
from .models import User, RefreshToken, Activity, ActivityType

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTP Bearer scheme
security = HTTPBearer()


# ──────────────────────────────────────────────────────────────────────────────
# Password Utilities
# ──────────────────────────────────────────────────────────────────────────────

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash 
    """
    pre_hashed = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(pre_hashed, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password 
    """
    password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    return pwd_context.hash(password)


# ──────────────────────────────────────────────────────────────────────────────
# JWT Token Creation
# ──────────────────────────────────────────────────────────────────────────────

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Payload data (typically {"sub": user_id})
        expires_delta: Optional expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(user_id: int, db: Session) -> str:
    """
    Create JWT refresh token and store in database
    
    Args:
        user_id: User ID
        db: Database session
    
    Returns:
        Encoded JWT refresh token
    """
    expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # Store in database
    refresh_token = RefreshToken(
        user_id=user_id,
        token=encoded_jwt,
        expires_at=expire
    )
    db.add(refresh_token)
    db.commit()
    
    return encoded_jwt


# ──────────────────────────────────────────────────────────────────────────────
# Token Verification
# ──────────────────────────────────────────────────────────────────────────────

def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        token_type: "access" or "refresh"
    
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            return None
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            return None
        
        return payload
    except JWTError:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Google OAuth
# ──────────────────────────────────────────────────────────────────────────────

def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Google OAuth token
    
    Args:
        token: Google ID token
    
    Returns:
        User info from Google or None if invalid
    """
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return None
        
        return {
            "google_id": idinfo['sub'],
            "email": idinfo['email'],
            "name": idinfo.get('name'),
            "picture": idinfo.get('picture'),
            "email_verified": idinfo.get('email_verified', False),
        }
    except ValueError:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# User Authentication
# ──────────────────────────────────────────────────────────────────────────────

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate user with email/password
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
    
    Returns:
        User object if authenticated, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()
    print(user)
    
    if not user:
        print("no user")
        return None
    
    if not user.hashed_password:
        # Google OAuth user trying to login with password
        print("googe oAuth user")
        return None
    
    if not verify_password(password, user.hashed_password):
        print("failed pass verifiction")
        return None
    
    return user


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI Dependencies
# ──────────────────────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user
    
    Usage:
        @app.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise credentials_exception
    
    # Get user ID
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check for active status)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# ──────────────────────────────────────────────────────────────────────────────
# Optional Authentication (for routes that work with or without auth)
# ──────────────────────────────────────────────────────────────────────────────

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    
    Useful for routes that provide extra features for logged-in users
    but also work without authentication
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Credits Management
# ──────────────────────────────────────────────────────────────────────────────

def check_and_consume_credits(user: User, db: Session, credits_needed: int = 1) -> bool:
    """
    Check if user has enough credits and consume them
    
    Args:
        user: User object
        db: Database session
        credits_needed: Number of credits to consume
    
    Returns:
        True if credits consumed, False if insufficient
    """
    # add credits for the admin user
    if user.is_admin:
        return True
    # Reset credits if it's a new month
    if user.credits_reset_date and user.credits_reset_date < datetime.utcnow():
        # Reset credits based on plan
        plan_credits = {
            "free": 20,
            "pro": 1000,
            "agency": 10000,
        }
        user.credits_remaining = plan_credits.get(user.plan, 20)
        user.credits_reset_date = datetime.utcnow() + timedelta(days=30)
        db.commit()
    
    # Check credits
    if user.credits_remaining < credits_needed:
        return False
    
    # Consume credits
    user.credits_remaining -= credits_needed
    db.commit()
    
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Activity Logging
# ──────────────────────────────────────────────────────────────────────────────

def log_activity(
    db: Session,
    user_id: int,
    activity_type: ActivityType,
    activity_id: str,
    target: Optional[str] = None,
    status: str = "pending",
    summary: Optional[dict] = None
) -> Activity:
    """Log a new activity for a user"""
    activity = Activity(
        user_id=user_id,
        activity_type=activity_type.value,
        activity_id=activity_id,
        target=target,
        status=status,
        summary=summary
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity

def update_activity_status(
    db: Session,
    activity_id: int,
    status: str,
    summary: Optional[dict] = None
) -> Activity:
    """Update activity status and summary"""
    activity = db.query(Activity).filter(Activity.activity_id == activity_id).first()
    if activity:
        activity.status = status
        if summary:
            activity.summary = summary
        if status == "completed":
            activity.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(activity)
    return activity

def get_user_activity_history(
    db: Session,
    user_id: int,
    limit: int = 50,
    days: Optional[int] = None,
    activity_type: Optional[ActivityType] = None
) -> List[Activity]:
    """
    Get unified activity history for a user
    
    Args:
        db: Database session
        user_id: User ID
        limit: Max results
        days: Filter to last N days (optional)
        activity_type: Filter by type (optional)
    
    Returns:
        List of activities sorted by newest first
    """
    query = db.query(Activity).filter(Activity.user_id == user_id)
    
    # Filter by type if provided
    if activity_type:
        query = query.filter(Activity.activity_type == activity_type.value)
    
    # Filter by date range if provided
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Activity.created_at >= since)
    
    return query.order_by(desc(Activity.created_at)).limit(limit).all()

def get_activity_stats(
    db: Session,
    user_id: int,
    days: int = 30,
    current_month: bool = False
) -> dict:
    """Get activity statistics for a user"""
    since = datetime.utcnow() - timedelta(days=days)
    if current_month:
        since = since.replace(day=1)

    activities = db.query(Activity).filter(
        Activity.user_id == user_id,
        Activity.created_at >= since
    ).all()
    
    stats = {
        "total": len(activities),
        "completed": len([a for a in activities if a.status == "completed"]),
        "failed": len([a for a in activities if a.status == "failed"]),
        "by_type": {}
    }
    
    # Count by type
    for activity_type in ActivityType:
        count = len([a for a in activities if a.activity_type == activity_type.value])
        if count > 0:
            stats["by_type"][activity_type.value] = count
    
    return stats