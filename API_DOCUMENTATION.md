# API Documentation

## Coordinator API

Base URL:

```text
http://127.0.0.1:8000
```

### GET /

Returns coordinator health and registered active nodes.

### GET /nodes

Returns active node metadata.

### POST /register

Registers a hospital node.

Request:

```json
{
  "node_id": "HOSPITAL_A",
  "url": "http://127.0.0.1:8001"
}
```

### POST /heartbeat

Updates node last-seen timestamp.

Request:

```json
{
  "node_id": "HOSPITAL_A"
}
```

### POST /find-matches

Broadcasts symptoms to active hospital nodes and returns ranked matches.

Request:

```json
{
  "symptoms": ["high temperature", "seizures", "small head"],
  "severity": {"fever": 5, "seizures": 5, "microcephaly": 5},
  "notes": "infant case with neurological symptoms",
  "top_k": 3
}
```

### GET /network-summary

Aggregates total records, logs, and online nodes.

### GET /network-analytics

Aggregates hotspots, rare patterns, duplicates, risk alerts, and symptom timeline.

## Hospital Node API

Base URL:

```text
http://127.0.0.1:8001
```

Protected endpoints require:

```text
X-API-Key: SUPER_SECURE_RARE_DISEASE_NETWORK_KEY_2026
X-Role: admin
```

### GET /

Node health.

### GET /status-summary

Node record counts and audit status.

### GET /symptoms

Returns symptoms from the local database.

### GET /cases

Returns shareable clinical cases. Protected.

### POST /search

Runs local TF-IDF cosine similarity matching. Protected.

### GET /audit-logs

Returns recent anonymized match logs. Protected.

### GET /analytics/hotspots

Detects repeated disease and symptom patterns.

### GET /analytics/symptom-evolution

Returns date-wise symptom progression.

### GET /analytics/duplicates

Detects highly similar clinical records.

### GET /analytics/rare-patterns

Flags uncommon symptom combinations.

### GET /analytics/risk-alerts

Returns records with multiple high-severity symptoms.
