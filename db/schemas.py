"""
Pydantic Schemas - Request/Response models for API validation
"""

from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ──────────────────────────────────────────────────────────────────────────────
# Authentication Schemas
# ──────────────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Google OAuth token"""
    token: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    user_id: Optional[int] = None
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class UserResponse(BaseModel):
    """User profile response"""
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    plan: str
    credits_remaining: int
    agency_name: str
    agency_url: Optional[str]
    agency_logo: Optional[str]
    accent_color: Optional[str]
    created_at: datetime
    credits_reset_date: datetime
    is_admin: bool
    trial_started_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    trial_used: bool = False
    trial_plan: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Update user profile"""
    full_name: Optional[str] = None
    agency_name: Optional[str] = None
    agency_logo: Optional[str] = None
    agency_url: Optional[str] = None
    accent_color: Optional[str] = None
    plan: Optional[str] = None
    credits_remaining: Optional[int] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class NotificationItem(BaseModel):
    id: int
    type: str
    title: str
    message: Optional[str]
    meta: Optional[Dict[str, Any]]
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ──────────────────────────────────────────────────────────────────────────────
# Audit Schemas (updated with user_id)
# ──────────────────────────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    """Website audit request"""
    url: HttpUrl
    client_name: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com"
            }
        }


class AuditResponse(BaseModel):
    """Audit job created response"""
    job_id: str
    status: str
    message: str


class AuditStatus(BaseModel):
    """Audit status response"""
    job_id: str
    status: str
    progress: Optional[int] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Crawl Schemas
# ──────────────────────────────────────────────────────────────────────────────

class CrawlRequest(BaseModel):
    """Site crawl request"""
    url: HttpUrl
    client_name: Optional[str]
    max_pages: Optional[int] = 500
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "max_pages": 500
            }
        }


# ──────────────────────────────────────────────────────────────────────────────
# Comparison Schemas
# ──────────────────────────────────────────────────────────────────────────────

class ComparisonRequest(BaseModel):
    """Competitor comparison request"""
    target_url: HttpUrl
    competitor_urls: List[HttpUrl]
    client_name: str

    @field_validator('competitor_urls')
    @classmethod
    def max_competitors(cls, v):
        if len(v) > 3:
            raise ValueError('Maximum 3 competitors allowed')
        if len(v) < 1:
            raise ValueError('At least 1 competitor required')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_url": "https://example.com",
                "competitor_urls": [
                    "https://competitor1.com",
                    "https://competitor2.com"
                ]
            }
        }

class CreateComparisonRequest(BaseModel):
    target_url: str
    competitor_urls: List[str]
    client_name: Optional[str] = None
 
    @field_validator("competitor_urls")
    @classmethod
    def max_three(cls, v):
        if not v:
            raise ValueError("At least one competitor required")
        if len(v) > 3:
            raise ValueError("Maximum 3 competitors allowed")
        return v
 
 
class CreateComparisonResponse(BaseModel):
    job_id: str
    status: str
    message: str

# ──────────────────────────────────────────────────────────────────────────────
# Keyword Analysis Schemas
# ──────────────────────────────────────────────────────────────────────────────

class KeywordRequest(BaseModel):
    """Keyword analysis request"""
    domain: str
    use_mock_data: Optional[bool] = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "use_mock_data": True
            }
        }


# ──────────────────────────────────────────────────────────────────────────────
# Backlink Analysis Schemas
# ──────────────────────────────────────────────────────────────────────────────

class BacklinkRequest(BaseModel):
    """Backlink analysis request"""
    domain: str
    competitor_domains: Optional[List[str]] = None
    
    @field_validator('competitor_domains')
    @classmethod
    def max_competitors_backlinks(cls, v):
        if v and len(v) > 3:
            raise ValueError('Maximum 3 competitors allowed')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "competitor_domains": ["competitor1.com", "competitor2.com"]
            }
        }


# ──────────────────────────────────────────────────────────────────────────────
# Rank Tracking Request/Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class RankTrackingRequest(BaseModel):
    domain: str
    client_name: Optional[str] = None
    keywords: List[str]
    engines: List[str] = ['google']
    frequency: str = "daily"  # daily, weekly, monthly
    is_scheduled: bool = False
 
 
class RankTrackingResponse(BaseModel):
    job_id: str
    status: str
    message: str
 
 
# class RankTrackingStatus(BaseModel):
#     job_id: str
#     status: str
#     progress: Optional[int]
#     results: Optional[dict]
#     error: Optional[str]
#     next_check: Optional[datetime]

class RankTrackingKeywordInput(BaseModel):
    """Keyword to add to rank tracking"""
    keyword: str


class RankTrackingRequest(BaseModel):
    """Start new rank tracking job"""
    domain: str
    client_name: Optional[str] = None
    keywords: List[str]
    search_engines: Optional[List[str]] = None  # Default: ["brave", "google"]
    
    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least 1 keyword required')
        if len(v) > 100:
            raise ValueError('Maximum 100 keywords per rank tracking job')
        return v
    
    @field_validator('search_engines')
    @classmethod
    def validate_engines(cls, v):
        if v is None:
            return ["brave", "google"]
        valid = {"brave", "google", "bing"}
        for eng in v:
            if eng not in valid:
                raise ValueError(f'Invalid search engine: {eng}')
        return v if v else ["brave", "google"]
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "client_name": "Example Corp",
                "keywords": ["best seo tools", "website audit", "rank tracker"],
                "search_engines": ["brave", "google"]
            }
        }


class RankTrackingResponse(BaseModel):
    """Rank tracking job created response"""
    job_id: str
    status: str
    message: str


class RankTrackingResultItem(BaseModel):
    """Individual rank result for a keyword"""
    search_engine: str
    current_rank: Optional[int] = None
    previous_rank: Optional[int] = None
    rank_change: Optional[int] = None
    found: bool
    url: Optional[str] = None
    title: Optional[str] = None


class RankTrackingKeywordStatus(BaseModel):
    """Keyword with its latest rank results"""
    keyword: str
    results: Dict[str, RankTrackingResultItem]


class RankTrackingStatus(BaseModel):
    """Rank tracking job status"""
    job_id: str
    domain: str
    status: str
    progress: int
    engines : Optional[List] = None
    client_name: Optional[str] = None
    frequency: Optional[str] = None
    country: Optional[str] = None
    results: Optional[Dict] = None
    is_scheduled :  Optional[bool]
    total_keywords: Optional[int] = None
    keywords_found: Optional[int] = None
    avg_position: Optional[float] = None
    best_position: Optional[int] = None
    worst_position: Optional[int] = None
    next_check: Optional[datetime] = None
    last_checked: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    keywords: Optional[List[Dict]] = None


class RankTrackingListItem(BaseModel):
    """Rank tracking history item"""
    id: int
    job_id: str
    domain: str
    status: str
    client_name: Optional[str]
    total_keywords: Optional[int]
    keywords_found: Optional[int]
    avg_position: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class RankTrackingSummary(BaseModel):
    """Rank tracking summary for dashboard"""
    domain: str
    total_keywords: int
    keywords_found: int
    keywords_ranking: int  # Top 50
    avg_position: Optional[float]
    best_position: Optional[int]
    worst_position: Optional[int]
    best_performing: List[str]  # Top 3 keywords
    worst_performing: List[str]  # Bottom 3 keywords

class KeywordIn(BaseModel):
    keyword: str
    search_volume: Optional[int] = None
    difficulty: Optional[float] = None
    group_name: Optional[str] = None
    tags: Optional[List[str]] = None
 
 
class CreateTrackingRequest(BaseModel):
    domain: str
    name: Optional[str] = None
    keywords: List[KeywordIn]
    engines: List[str] = ["google"]
    country: str = "us"
    frequency: str = "daily"
    is_scheduled: bool = False
 
 
class CreateTrackingResponse(BaseModel):
    job_id: str
    status: str
    message: str


# ──────────────────────────────────────────────────────────────────────────────
# History/List Schemas
# ──────────────────────────────────────────────────────────────────────────────

class AuditListItem(BaseModel):
    """Audit history item"""
    id: int
    job_id: str
    url: str
    status: str
    overall_score: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class CrawlListItem(BaseModel):
    """Crawl history item"""
    id: int
    job_id: str
    url: str
    status: str
    pages_crawled: Optional[int]
    issues_found: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ActivityListItem(BaseModel):
    """Activity history item"""
    id: int
    job_id: str
    url: str
    status: str
    type: str
    title: Optional[str]
    description: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    """Paginated list response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    metadata : Optional[Dict] = None

