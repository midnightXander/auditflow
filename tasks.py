"""
Authenticated API - Complete FastAPI server with JWT auth, Google OAuth, and database
"""

from datetime import datetime, timedelta

from db.auth import create_notification
from db.models import ActivityType, User, Audit, Crawl, Comparison, KeywordAnalysis, BacklinkAnalysis, RefreshToken, RankTracking,RankHistory, TrackedKeyword,KeywordHistory
from typing import List, Optional
from services.email_service import send_email, send_audit_complete_email, send_deep_crawl_complete_email, send_comparison_complete_email, send_rank_check_complete_email
# Audit engines
from auditor import WebsiteAuditor
from apps.crawler import crawl_website
from apps.competitor import compare_competitors
from apps.keywords import analyze_keywords
from apps.backlinks import analyze_backlinks, find_competitor_gaps
from apps.rank_tracker import track_rankings
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
import asyncio
import os

FRONTEND_URL = os.getenv("FRONTEND_URL", "localhost:3000")

def run_audit_task(job_id: str, url: str, user_id: int, db_session=None):
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
        
        # results = await auditor.run_full_audit()
        results = asyncio.run(auditor.run_full_audit())
        
        audit.status = "completed"
        audit.progress = 100
        audit.overall_score = results.get("overall_score")
        audit.results = results
        audit.completed_at = datetime.utcnow()
        db.commit()
        
        create_notification(
        db=db,
        user_id=user_id,
        type="audit",
        title="Site Audit done",
        message=f"Audit for {url} has been completed. check results.",
        metadata={"job_id": job_id, "url": str(url)}
        )

        if not audit.is_embedded:
            try:
                print(f"sending email to {audit.user.email} ...")
                send_audit_complete_email(audit.user.email, f'{FRONTEND_URL}/audit/{job_id}', audit.overall_score, audit.client_name, audit.user.full_name)
            except Exception as e:
                print(f"Failed to send email: {e}")



        
    except Exception as e:
        audit.status = "failed"
        audit.error = str(e)
        db.commit()
    finally:
        db.close()

def run_crawl_task(job_id: str, url: str, user_id: int, db_session=None):
    """Background task for deep crawl (needs separate DB session)"""
    from db.database import SessionLocal
    db = SessionLocal()
    
    try:
        print("starting crawl process for job_id: ", job_id)
        crawl = db.query(Crawl).filter(Crawl.job_id == job_id).first()
        crawl.status = "running"
        crawl.progress = 10
        db.commit()

        
        crawl.progress = 30
        db.commit()
        
        results = asyncio.run(crawl_website(url, max_pages=crawl.max_pages))

        crawl.status = "completed"
        crawl.progress = 100
        crawl.results = results
        crawl.completed_at = datetime.utcnow()
        db.commit()
        
        create_notification(
        db=db,
        user_id=crawl.user_id,
        type="crawl",
        title=f"Crawl Terminated!",
        message=f"Deep Crawl for {crawl.url} has been completed.",
        metadata={"job_id": job_id, "url": str(crawl.url)}
    )
        def count_issues(issues: dict) -> int:
                """
                Count the total number of issues across all categories in the issues dict.
                Handles dicts, lists, and empty values gracefully.
                """
                total = 0
                for category, value in issues.items():
                    if isinstance(value, dict):
                        # Count entries in dict
                        total += len(value)
                    elif isinstance(value, list):
                        # Count entries in list
                        total += len(value)
                    else:
                        # If it's something else (unlikely), skip
                        continue
                return total
        total_issues_found = count_issues(results.get("issues", {}))
        try:
            print(f"sending email to {crawl.user.email} ...")
            #send_deep_crawl_complete_email('denzeldecode@gmail.com', crawl.url,results.get("summary").get("total_pages_crawled",0), total_issues_found)
            send_deep_crawl_complete_email(crawl.user.email, f'{FRONTEND_URL}/crawl/{job_id}', results.get("summary").get("total_pages_crawled",0), total_issues_found, crawl.client_name, crawl.user.full_name)
        except Exception as e:
            print(f"Failed to send email: {e}")

    except Exception as e:
        crawl.status = "failed"
        crawl.error = str(e)
        db.commit()
    finally:
        db.close()

