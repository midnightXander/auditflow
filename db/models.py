"""
Database Models - SQLAlchemy ORM models for users and audit data
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Null for Google OAuth users
    full_name = Column(String(255), nullable=True)
    
    # Authentication
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # White-label settings
    agency_name = Column(String(255), default="AuditSE")
    agency_logo = Column(Text, nullable=True)  # Base64 or URL
    agency_url = Column(String(500), nullable=True)
    accent_color = Column(String(7), default="#0075FF")
    
    # Subscription / Usage
    plan = Column(String(50), default="free")  # free, pro, agency
    credits_remaining = Column(Integer, default=10)  # Monthly audit credits
    credits_reset_date = Column(DateTime, nullable=True)

    # Stripe
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    audits = relationship("Audit", back_populates="user", cascade="all, delete-orphan")
    crawls = relationship("Crawl", back_populates="user", cascade="all, delete-orphan")
    comparisons = relationship("Comparison", back_populates="user", cascade="all, delete-orphan")
    keyword_analyses = relationship("KeywordAnalysis", back_populates="user", cascade="all, delete-orphan")
    backlink_analyses = relationship("BacklinkAnalysis", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")


class Audit(Base):
    """Website audit results"""
    __tablename__ = "audits"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    url = Column(String(500), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)
    
    # Results
    overall_score = Column(Integer, nullable=True)
    results = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="audits")


class Crawl(Base):
    """Deep site crawl results"""
    __tablename__ = "crawls"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    url = Column(String(500), nullable=False)
    max_pages = Column(Integer, default=500)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    
    # Summary stats
    pages_crawled = Column(Integer, nullable=True)
    issues_found = Column(Integer, nullable=True)
    
    # Results
    results = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="crawls")


class Comparison(Base):
    """Competitor comparison results"""
    __tablename__ = "comparisons"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    target_url = Column(String(500), nullable=False)
    competitor_urls = Column(JSON, nullable=False)  # List of URLs
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    
    # Results
    results = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="comparisons")


class KeywordAnalysis(Base):
    """Keyword opportunity analysis"""
    __tablename__ = "keyword_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    domain = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    
    # Summary
    total_opportunities = Column(Integer, nullable=True)
    estimated_traffic_gain = Column(Integer, nullable=True)
    
    # Results
    results = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="keyword_analyses")


class BacklinkAnalysis(Base):
    """Backlink analysis results"""
    __tablename__ = "backlink_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    domain = Column(String(255), nullable=False)
    competitor_domains = Column(JSON, nullable=True)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    
    # Summary
    total_backlinks = Column(Integer, nullable=True)
    toxic_count = Column(Integer, nullable=True)
    avg_quality_score = Column(Float, nullable=True)
    
    # Results
    results = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="backlink_analyses")


class RefreshToken(Base):
    """Refresh tokens for JWT authentication"""
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

from enum import Enum

class ActivityType(str, Enum):
    """Activity types for user history"""
    AUDIT = "audit"
    CRAWL = "crawl"
    COMPARISON = "comparison"
    KEYWORD_ANALYSIS = "keyword_analysis"
    BACKLINK_ANALYSIS = "backlink_analysis"


class Activity(Base):
    """Unified activity log for all user operations"""
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Activity metadata
    activity_type = Column(String(50), nullable=False, index=True)  # enum value
    activity_id = Column(String(36), nullable=False)  # job_id or analysis_id
    
    # What was analyzed
    target = Column(String(500), nullable=True)  # URL or domain
    
    # Status tracking
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    
    # Summary (denormalized for fast queries)
    summary = Column(JSON, nullable=True)  # {'score': 85, 'issues': 10} or relevant data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="activities")


class VerificationToken(Base):
    """Email verification tokens"""
    __tablename__ = "verification_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
 
 
class PasswordResetToken(Base):
    """Password reset tokens"""
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)