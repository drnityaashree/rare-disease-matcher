from datetime import date
import uuid

from sqlalchemy.orm import Session

from node.core.crypto import hash_patient_pii
from shared.database import Base, engine
from shared.models import (
    CaseMatchLog,
    ClinicalRecord,
    Diagnosis,
    Hospital,
    Patient,
    RecordSymptom,
    Symptom,
)


def _new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _code(prefix, index):
    return f"{prefix}-{index:03d}"


def _clear_database(session):
    session.query(CaseMatchLog).delete()
    session.query(RecordSymptom).delete()
    session.query(ClinicalRecord).delete()
    session.query(Patient).delete()
    session.query(Symptom).delete()
    session.query(Diagnosis).delete()
    session.query(Hospital).delete()
    session.commit()


SYMPTOM_NAMES = [
    "Fever", "Fatigue", "Headache", "Body Ache", "Cough", "Sore Throat", "Runny Nose",
    "Chills", "Sweating", "Rash", "Joint Pain", "Low Platelet Count", "Abdominal Pain",
    "Diarrhea", "Vomiting", "Nausea", "Dehydration", "Dizziness", "Shortness Of Breath",
    "Chest Pain", "Wheezing", "Chest Tightness", "Seizures", "Loss Of Consciousness",
    "Confusion", "Microcephaly", "Developmental Delay", "Developmental Regression",
    "Delayed Milestones", "Vision Loss", "Muscle Weakness", "Progressive Weakness",
    "Respiratory Weakness", "Neuropathic Pain", "Kidney Issue", "Enlarged Spleen",
    "Bone Pain", "Anemia", "Chorea", "Behavior Change", "Cognitive Decline",
    "Family History", "Liver Dysfunction", "Tremor", "Jaundice", "Loss Of Speech",
    "Hand Wringing", "Hypotonia", "Muscle Wasting", "Difficulty Swallowing",
    "Tall Stature", "Lens Dislocation", "Aortic Dilation", "Joint Laxity",
    "Joint Hypermobility", "Easy Bruising", "Skin Hyperextensibility", "Chronic Pain",
    "Red Eyes", "Swollen Lymph Nodes", "Movement Disorder", "Feeding Difficulty",
    "Obesity", "Numbness", "Areflexia", "Weight Loss", "Low Blood Pressure",
    "Hyperpigmentation", "Light Sensitivity", "Conjunctivitis", "Retro Orbital Pain",
    "Night Sweats", "Mouth Ulcers", "Photosensitivity", "Proteinuria", "Palpitations",
    "Heat Intolerance", "Goiter", "Persistent Cough", "Blood In Sputum",
    "Recurrent Fever", "Swollen Feet", "Burning Pain", "Hepatomegaly",
    "Growth Delay", "Blue Sclera", "Frequent Fractures", "Hearing Loss",
]


