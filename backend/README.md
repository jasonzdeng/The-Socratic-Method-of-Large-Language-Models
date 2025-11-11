# Backend Service

This service exposes a FastAPI application alongside a Celery worker for background task
processing. Install dependencies with Poetry and run the development server via Uvicorn.

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

Start a Celery worker that processes tasks defined in `app.tasks` with:

```bash
poetry run celery -A app.celery_app.celery_app worker --loglevel=info
```