async def run_comparison_task2(job_id: str, target_url: str, competitor_urls: List[str], user_id: int, db_session):
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
        
        create_notification(
        db=db,
        user_id=user_id,
        type="comparison",
        title="Comparison completed",
        message=f"Competitor Comparison results for {target_url} are ready.",
        metadata={"job_id": job_id, "url": str(target_url)}
        )

        try:
            print(f"sending email to {comparison.user.email} ...")
            send_comparison_complete_email(comparison.user.email, f'{FRONTEND_URL}/compare/{job_id}', comparison.competitor_urls, comparison.user.full_name)
            
        except Exception as e:
            print(f"Failed to send email: {e}")
        
    except Exception as e:
        comparison.status = "failed"
        comparison.error = str(e)
        db.commit()
    finally:
        db.close()

def run_comparison_task(job_id: str) -> None:
    from db.database import SessionLocal
 
    db: Session = SessionLocal()
    try:
        comp: Comparison = db.query(Comparison).filter(Comparison.job_id == job_id).first()
        if not comp:
            return
 
        comp.status = "running"
        comp.progress = 10
        db.commit()
 
        async def progress_cb(pct, status):
            comp.progress = int(pct)
            db.commit()
 
        results = asyncio.run(compare_competitors(
            target_url=comp.target_url,
            competitor_urls=comp.competitor_urls,
            progress_callback=progress_cb,
        ))
 
        # ── Extract snapshot for fast KPI queries ──
        overall = results.get("overall_scores", {})
        target_score = overall.get("target", {}).get("score")
        comp_scores = [c.get("score", 0) for c in overall.get("competitors", [])]
        comp_urls   = overall.get("competitors", [])
 
        best_comp = max(comp_urls, key=lambda c: c.get("score", 0), default=None)
        worst_score = min(comp_scores) if comp_scores else None
        avg_score   = round(sum(comp_scores) / len(comp_scores), 1) if comp_scores else None
 
        comp.target_score = target_score
        comp.best_competitor_score = best_comp.get("score") if best_comp else None
        comp.best_competitor_url = best_comp.get("url") if best_comp else None
        comp.worst_competitor_score = worst_score
        comp.avg_competitor_score = avg_score
        comp.score_gap = (
            (target_score - best_comp.get("score"))
            if (target_score is not None and best_comp)
            else None
        )
 
        comp.status = "completed"
        comp.progress = 100
        comp.results = results
        comp.completed_at = datetime.utcnow()
        db.commit()

        create_notification(
        db=db,
        user_id=comp.user_id,
        type="comparison",
        title="Comparison completed",
        message=f"Competitor Comparison results for {comp.target_url} are ready.",
        metadata={"job_id": job_id, "url": str(comp.target_url)}
        )

        try:
            print(f"sending email to {comp.user.email} ...")
            send_comparison_complete_email(comp.user.email, f'{FRONTEND_URL}/compare/{job_id}', len(comp_urls), comp.user.full_name)
        except Exception as e:
            print(f"Failed to send email: {e}")
 
    except Exception as exc:
        db.rollback()
        comp.status = "failed"
        comp.error = str(exc)
        db.commit()
    finally:
        db.close()

async def run_keyword_analysis_task(job_id: str   , user_id: int, db_session):
    """Background task for keyword analysis task"""
    from db.database import SessionLocal
    db = SessionLocal

    # try:
    #     analaysis = db.query(KeywordAnalysis)

