"""Database initialization and configuration."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from flask import current_app
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
logger = logging.getLogger(__name__)


def init_db():
    """Initialize the database."""
    if not current_app:
        logger.error("No Flask application context")
        return

    db_path = Path(current_app.instance_path) / "app.db"

    if db_path.exists():
        logger.info("Database already exists at {db_path}")
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(str(db_path))
        conn.close()
        logger.info("Created new database at {db_path}")

        from src.app.models.api_endpoint import APIEndpoint  # noqa: F401
        from src.app.models.api_token import APIToken  # noqa: F401
        from src.app.models.block_library import BlockLibrary  # noqa: F401
        from src.app.models.fence import Fence  # noqa: F401
        from src.app.models.prompt import Prompt  # noqa: F401
        from src.app.models.reference_models import (  # noqa: F401
            AllowedDirectory,
            APIKey,
            FenceReference,
            PersistentVariable,
        )
        from src.app.models.token_count import TokenCount  # noqa: F401

        try:
            db.create_all()
        except Exception:
            logger.exception("Error creating database tables")
            raise

        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS alembic_version(version_num VARCHAR(32) NOT NULL)"""
        )
        conn.commit()
        conn.close()

    except Exception:
        logger.exception("Error initializing database")
        raise


if __name__ == "__main__":
    from src.app import app

    with app.app_context():
        init_db()
