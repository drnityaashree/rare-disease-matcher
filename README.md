# Secure Distributed Clinical Rare Disease Case Matching System

A demo-ready DBMS + ML + Distributed Systems project for matching rare disease cases across hospital nodes while preserving patient privacy.

## Overview

Hospitals keep clinical records in their own local SQLite databases. A central coordinator registers active hospital nodes and broadcasts symptom queries. Each node searches its local database using TF-IDF and cosine similarity, then returns ranked, explainable rare disease matches.

## Architecture

```text
Doctor/Admin Dashboard
        |
        v
Coordinator API :8000
        |
        +---- Hospital Node A :8001 ---- SQLite DB
        |
        +---- Hospital Node B :8002 ---- SQLite DB
```

## Features

- SQLAlchemy ORM with SQLite
- FastAPI coordinator and hospital node services
- Dynamic node registration and heartbeat monitoring
- TF-IDF + cosine similarity case matching
- Symptom synonym handling
- Explainable AI matching results
- Risk alert scoring, including CRITICAL alerts
- SHA-256 patient contact hashing
- API key and role-based access headers
- Audit logging
- Disease hotspot detection
- Symptom evolution timeline
- Duplicate case detection
- Rare symptom pattern discovery
- Static healthcare dashboard
- Docker Compose multi-node setup

## Setup

```powershell
pip install -r requirements.txt
python seed_data.py
```

Start coordinator:

```powershell
python -m uvicorn coordinator.main:app --reload --port 8000
```

Start hospital node:

```powershell
$env:NODE_ID="HOSPITAL_A"
$env:NODE_URL="http://127.0.0.1:8001"
$env:COORDINATOR_URL="http://127.0.0.1:8000"
python -m uvicorn node.main:app --reload --port 8001
```

Open dashboard:

```text
http://127.0.0.1:8000/dashboard
```

API docs:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8001/docs
```

## Security Headers

Protected node APIs require:

```text
X-API-Key: SUPER_SECURE_RARE_DISEASE_NETWORK_KEY_2026
X-Role: admin
```

## Sample Search

```json
{
  "symptoms": ["high temperature", "seizures", "small head"],
  "severity": {
    "fever": 5,
    "seizures": 5,
    "microcephaly": 5
  },
  "notes": "infant case with neurological symptoms",
  "top_k": 3
}
```

Expected top result:

```text
Congenital Zika Syndrome
Matched symptoms: Fever, Microcephaly, Seizures
Risk: HIGH or CRITICAL
```

## Docker

```powershell
docker compose up --build
```

Expected services:

```text
coordinator  -> http://127.0.0.1:8000
hospital_a   -> http://127.0.0.1:8001
hospital_b   -> http://127.0.0.1:8002
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/nodes
```

## Testing

```powershell
python smoke_test.py
python integration_test.py
```

## Final Folder Structure

```text
coordinator/
  Dockerfile
  main.py
  registry.py

frontend/
  index.html
  styles.css
  app.js

node/
  Dockerfile
  main.py
  core/
    analytics.py
    crypto.py
    matching.py

shared/
  database.py
  models.py
  schemas.py
  seed_data.py

integration_test.py
smoke_test.py
seed_data.py
setup_db.py
docker-compose.yml
requirements.txt
```

## Screenshots

Run the project and capture:

- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/docs`
- successful `/find-matches` response
- `/nodes` showing active hospital nodes
