# gunicorn.conf.py
from alembic.config import Config
from alembic import command
import logging

logger = logging.getLogger(__name__)

def on_starting(server):
    """Runs once in the master process before workers boot."""
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise