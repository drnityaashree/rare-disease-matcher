import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# Each hospital node owns a local SQLite database. The environment variable lets
# Docker run multiple nodes with different database files.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./node_database.db")

# check_same_thread=False is needed only for SQLite to allow concurrent FastAPI requests
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get the database session in FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
