"""
Integration example: Rank Tracker with FastAPI backend

This file shows how to integrate the rank tracking engine into your existing
FastAPI API for the website auditor tool.

Add these endpoints to your api.py file.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime

from backend.apps.rank_tracker_sample import (
    RankTracker,
    SearchEngine,
    RankRecord,
    RankAlert,
    RankDatabase,
)


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Models for API
# ──────────────────────────────────────────────────────────────────────────────

class TrackingRequest(BaseModel):
    """Request to start rank tracking"""
    domain: str
    keywords: List[str]
    search_engines: Optional[List[str]] = ["google"]
    proxies: Optional[List[str]] = None
    min_delay: float = 2.0
    max_delay: float = 5.0


class RankCheckResponse(BaseModel):
    """Response from rank check"""
    keyword: str
    domain: str
    search_engine: str
    position: Optional[int]
    url: Optional[str]
    title: Optional[str]
    snippet: Optional[str]
    timestamp: str


class RankAlertResponse(BaseModel):
    """Alert response"""
    keyword: str
    domain: str
    search_engine: str
    previous_position: Optional[int]
    current_position: Optional[int]
    change: int
    alert_level: str
    timestamp: str


class TrackingResultsResponse(BaseModel):
    """Results from tracking session"""
    domain: str
    timestamp: str
    records: List[RankCheckResponse]
    alerts: List[RankAlertResponse]
    summary: Dict[str, Any]


class RankHistoryResponse(BaseModel):
    """Historical ranking data"""
    keyword: str
    search_engine: str
    domain: str
    data: List[Dict[str, Any]]


class TrendAnalysisResponse(BaseModel):
    """Trend analysis"""
    keyword: str
    search_engine: str
    trend: str
    first_position: Optional[int]
    last_position: Optional[int]
    best_position: int
    worst_position: int
    average_position: float
    data_points: int


# ──────────────────────────────────────────────────────────────────────────────
# Async tracking status storage (in production, use Redis or database)
# ──────────────────────────────────────────────────────────────────────────────

tracking_jobs = {}  # job_id -> {status, progress, results}


# ──────────────────────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/rank-tracker", tags=["rank-tracking"])


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/check")
async def check_ranks(
    request: TrackingRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Check keyword rankings (runs in background)
    
    Returns:
        - job_id: ID to check status/results
        - status: "processing"
    """
    import uuid
    job_id = str(uuid.uuid4())
    
    # Store job
    tracking_jobs[job_id] = {
        "status": "processing",
        "progress": 0,
        "results": None,
        "error": None,
    }
    
    # Run in background
    background_tasks.add_task(
        _run_tracking_job,
        job_id,
        request
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Started tracking {len(request.keywords)} keywords"
    }


async def _run_tracking_job(job_id: str, request: TrackingRequest):
    """Background task to run tracking"""
    try:
        engines = [SearchEngine(e) for e in request.search_engines]
        
        async def progress_callback(progress: int, status: str):
            tracking_jobs[job_id]["progress"] = progress
            tracking_jobs[job_id]["status"] = status
        
        async with RankTracker(
            domain=request.domain,
            keywords=request.keywords,
            search_engines=engines,
            proxies=request.proxies,
            min_delay=request.min_delay,
            max_delay=request.max_delay,
        ) as tracker:
            results = await tracker.check_all_keywords(progress_callback)
            
            tracking_jobs[job_id]["results"] = results
            tracking_jobs[job_id]["status"] = "completed"
            tracking_jobs[job_id]["progress"] = 100
    
    except Exception as e:
        tracking_jobs[job_id]["status"] = "failed"
        tracking_jobs[job_id]["error"] = str(e)


@router.get("/check/{job_id}")
async def get_check_status(job_id: str) -> Dict[str, Any]:
    """
    Get status and results of tracking job
    
    Returns:
        - status: "processing", "completed", or "failed"
        - progress: 0-100
        - results: Full tracking results (if completed)
        - error: Error message (if failed)
    """
    if job_id not in tracking_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = tracking_jobs[job_id]
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "results": job["results"],
        "error": job["error"],
    }


@router.post("/check-sync")
async def check_ranks_sync(request: TrackingRequest) -> TrackingResultsResponse:
    """
    Check keyword rankings (synchronous - blocks until complete)
    
    ⚠️ Warning: This will block the API for the duration of the check.
    For better performance, use the async /check endpoint.
    """
    engines = [SearchEngine(e) for e in request.search_engines]
    
    async with RankTracker(
        domain=request.domain,
        keywords=request.keywords,
        search_engines=engines,
        proxies=request.proxies,
        min_delay=request.min_delay,
        max_delay=request.max_delay,
    ) as tracker:
        results = await tracker.check_all_keywords()
        
        return TrackingResultsResponse(
            domain=results["domain"],
            timestamp=results["timestamp"],
            records=[RankCheckResponse(**r) for r in results["records"]],
            alerts=[RankAlertResponse(**a) for a in results["alerts"]],
            summary=results["summary"],
        )


