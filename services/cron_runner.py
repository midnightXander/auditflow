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
            from email_sequences import process_sequences
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
        log.info("[3/3] Expiring stale anonymous audits…")
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

    finally:
        db.close()

    log.info("=== Cron run complete — %d error(s) ===", errors)

    # Exit with non-zero so Railway marks the run as failed on errors.
    # This triggers Railway's failure notification if configured.
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()