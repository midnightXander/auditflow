"""
Database Models - SQLAlchemy ORM models for users and audit data
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Table
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

tracking_keywords = Table(
    "tracking_keywords",
    Base.metadata,
    Column("tracking_id", Integer, ForeignKey("rank_trackings.id"), primary_key=True),
    Column("keyword_id",  Integer, ForeignKey("tracked_keywords.id"), primary_key=True),
)
 

class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Null for Google OAuth users
    full_name = Column(String(255), nullable=True)
    avatar = Column(Text, nullable=True)  # Base64 or URL
    
    # Authentication
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # White-label settings
    agency_name = Column(String(255), default="MY AGENCY")
    agency_logo = Column(Text, nullable=True)  # Base64 or URL
    agency_url = Column(String(500), nullable=True)
    accent_color = Column(String(7), default="#00a4c6")
    
    # Subscription / Usage
    plan = Column(String(50), default="free")  # free, pro, agency
    credits_remaining = Column(Integer, default=20)  # Monthly audit credits
    credits_reset_date = Column(DateTime, nullable=True)

    # Stripe
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)

    # Whop Payment Integration
    whop_subscription_id = Column(String(255), unique=True, nullable=True, index=True)
    whop_product_id = Column(String(255), nullable=True)  # Product ID: pro or agency
    subscription_status = Column(String(50), default="inactive")  # active, cancelled, expired
    subscription_started_at = Column(DateTime, nullable=True)
    subscription_renews_at = Column(DateTime, nullable=True)
    whop_metadata = Column(JSON, nullable=True)  # Store any additional Whop data

    # Free Trial Management (14-day Pro trial)
    trial_started_at = Column(DateTime, nullable=True)  # When trial began
    trial_ends_at = Column(DateTime, nullable=True)  # When trial expires (14 days from start)
    trial_used = Column(Boolean, default=False)  # Has user already used their trial?
    trial_plan = Column(String(50), nullable=True)  # "pro" - the only plan with trial
    trial_email_sent_start = Column(Boolean, default=False)  # Trial start email sent
    trial_email_sent_day3 = Column(Boolean, default=False)  # Day 3 reminder sent
    trial_email_sent_day10 = Column(Boolean, default=False)  # Day 10 reminder sent
    trial_email_sent_expiring_soon = Column(Boolean, default=False)  # Expiring soon (day 13) sent

    # Embed Widget
    embed_api_key = Column(String(255), unique=True, nullable=True, index=True)
    embed_enabled = Column(Boolean, default=False)
    embed_lead_capture = Column(Boolean, default=True)
    embed_require_email = Column(Boolean, default=True)
    embed_button_text = Column(String(100), default="Analyze Website")
    embed_headline = Column(String(200), default="Free Website SEO Audit")
    embed_description = Column(Text, default="Get a comprehensive SEO analysis in seconds")
    embed_primary_color = Column(String(200), default="#00a4c6")
    embed_bg_color = Column(String(200), default="#ffffff")
    embed_text_color = Column(String(200), default="#141e27")
    embed_border_radius =  Column(Integer, default = 8)
    embed_show_logo = Column(Boolean, default=True)
    embed_show_poweredBy = Column(Boolean, default=True)
    embed_email_placeholder = Column(String(200), default="Enter your email")
    embed_width = Column(String(100), default="100%")
    embed_shadow = Column(Boolean, default=True)
    
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
    rank_trackings     = relationship("RankTracking",    back_populates="user", cascade="all, delete-orphan")
    tracked_keywords   = relationship("TrackedKeyword",  back_populates="user", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Notification(Base):
    """In-app notifications for users"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    type = Column(String(100), nullable=False)  # e.g., audit, billing, system
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    read = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="notifications")

class Audit(Base):
    """Website audit results"""
    __tablename__ = "audits"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    url = Column(String(500), nullable=False)
    client_name = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)
    
    # Results
    overall_score = Column(Integer, nullable=True)
    results = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Embed tracking
    is_embedded = Column(Boolean, default=False)
    embed_email = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="audits")

