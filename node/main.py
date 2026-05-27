import asyncio
import httpx
import os
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from shared.schemas import ClinicalRecordInput, DiseaseInput, MatchRequest, MatchResponse, SymptomInput
from shared.database import Base, SessionLocal, engine, get_db
import uuid
from node.core.crypto import hash_patient_pii, require_role, verify_api_key
from shared.models import ClinicalRecord, Diagnosis, Hospital, Patient, Symptom, RecordSymptom, CaseMatchLog

from node.core.analytics import (
    disease_hotspots,
    duplicate_cases,
    emergency_alerts,
    rare_patterns,
    symptom_evolution,
)
from node.core.matching import MLMatcher
from shared.seed_data import seed_database

# Node Configuration
NODE_ID = os.getenv("NODE_ID", "HOSPITAL_NODE_1")
NODE_URL = os.getenv("NODE_URL", "http://127.0.0.1:8001")
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://127.0.0.1:8000")
HOSPITAL_NAME = os.getenv("HOSPITAL_NAME") or NODE_ID.replace("_", " ").title()

def _local_counts():
    with SessionLocal() as db:
        return {
            "records": db.query(ClinicalRecord).filter(ClinicalRecord.is_shareable.is_(True)).count(),
            "symptoms": db.query(Symptom).count(),
        }

async def register_with_coordinator():
    counts = _local_counts()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COORDINATOR_URL}/register",
            json={
                "node_id": NODE_ID,
                "url": NODE_URL,
                "hospital_name": HOSPITAL_NAME,
                **counts,
            },
        )
        print(f"Registration response: {response.status_code}")

async def heartbeat_task():
    """Sends a heartbeat to the coordinator every 15 seconds."""
    while True:
        try:
            counts = _local_counts()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{COORDINATOR_URL}/heartbeat",
                    json={"node_id": NODE_ID, "hospital_name": HOSPITAL_NAME, **counts},
                )
                if response.status_code == 200 and response.json().get("status") == "Unknown Node":
                    await register_with_coordinator()
        except Exception as e:
            pass # Silent fail if coordinator is offline
        await asyncio.sleep(15)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if os.getenv("AUTO_SEED", "true").lower() == "true":
        with SessionLocal() as db:
            if db.query(ClinicalRecord).count() == 0:
                seed_database(hospital_name=HOSPITAL_NAME, node_id=NODE_ID)

    # Startup Action: Register with Coordinator
    try:
        await register_with_coordinator()
    except Exception as e:
        print(f"Could not register with coordinator: {e}")
    
    # Start Heartbeat
    task = asyncio.create_task(heartbeat_task())
    
    yield
    
    # Shutdown Action
    task.cancel()

app = FastAPI(lifespan=lifespan)


def _records_query(db: Session):
    return (
        db.query(ClinicalRecord)
        .options(
            joinedload(ClinicalRecord.record_symptoms).joinedload(RecordSymptom.symptom),
            joinedload(ClinicalRecord.hospital),
            joinedload(ClinicalRecord.diagnosis),
        )
        .filter(ClinicalRecord.is_shareable.is_(True))
    )

def _slug_id(prefix, value):
    cleaned = "".join(char if char.isalnum() else "-" for char in value.upper()).strip("-")
    return f"{prefix}-{cleaned[:36]}" or f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

def _get_or_create_hospital(db: Session, name: str):
    hospital = db.query(Hospital).filter(Hospital.name == name).first()
    if hospital:
        return hospital
    hospital = Hospital(id=_slug_id("HOSP", name), name=name, location="Manual Entry", public_key="manual-entry")
    db.add(hospital)
    db.flush()
    return hospital

def _get_or_create_diagnosis(db: Session, name: str, icd10_code: str | None = None):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.disease_name == name).first()
    if diagnosis:
        return diagnosis
    diagnosis = Diagnosis(id=_slug_id("DIAG", name), disease_name=name, icd10_code=icd10_code or f"MAN-{uuid.uuid4().hex[:6].upper()}")
    db.add(diagnosis)
    db.flush()
    return diagnosis

def _get_or_create_symptom(db: Session, name: str, snomed_code: str | None = None):
    symptom = db.query(Symptom).filter(Symptom.symptom_name == name).first()
    if symptom:
        return symptom
    symptom = Symptom(id=_slug_id("SYM", name), symptom_name=name, snomed_code=snomed_code or f"MAN-{uuid.uuid4().hex[:6].upper()}")
    db.add(symptom)
    db.flush()
    return symptom

@app.get("/")
def health_check():
    return {"status": "Hospital Node is running", "node_id": NODE_ID, "hospital_name": HOSPITAL_NAME}

@app.get("/status-summary")
def status_summary(db: Session = Depends(get_db)):
    record_count = db.query(ClinicalRecord).filter(ClinicalRecord.is_shareable.is_(True)).count()
    symptom_count = db.query(Symptom).count()
    hospital_count = db.query(Hospital).count()
    audit_count = db.query(CaseMatchLog).count()
    return {
        "node_id": NODE_ID,
        "hospital_name": HOSPITAL_NAME,
        "status": "online",
        "records": record_count,
        "symptoms": symptom_count,
        "hospitals": hospital_count,
        "audit_logs": audit_count,
    }

@app.get("/symptoms")
def list_symptoms(db: Session = Depends(get_db)):
    symptoms = db.query(Symptom).order_by(Symptom.symptom_name).all()
    return {
        "total": len(symptoms),
        "symptoms": [
            {
                "id": symptom.id,
                "name": symptom.symptom_name,
                "snomed_code": symptom.snomed_code,
            }
            for symptom in symptoms
        ],
    }

