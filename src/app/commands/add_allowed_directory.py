from __future__ import annotations

import click
from flask.cli import with_appcontext

from src.app import db
from src.app.models.reference_models import AllowedDirectory


@click.command("add-allowed-dir")
@click.argument("path")
@click.option("--description", default="", help="Description of the allowed directory")
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Allow access to subdirectories",
)
@with_appcontext
def add_allowed_directory(path: str, description: str, *, recursive: bool = False):
    """Add a new allowed directory for file references."""
    try:
        allowed_dir = AllowedDirectory(
            path=path, description=description, is_recursive=recursive
        )
        db.session.add(allowed_dir)
        db.session.commit()
        click.echo(
            f"Added allowed directory: {path} ({'recursive' if recursive else 'non-recursive'})"
        )
    except ValueError as ve:  # Catch specific exceptions
        click.echo(f"Value error: {ve!s}", err=True)
        db.session.rollback()
    except db.DatabaseError as dbe:  # Hypothetical example for database-specific error
        click.echo(f"Database error: {dbe!s}", err=True)
        db.session.rollback()
