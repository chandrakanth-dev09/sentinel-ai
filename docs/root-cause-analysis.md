# Root Cause Analysis

`POST /api/v1/incidents/analyze` reads persisted metrics, detected anomaly events, application logs, and the directed service dependency graph for a requested time window. It does not call an LLM or infer evidence that is not stored.

## Evidence signals

- An anomaly event contributes the model's normalized score, severity, and feature deviation context.
- An `ERROR` or `CRITICAL` log contributes its service, event timestamp, error type, trace ID, request ID, and message.
- A metric is flagged by explicit initial thresholds: zero database connections, response time at least 500 ms, error rate at least 5%, or availability below 99%.

These are rule-based signals, not universal service-health limits. Thresholds will become configurable with the settings module.

## Ranking

For each service with evidence, the engine calculates:

- 50% downstream coverage: fraction of other affected services reachable from this candidate in the dependency graph.
- 30% event precedence: how early this service's first signal occurred within the analysis window.
- 20% evidence strength: mean strength of the candidate's anomaly, error-log, and metric signals.

The combined score is used only to rank candidates. It is not a probability or calibrated confidence. A probable root is returned only when the top-ranked service is upstream of at least one other affected service. Without dependency coverage, the result reports evidence and alternatives but leaves the root cause unset.

The response includes an ordered evidence timeline, affected service names, alternatives, a plain-language ranking method, and investigation steps. Evidence summaries and values originate from the stored telemetry.
