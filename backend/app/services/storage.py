from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Dict

import boto3


@dataclass
class ArtifactStorageService:
  bucket: str

  def _client(self):
    endpoint_url = os.getenv("STORAGE_ENDPOINT_URL")
    return boto3.client(
      "s3",
      endpoint_url=endpoint_url,
      aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
      aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
      region_name=os.getenv("AWS_REGION", "us-east-1"),
    )

  def build_artifact_key(self, *, topic_id: str, title: str, storage_prefix: str) -> str:
    safe_title = "-".join(title.lower().split())
    digest = hashlib.sha256(title.encode("utf-8")).hexdigest()[:8]
    return f"{storage_prefix.rstrip('/')}/{topic_id}/{safe_title}-{digest}.json"

  def build_agent_output_key(self, *, topic_id: str, agent_id: str) -> str:
    return f"agent-outputs/{topic_id}/{agent_id}-{hashlib.sha256(agent_id.encode('utf-8')).hexdigest()[:8]}.json"

  def put_json_object(self, *, key: str, document: Dict[str, object]) -> None:
    body = json.dumps(document, ensure_ascii=False).encode("utf-8")
    self._client().put_object(Bucket=self.bucket, Key=key, Body=body, ContentType="application/json")