RECORDS = [
    ("Viral Fever", "B34.9", 22, "Mild fever with fatigue, headache, and body ache for two days. No red flag symptoms.", [("Fever", 2), ("Fatigue", 2), ("Headache", 2), ("Body Ache", 2)], date(2026, 1, 5), "bnmit"),
    ("Dengue Fever", "A90", 19, "High fever, rash, severe body ache, joint pain, and low platelet count after mosquito exposure.", [("Fever", 4), ("Rash", 3), ("Joint Pain", 4), ("Low Platelet Count", 5), ("Headache", 3)], date(2026, 1, 11), "bnmit"),
    ("Malaria", "B54", 31, "Intermittent fever with chills, sweating, fatigue, and travel to endemic area.", [("Fever", 4), ("Chills", 4), ("Sweating", 3), ("Fatigue", 3)], date(2026, 1, 18), "bnmit"),
    ("Typhoid Fever", "A01.0", 25, "Persistent fever, abdominal pain, diarrhea, fatigue, and contaminated food exposure.", [("Fever", 4), ("Abdominal Pain", 3), ("Diarrhea", 3), ("Fatigue", 3)], date(2026, 1, 23), "bnmit"),
    ("Influenza", "J11.1", 29, "Acute fever with cough, sore throat, headache, and body ache during seasonal flu cluster.", [("Fever", 3), ("Cough", 3), ("Sore Throat", 2), ("Headache", 2), ("Body Ache", 3)], date(2026, 2, 3), "bnmit"),
    ("Migraine", "G43.9", 34, "Recurrent severe headache with nausea, vomiting, and light sensitivity. Neurological exam normal.", [("Headache", 5), ("Nausea", 3), ("Vomiting", 2), ("Light Sensitivity", 5)], date(2026, 2, 8), "bnmit"),
    ("Food Poisoning", "A05.9", 17, "Vomiting, diarrhea, abdominal pain, dehydration, and dizziness after restaurant meal.", [("Vomiting", 4), ("Diarrhea", 4), ("Abdominal Pain", 3), ("Dehydration", 3), ("Dizziness", 2)], date(2026, 2, 15), "bnmit"),
    ("Common Cold", "J00", 12, "Runny nose, sore throat, cough, mild fever, and quick recovery expected.", [("Runny Nose", 3), ("Sore Throat", 2), ("Cough", 2), ("Fever", 1)], date(2026, 2, 21), "bnmit"),
    ("Pneumonia", "J18.9", 68, "Fever, productive cough, shortness of breath, chest pain, and abnormal chest findings.", [("Fever", 4), ("Cough", 4), ("Shortness Of Breath", 5), ("Chest Pain", 4), ("Fatigue", 3)], date(2026, 3, 2), "bnmit"),
    ("Dehydration", "E86.0", 8, "Vomiting, poor oral intake, dehydration, dizziness, and fatigue after gastroenteritis.", [("Vomiting", 3), ("Dehydration", 5), ("Dizziness", 3), ("Fatigue", 3)], date(2026, 3, 8), "bnmit"),
    ("Epilepsy", "G40.9", 16, "Recurrent seizures with brief loss of consciousness, post-event confusion, and normal infection screen.", [("Seizures", 5), ("Loss Of Consciousness", 4), ("Confusion", 3)], date(2026, 3, 16), "bnmit"),
    ("Asthma", "J45.9", 14, "Wheezing, cough, shortness of breath, and chest tightness triggered by dust exposure.", [("Wheezing", 5), ("Cough", 3), ("Shortness Of Breath", 4), ("Chest Tightness", 4)], date(2026, 3, 20), "bnmit"),
    ("Systemic Lupus Erythematosus", "M32.9", 18, "Butterfly-pattern rash, persistent joint pain, fatigue, recurring low fever, and autoimmune serology pending.", [("Joint Pain", 5), ("Fatigue", 4), ("Rash", 5), ("Fever", 2)], date(2026, 3, 28), "rare"),
    ("Congenital Zika Syndrome", "A92.5", 1, "Infant with microcephaly, seizures, developmental delay, vision loss, and maternal travel exposure.", [("Fever", 3), ("Seizures", 5), ("Microcephaly", 5), ("Developmental Delay", 4), ("Vision Loss", 4)], date(2026, 4, 1), "rare"),
    ("Fabry Disease", "E75.21", 27, "Neuropathic pain, kidney involvement, corneal opacity with vision loss, fatigue, and family history.", [("Neuropathic Pain", 5), ("Kidney Issue", 5), ("Fatigue", 3), ("Vision Loss", 4), ("Family History", 4)], date(2026, 4, 4), "rare"),
    ("Gaucher Disease", "E75.22", 9, "Enlarged spleen, bone pain, anemia, fatigue, and recurrent bruising pattern.", [("Enlarged Spleen", 5), ("Bone Pain", 4), ("Anemia", 4), ("Fatigue", 3), ("Easy Bruising", 3)], date(2026, 4, 7), "rare"),
    ("Huntington Disease", "G10", 42, "Adult with chorea, behavior change, cognitive decline, progressive symptoms, and family history.", [("Chorea", 5), ("Behavior Change", 4), ("Cognitive Decline", 4), ("Family History", 5)], date(2026, 4, 10), "rare"),
    ("Wilson Disease", "E83.0", 19, "Teen with liver dysfunction, tremor, jaundice, behavior change, and low ceruloplasmin evaluation.", [("Liver Dysfunction", 5), ("Tremor", 4), ("Jaundice", 4), ("Behavior Change", 3)], date(2026, 4, 12), "rare"),
    ("Rett Syndrome", "F84.2", 4, "Pediatric developmental regression with seizures, loss of speech, hand wringing, and motor delay.", [("Developmental Regression", 5), ("Seizures", 4), ("Loss Of Speech", 5), ("Hand Wringing", 5), ("Developmental Delay", 4)], date(2026, 4, 14), "rare"),
    ("Tay-Sachs Disease", "E75.02", 2, "Infant developmental regression, seizures, vision loss, hypotonia, and progressive neurodegeneration.", [("Developmental Regression", 5), ("Seizures", 5), ("Vision Loss", 4), ("Hypotonia", 5)], date(2026, 4, 16), "rare"),
    ("Pompe Disease", "E74.02", 10, "Progressive muscle weakness, respiratory weakness, fatigue, and delayed motor milestones.", [("Muscle Weakness", 5), ("Respiratory Weakness", 4), ("Fatigue", 4), ("Delayed Milestones", 3), ("Progressive Weakness", 4)], date(2026, 4, 18), "rare"),
    ("Amyotrophic Lateral Sclerosis", "G12.21", 55, "Adult progressive weakness with muscle wasting, difficulty swallowing, respiratory weakness, and no sensory loss.", [("Progressive Weakness", 5), ("Muscle Wasting", 5), ("Difficulty Swallowing", 4), ("Respiratory Weakness", 4)], date(2026, 4, 20), "rare"),
    ("Marfan Syndrome", "Q87.4", 21, "Tall stature, lens dislocation, aortic dilation, joint laxity, and family history of sudden cardiac death.", [("Tall Stature", 4), ("Lens Dislocation", 5), ("Aortic Dilation", 5), ("Joint Laxity", 4), ("Family History", 4)], date(2026, 4, 22), "rare"),
    ("Ehlers-Danlos Syndrome", "Q79.6", 24, "Joint hypermobility, skin hyperextensibility, easy bruising, chronic pain, and recurrent dislocations.", [("Joint Hypermobility", 5), ("Skin Hyperextensibility", 5), ("Easy Bruising", 4), ("Chronic Pain", 4), ("Joint Pain", 3)], date(2026, 4, 24), "rare"),
    ("Kawasaki Disease", "M30.3", 3, "Pediatric persistent fever with rash, red eyes, swollen lymph nodes, and mucosal inflammation.", [("Fever", 5), ("Rash", 4), ("Red Eyes", 4), ("Swollen Lymph Nodes", 4)], date(2026, 4, 26), "rare"),
    ("Batten Disease", "E75.4", 7, "Child with vision loss, seizures, developmental regression, and movement disorder.", [("Vision Loss", 5), ("Seizures", 5), ("Developmental Regression", 5), ("Movement Disorder", 4)], date(2026, 4, 28), "rare"),
    ("Niemann-Pick Disease", "E75.24", 5, "Enlarged spleen, liver dysfunction, developmental delay, movement disorder, and feeding difficulty.", [("Enlarged Spleen", 5), ("Liver Dysfunction", 4), ("Developmental Delay", 4), ("Movement Disorder", 4), ("Feeding Difficulty", 3)], date(2026, 5, 1), "rare"),
    ("Prader-Willi Syndrome", "Q87.1", 6, "Hypotonia, feeding difficulty in infancy, developmental delay, obesity, and behavioral food seeking.", [("Hypotonia", 4), ("Feeding Difficulty", 4), ("Developmental Delay", 4), ("Obesity", 5), ("Behavior Change", 3)], date(2026, 5, 4), "rare"),
    ("Chronic Inflammatory Demyelinating Polyneuropathy", "G61.81", 46, "Adult progressive weakness, numbness, areflexia, fatigue, and relapsing neuropathy pattern.", [("Progressive Weakness", 5), ("Numbness", 4), ("Areflexia", 5), ("Fatigue", 3)], date(2026, 5, 7), "rare"),
    ("Addison Disease", "E27.1", 33, "Fatigue, weight loss, low blood pressure, hyperpigmentation, dizziness, and recurrent dehydration.", [("Fatigue", 5), ("Weight Loss", 4), ("Low Blood Pressure", 5), ("Hyperpigmentation", 4), ("Dizziness", 3)], date(2026, 5, 10), "rare"),
    ("Zika Virus Disease", "A92.8", 24, "Mild fever, rash, conjunctivitis, joint pain, and travel exposure during local mosquito outbreak.", [("Fever", 2), ("Rash", 3), ("Conjunctivitis", 3), ("Joint Pain", 2), ("Headache", 2)], date(2026, 5, 12), "bnmit"),
    ("Tuberculosis", "A15.9", 39, "Persistent cough with fever, night sweats, weight loss, fatigue, and blood in sputum.", [("Persistent Cough", 5), ("Fever", 3), ("Night Sweats", 4), ("Weight Loss", 4), ("Blood In Sputum", 4), ("Fatigue", 3)], date(2026, 5, 14), "bnmit"),
    ("Hyperthyroidism", "E05.9", 28, "Palpitations, sweating, weight loss, tremor, heat intolerance, and goiter in adult outpatient case.", [("Palpitations", 4), ("Sweating", 3), ("Weight Loss", 3), ("Tremor", 3), ("Heat Intolerance", 4), ("Goiter", 4)], date(2026, 5, 15), "bnmit"),
    ("Systemic Lupus Erythematosus", "M32.8", 31, "Adult lupus flare with photosensitivity, mouth ulcers, joint pain, fatigue, and proteinuria.", [("Photosensitivity", 5), ("Mouth Ulcers", 4), ("Joint Pain", 4), ("Fatigue", 4), ("Proteinuria", 5), ("Rash", 4)], date(2026, 5, 16), "rare"),
    ("Fabry Disease", "E75.20", 14, "Teen with burning pain in hands and feet, recurrent fever, fatigue, proteinuria, and family history.", [("Burning Pain", 5), ("Recurrent Fever", 3), ("Fatigue", 3), ("Proteinuria", 4), ("Family History", 5), ("Neuropathic Pain", 4)], date(2026, 5, 17), "rare"),
    ("Gaucher Disease", "E75.23", 36, "Adult Gaucher presentation with hepatomegaly, enlarged spleen, anemia, bone pain, fatigue, and swollen feet.", [("Hepatomegaly", 5), ("Enlarged Spleen", 5), ("Anemia", 4), ("Bone Pain", 5), ("Fatigue", 3), ("Swollen Feet", 3)], date(2026, 5, 18), "rare"),
    ("Osteogenesis Imperfecta", "Q78.0", 11, "Pediatric recurrent fractures with blue sclera, hearing loss, growth delay, and chronic bone pain.", [("Frequent Fractures", 5), ("Blue Sclera", 5), ("Hearing Loss", 3), ("Growth Delay", 4), ("Bone Pain", 4)], date(2026, 5, 19), "rare"),
]