class AnonymousAudit(Base):
    """
    A combined audit + crawl run by an unauthenticated visitor.
    Identified by a session_token stored in the browser.
    Claimed to a real user on signup and expires after 24 hours if unclaimed.
    """
    __tablename__ = "anonymous_audits"
 
    id            = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(64), unique=True, index=True, nullable=False)
 
    url    = Column(String(500), nullable=False)
    status = Column(String(20), default="pending")  # pending | running | completed | failed
    progress   = Column(Integer, default=0)
    stage      = Column(String(50), default="audit")  # audit | crawl | done
    stage_label = Column(String(100), default="Starting…")
 
    # Audit results
    audit_score   = Column(Integer, nullable=True)
    audit_results = Column(JSON, nullable=True)
 
    # Crawl results (50-page crawl)
    crawl_results = Column(JSON, nullable=True)
    pages_crawled = Column(Integer, nullable=True)
 
    # Claimed by a real user on signup
    claimed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    claimed_at         = Column(DateTime, nullable=True)
 
    error      = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)  # created_at + 24h


class EmbedLead(Base):
    """Leads captured from embedded widgets"""
    __tablename__ = "embed_leads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Agency owner
    
    full_name = Column(String(255), nullable=True, index=True) 
    email = Column(String(255), nullable=False, index=True)
    website = Column(String(500), nullable=True)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=True)
    
    # Lead source tracking
    source = Column(String(100), default="embed_widget")
    referrer = Column(String(500), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Lead status
    status = Column(String(50), default="new")  # new, contacted, converted, lost
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User")
    audit = relationship("Audit")


class Crawl(Base):
    """Deep site crawl results"""
    __tablename__ = "crawls"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    url = Column(String(500), nullable=False)
    client_name = Column(String(255), nullable=True)
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
    client_name = Column(String(255), nullable=True)
    competitor_urls = Column(JSON, nullable=False)  # List of URLs
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)

    # Denormalised snapshot (filled once results are ready) — avoids parsing
    # the full `results` JSON blob just to render KPI cards / list cards.
    target_score = Column(Integer, nullable=True)
    best_competitor_score = Column(Integer, nullable=True)
    best_competitor_url = Column(String(500), nullable=True)
    worst_competitor_score = Column(Integer, nullable=True)
    avg_competitor_score = Column(Float, nullable=True)
    score_gap = Column(Integer, nullable=True)  # target_score - best_competitor_score
    
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

class RankTracking(Base):
    """Rank tracking jobs for keyword monitoring"""
    __tablename__ = "rank_trackings"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    
    # Tracking target
    domain = Column(String(255), nullable=False, index=True)
    client_name = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)

    keywords = Column(JSON, nullable=True)  # List of keywords to track
    
    # Search engines to track
    engines = Column(JSON, nullable=False)  # ["brave", "google", "bing"]
    
    # Status
    status = Column(String(20), default="pending", index=True)  # pending, running, completed, failed
    progress = Column(Integer, default=0)
    
    # Results summary
    total_keywords = Column(Integer, nullable=True)
    keywords_found = Column(Integer, nullable=True)
    avg_position = Column(Float, nullable=True)
    best_position = Column(Integer, nullable=True)
    worst_position = Column(Integer, nullable=True)

    # Schedule
    frequency = Column(String(20), default="daily")  # daily, weekly, monthly
    is_scheduled = Column(Boolean, default=False)
    next_check = Column(DateTime, nullable=True)
    
    # Full results
    results = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    last_checked = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="rank_trackings")
    history = relationship("RankHistory", back_populates="tracking", cascade="all, delete-orphan")
    keywords_rel = relationship("TrackedKeyword", secondary=tracking_keywords,
                                back_populates="trackings")
    # keywords = relationship("RankTrackingKeyword", back_populates="rank_tracking", cascade="all, delete-orphan")

class RankHistory(Base):
    """Historical rank tracking data points"""
    __tablename__ = "rank_history"
    
    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(Integer, ForeignKey("rank_trackings.id"), nullable=False)
    
    keyword = Column(String(500), nullable=False, index=True)
    engine = Column(String(50), nullable=False)
    position = Column(Integer, nullable=True)  # Null if not found
    url = Column(String(1000), nullable=True)
    title = Column(String(500), nullable=True)
    
    # Change from previous check
    previous_position = Column(Integer, nullable=True)
    position_change = Column(Integer, nullable=True)  # Positive = improved
    
    # Timestamp
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    tracking = relationship("RankTracking", back_populates="history")
    # keywords_rel = relationship("TrackedKeyword", secondary=tracking_keywords,
    #                             back_populates="trackings")


