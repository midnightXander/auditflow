from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any, List

class AuditRequest(BaseModel):
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com"
            }
        }


class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = 500
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "max_pages": 500
            }
        }


class ComparisonRequest(BaseModel):
    target_url: HttpUrl
    competitor_urls: List[HttpUrl]
    
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


class KeywordRequest(BaseModel):
    domain: str
    use_mock_data: Optional[bool] = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "use_mock_data": True
            }
        }


class BacklinkRequest(BaseModel):
    domain: str
    competitor_domains: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain": "example.com",
                "competitor_domains": ["competitor1.com", "competitor2.com"]
            }
        }


class AuditResponse(BaseModel):
    job_id: str
    status: str
    message: str


class AuditStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[int] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None