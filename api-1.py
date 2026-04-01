"""
FastAPI server for Website Auditor
Provides REST API endpoints for website auditing
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import asyncio
import uuid
from datetime import datetime
from auditor import WebsiteAuditor

app = FastAPI(
    title="Website Auditor API",
    description="API for automated website auditing",
    version="1.0.0"
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


class AuditRequest(BaseModel):
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com"
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
        "message": "AuditFlow API",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
