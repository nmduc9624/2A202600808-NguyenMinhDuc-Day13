# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: Nguyễn Minh Đức
- [REPO_URL]: [nmduc9624/Lab13-Observability.git](https://github.com/nmduc9624/Lab13-Observability.git)
- [MEMBERS]:
  - Member A: Nguyễn Minh Đức | Role: Logging & PII
  - Member B: Nguyễn Minh Đức | Role: Tracing & Enrichment
  - Member C: Nguyễn Minh Đức | Role: SLO & Alerts
  - Member D: Nguyễn Minh Đức | Role: Load Test & Dashboard
  - Member E: Nguyễn Minh Đức | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 30
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_TRACE_LIST_SCREENSHOT]: docs/evidence/01-langfuse-trace-list.png
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: docs/evidence/03-json-correlation-id.png
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: docs/evidence/04-pii-redaction.png
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: docs/evidence/02-trace-waterfall.png
- [TRACE_WATERFALL_EXPLANATION]: The trace shows the `chat-response` request with nested `agent-run` and `fake-llm-generate` observations. The trace metadata includes the hashed user id, session id, feature, model, and correlation id so the same request can be followed from dashboard metrics to Langfuse trace to JSON log lines.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: docs/evidence/05-dashboard-6-panels.png
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | 2653ms |
| Error Rate | < 2% | 28d | 0% |
| Cost Budget | < $2.5/day | 1d | $0.0615 |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: docs/evidence/06-alert-rules-runbook.png
- [SAMPLE_RUNBOOK_LINK]: [docs/alerts.md#1-high-latency-p95](docs/alerts.md#1-high-latency-p95)

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: After enabling `rag_slow`, client-side request latency increased sharply and the app metrics showed latency P95 rising from 154ms to 2653ms while errors stayed at 0%.
- [ROOT_CAUSE_PROVED_BY]: The high-latency request logs show `latency_ms` around 2651-2653ms with correlation ids such as `req-13c206bd`, `req-3055c2f8`, and `req-7af30175`. In Langfuse, the matching `chat-response` trace shows the slow agent path and the request metadata links back to the same correlation id.
- [FIX_ACTION]: Disabled the incident with `python scripts/inject_incident.py --scenario rag_slow --disable` and confirmed `/health` reported `rag_slow: false`.
- [PREVENTIVE_MEASURE]: Keep the `high_latency_p95` alert active, use the runbook in `docs/alerts.md#1-high-latency-p95`, inspect top slow traces first, and add fallback retrieval or query truncation when retrieval latency dominates.

---

## 5. Individual Contributions & Evidence

### Nguyễn Minh Đức
- [TASKS_COMPLETED]: Implemented correlation ID middleware, structured JSON logging, request context enrichment, recursive PII redaction, Langfuse tracing with trace/span metadata, metrics validation, dashboard route, alert/runbook configuration, load testing, incident injection, and final report preparation.
- [EVIDENCE_LINK]: [Repository](https://github.com/nmduc9624/Lab13-Observability.git)

### Nguyễn Minh Đức - Logging & PII
- [TASKS_COMPLETED]: Added `x-request-id` propagation, bound `correlation_id` to structlog contextvars, hashed user ids, enriched API logs with `session_id`, `feature`, `model`, and `env`, and verified PII redaction for email, phone, and credit-card examples.
- [EVIDENCE_LINK]: [Repository](https://github.com/nmduc9624/Lab13-Observability.git)

### Nguyễn Minh Đức - Tracing & Enrichment
- [TASKS_COMPLETED]: Configured Langfuse credentials from `.env`, added trace metadata and tags, captured sanitized trace input/output previews, created generation observations for fake LLM calls, and flushed traces after requests so they appear in Langfuse.
- [EVIDENCE_LINK]: [Repository](https://github.com/nmduc9624/Lab13-Observability.git)

### Nguyễn Minh Đức - SLO & Alerts
- [TASKS_COMPLETED]: Verified SLO targets for latency, error rate, cost, and quality; confirmed three alert rules in `config/alert_rules.yaml`; and linked alerts to the runbook in `docs/alerts.md`.
- [EVIDENCE_LINK]: [Repository](https://github.com/nmduc9624/Lab13-Observability.git)

### Nguyễn Minh Đức - Load Test, Dashboard & Demo
- [TASKS_COMPLETED]: Ran load tests with concurrency 5, validated logs at 100/100, created a 6-panel dashboard at `/dashboard`, executed the `rag_slow` incident scenario, and documented the root-cause workflow from metrics to traces to logs.
- [EVIDENCE_LINK]: [Repository](https://github.com/nmduc9624/Lab13-Observability.git)

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: Added cost tracking through `cost_usd`, `total_cost_usd`, and dashboard cost panel. Evidence: docs/evidence/05-dashboard-6-panels.png
- [BONUS_AUDIT_LOGS]: Not submitted.
- [BONUS_CUSTOM_METRIC]: Added quality proxy tracking through `quality_score` and `quality_avg`, displayed as the dashboard quality panel. Evidence: docs/evidence/05-dashboard-6-panels.png
