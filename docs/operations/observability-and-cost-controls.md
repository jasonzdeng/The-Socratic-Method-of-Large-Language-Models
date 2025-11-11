# Observability and Cost Control Review

Use this runbook to close the production readiness review for monitoring, alerting, and spend management. Each section includes validation steps, tooling references, and required artifacts for sign-off.

## Telemetry Coverage
- **Distributed tracing**
  - Confirm OpenTelemetry spans wrap all orchestrator pathways (agent turns, tool calls, judge deliberations).
  - Verify span attributes include vendor, model, tool, latency, and cost metadata to enable per-vendor drilldowns.
  - Run a synthetic end-to-end discussion and export the trace graph to the review folder.
- **Metrics dashboards**
  - Validate Prometheus exporters expose the following baseline metrics and that Grafana visualizations exist for each:
    - Request latency/throughput per API route and background worker queue.
    - Tool invocation counts, error rates, and P95/P99 latencies broken down by provider.
    - Cost-per-session, cost-per-round, tool budget utilization, and Sonar Pro search spend.
  - Ensure dashboard panels include descriptive runbooks linked via annotations.
- **Log hygiene**
  - Confirm centralized logging pipelines (e.g., Loki/ELK) capture structured JSON logs with correlation IDs while redacting PII and API secrets.
  - Review log retention, access controls, and backup configurations for compliance alignment.
  - Trigger sample warnings/errors to confirm parsing and alert routing.
- **Instrumentation gaps**
  - Maintain an issue list for missing metrics or spans; provide owner, fix version, and mitigation plan before sign-off.

## Alerting and Guardrails
- Configure Grafana alert rules for the following categories with actionable thresholds and escalation targets:
  - Latency breaches for debate rounds (>2× baseline), judge summaries, or tool invocations.
  - Error rate spikes (HTTP 5xx, tool call failures, model timeouts) exceeding 1% of traffic.
  - Cost burn-rate anomalies relative to daily and weekly budgets.
- Test alert delivery to PagerDuty/Slack channels via sandbox events and confirm runbooks auto-populate in the notification payload.
- Document auto-remediation scripts (e.g., queue drain, model downgrade) and ensure SRE on-call can trigger them within five minutes.

## Load & Resilience Validation
- Execute a four-hour load soak that mirrors peak traffic assumptions; capture latency, error, and cost metrics.
- Perform chaos drills for the following scenarios and document system responses:
  - Loss of a primary LLM vendor (failover to alternate provider).
  - Degraded Perplexity Sonar search availability.
  - Redis/queue outage impacting orchestration throughput.
- Record remediation steps, owner acknowledgements, and residual risks.

## Cost Control Checklist
- Enforce per-discussion and per-agent budgets at the orchestration layer; automatically pause sessions when thresholds are exceeded and notify users with remediation options.
- Enable dynamic model downgrades (e.g., switch from frontier models to cost-efficient alternates) while preserving minimum reasoning quality scores.
- Audit vendor usage reports weekly; reconcile against the internal ledger and update unit-cost assumptions.
- Implement automated pruning of cold storage artifacts and discussion logs according to retention policy to reduce storage cost.
- Review cost anomaly detection alerts from the finance liaison and confirm they map to escalation procedures.

## Compliance & Security Validation
- Re-run penetration tests on observability stack endpoints and track findings to closure.
- Confirm secrets rotation for API keys and service tokens feeding monitoring systems; store rotation evidence in the security vault.
- Validate data residency constraints and encryption at rest/in transit for telemetry data stores; document any third-country transfers.
- Review audit logs for privileged access to monitoring dashboards and ensure quarterly access recertification is scheduled.

## Deliverables & Sign-off
- Capture screenshots/exports of dashboards post-review and archive them under `docs/operations/review-artifacts/` with timestamps.
- Document any gaps and file follow-up tickets with owners, due dates, and interim mitigations.
- Obtain written approvals from engineering, finance, and compliance stakeholders before launch freeze; store approvals alongside the review artifacts.
