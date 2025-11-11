from __future__ import annotations

import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..services.notifications import notify_consensus_reached, notify_manual_intervention
from ..services.storage import ArtifactStorageService

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def get_storage_service() -> ArtifactStorageService:
  bucket = os.getenv("ARTIFACT_BUCKET", "artifacts")
  return ArtifactStorageService(bucket=bucket)


@router.post("/export")
async def export_artifact(
  payload: Dict[str, Any],
  storage: ArtifactStorageService = Depends(get_storage_service),
):
  """Compile a final brief and persist it to object storage."""
  topic_id = payload.get("topic_id")
  title = payload.get("title")
  body_markdown = payload.get("body_markdown")
  storage_prefix = payload.get("storage_prefix", "artifacts/")
  citations: Optional[List[Dict[str, Any]]] = payload.get("citations")
  consensus_state = payload.get("consensus_state", "pending")

  if not topic_id or not title or not body_markdown:
    raise HTTPException(status_code=422, detail="Topic, title, and markdown body are required")

  artifact_key = storage.build_artifact_key(
    topic_id=topic_id,
    title=title,
    storage_prefix=storage_prefix,
  )

  artifact_document = {
    "topic_id": topic_id,
    "title": title,
    "body_markdown": body_markdown,
    "citations": citations or [],
    "exported_at": datetime.utcnow().isoformat() + "Z",
  }

  storage.put_json_object(key=artifact_key, document=artifact_document)

  if consensus_state == "consensus":
    notify_consensus_reached(topic_id=topic_id, artifact_key=artifact_key)
  elif consensus_state == "manual_review":
    notify_manual_intervention(topic_id=topic_id, artifact_key=artifact_key)

  return {"artifact_key": artifact_key, "storage_bucket": storage.bucket}


@router.post("/compile")
async def compile_brief(
  payload: Dict[str, Any],
):
  """Compile a markdown brief with citations and stream it as a download."""
  title = payload.get("title", "debate-brief")
  sections: List[Dict[str, Any]] = payload.get("sections", [])

  if not sections:
    raise HTTPException(status_code=422, detail="At least one section is required")

  buffer = io.StringIO()
  buffer.write(f"# {title}\n\n")

  for section in sections:
    heading = section.get("heading", "Summary")
    content = section.get("content", "")
    citations = section.get("citations", [])

    buffer.write(f"## {heading}\n\n")
    buffer.write(f"{content}\n\n")

    if citations:
      buffer.write("### Citations\n")
      for citation in citations:
        label = citation.get("label", "Source")
        url = citation.get("url")
        note = citation.get("note")
        buffer.write(f"- **{label}**: {url} ({note})\n")
      buffer.write("\n")

  buffer.seek(0)

  return StreamingResponse(
    iter([buffer.getvalue().encode("utf-8")]),
    media_type="text/markdown",
    headers={
      "Content-Disposition": f"attachment; filename={title.replace(' ', '_')}.md",
    },
  )


@router.post("/ingest-agent-output")
async def ingest_agent_output(
  payload: Dict[str, Any],
  storage: ArtifactStorageService = Depends(get_storage_service),
):
  """Persist raw agent output for later reference in artifacts or drill-down views."""
  topic_id = payload.get("topic_id")
  agent_id = payload.get("agent_id")
  content = payload.get("content")
  metadata = payload.get("metadata", {})

  if not topic_id or not agent_id or not content:
    raise HTTPException(status_code=422, detail="topic_id, agent_id, and content are required")

  key = storage.build_agent_output_key(topic_id=topic_id, agent_id=agent_id)

  storage.put_json_object(
    key=key,
    document={
      "topic_id": topic_id,
      "agent_id": agent_id,
      "content": content,
      "metadata": metadata,
      "ingested_at": datetime.utcnow().isoformat() + "Z",
    },
  )

  return {"status": "stored", "key": key}
