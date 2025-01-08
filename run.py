"""Run the Flask application."""

from __future__ import annotations

from src.app import app

if __name__ == "__main__":
    app.run(debug=True)
