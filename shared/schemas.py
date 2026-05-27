from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class MatchRequest(BaseModel):
    symptoms: List[str]  # e.g. ["fever", "rash"]
    top_k: int = Field(default=5, ge=1, le=20)
    severity: Dict[str, int] = Field(default_factory=dict)
    notes: Optional[str] = None

class MatchDetail(BaseModel):
    record_id: str
    hospital_name: str
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    disease_name: Optional[str] = None
    similarity_score: float
    confidence_score: str
    explanation: str
    matched_symptoms: List[str] = Field(default_factory=list)
    disease_classification: str = "unknown"
    confidence_breakdown: Dict[str, float] = Field(default_factory=dict)
    rare_disease_probability: float
    risk_alert: str
    age_at_encounter: Optional[int] = None
    record_date: Optional[str] = None

class MatchResponse(BaseModel):
    results: List[MatchDetail]
    message: str

class DiseaseInput(BaseModel):
    disease_name: str
    icd10_code: Optional[str] = None

class SymptomInput(BaseModel):
    symptom_name: str
    snomed_code: Optional[str] = None

class ClinicalRecordInput(BaseModel):
    disease_name: str
    symptoms: Dict[str, int]
    notes: Optional[str] = None
    age_at_encounter: Optional[int] = None
    hospital_name: Optional[str] = None
    patient_label: Optional[str] = None
    is_shareable: bool = True

class NodeRegistration(BaseModel):
    node_id: str
    url: str
    hospital_name: Optional[str] = None
    records: int = 0
    symptoms: int = 0

class HeartbeatRequest(BaseModel):
    node_id: str
    records: int = 0
    symptoms: int = 0
    hospital_name: Optional[str] = None
