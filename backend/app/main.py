"""Entrypoint for launching the FastAPI application."""
from __future__ import annotations

from fastapi import FastAPI

from backend.app.api.routes import app as application


def get_app() -> FastAPI:
    """Return the FastAPI instance for external servers."""
    return application


app = get_app()