@app.post("/admin/diseases")
def add_disease(
    payload: DiseaseInput,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin"])),
):
    diagnosis = _get_or_create_diagnosis(db, payload.disease_name.strip(), payload.icd10_code)
    db.commit()
    return {"status": "saved", "id": diagnosis.id, "disease_name": diagnosis.disease_name, "icd10_code": diagnosis.icd10_code}

@app.post("/admin/symptoms")
def add_symptom(
    payload: SymptomInput,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin"])),
):
    symptom = _get_or_create_symptom(db, payload.symptom_name.strip().title(), payload.snomed_code)
    db.commit()
    return {"status": "saved", "id": symptom.id, "symptom_name": symptom.symptom_name, "snomed_code": symptom.snomed_code}

@app.post("/admin/clinical-records")
def add_clinical_record(
    payload: ClinicalRecordInput,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin"])),
):
    hospital = _get_or_create_hospital(db, payload.hospital_name or "Manual Clinical Registry")
    diagnosis = _get_or_create_diagnosis(db, payload.disease_name.strip())
    patient_label = payload.patient_label or f"Manual Patient {uuid.uuid4().hex[:6].upper()}"
    patient = Patient(
        id=str(uuid.uuid4()),
        hospital_id=hospital.id,
        full_name=patient_label,
        dob=None,
        gender=None,
        contact_hash=hash_patient_pii(patient_label),
    )
    db.add(patient)
    db.flush()

    record = ClinicalRecord(
        id=str(uuid.uuid4()),
        patient_id=patient.id,
        hospital_id=hospital.id,
        diagnosis_id=diagnosis.id,
        age_at_encounter=payload.age_at_encounter,
        notes=payload.notes,
        is_shareable=payload.is_shareable,
        record_date=date.today(),
    )
    db.add(record)
    db.flush()

    for symptom_name, severity in payload.symptoms.items():
        symptom = _get_or_create_symptom(db, symptom_name.strip().title())
        db.add(RecordSymptom(record_id=record.id, symptom_id=symptom.id, severity=max(1, min(int(severity), 5))))

    db.commit()
    return {"status": "saved", "record_id": record.id, "disease_name": diagnosis.disease_name, "symptom_count": len(payload.symptoms)}

@app.get("/cases")
def list_shareable_cases(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin", "clinician"])),
):
    records = _records_query(db).order_by(ClinicalRecord.record_date.desc()).all()
    return {
        "total": len(records),
        "cases": [
            {
                "record_id": record.id,
                "hospital_name": record.hospital.name if record.hospital else "Unknown",
                "diagnosis": record.diagnosis.disease_name if record.diagnosis else "Undiagnosed",
                "symptoms": [
                    {
                        "name": item.symptom.symptom_name,
                        "severity": item.severity,
                    }
                    for item in record.record_symptoms
                ],
                "record_date": record.record_date.isoformat() if record.record_date else None,
            }
            for record in records
        ],
    }

@app.post("/search", response_model=MatchResponse)
def search(
    request: MatchRequest, 
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin", "clinician"])),
):
    """
    Searches the local hospital node database for matching clinical records
    based on the provided symptoms using Advanced ML (TF-IDF & Cosine Similarity).
    Access is secured via API Key.
    """
    
    # Fetch all clinical records eagerly loading the symptoms, diagnosis, and hospital
    records = _records_query(db).all()

    # Initialize the Machine Learning Matcher
    matcher = MLMatcher(records)
    
    # Get top matches
    matches = matcher.find_matches(
        request.symptoms,
        top_k=request.top_k,
        severity=request.severity,
        notes=request.notes,
    )
    
    # PHASE 5: Secure Anonymized Audit Logging
    for match in matches:
        log_entry = CaseMatchLog(
            id=str(uuid.uuid4()),
            querying_hospital_id="COORDINATOR",
            responding_hospital_id=NODE_ID,
            matched_record_id=match["record_id"],
            similarity_score=match["similarity_score"]
        )
        db.add(log_entry)
    if matches:
        db.commit()
    
    return MatchResponse(
        results=matches,
        message="Search completed successfully." if matches else "No matches found."
    )

@app.get("/audit-logs")
def audit_logs(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin"])),
):
    logs = db.query(CaseMatchLog).order_by(CaseMatchLog.timestamp.desc()).limit(25).all()
    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "querying_hospital_id": log.querying_hospital_id,
                "responding_hospital_id": log.responding_hospital_id,
                "matched_record_id": log.matched_record_id,
                "similarity_score": log.similarity_score,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ],
    }

@app.get("/analytics/hotspots")
def hotspots(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin", "clinician"])),
):
    return {"hotspots": disease_hotspots(_records_query(db).all())}

@app.get("/analytics/symptom-evolution")
def evolution(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin", "clinician"])),
):
    return {"timeline": symptom_evolution(_records_query(db).all())}

@app.get("/analytics/duplicates")
def duplicates(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin"])),
):
    duplicates_found = duplicate_cases(_records_query(db).all())
    return {"total": len(duplicates_found), "duplicates": duplicates_found}

@app.get("/analytics/rare-patterns")
def rare_pattern_report(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin", "clinician"])),
):
    patterns = rare_patterns(_records_query(db).all())
    return {"total": len(patterns), "patterns": patterns}

@app.get("/analytics/risk-alerts")
def risk_alerts(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
    role: str = Depends(require_role(["admin", "clinician"])),
):
    alerts = emergency_alerts(_records_query(db).all())
    return {"total": len(alerts), "alerts": alerts}
