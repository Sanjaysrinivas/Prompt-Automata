"""Main application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from src.app import app
from src.app.models.db import init_db

if __name__ == "__main__":
    # Initialize the database
    init_db()

    # Run the application
    app.run(debug=True)
