"""Flask application configuration."""

from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Base configuration."""

    # Ensure instance directory exists
    BASE_DIR = Path(__file__).resolve().parent
    INSTANCE_PATH = BASE_DIR / "instance"
    INSTANCE_PATH.mkdir(parents=True, exist_ok=True)

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{INSTANCE_PATH / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")

    UPLOAD_FOLDER = BASE_DIR / "src" / "app" / "static" / "uploads"

    WORKSPACE_PATH = os.getenv("WORKSPACE_PATH", str(BASE_DIR))

    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev-admin-token-change-in-production")

    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    TESTING = os.getenv("TESTING", "false").lower() == "true"
    ENV = os.getenv("ENV", "development")
    FLASK_APP = os.getenv("FLASK_APP", "app")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
