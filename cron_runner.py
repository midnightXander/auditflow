"""
cron_runner.py — standalone cron runner (Approach B)
=====================================================
Called by Railway's Cron service on a schedule (e.g. "0 * * * *").
Runs once per invocation and exits.

This is the recommended approach for production: it runs independently
of the API workers so it survives restarts and scales separately.

Railway Cron setup:
  Service type : Cron
  Schedule     : 0 * * * *   (every hour)
  Start command: python cron_runner.py
"""

import asyncio
import logging
import sys
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("cron_runner")


def main() -> None:
    log.info("=== Cron run started at %s UTC ===", datetime.utcnow().isoformat())

    from  db.database import SessionLocal, init_db
    init_db()   # create any missing tables (idempotent)

    db = SessionLocal()
    errors = 0

    try:
        # ── 1. Email sequences ────────────────────────────────────────────────
        log.info("[1/3] Processing email sequences…")
        try:
            from services.email_sequences import process_sequences
            summary = process_sequences(db)
            log.info("      Done: %s", summary)
            print("      Done: %s", summary)
        except Exception as exc:
            log.error("      FAILED: %s", exc, exc_info=True)
            errors += 1

        # # ── 2. Scheduled rank checks ──────────────────────────────────────────
        # log.info("[2/3] Running scheduled rank checks…")
        # try:
        #     from routes.tracking_routes import run_scheduled_rank_checks
        #     asyncio.run(run_scheduled_rank_checks(db))
        #     log.info("      Done")
        # except Exception as exc:
        #     log.error("      FAILED: %s", exc, exc_info=True)
        #     errors += 1

        # ── 3. Expire anonymous audits (only actually deletes when due) ────────
        log.info("[3/4] Expiring stale anonymous audits…")
        try:
            from db.models import AnonymousAudit
            deleted = (
                db.query(AnonymousAudit)
                .filter(
                    AnonymousAudit.expires_at < datetime.utcnow(),
                    AnonymousAudit.claimed_by_user_id == None,  # noqa: E711
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            log.info("      Deleted %d expired sessions", deleted)
            print(f"      Deleted {deleted} expired sessions")
        except Exception as exc:
            log.error("      FAILED: %s", exc, exc_info=True)
            errors += 1

        # ── 4. Free Trial Email Reminders & Expirations ───────────────────────
        log.info("[4/4] Processing free trial reminders & expirations…")
        try:
            from services import whop_service
            from services.email_service import (
                send_trial_start_email,
                send_trial_day3_email,
                send_trial_day10_email,
                send_trial_expiring_email,
                send_trial_expired_email
            )
            from db.models import User

            # A. Expirations
            expired_users = db.query(User).filter(
                User.subscription_status == "trial",
                User.trial_ends_at <= datetime.utcnow()
            ).all()
            log.info("      Found %d expired trials to process", len(expired_users))
            for user in expired_users:
                try:
                    success = asyncio.run(whop_service.handle_trial_expiration(user.id, db))
                    if success:
                        send_trial_expired_email(user)
                        log.info("      Reverted user %s to free plan and sent expired email", user.email)
                except Exception as e:
                    log.error("      Error expiring trial for user %s: %s", user.email, e, exc_info=True)

            # B. Reminders (only for active trials)
            active_trials = db.query(User).filter(
                User.subscription_status == "trial",
                User.trial_ends_at > datetime.utcnow()
            ).all()
            log.info("      Found %d active trials to check for reminders", len(active_trials))
            for user in active_trials:
                try:
                    reminders = whop_service.get_trial_email_reminders(user)
                    
                    if reminders["should_send_start"]:
                        send_trial_start_email(user)
                        whop_service.mark_trial_email_sent(user.id, "start", db)
                        log.info("      Sent trial start email to %s", user.email)
                        
                    if reminders["should_send_day3"]:
                        send_trial_day3_email(user)
                        whop_service.mark_trial_email_sent(user.id, "day3", db)
                        log.info("      Sent trial day 3 email to %s", user.email)
                        
                    if reminders["should_send_day10"]:
                        send_trial_day10_email(user)
                        whop_service.mark_trial_email_sent(user.id, "day10", db)
                        log.info("      Sent trial day 10 email to %s", user.email)
                        
                    if reminders["should_send_expiring_soon"]:
                        send_trial_expiring_email(user)
                        whop_service.mark_trial_email_sent(user.id, "expiring_soon", db)
                        log.info("      Sent trial expiring soon email to %s", user.email)
                except Exception as e:
                    log.error("      Error processing reminders for user %s: %s", user.email, e, exc_info=True)
            
            log.info("      Done processing trial updates")
        except Exception as exc:
            log.error("      FAILED trial processing: %s", exc, exc_info=True)
            errors += 1

    finally:
        db.close()

    log.info("=== Cron run complete — %d error(s) ===", errors)

    # Exit with non-zero so Railway marks the run as failed on errors.
    # This triggers Railway's failure notification if configured.
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()