def run_rank_tracking_task(job_id: str, user_id: int):
    """Background task to run rank tracking"""
    from db.database import SessionLocal
    db = SessionLocal()
    
    try:
        tracking = db.query(RankTracking).filter(RankTracking.job_id == job_id).first()
        if not tracking:
            return
        
        tracking.status = "running"
        tracking.progress = 10
        db.commit()
        
        # Progress callback
        async def update_progress(progress, status):
            tracking.progress = int(progress)
            db.commit()
        
        # Run tracking
        results = asyncio.run(track_rankings(
            domain=tracking.domain,
            keywords=tracking.keywords,
            engines=tracking.engines,
            progress_callback=update_progress
        ))
        
        # Store results
        tracking.status = "completed"
        tracking.progress = 100
        tracking.results = results
        tracking.last_checked = datetime.utcnow()
        
        # Save historical data
        asyncio.run(save_to_history(tracking, results, db))
        
        # Generate alerts if needed
        alerts = asyncio.run(check_for_alerts(tracking, db))
        
        if alerts:
            tracking.results['alerts'] = alerts
            # Send email notification
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                asyncio.run(send_alert_email(user, tracking, alerts))
        
        # Schedule next check
        if tracking.is_scheduled:
            tracking.next_check = calculate_next_check(tracking.frequency)
        
        db.commit()

        try:
            print(f"sending email to {tracking.user.email} ...")
            send_rank_check_complete_email(tracking.user.email, f'{FRONTEND_URL}/rank-tracker/{job_id}', tracking.domain, len(tracking.keywords), user_name = tracking.user.full_name)
        except Exception as e:
            print(f"Failed to send email: {e}")
        
    except Exception as e:
        tracking.status = "failed"
        tracking.error = str(e)
        db.commit()
    finally:
        db.close()


async def run_tracking_task(job_id: str, user_id: int) -> None:
    from db.database import SessionLocal
 
    db: Session = SessionLocal()
    try:
        campaign: RankTracking = (
            db.query(RankTracking).filter(RankTracking.job_id == job_id).first()
        )
        if not campaign:
            return

        campaign.status = "running"
        campaign.progress = 5
        db.commit()

        kw_objs: List[TrackedKeyword] = campaign.keywords_rel
        total = len(kw_objs) * len(campaign.engines)
        done = 0
        print("keywords: ",kw_objs)

        for kw_obj in kw_objs:
            for engine in campaign.engines:
                results = await track_rankings(
                    domain=campaign.domain,
                    keywords=[kw_obj.keyword],
                    engines=[engine],
                )
                print("results: ",results)
                campaign.results = results
                kw_data = results["results"].get(kw_obj.keyword, {}).get(engine, {})
                current_pos: Optional[int] = kw_data.get("position")

                print("kw_data: ", kw_data)

                # --- write history row ---
                hist = KeywordHistory(
                    keyword_id=kw_obj.id,
                    position=current_pos,
                    previous_position=kw_obj.current_position,
                    position_change=(
                        (kw_obj.current_position - current_pos)
                        if (kw_obj.current_position and current_pos)
                        else None
                    ),
                    landing_url=kw_data.get("url"),
                    title=kw_data.get("title"),
                    engine=engine,
                    checked_at=datetime.utcnow(),
                )
                db.add(hist)

                # --- update denormalised snapshot on keyword ---
                kw_obj.previous_position = kw_obj.current_position
                kw_obj.current_position = current_pos
                kw_obj.position_change = hist.position_change
                kw_obj.landing_url = kw_data.get("url")
                kw_obj.last_checked_at = datetime.utcnow()

                if current_pos and (
                    kw_obj.best_position is None or current_pos < kw_obj.best_position
                ):
                    kw_obj.best_position = current_pos

                db.commit()

                done += 1
                campaign.progress = int(5 + 90 * done / total)
                db.commit()
            # Save historical data
            await save_to_history(campaign, results, db)
            
            # Generate alerts if needed
            alerts = await check_for_alerts(campaign, db)
            
            if alerts:
                campaign.results['alerts'] = alerts
                # Send email notification
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    await send_alert_email(user, campaign, alerts)        

            campaign.status = "completed"
            campaign.progress = 100
            
            
            create_notification(
            db=db,
            user_id=user.id,
            type="tracking",
            title="Tracking Done!",
            message=f"Results for keyword trackings for {campaign.domain} are ready! click to view.",
            metadata={"job_id": job_id, "url": str(campaign.domain)})

            campaign.last_checked = datetime.utcnow()
            if campaign.is_scheduled:
                campaign.next_check = _next_check_time(campaign.frequency)
            db.commit()
 
    except Exception as exc:
        db.rollback()
        campaign.status = "failed"
        campaign.error = str(exc)
        db.commit()
    finally:
        db.close()
 
 
def _next_check_time(frequency: str) -> datetime:
    deltas = {"daily": timedelta(days=1), "weekly": timedelta(weeks=1), "monthly": timedelta(days=30)}
    return datetime.utcnow() + deltas.get(frequency, timedelta(days=1))

