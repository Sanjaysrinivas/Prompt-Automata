from __future__ import annotations

import sys

from src.app import app, db
from src.app.models.reference_models import AllowedDirectory

with app.app_context():
    workspace_path = app.config["WORKSPACE_PATH"]
    if not workspace_path:
        sys.exit(1)

    existing = AllowedDirectory.query.filter_by(path=workspace_path).first()
    if not existing:
        directory = AllowedDirectory(path=workspace_path, description="Main workspace")
        db.session.add(directory)
        db.session.commit()
    else:
        pass
