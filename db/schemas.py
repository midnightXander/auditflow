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
    created_at: datetime
    credits_reset_date: datetime
    is_admin: bool

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
    client_name: str
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