"""
Authenticated API - Complete FastAPI server with JWT auth, Google OAuth, and database
"""

from datetime import datetime, timedelta

from db.models import ActivityType, User, Audit, Crawl, Comparison, KeywordAnalysis, BacklinkAnalysis, RefreshToken
from typing import List

# Audit engines
from auditor import WebsiteAuditor
from apps.crawler import crawl_website
from apps.competitor import compare_competitors
from apps.keywords import analyze_keywords
from apps.backlinks import analyze_backlinks, find_competitor_gaps

async def run_audit_task(job_id: str, url: str, user_id: int, db_session):
    """Background task for audit (needs separate DB session)"""
    from db.database import SessionLocal
    db = SessionLocal()
    
    try:
        audit = db.query(Audit).filter(Audit.job_id == job_id).first()
        audit.status = "running"
        audit.progress = 10
        db.commit()
        
        auditor = WebsiteAuditor(url)
        audit.progress = 30
        db.commit()
        
        results = await auditor.run_full_audit()
        
        audit.status = "completed"
        audit.progress = 100
        audit.overall_score = results.get("overall_score")
        audit.results = results
        audit.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        audit.status = "failed"
        audit.error = str(e)
        db.commit()
    finally:
        db.close()

async def run_crawl_task(job_id: str, url: str, user_id: int, db_session):
    """Background task for deep crawl (needs separate DB session)"""
    from db.database import SessionLocal
    db = SessionLocal()
    
    try:
        crawl = db.query(Crawl).filter(Crawl.job_id == job_id).first()
        crawl.status = "running"
        crawl.progress = 10
        db.commit()

        
        crawl.progress = 30
        db.commit()
        
        results = await crawl_website(url, max_pages=crawl.max_pages)

        crawl.status = "completed"
        crawl.progress = 100
        crawl.results = results
        crawl.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        crawl.status = "failed"
        crawl.error = str(e)
        db.commit()
    finally:
        db.close()

async def run_comparison_task(job_id: str, target_url: str, competitor_urls: List[str], user_id: int, db_session):
    """Background task for competitor comparison """
    from db.database import SessionLocal
    db = SessionLocal()
    
    try:
        comparison = db.query(Comparison).filter(Comparison.job_id == job_id).first() 
        comparison.status = "running"
        comparison.progress = 10
        db.commit()

        
        comparison.progress = 30
        db.commit()
        
        results = await compare_competitors(target_url, competitor_urls)

        comparison.status = "completed"
        comparison.progress = 100
        comparison.results = results
        comparison.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        comparison.status = "failed"
        comparison.error = str(e)
        db.commit()
    finally:
        db.close()

async def run_keyword_analysis_task(job_id: str   , user_id: int, db_session):
    """Background task for keyword analysis task"""
    from db.database import SessionLocal
    db = SessionLocal

    # try:
    #     analaysis = db.query(KeywordAnalysis)