# ──────────────────────────────────────────────────────────────────────────────
# Site data Schemas
# ──────────────────────────────────────────────────────────────────────────────
class CrawlSummary(BaseModel):
    job_id: str
    issues: Optional[Dict[str, Any]] = None
    pages_crawled: Optional[int]
    issues_found: Optional[int]
    completed_at: Optional[datetime]
    results_summary: Optional[Dict[str, Any]] = None


class CoreWebVital(BaseModel):
    name: str
    displayValue: str
    score: float
    rating: str

class SiteHealthOverview(BaseModel):
    overall_score: float
    seo_score: float
    performance_score: float
    accessibility_score: float
    best_practices_score: float
    pwa_score: float
    core_web_vitals: Dict[str, Any]
    broken_links_count: int
    technical_seo: Dict[str, Any]
    security: Dict[str, Any]
    content_quality: Dict[str, Any]

class SiteRecommendation(BaseModel):
    title: str
    description: str
    savings_ms: Optional[int] = None
    priority: str = "medium"  # high, medium, low

class KeywordRanking(BaseModel):
    keyword: str
    current_rank: int
    previous_rank: int
    search_volume: int
    difficulty: int
    trend: str  # up, down, stable

class ComparisonSummary(BaseModel):
    vs_competitors: List[Any]
    your_position: str  # leader, competitive, needs_improvement
    your_score: float
    overall_scores: Dict[str, Any]
    average_competitor_score: float
    key_advantages: List[str]
    key_disadvantages: List[str]
    comparison_date: str

class SiteDataResponse(BaseModel):
    site_url: str
    last_audit_date: str
    health_overview: SiteHealthOverview
    recommendations: List[SiteRecommendation]
    comparison_summary: Optional[ComparisonSummary] = None
    top_keywords: List[KeywordRanking]
    latest_crawl: Optional[CrawlSummary] = None
