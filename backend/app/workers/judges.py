"""Judge workflows combining LLM reasoning with rule-based validation."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mode
from typing import Iterable, List, Protocol

from backend.app.domain.discussion import DiscussionSession, JudgeVerdict


class LLMClient(Protocol):
    """Minimal abstraction for interacting with an LLM."""

    model: str

    def generate_summary(self, session: DiscussionSession) -> str:
        ...

    def identify_issues(self, session: DiscussionSession) -> List[str]:
        ...


class RuleValidator(Protocol):
    """Synchronous validation rule applied to a session."""

    name: str

    def evaluate(self, session: DiscussionSession) -> List[str]:
        ...


@dataclass
class JudgeCommitteeConfig:
    """Configuration for building judge committees."""

    committee_id: str
    llm_clients: List[LLMClient]
    validators: List[RuleValidator]


class CommitteeJudge:
    """Judge worker that orchestrates multiple LLMs and validators."""

    def __init__(self, config: JudgeCommitteeConfig) -> None:
        self.judge_id = config.committee_id
        self._llm_clients = config.llm_clients
        self._validators = config.validators

    def review(self, session: DiscussionSession) -> JudgeVerdict:
        """Produce a consensus verdict for a discussion session."""
        llm_summaries = [client.generate_summary(session) for client in self._llm_clients]
        llm_issues = [client.identify_issues(session) for client in self._llm_clients]
        validator_flags = [validator.evaluate(session) for validator in self._validators]

        flattened_issues: List[str] = []
        for issue_list in llm_issues + validator_flags:
            flattened_issues.extend(issue_list)

        consensus_summary = self._consensus_summary(llm_summaries)
        unique_issues = sorted(set(flattened_issues))

        metadata = {
            "summaries": llm_summaries,
            "llm_models": [client.model for client in self._llm_clients],
            "validator_names": [validator.name for validator in self._validators],
        }
        return JudgeVerdict(
            judge_id=self.judge_id,
            summary=consensus_summary,
            open_issues=unique_issues,
            metadata=metadata,
        )

    def _consensus_summary(self, summaries: Iterable[str]) -> str:
        """Choose a summary based on plurality voting with fallback."""
        non_empty = [summary.strip() for summary in summaries if summary.strip()]
        if not non_empty:
            return "No summary available."
        try:
            return mode(non_empty)
        except Exception:
            return non_empty[0]
