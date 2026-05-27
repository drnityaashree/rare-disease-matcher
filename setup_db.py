from shared.database import engine, Base
from shared.models import Hospital, Patient, Diagnosis, Symptom, ClinicalRecord, RecordSymptom, CaseMatchLog

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully in node_database.db!")

if __name__ == "__main__":
    init_db()
