# Demo Script

## 1. Start Backend

Terminal 1:

```powershell
python -m uvicorn coordinator.main:app --reload --port 8000
```

Terminal 2:

```powershell
$env:NODE_ID="HOSPITAL_A"
$env:NODE_URL="http://127.0.0.1:8001"
$env:COORDINATOR_URL="http://127.0.0.1:8000"
python -m uvicorn node.main:app --reload --port 8001
```

## 2. Show Node Registration

Open:

```text
http://127.0.0.1:8000/nodes
```

Expected:

```text
HOSPITAL_A registered
```

## 3. Show Dashboard

Open:

```text
http://127.0.0.1:8000/dashboard
```

Login:

```text
Role: Admin
API Key: SUPER_SECURE_RARE_DISEASE_NETWORK_KEY_2026
```

Show:

- Active nodes
- Clinical record count
- Network status
- Node monitoring

## 4. Run Symptom Search

Symptoms:

```text
high temperature, seizures, small head
```

Severity:

```text
Critical
```

Expected top result:

```text
Congenital Zika Syndrome
Matched symptoms: Fever, Microcephaly, Seizures
Risk: HIGH or CRITICAL
```

## 5. Show Analytics

Open Analytics tab and explain:

- Disease hotspots
- Risk alerts
- Rare patterns
- Duplicate detection
- Symptom evolution

## 6. Show Swagger

Coordinator:

```text
http://127.0.0.1:8000/docs
```

Hospital node:

```text
http://127.0.0.1:8001/docs
```

## 7. Run Tests

```powershell
python integration_test.py
```

Expected:

```text
PASS: node health
PASS: symptoms loaded
PASS: node ML search
PASS: zika top result
PASS: risk alert generated
PASS: security rejects missing key
PASS: risk analytics
PASS: coordinator health
All integration checks completed.
```
