from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

from asgiref.wsgi import WsgiToAsgi
from dotenv import load_dotenv
from flask import Flask, jsonify, session
from flask_migrate import Migrate
from flask_session import Session

from .auth import check_session_expiry, cleanup_session
from .models.db import db, init_db
from .services.background_processor import BackgroundProcessor
from .services.task_manager import TokenCountingTaskManager
from .services.token_service import TokenCountingService

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HTTP_UNAUTHORIZED = 401


@dataclass
class ServiceContainer:
    """Container for application services with validation."""

    token_service: TokenCountingService | None = field(default=None)
    background_processor: BackgroundProcessor | None = field(default=None)
    token_task_manager: TokenCountingTaskManager | None = field(default=None)

    def validate_services(self) -> list[str]:
        """Validate that all required services are initialized.

        Returns:
            List of error messages for uninitialized services.
        """
        errors = []
        if self.token_service is None:
            errors.append("TokenCountingService not initialized")
        if self.background_processor is None:
            errors.append("BackgroundProcessor not initialized")
        if self.token_task_manager is None:
            errors.append("TokenCountingTaskManager not initialized")
        return errors


class MyFlask(Flask):
    """Custom Flask class with additional attributes and validation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize Flask application with service container."""
        super().__init__(*args, **kwargs)
        self._services = ServiceContainer()
        self.logger = logger

        self.async_mode = True
        self.asgi_app = None

    def run(self, *args: Any, **kwargs: Any) -> None:
        """Run the application with ASGI support."""
        if self.async_mode and not self.asgi_app:
            self.asgi_app = WsgiToAsgi(self.wsgi_app)
        super().run(*args, **kwargs)

    @property
    def token_service(self) -> TokenCountingService | None:
        """Get token counting service."""
        return self._services.token_service

    @token_service.setter
    def token_service(self, service: TokenCountingService | None) -> None:
        """Set token counting service with type validation."""
        if service is not None and not isinstance(service, TokenCountingService):
            msg = "token_service must be an instance of TokenCountingService"
            raise TypeError(msg)
        self._services.token_service = service

    @property
    def background_processor(self) -> BackgroundProcessor | None:
        """Get background processor service."""
        return self._services.background_processor

    @background_processor.setter
    def background_processor(self, processor: BackgroundProcessor | None) -> None:
        """Set background processor with type validation."""
        if processor is not None and not isinstance(processor, BackgroundProcessor):
            msg = "background_processor must be an instance of BackgroundProcessor"
            raise TypeError(msg)
        self._services.background_processor = processor

    @property
    def token_task_manager(self) -> TokenCountingTaskManager | None:
        """Get token task manager service."""
        return self._services.token_task_manager

    @token_task_manager.setter
    def token_task_manager(self, manager: TokenCountingTaskManager | None) -> None:
        """Set token task manager with type validation."""
        if manager is not None and not isinstance(manager, TokenCountingTaskManager):
            msg = "token_task_manager must be an instance of TokenCountingTaskManager"
            raise TypeError(msg)
        self._services.token_task_manager = manager

    def validate_services(self) -> None:
        """Validate that all required services are properly initialized.

        Raises:
            RuntimeError: If any required services are not initialized.
        """
        errors = self._services.validate_services()
        if errors:
            error_msg = "Application services not properly initialized:\n" + "\n".join(
                errors
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)


async def ensure_directory_exists(directory: str) -> None:
    """Ensure directory exists without blocking the event loop."""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            await loop.run_in_executor(
                pool, lambda: Path(directory).mkdir(parents=True, exist_ok=True)
            )
            logger.info("Ensured directory exists at %s", directory)
        except Exception:
            logger.exception("Error creating directory %s", directory)


def configure_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("src.app").setLevel(logging.DEBUG)
    logging.getLogger("werkzeug").setLevel(logging.INFO)


def configure_sessions(app):
    """Configure session management for the application."""
    session_dir = Path(tempfile.gettempdir()) / "prompt_automata_sessions"
    if not session_dir.exists():
        session_dir.mkdir(parents=True)
    else:
        for file in session_dir.iterdir():
            file_path = session_dir / file
            try:
                if file_path.is_file():
                    file_path.unlink()
                    logger.debug("Cleaned up old session file: %s", file_path)
            except Exception:
                logger.exception("Error deleting session file: %s", file_path)

    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = session_dir
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_PERMANENT"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)
    Session(app)


