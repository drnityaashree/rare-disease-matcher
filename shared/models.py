from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Hospital(Base):
    __tablename__ = "hospital"
    
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(100))
    public_key = Column(String(256))
    
    records = relationship("ClinicalRecord", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")

class Patient(Base):
    __tablename__ = "patient"
    
    id = Column(String(50), primary_key=True, index=True)
    hospital_id = Column(String(50), ForeignKey("hospital.id"))
    full_name = Column(String(100), nullable=False)
    dob = Column(Date)
    gender = Column(String(10))
    contact_hash = Column(String(256))
    
    hospital = relationship("Hospital", back_populates="patients")
    records = relationship("ClinicalRecord", back_populates="patient")

class Diagnosis(Base):
    __tablename__ = "diagnosis"
    
    id = Column(String(50), primary_key=True, index=True)
    disease_name = Column(String(100), nullable=False)
    icd10_code = Column(String(20), unique=True)
    
    records = relationship("ClinicalRecord", back_populates="diagnosis")

class Symptom(Base):
    __tablename__ = "symptom"
    
    id = Column(String(50), primary_key=True, index=True)
    symptom_name = Column(String(100), nullable=False)
    snomed_code = Column(String(50), unique=True)
    
    record_symptoms = relationship("RecordSymptom", back_populates="symptom")

class ClinicalRecord(Base):
    __tablename__ = "clinical_record"
    
    id = Column(String(50), primary_key=True, index=True)
    patient_id = Column(String(50), ForeignKey("patient.id"))
    hospital_id = Column(String(50), ForeignKey("hospital.id"))
    diagnosis_id = Column(String(50), ForeignKey("diagnosis.id"), nullable=True)
    
    age_at_encounter = Column(Integer)
    notes = Column(String(500))
    is_shareable = Column(Boolean, default=True)
    record_date = Column(Date)
    
    patient = relationship("Patient", back_populates="records")
    hospital = relationship("Hospital", back_populates="records")
    diagnosis = relationship("Diagnosis", back_populates="records")
    record_symptoms = relationship("RecordSymptom", back_populates="record")

class RecordSymptom(Base):
    __tablename__ = "record_symptom"
    
    record_id = Column(String(50), ForeignKey("clinical_record.id"), primary_key=True)
    symptom_id = Column(String(50), ForeignKey("symptom.id"), primary_key=True)
    severity = Column(Integer) # Expected range: 1 to 5
    
    record = relationship("ClinicalRecord", back_populates="record_symptoms")
    symptom = relationship("Symptom", back_populates="record_symptoms")

class CaseMatchLog(Base):
    __tablename__ = "case_match_log"
    
    id = Column(String(50), primary_key=True, index=True)
    querying_hospital_id = Column(String(50))
    responding_hospital_id = Column(String(50))
    matched_record_id = Column(String(50))
    similarity_score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
