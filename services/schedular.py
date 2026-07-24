"""
scheduler.py — in-process scheduler (Approach A)
=================================================
Runs inside the FastAPI process using APScheduler.
Started from the FastAPI lifespan in api.py.

Use this when:
  • You're on Railway Starter plan (single worker)
  • You want zero extra services
  • You're just getting started

Switch to cron_runner.py (Approach B) when you need multiple API workers
or want completely separate cron infrastructure.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from rq_app import queue
from rq import Retry

log = logging.getLogger(__name__)

_scheduler = None   # BackgroundScheduler | None


def start():
    """
    Create and start the background scheduler.
    Call once from the FastAPI lifespan startup hook.
    Returns the scheduler so the lifespan can stop it cleanly.
    """
    global _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC", daemon=True)

    # ── Email sequences: every hour ───────────────────────────────────────────
    # _scheduler.add_job(
    #     func=_tick_email_sequences,
    #     trigger=IntervalTrigger(hours=1),
    #     id="email_sequences",
    #     name="Email sequence processor",
    #     replace_existing=True,
    #     max_instances=1,        # never allow overlap
    #     misfire_grace_time=300, # run even if up to 5 min late
    # )

    # ── Rank checks: every hour ───────────────────────────────────────────────
    # _scheduler.add_job(
    #     func=_tick_rank_checks,
    #     trigger=IntervalTrigger(hours=1),
    #     id="rank_checks",
    #     name="Scheduled rank checks",
    #     replace_existing=True,
    #     max_instances=1,
    #     misfire_grace_time=300,
    # )

    # ── Anon audit expiry: daily at 03:00 UTC ─────────────────────────────────
    # _scheduler.add_job(
    #     func=_tick_expire_anon_audits,
    #     trigger="cron",
    #     hour=3,
    #     minute=0,
    #     id="anon_audit_expiry",
    #     name="Expire unclaimed anonymous audits",
    #     replace_existing=True,
    #     max_instances=1,
    # )

    # - Rank trackings : weekly on Monday at 03:00 UTC
    _scheduler.add_job(
        func = _run_scheduled_rank_checks,
        trigger= "cron",
        day_of_week = "mon",
        hour = 3,
        minute = 0,
        id = "scheduled_rank_checks",
        name = "Run Scheduled rank checks",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    log.info("APScheduler started — %d jobs registered", len(_scheduler.get_jobs()))
    print("APScheduler started — %d jobs registered", len(_scheduler.get_jobs()))
    return _scheduler


def stop():
    """Cleanly shut down on app shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("APScheduler stopped")


# ── Job implementations ───────────────────────────────────────────────────────

def _tick_email_sequences():
    from db.database import SessionLocal
    from email_sequences import process_sequences
    db = SessionLocal()
    try:
        summary = process_sequences(db)
        log.info("Email sequences done: %s", summary)
        print("Email sequences done: %s", summary)
    except Exception as exc:
        log.error("Email sequences failed: %s", exc, exc_info=True)
    finally:
        db.close()


def _tick_rank_checks():
    import asyncio
    from db.database import SessionLocal
    from routes.tracking_routes import run_scheduled_rank_checks
    db = SessionLocal()
    try:
        asyncio.run(run_scheduled_rank_checks(db))
        log.info("Rank checks done")
        print("Rank checks done")
    except Exception as exc:
        log.error("Rank checks failed: %s", exc, exc_info=True)
    finally:
        db.close()


def _tick_expire_anon_audits():
    from db.database import SessionLocal
    from db.models import AnonymousAudit
    from datetime import datetime
    db = SessionLocal()
    try:
        deleted = (
            db.query(AnonymousAudit)
            .filter(
                AnonymousAudit.expires_at < datetime.utcnow(),
                AnonymousAudit.claimed_by_user_id == None,  # noqa: E711
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        log.info("Expired %d unclaimed anonymous audits", deleted)
        print("Expired %d unclaimed anonymous audits", deleted)
    except Exception as exc:
        log.error("Anon audit expiry failed: %s", exc, exc_info=True)
    finally:
        db.close()

def _run_scheduled_rank_checks():
    """Run all scheduled rank checks that are due"""
    from db.database import SessionLocal
    from db.models import RankTracking, User
    from routes.tracking_routes import run_rank_tracking_task
    from datetime import datetime
    import asyncio
    from sqlalchemy import and_

    db = SessionLocal()
    
    now = datetime.utcnow()
    
    # Find all trackings due for check
    due_trackings = db.query(RankTracking).filter(
        and_(
            RankTracking.is_scheduled == True,
            RankTracking.next_check <= now,
            RankTracking.status != "running"
        )
    ).all()
    
    print(f"Found {len(due_trackings)} rank trackings due for check")
    
    for tracking in due_trackings:
        try:
            # Check if user has credits
            user = db.query(User).filter(User.id == tracking.user_id).first()
            if not user or user.credits_remaining < 1:
                continue
            
            # Run tracking
            # asyncio.run(run_rank_tracking_task(tracking.job_id, tracking.user_id))
            queue.enqueue(run_rank_tracking_task, tracking.job_id, tracking.user_id, retry=Retry(max=3, interval=[10, 30, 60]))
            
        except Exception as e:
            print(f"Error running scheduled tracking {tracking.job_id}: {e}")