def _get_or_create_symptoms(session):
    symptoms = {}
    for index, name in enumerate(SYMPTOM_NAMES, start=1):
        key = name.lower()
        symptom = Symptom(id=f"SYM-{key.replace(' ', '-').upper()[:38]}", symptom_name=name, snomed_code=_code("SNOMED", index))
        session.add(symptom)
        symptoms[key] = symptom
    return symptoms


def _add_record(session, patient, hospital, diagnosis, symptoms, age, notes, record_date):
    record = ClinicalRecord(
        id=_new_id("REC"),
        patient_id=patient.id,
        hospital_id=hospital.id,
        diagnosis_id=diagnosis.id,
        age_at_encounter=age,
        notes=notes,
        is_shareable=True,
        record_date=record_date,
    )
    session.add(record)
    session.flush()

    for symptom, severity in symptoms:
        session.add(RecordSymptom(record_id=record.id, symptom_id=symptom.id, severity=severity))
    return record


def seed_database(hospital_name=None, node_id=None):
    """Create tables and load realistic common plus rare disease demo data."""
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        _clear_database(session)

        node_label = (hospital_name or "BNMIT Teaching Hospital").strip()
        node_key = (node_id or node_label).upper()
        referral_label = f"{node_label} Rare Disease Unit"
        hospitals = {
            "bnmit": Hospital(id="HOSP-LOCAL", name=node_label, location="Bengaluru, India", public_key=f"demo-public-key-{node_key.lower()}"),
            "rare": Hospital(id="HOSP-RARE", name=referral_label, location="Referral Network", public_key=f"demo-public-key-rare-{node_key.lower()}"),
        }
        session.add_all(hospitals.values())
        symptoms = _get_or_create_symptoms(session)

        records_for_node = RECORDS
        if node_id and node_id.upper().endswith("_A"):
            records_for_node = [record for index, record in enumerate(RECORDS, start=1) if index % 2 == 1 or record[0] in {"Malaria", "Dengue Fever", "Common Cold"}]
        elif node_id and node_id.upper().endswith("_B"):
            records_for_node = [record for index, record in enumerate(RECORDS, start=1) if index % 2 == 0 or record[0] in {"Typhoid Fever", "Zika Virus Disease", "Fabry Disease"}]

        diagnoses = []
        for index, (name, icd10, *_rest) in enumerate(records_for_node, start=1):
            diag = Diagnosis(id=f"DIAG-{index:03d}", disease_name=name, icd10_code=f"{icd10}-{index:02d}")
            session.add(diag)
            diagnoses.append(diag)
        session.flush()

        for index, (name, _icd10, age, notes, symptom_rows, record_date, hospital_key) in enumerate(records_for_node, start=1):
            hospital = hospitals[hospital_key]
            patient = Patient(
                id=_new_id("PAT"),
                hospital_id=hospital.id,
                full_name=f"Demo Patient {index:02d}",
                dob=date(max(1940, record_date.year - max(age, 1)), 1, min(index, 28)),
                gender="F" if index % 2 else "M",
                contact_hash=hash_patient_pii(f"demo.patient.{index}@example.com"),
            )
            session.add(patient)
            session.flush()
            _add_record(
                session,
                patient,
                hospital,
                diagnoses[index - 1],
                [(symptoms[symptom_name.lower()], severity) for symptom_name, severity in symptom_rows],
                age,
                notes,
                record_date,
            )

        session.commit()
        print(f"Seeded database with {len(hospitals)} hospitals, {len(records_for_node)} records, {len(SYMPTOM_NAMES)} symptoms, and {len(diagnoses)} diagnoses.")


if __name__ == "__main__":
    seed_database()
