from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
  slack_webhook_url: Optional[str]
  email_endpoint: Optional[str]
  api_key: Optional[str]

  @classmethod
  def from_env(cls) -> "NotificationConfig":
    return cls(
      slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
      email_endpoint=os.getenv("EMAIL_WEBHOOK_URL"),
      api_key=os.getenv("NOTIFICATION_API_KEY"),
    )


def _post_json(url: str, payload: Dict[str, object], api_key: Optional[str] = None) -> None:
  headers = {"Content-Type": "application/json"}
  if api_key:
    headers["Authorization"] = f"Bearer {api_key}"

  try:
    response = httpx.post(url, json=payload, timeout=5)
    response.raise_for_status()
  except httpx.HTTPError as error:
    logger.warning("Notification delivery failed: %s", error)


def notify_consensus_reached(topic_id: str, artifact_key: str) -> None:
  config = NotificationConfig.from_env()
  message = {
    "topic_id": topic_id,
    "artifact_key": artifact_key,
    "event": "consensus_reached",
  }

  if config.slack_webhook_url:
    _post_json(
      url=config.slack_webhook_url,
      payload={"text": f"Consensus reached for {topic_id}: {artifact_key}"},
      api_key=config.api_key,
    )

  if config.email_endpoint:
    _post_json(
      url=config.email_endpoint,
      payload={
        "subject": f"Consensus reached for {topic_id}",
        "body": json.dumps(message, indent=2),
      },
      api_key=config.api_key,
    )


def notify_manual_intervention(topic_id: str, artifact_key: str) -> None:
  config = NotificationConfig.from_env()

  message = {
    "topic_id": topic_id,
    "artifact_key": artifact_key,
    "event": "manual_intervention_requested",
  }

  if config.slack_webhook_url:
    _post_json(
      url=config.slack_webhook_url,
      payload={
        "text": f"Manual review requested for {topic_id}. Artifact: {artifact_key}",
      },
      api_key=config.api_key,
    )

  if config.email_endpoint:
    _post_json(
      url=config.email_endpoint,
      payload={
        "subject": f"Manual review needed for {topic_id}",
        "body": json.dumps(message, indent=2),
      },
      api_key=config.api_key,
    )
