from __future__ import annotations

from fastapi import FastAPI

from .routers import artifacts

app = FastAPI(title="Debate Artifact Service")
app.include_router(artifacts.router)


@app.get("/health")
async def health_check():
  return {"status": "ok"}
