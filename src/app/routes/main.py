"""Main routes for the application."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home() -> str:
    """Render the home page.

    Returns:
        str: Rendered HTML template for the home page.
    """
    current_app.logger.info("Rendering home page")
    return render_template("home.html", admin_token=current_app.config["ADMIN_TOKEN"])


@main_bp.route("/about")
def about() -> str:
    """Render the about page.

    Returns:
        str: Rendered HTML template for the about page.
    """
    return render_template("about.html")