class TrackedKeyword(Base):
    """
    A single keyword the user wants to track across one or more RankTracking
    campaigns.  Metadata (volume, difficulty, tags) lives here so it doesn't
    repeat in every history row.
    """
    __tablename__ = "tracked_keywords"
 
    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
 
    keyword    = Column(String(500), nullable=False, index=True)
    domain     = Column(String(255), nullable=False, index=True)
    engine     = Column(String(50),  default="google")   # google | bing | duckduckgo
    country    = Column(String(10),  default="us")        # ISO-2
    group_name = Column(String(100), nullable=True)       # e.g. "Brand", "Competitor"
    tags       = Column(JSON, nullable=True)              # ["seo", "brand"]
 
    # Enrichment (can come from a keyword API or manual entry)
    search_volume = Column(Integer, nullable=True)
    difficulty    = Column(Float,   nullable=True)   # 0-100
 
    # Denormalised "latest snapshot" for fast table queries
    current_position  = Column(Integer, nullable=True)
    previous_position = Column(Integer, nullable=True)
    position_change   = Column(Integer, nullable=True)   # positive = improved
    best_position     = Column(Integer, nullable=True)
    landing_url       = Column(String(1000), nullable=True)
    last_checked_at   = Column(DateTime, nullable=True)
 
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
 
    # Relationships
    user     = relationship("User", back_populates="tracked_keywords")
    history  = relationship("KeywordHistory", back_populates="keyword_obj",
                            cascade="all, delete-orphan", order_by="KeywordHistory.checked_at")
    trackings = relationship("RankTracking", secondary=tracking_keywords,
                             back_populates="keywords_rel")

# ── Keyword History ───────────────────────────────────────────────────────────
 
class KeywordHistory(Base):
    """One data-point per keyword per check run."""
    __tablename__ = "keyword_history"
 
    id         = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("tracked_keywords.id"), nullable=False)
 
    position          = Column(Integer, nullable=True)
    previous_position = Column(Integer, nullable=True)
    position_change   = Column(Integer, nullable=True)
    landing_url       = Column(String(1000), nullable=True)
    title             = Column(String(500),  nullable=True)
    engine            = Column(String(50),   nullable=False)
    checked_at        = Column(DateTime, default=datetime.utcnow, index=True)
 
    keyword_obj = relationship("TrackedKeyword", back_populates="history")

class RankTrackingKeyword(Base):
    """Keywords being tracked for a rank tracking job"""
    __tablename__ = "rank_tracking_keywords"
    
    id = Column(Integer, primary_key=True, index=True) 
    rank_tracking_id = Column(Integer, ForeignKey("rank_trackings.id"), nullable=False, index=True)
    
    # Keyword data
    keyword = Column(String(255), nullable=False, index=True)
    is_tracked = Column(Boolean, default=True, index=True)
    
    # Timestamps
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    # rank_tracking = relationship("RankTracking", back_populates="keywords")
    results = relationship("RankTrackingResult", back_populates="keyword", cascade="all, delete-orphan")


class RankTrackingResult(Base):
    """Individual rank check results for a keyword across search engines"""
    __tablename__ = "rank_tracking_results"
    
    id = Column(Integer, primary_key=True, index=True)
    rank_tracking_keyword_id = Column(Integer, ForeignKey("rank_tracking_keywords.id"), nullable=False, index=True)
    
    # Search engine and result
    search_engine = Column(String(50), nullable=False, index=True)  # brave, google, bing
    current_rank = Column(Integer, nullable=True)  # Position or null if not found
    previous_rank = Column(Integer, nullable=True)  # For trend tracking
    rank_change = Column(Integer, nullable=True)  # +/- from previous rank
    found = Column(Boolean, default=False, index=True)
    
    # Result details
    url = Column(String(500), nullable=True)
    title = Column(String(500), nullable=True)
    
    # Timestamps
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    keyword = relationship("RankTrackingKeyword", back_populates="results")

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
    RANK_TRACKING = "rank_tracking"


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


class Visitor(Base):
    """Track landing page visitors for conversion analysis"""
    __tablename__ = "visitors"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Visitor info
    ip_address = Column(String(45), nullable=False, index=True)  # IPv4 or IPv6
    country = Column(String(100), nullable=True, index=True)
    country_code = Column(String(2), nullable=True, index=True)  # ISO 3166-1 alpha-2
    city = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # User agent info
    user_agent = Column(Text, nullable=True)
    referer = Column(String(500), nullable=True)
    
    # Page info
    page_url = Column(String(500), nullable=True)
    
    # Timestamps
    visited_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Optional: link to user if they later convert
    converted = Column(Boolean, default=False, index=True)
    converted_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    def __repr__(self):
        return f"<Visitor ip={self.ip_address} country={self.country} visited={self.visited_at}>"