async def save_to_history(tracking: RankTracking, results: dict, db: Session):
    """Save rank tracking results to history"""
    
    for keyword, engines in results['results'].items():
        for engine, data in engines.items():
            # Get previous position
            prev_history = db.query(RankHistory).filter(
                and_(
                    RankHistory.tracking_id == tracking.id,
                    RankHistory.keyword == keyword,
                    RankHistory.engine == engine
                )
            ).order_by(desc(RankHistory.checked_at)).first()
            
            previous_position = prev_history.position if prev_history else None
            current_position = data.get('position')
            
            # Calculate change
            if previous_position and current_position:
                position_change = previous_position - current_position  # Positive = improved
            else:
                position_change = None
            
            # Create history record
            history = RankHistory(
                tracking_id=tracking.id,
                keyword=keyword,
                engine=engine,
                position=current_position,
                url=data.get('url'),
                title=data.get('title'),
                previous_position=previous_position,
                position_change=position_change,
                checked_at=datetime.utcnow()
            )
            
            db.add(history)
    
    db.commit()


async def check_for_alerts(tracking: RankTracking, db: Session) -> List[dict]:
    """Check for significant ranking changes and generate alerts"""
    
    alerts = []
    
    for keyword in [kw.keyword for kw in tracking.keywords_rel]:
        print("checking alert for: ",keyword)
        for engine in tracking.engines:
            # Get last two checks
            history = db.query(RankHistory).filter(
                and_(
                    RankHistory.tracking_id == tracking.id,
                    RankHistory.keyword == keyword,
                    RankHistory.engine == engine
                )
            ).order_by(desc(RankHistory.checked_at)).limit(2).all()
            
            if len(history) < 2:
                continue
            
            current, previous = history[0], history[1]
            
            # Significant drop (10+ positions)
            if current.position_change and current.position_change < -10:
                alerts.append({
                    'severity': 'high',
                    'type': 'significant_drop',
                    'keyword': keyword,
                    'engine': engine,
                    'message': f"Dropped {abs(current.position_change)} positions",
                    'from_position': previous.position,
                    'to_position': current.position
                })
            
            # Left top 10
            if previous.position <= 10 and current.position and current.position > 10:
                alerts.append({
                    'severity': 'medium',
                    'type': 'left_top_10',
                    'keyword': keyword,
                    'engine': engine,
                    'message': f"Left top 10 (#{previous.position} → #{current.position})"
                })
            
            # Entered top 10
            if previous.position > 10 and current.position and current.position <= 10:
                alerts.append({
                    'severity': 'positive',
                    'type': 'entered_top_10',
                    'keyword': keyword,
                    'engine': engine,
                    'message': f"Entered top 10! (#{previous.position} → #{current.position})"
                })
            
            # Lost ranking
            if previous.position and not current.position:
                alerts.append({
                    'severity': 'critical',
                    'type': 'ranking_lost',
                    'keyword': keyword,
                    'engine': engine,
                    'message': f"Ranking lost (was #{previous.position})"
                })
    
    return alerts





def calculate_next_check(frequency: str) -> datetime:
    """Calculate next check time based on frequency"""
    now = datetime.utcnow()
    
    if frequency == "daily":
        return now + timedelta(days=1)
    elif frequency == "weekly":
        return now + timedelta(weeks=1)
    elif frequency == "monthly":
        return now + timedelta(days=30)
    else:
        return now + timedelta(days=1)

async def send_alert_email(user: User, tracking: RankTracking, alerts: List[dict]):
    """Send email notification for ranking alerts"""
    
    high_severity = [a for a in alerts if a['severity'] in ['high', 'critical']]
    
    if not high_severity:
        return
    
    subject = f"⚠️ Ranking Alert: {tracking.domain}"
    
    html = f"""
    <h2>Ranking Alert for {tracking.domain}</h2>
    <p>We detected significant changes in your rankings:</p>
    <ul>
    """
    
    for alert in high_severity:
        html += f"<li><strong>{alert['keyword']}</strong> ({alert['engine']}): {alert['message']}</li>"
    
    html += """
    </ul>
    <p><a href="{}/rank-tracking/{}">View Full Report</a></p>
    """.format(os.getenv("FRONTEND_URL", "http://localhost:3000"), tracking.job_id)
    
    send_email(user.email, subject, html)

