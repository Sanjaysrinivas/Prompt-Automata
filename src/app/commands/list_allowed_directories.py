"""Command to list allowed directories."""

from __future__ import annotations

import click
from flask.cli import with_appcontext
from sqlalchemy.exc import SQLAlchemyError

from src.app import db
from src.app.models.reference_models import AllowedDirectory


@click.command("list-allowed-dirs")
@with_appcontext
def list_allowed_directories():
    """List all allowed directories."""
    try:
        allowed_dirs = db.session.query(AllowedDirectory).all()
        if not allowed_dirs:
            click.echo("No allowed directories configured")
            return

        for dir in allowed_dirs:
            click.echo(f"Path: {dir.path}")
            click.echo(f"Description: {dir.description or 'No description'}")
            click.echo("---")

    except SQLAlchemyError as se:  # Catch database-related exceptions
        click.echo(f"Database error: {se!s}", err=True)