def configure_database(app):
    """Configure the database for the application."""
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config[
        "SQLALCHEMY_DATABASE_URI"
    ].replace("sqlite+aiosqlite:///", "sqlite:///")

    uploads_dir = Path(__file__).resolve().parent / "static" / "uploads"
    app.config["UPLOAD_FOLDER"] = uploads_dir
    asyncio.run(ensure_directory_exists(app.config["UPLOAD_FOLDER"]))

    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            init_db()
        except Exception:
            logger.exception("Error creating tables")
            raise
    Migrate(app, db)


def _configure_request_handlers(app):
    """Configure before and after request handlers."""

    @app.before_request
    def before_request():
        if check_session_expiry():
            return jsonify({"error": "Session expired"}), HTTP_UNAUTHORIZED
        if not session.get("initialized"):
            from src.app.services.global_token_counter import GlobalTokenCounter

            token_counter = GlobalTokenCounter()
            token_counter.reset()
        return None

    @app.after_request
    def after_request(response):
        if response.status_code == HTTP_UNAUTHORIZED:
            try:
                json_data = response.get_json() if response.is_json else None
                if (
                    json_data
                    and isinstance(json_data, dict)
                    and json_data.get("error") == "Session expired"
                ):
                    cleanup_session()
            except Exception:
                app.logger.exception("Error checking response JSON")
        session.modified = True
        return response


def _initialize_services(app):
    """Initialize and validate application services."""
    app.token_service = TokenCountingService()
    app.background_processor = BackgroundProcessor()
    app.token_task_manager = TokenCountingTaskManager(
        app.token_service, app.background_processor
    )
    app.validate_services()


def _setup_background_tasks(app):
    """Set up and start background task processing."""

    def check_background_processor():
        if app.background_processor is None:
            msg = "BackgroundProcessor is not initialized."
            raise RuntimeError(msg)

    def run_background_tasks():
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            check_background_processor()
            loop.run_until_complete(app.background_processor.start())
            loop.run_forever()
        except Exception:
            logger.exception("Error in background task loop")
        finally:
            if loop is not None:
                loop.close()

    with app.app_context():
        background_thread = threading.Thread(target=run_background_tasks, daemon=True)
        background_thread.start()


def _register_blueprints(app):
    """Register all application blueprints."""
    from .routes.admin import admin_bp
    from .routes.block_library import block_library_bp
    from .routes.fences import fences_bp
    from .routes.files import files_bp
    from .routes.github_reference import github_reference_bp
    from .routes.llm_completion import bp as llm_completion_bp
    from .routes.llm_token_management import llm_token_bp
    from .routes.main import main_bp
    from .routes.preview_routes import preview_bp
    from .routes.prompts import prompts_bp
    from .routes.reference_options import reference_options_bp
    from .routes.references import references_bp
    from .routes.refresh_routes import refresh_bp
    from .routes.token_counting import token_counting_bp
    from .routes.token_status import token_status_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(block_library_bp)
    app.register_blueprint(fences_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(preview_bp)
    app.register_blueprint(prompts_bp)
    app.register_blueprint(reference_options_bp, url_prefix="/api")
    app.register_blueprint(references_bp)
    app.register_blueprint(token_counting_bp, url_prefix="/api")
    app.register_blueprint(token_status_bp)
    app.register_blueprint(github_reference_bp)
    app.register_blueprint(llm_token_bp)
    app.register_blueprint(llm_completion_bp)
    app.register_blueprint(refresh_bp)


def _register_cli_commands(app):
    """Register CLI commands."""
    from src.app.commands.add_allowed_directory import add_allowed_directory
    from src.app.commands.list_allowed_directories import list_allowed_directories

    app.cli.add_command(add_allowed_directory)
    app.cli.add_command(list_allowed_directories)


def create_app():
    """Create Flask application."""
    app = MyFlask(__name__)

    configure_logging()
    configure_sessions(app)
    configure_database(app)

    app.config["WORKSPACE_PATH"] = os.getenv(
        "WORKSPACE_PATH", Path(__file__).resolve().parent.parent.parent
    )
    app.logger.info("Using workspace path: %s", app.config["WORKSPACE_PATH"])

    from src.app.services.global_token_counter import GlobalTokenCounter

    token_counter = GlobalTokenCounter()
    with app.app_context():
        token_counter.reset()

    _configure_request_handlers(app)
    _initialize_services(app)
    _setup_background_tasks(app)
    _register_blueprints(app)
    _register_cli_commands(app)

    return app


app = create_app()
