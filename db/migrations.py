"""
Database migration manager for production deployments
"""

import logging
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text
from .database import engine

logger = logging.getLogger(__name__)


def run_migrations():
    """
    Run all pending Alembic migrations
    Call this on application startup
    """
    try:
        logger.info("Starting database migration check...")
        
        # Get Alembic config
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        
        # Get current revision
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_revision = context.get_current_revision()
            
            logger.info(f"Current database revision: {current_revision or 'None (fresh database)'}")
            
            # Get head revision
            head_revision = script.get_current_head()
            logger.info(f"Target revision: {head_revision}")
            
            # Run migrations if needed
            if current_revision != head_revision:
                logger.warning(f"Database migration needed: {current_revision} -> {head_revision}")
                
                # Use Alembic CLI to run migrations
                from alembic.command import upgrade
                upgrade(alembic_cfg, "head")
                
                logger.info("✓ Migrations completed successfully")
            else:
                logger.info("✓ Database is up-to-date")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Migration failed: {str(e)}")
        logger.error("Please run 'alembic upgrade head' manually")
        raise


def check_migration_status() -> dict:
    """Check current migration status without running them"""
    try:
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current = context.get_current_revision()
            head = script.get_current_head()
            
            return {
                "current_revision": current,
                "head_revision": head,
                "is_up_to_date": current == head,
                "pending_migrations": current != head
            }
    except Exception as e:
        return {"error": str(e)}