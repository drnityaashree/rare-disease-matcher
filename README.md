# Secure Distributed Clinical Rare Disease Case Matching System

A distributed healthcare case-matching prototype that uses machine-learning-based similarity retrieval to identify related rare-disease cases across simulated hospital nodes without centralizing clinical records.

> Note: This is an academic prototype built using synthetic clinical data. It is not a medical diagnostic tool and is not intended for real-world clinical decision-making.

---

## Problem Statement

Rare-disease cases are difficult to identify because relevant patient records may be scattered across different hospitals. Centralizing clinical records can introduce privacy and security concerns.

This project demonstrates a distributed approach in which each hospital stores its records locally. A central coordinator broadcasts a symptom query to registered hospital nodes, and each node returns ranked similar cases using TF-IDF vectorization and cosine similarity.

---

## System Architecture

```text
Doctor / Admin Dashboard
          |
          v
Coordinator API :8000
          |
          +---- Hospital Node A :8001 ---- Local SQLite Database
          |
          +---- Hospital Node B :8002 ---- Local SQLite Database
```

The coordinator manages node registration and query broadcasting. The hospital nodes process queries locally and return ranked, explainable case matches.

---

## Dataset Summary

The project uses a custom synthetic dataset created for prototype testing.

* 37 unique synthetic clinical case records
* 34 disease labels
* 88 symptom terms
* 2 simulated hospital nodes
* 21 local records per hospital node
* 42 node-local records across the distributed network, including intentional overlap between nodes

No real patient data is used.

---

## Machine-Learning Approach

The matching engine uses:

* TF-IDF vectorization for symptom and clinical-note representation
* Cosine similarity for case ranking
* Symptom synonym normalization
* Severity-weighted matching
* Clinical-note enrichment
* Age-context scoring
* Rare-disease filtering
* Explainable matched-symptom output

The project performs similarity-based retrieval and ranking. It does not claim clinically validated disease prediction.

---

## Key Features

### Distributed Architecture

* FastAPI coordinator service
* FastAPI hospital-node services
* Dynamic node registration
* Heartbeat monitoring
* Distributed query broadcasting
* Ranked result aggregation
* Docker Compose multi-node setup

### Database Layer

* SQLite local databases
* SQLAlchemy ORM
* Structured clinical-record storage
* Audit logging
* Duplicate-case analysis
* Symptom-evolution timeline

### ML and Analytics

* TF-IDF and cosine-similarity matching
* Severity-aware ranking
* Symptom synonym handling
* Explainable matching results
* Risk-alert scoring
* Disease hotspot detection
* Rare symptom-pattern discovery

### Prototype Security Controls

* SHA-256 hashing for simulated patient-contact values
* API-key-based access control
* Role headers
* Audit logging

> The security controls are implemented for academic demonstration purposes and require production hardening before real-world use.

### Frontend

* Static HTML, CSS, and JavaScript dashboard
* Symptom-search interface
* Ranked case-match display
* Risk-alert display
* Analytics visualization

---

## Technologies Used

* Python
* FastAPI
* SQLAlchemy
* SQLite
* Scikit-learn
* TF-IDF Vectorization
* Cosine Similarity
* HTML
* CSS
* JavaScript
* Docker Compose
* Git
* GitHub

---

## Project Structure

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
.gitignore
README.md
```

---

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/drnityaashree/rare-disease-matcher.git
cd rare-disease-matcher
```

### 2. Create and Activate a Virtual Environment

#### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Seed the Synthetic Dataset

```bash
python seed_data.py
```

---

## Start the Services Manually

### Start the Coordinator

```bash
python -m uvicorn coordinator.main:app --reload --port 8000
```

### Start Hospital Node A

Open a new PowerShell terminal:

```powershell
$env:NODE_ID="HOSPITAL_A"
$env:NODE_URL="http://127.0.0.1:8001"
$env:COORDINATOR_URL="http://127.0.0.1:8000"
python -m uvicorn node.main:app --reload --port 8001
```

### Start Hospital Node B

Open another PowerShell terminal:

```powershell
$env:NODE_ID="HOSPITAL_B"
$env:NODE_URL="http://127.0.0.1:8002"
$env:COORDINATOR_URL="http://127.0.0.1:8000"
python -m uvicorn node.main:app --reload --port 8002
```

---

## Dashboard and API Documentation

Dashboard:

```text
http://127.0.0.1:8000/dashboard
```

Coordinator API documentation:

```text
http://127.0.0.1:8000/docs
```

Hospital Node A API documentation:

```text
http://127.0.0.1:8001/docs
```

Hospital Node B API documentation:

```text
http://127.0.0.1:8002/docs
```

---

## Docker Compose Setup

Run:

```bash
docker compose up --build
```

Expected services:

```text
coordinator  -> http://127.0.0.1:8000
hospital_a   -> http://127.0.0.1:8001
hospital_b   -> http://127.0.0.1:8002
```

Verify registered nodes:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/nodes
```

---

## Sample Search Request

```json
{
  "symptoms": [
    "high temperature",
    "seizures",
    "small head"
  ],
  "severity": {
    "fever": 5,
    "seizures": 5,
    "microcephaly": 5
  },
  "notes": "infant case with neurological symptoms",
  "top_k": 3
}
```

Expected top-ranked result:

```text
Congenital Zika Syndrome
```

Expected matched symptoms:

```text
Fever
Microcephaly
Seizures
```

The system may generate a high-risk or critical-risk alert based on the severity values.

---

## Testing

Run the smoke test:

```bash
python smoke_test.py
```

Run the integration test:

```bash
python integration_test.py
```

The prototype has passed local smoke tests, integration checks, and distributed multi-node query testing using synthetic clinical records.

---

## Evaluation Status

Formal retrieval evaluation is in progress.

Future evaluation will use labelled query-to-relevant-case pairs and ranking metrics such as:

* Precision@K
* Recall@K
* Mean Reciprocal Rank
* Top-K retrieval accuracy

The current version does not claim a clinically validated accuracy score.

---

## Limitations

* The dataset is synthetic and intended for academic prototype testing.
* The system is not a medical diagnostic tool.
* Similarity scores must not be interpreted as clinical recommendations.
* The security controls are demonstration-level controls and require production hardening.
* The prototype has not been connected to real hospital databases.
* Formal retrieval benchmarking is still in progress.

---

## Future Enhancements

* Evaluate retrieval performance using labelled relevance pairs
* Add Precision@K, Recall@K, and Mean Reciprocal Rank metrics
* Extend the synthetic dataset
* Improve dashboard visualizations
* Add production-grade authentication
* Add encrypted communication between nodes

---

## Author

Nityaashree D R
Computer Science and Engineering
B.N.M. Institute of Technology, Bengaluru

GitHub: [drnityaashree](https://github.com/drnityaashree)

---

## License

This project is intended for academic and educational purposes.
