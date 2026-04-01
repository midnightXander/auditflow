"""
FastAPI server for Website Auditor
Provides REST API endpoints for website auditing
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
import asyncio
import uuid
from datetime import datetime
from auditor import WebsiteAuditor
from models import * 
from backend.apps.crawler import crawl_website
from backend.apps.competitor import compare_competitors
from backend.apps.keywords import analyze_keywords
from backend.apps.backlinks import analyze_backlinks, find_competitor_gaps

app = FastAPI(
    title="Website Auditor API",
    description="API for automated website auditing with comprehensive analysis and competitor comparison",
    version="1.5.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for audit results (use Redis/Database in production)
audit_results = {}
crawl_results = {}
comparison_results = {}
keyword_results = {}
backlink_results = {}





async def run_audit_task(job_id: str, url: str):
    """Background task to run the audit"""
    try:
        audit_results[job_id]["status"] = "running"
        audit_results[job_id]["progress"] = 10
        
        auditor = WebsiteAuditor(url)
        
        audit_results[job_id]["progress"] = 30
        results = await auditor.run_full_audit()
        
        audit_results[job_id]["status"] = "completed"
        audit_results[job_id]["progress"] = 100
        audit_results[job_id]["results"] = results
        audit_results[job_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        audit_results[job_id]["status"] = "failed"
        audit_results[job_id]["error"] = str(e)


@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "Website Auditor API",
        "version": "1.0.0",
        "status": "online"
    }


@app.post("/api/audit", response_model=AuditResponse)
async def create_audit(
    request: AuditRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new website audit
    
    Returns a job_id that can be used to check the audit status
    """
    job_id = str(uuid.uuid4())
    url = str(request.url)
    
    # Initialize job status
    audit_results[job_id] = {
        "job_id": job_id,
        "url": url,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "results": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(run_audit_task, job_id, url)
    
    return AuditResponse(
        job_id=job_id,
        status="pending",
        message=f"Audit started for {url}. Use job_id to check status."
    )


@app.get("/api/audit/{job_id}", response_model=AuditStatus)
async def get_audit_status(job_id: str):
    """
    Get the status of an audit job
    
    Returns the current status and results (if completed)
    """
    if job_id not in audit_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    job_data = audit_results[job_id]
    
    return AuditStatus(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data.get("progress"),
        results=job_data.get("results"),
        error=job_data.get("error")
    )


@app.get("/api/audits")
async def list_audits():
    """
    List all audit jobs (for debugging)
    """
    return {
        "total": len(audit_results),
        "audits": [
            {
                "job_id": job_id,
                "url": data["url"],
                "status": data["status"],
                "created_at": data["created_at"]
            }
            for job_id, data in audit_results.items()
        ]
    }


@app.delete("/api/audit/{job_id}")
async def delete_audit(job_id: str):
    """
    Delete an audit job and its results
    """
    if job_id not in audit_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    del audit_results[job_id]
    return {"message": "Audit deleted successfully"}


# ──────────────────────────────────────────────────────────────────────────────
# DEEP CRAWL ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

async def run_crawl_task(job_id: str, url: str, max_pages: int):
    """Background task to run the site crawl"""
    try:
        crawl_results[job_id]["status"] = "running"
        
        async def update_progress(progress):
            crawl_results[job_id]["progress"] = int(progress)
        
        results = await crawl_website(url, max_pages=max_pages, progress_callback=update_progress)
        
        crawl_results[job_id]["status"] = "completed"
        crawl_results[job_id]["progress"] = 100
        crawl_results[job_id]["results"] = results
        crawl_results[job_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        crawl_results[job_id]["status"] = "failed"
        crawl_results[job_id]["error"] = str(e)


@app.post("/api/crawl", response_model=AuditResponse)
async def create_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a deep site crawl
    
    Crawls up to max_pages (default 500) and returns comprehensive analysis
    """
    job_id = str(uuid.uuid4())
    url = str(request.url)
    max_pages = request.max_pages or 500
    
    # Initialize job status
    crawl_results[job_id] = {
        "job_id": job_id,
        "url": url,
        "max_pages": max_pages,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "results": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(run_crawl_task, job_id, url, max_pages)
    
    return AuditResponse(
        job_id=job_id,
        status="pending",
        message=f"Crawl started for {url}. Crawling up to {max_pages} pages."
    )


@app.get("/api/crawl/{job_id}", response_model=AuditStatus)
async def get_crawl_status(job_id: str):
    """
    Get the status of a crawl job
    
    Returns the current status and results (if completed)
    """
    if job_id not in crawl_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    job_data = crawl_results[job_id]
    
    return AuditStatus(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data.get("progress"),
        results=job_data.get("results"),
        error=job_data.get("error")
    )


@app.get("/api/crawls")
async def list_crawls():
    """
    List all crawl jobs (for debugging)
    """
    return {
        "total": len(crawl_results),
        "crawls": [
            {
                "job_id": job_id,
                "url": data["url"],
                "status": data["status"],
                "max_pages": data.get("max_pages"),
                "created_at": data["created_at"]
            }
            for job_id, data in crawl_results.items()
        ]
    }


@app.delete("/api/crawl/{job_id}")
async def delete_crawl(job_id: str):
    """
    Delete a crawl job and its results
    """
    if job_id not in crawl_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    del crawl_results[job_id]
    return {"message": "Crawl deleted successfully"}


# ──────────────────────────────────────────────────────────────────────────────
# COMPETITOR COMPARISON ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

async def run_comparison_task(job_id: str, target_url: str, competitor_urls: List[str]):
    """Background task to run competitor comparison"""
    try:
        comparison_results[job_id]["status"] = "running"
        
        async def update_progress(progress, status):
            comparison_results[job_id]["progress"] = int(progress)
            comparison_results[job_id]["current_status"] = status
        
        results = await compare_competitors(
            target_url,
            competitor_urls,
            progress_callback=update_progress
        )
        
        comparison_results[job_id]["status"] = "completed"
        comparison_results[job_id]["progress"] = 100
        comparison_results[job_id]["results"] = results
        comparison_results[job_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        comparison_results[job_id]["status"] = "failed"
        comparison_results[job_id]["error"] = str(e)


@app.post("/api/compare", response_model=AuditResponse)
async def create_comparison(
    request: ComparisonRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a competitor comparison analysis
    
    Audits your site + up to 3 competitors in parallel
    """
    job_id = str(uuid.uuid4())
    target_url = str(request.target_url)
    competitor_urls = [str(url) for url in request.competitor_urls[:3]]  # Max 3
    
    # Initialize job status
    comparison_results[job_id] = {
        "job_id": job_id,
        "target_url": target_url,
        "competitor_urls": competitor_urls,
        "status": "pending",
        "progress": 0,
        "current_status": "Starting",
        "created_at": datetime.now().isoformat(),
        "results": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(run_comparison_task, job_id, target_url, competitor_urls)
    
    return AuditResponse(
        job_id=job_id,
        status="pending",
        message=f"Comparison started: {target_url} vs {len(competitor_urls)} competitors"
    )


@app.get("/api/compare/{job_id}", response_model=AuditStatus)
async def get_comparison_status(job_id: str):
    """
    Get the status of a comparison job
    
    Returns the current status and results (if completed)
    """
    if job_id not in comparison_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    job_data = comparison_results[job_id]
    
    return AuditStatus(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data.get("progress"),
        results=job_data.get("results"),
        error=job_data.get("error")
    )


@app.get("/api/comparisons")
async def list_comparisons():
    """
    List all comparison jobs (for debugging)
    """
    return {
        "total": len(comparison_results),
        "comparisons": [
            {
                "job_id": job_id,
                "target_url": data["target_url"],
                "competitor_count": len(data.get("competitor_urls", [])),
                "status": data["status"],
                "created_at": data["created_at"]
            }
            for job_id, data in comparison_results.items()
        ]
    }


@app.delete("/api/compare/{job_id}")
async def delete_comparison(job_id: str):
    """
    Delete a comparison job and its results
    """
    if job_id not in comparison_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    del comparison_results[job_id]
    return {"message": "Comparison deleted successfully"}


# ──────────────────────────────────────────────────────────────────────────────
# KEYWORD OPPORTUNITIES ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

async def run_keyword_analysis_task(job_id: str, domain: str, use_mock_data: bool):
    """Background task to analyze keyword opportunities"""
    try:
        keyword_results[job_id]["status"] = "running"
        
        async def update_progress(progress, status):
            keyword_results[job_id]["progress"] = int(progress)
            keyword_results[job_id]["current_status"] = status
        
        results = await analyze_keywords(
            domain=domain,
            gsc_data=None,
            use_mock_data=use_mock_data,
            progress_callback=update_progress
        )
        
        keyword_results[job_id]["status"] = "completed"
        keyword_results[job_id]["progress"] = 100
        keyword_results[job_id]["results"] = results
        keyword_results[job_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        keyword_results[job_id]["status"] = "failed"
        keyword_results[job_id]["error"] = str(e)


@app.post("/api/keywords", response_model=AuditResponse)
async def create_keyword_analysis(
    request: KeywordRequest,
    background_tasks: BackgroundTasks
):
    """
    Start keyword opportunity analysis
    
    Identifies quick wins (positions 11-30), clusters keywords,
    and generates content recommendations
    """
    job_id = str(uuid.uuid4())
    domain = request.domain.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
    
    # Initialize job status
    keyword_results[job_id] = {
        "job_id": job_id,
        "domain": domain,
        "status": "pending",
        "progress": 0,
        "current_status": "Starting",
        "created_at": datetime.now().isoformat(),
        "results": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(
        run_keyword_analysis_task, 
        job_id, 
        domain, 
        request.use_mock_data
    )
    
    return AuditResponse(
        job_id=job_id,
        status="pending",
        message=f"Keyword analysis started for {domain}"
    )


@app.get("/api/keywords/{job_id}", response_model=AuditStatus)
async def get_keyword_analysis_status(job_id: str):
    """
    Get the status of a keyword analysis job
    
    Returns the current status and results (if completed)
    """
    if job_id not in keyword_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    job_data = keyword_results[job_id]
    
    return AuditStatus(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data.get("progress"),
        results=job_data.get("results"),
        error=job_data.get("error")
    )


@app.get("/api/keyword-analyses")
async def list_keyword_analyses():
    """
    List all keyword analysis jobs (for debugging)
    """
    return {
        "total": len(keyword_results),
        "analyses": [
            {
                "job_id": job_id,
                "domain": data["domain"],
                "status": data["status"],
                "created_at": data["created_at"]
            }
            for job_id, data in keyword_results.items()
        ]
    }


@app.delete("/api/keywords/{job_id}")
async def delete_keyword_analysis(job_id: str):
    """
    Delete a keyword analysis job and its results
    """
    if job_id not in keyword_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    del keyword_results[job_id]
    return {"message": "Keyword analysis deleted successfully"}


# ──────────────────────────────────────────────────────────────────────────────
# BACKLINK ANALYSIS ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

async def run_backlink_analysis_task(job_id: str, domain: str, competitor_domains: Optional[List[str]]):
    """Background task to analyze backlinks"""
    try:
        backlink_results[job_id]["status"] = "running"
        
        async def update_progress(progress, status):
            backlink_results[job_id]["progress"] = int(progress)
            backlink_results[job_id]["current_status"] = status
        
        # If competitors provided, find gaps; otherwise just analyze backlinks
        if competitor_domains and len(competitor_domains) > 0:
            results = await find_competitor_gaps(
                domain,
                competitor_domains,
                progress_callback=update_progress
            )
        else:
            results = await analyze_backlinks(
                domain=domain,
                progress_callback=update_progress
            )
        
        backlink_results[job_id]["status"] = "completed"
        backlink_results[job_id]["progress"] = 100
        backlink_results[job_id]["results"] = results
        backlink_results[job_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        backlink_results[job_id]["status"] = "failed"
        backlink_results[job_id]["error"] = str(e)


@app.post("/api/backlinks", response_model=AuditResponse)
async def create_backlink_analysis(
    request: BacklinkRequest,
    background_tasks: BackgroundTasks
):
    """
    Start backlink analysis
    
    Discovers who's linking to you, analyzes link quality,
    identifies toxic links, and finds competitor gaps
    """
    job_id = str(uuid.uuid4())
    domain = request.domain.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
    competitor_domains = request.competitor_domains or []
    
    # Initialize job status
    backlink_results[job_id] = {
        "job_id": job_id,
        "domain": domain,
        "competitor_domains": competitor_domains,
        "status": "pending",
        "progress": 0,
        "current_status": "Starting",
        "created_at": datetime.now().isoformat(),
        "results": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(
        run_backlink_analysis_task, 
        job_id, 
        domain,
        competitor_domains
    )
    
    message = f"Backlink analysis started for {domain}"
    if competitor_domains:
        message += f" (comparing with {len(competitor_domains)} competitors)"
    
    return AuditResponse(
        job_id=job_id,
        status="pending",
        message=message
    )


@app.get("/api/backlinks/{job_id}", response_model=AuditStatus)
async def get_backlink_analysis_status(job_id: str):
    """
    Get the status of a backlink analysis job
    
    Returns the current status and results (if completed)
    """
    if job_id not in backlink_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    job_data = backlink_results[job_id]
    
    return AuditStatus(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data.get("progress"),
        results=job_data.get("results"),
        error=job_data.get("error")
    )


@app.get("/api/backlink-analyses")
async def list_backlink_analyses():
    """
    List all backlink analysis jobs (for debugging)
    """
    return {
        "total": len(backlink_results),
        "analyses": [
            {
                "job_id": job_id,
                "domain": data["domain"],
                "status": data["status"],
                "created_at": data["created_at"]
            }
            for job_id, data in backlink_results.items()
        ]
    }


@app.delete("/api/backlinks/{job_id}")
async def delete_backlink_analysis(job_id: str):
    """
    Delete a backlink analysis job and its results
    """
    if job_id not in backlink_results:
        raise HTTPException(status_code=404, detail="Job ID not found")
    
    del backlink_results[job_id]
    return {"message": "Backlink analysis deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)