@router.get("/history/{domain}/{keyword}")
async def get_ranking_history(
    domain: str,
    keyword: str,
    search_engine: str = "google",
    days: int = 30,
) -> RankHistoryResponse:
    """
    Get historical ranking data for a keyword
    
    Returns:
        - keyword: The keyword
        - search_engine: google, bing, or duckduckgo
        - data: List of {date, position, url, title}
    """
    db = RankDatabase()
    
    try:
        engine = SearchEngine(search_engine)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid search engine: {search_engine}")
    
    async with RankTracker(domain, [keyword]) as tracker:
        chart = tracker.get_ranking_chart(keyword, engine, days)
    
    return RankHistoryResponse(
        keyword=chart["keyword"],
        search_engine=chart["search_engine"],
        domain=chart["domain"],
        data=chart["data"],
    )


@router.get("/trend/{domain}/{keyword}")
async def get_trend_analysis(
    domain: str,
    keyword: str,
    search_engine: str = "google",
    days: int = 30,
) -> TrendAnalysisResponse:
    """
    Get trend analysis for a keyword
    
    Returns:
        - trend: improving, declining, stable, or dropped_out
        - first_position: Position at start of period
        - last_position: Position at end of period
        - best_position: Best position in period
        - average_position: Average ranking position
    """
    try:
        engine = SearchEngine(search_engine)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid search engine: {search_engine}")
    
    async with RankTracker(domain, [keyword]) as tracker:
        trend = tracker.get_trend_analysis(keyword, engine, days)
    
    return TrendAnalysisResponse(**trend)


@router.get("/alerts/{domain}")
async def get_alerts(domain: str, limit: int = 50) -> Dict[str, Any]:
    """
    Get recent rank change alerts
    
    Returns list of alerts with:
        - keyword: The keyword that changed
        - previous_position: Old position
        - current_position: New position
        - change: Position change (+/-)
        - alert_level: critical, warning, or info
    """
    db = RankDatabase()
    alerts = db.get_alerts(domain, limit)
    
    return {
        "domain": domain,
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


@router.get("/summary/{domain}")
async def get_domain_summary(domain: str) -> Dict[str, Any]:
    """
    Get ranking summary for domain
    
    Returns:
        - total_keywords: Total tracked keywords
        - top_10_count: Keywords ranking in top 10
        - top_50_count: Keywords ranking in top 50
        - unranked_count: Keywords not in top 100
        - recent_alerts: Recent rank changes
    """
    db = RankDatabase()
    alerts = db.get_alerts(domain, 10)
    
    # Count rankings (you'd expand this with actual counts from DB)
    total_keywords = len(alerts) if alerts else 0
    top_10 = sum(1 for a in alerts if a.current_position and a.current_position <= 10)
    top_50 = sum(1 for a in alerts if a.current_position and a.current_position <= 50)
    unranked = sum(1 for a in alerts if a.current_position is None)
    
    return {
        "domain": domain,
        "summary": {
            "total_keywords": total_keywords,
            "top_10_count": top_10,
            "top_50_count": top_50,
            "unranked_count": unranked,
        },
        "recent_alerts": [a.to_dict() for a in alerts[:5]],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Integration into main API
# ──────────────────────────────────────────────────────────────────────────────

# Add this to your main api.py file:
"""
from fastapi import FastAPI
from rank_tracker_api import router as rank_tracker_router

app = FastAPI()

# Include rank tracker routes
app.include_router(rank_tracker_router)
"""


# ──────────────────────────────────────────────────────────────────────────────
# Usage Examples
# ──────────────────────────────────────────────────────────────────────────────

"""
CURL EXAMPLES:

1. Start async rank check:
curl -X POST http://localhost:8000/api/rank-tracker/check \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "keywords": ["seo tools", "rank tracking"],
    "search_engines": ["google", "bing"],
    "min_delay": 2.0,
    "max_delay": 5.0
  }'

Response:
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Started tracking 2 keywords"
}

2. Get job status:
curl http://localhost:8000/api/rank-tracker/check/550e8400-e29b-41d4-a716-446655440000

3. Get ranking history:
curl http://localhost:8000/api/rank-tracker/history/example.com/seo%20tools?search_engine=google&days=30

4. Get trend analysis:
curl http://localhost:8000/api/rank-tracker/trend/example.com/seo%20tools

5. Get recent alerts:
curl http://localhost:8000/api/rank-tracker/alerts/example.com

6. Get domain summary:
curl http://localhost:8000/api/rank-tracker/summary/example.com
"""
