import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:<your_password>@localhost:5432/medical_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    gender = Column(String(1))
    phone = Column(String(20))

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50), nullable=False)
    role = Column(String(50), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    created_at = Column(DateTime, server_default=func.now())

Base.metadata.create_all(bind=engine)

class PatientCreate(BaseModel):
    name: str
    gender: str
    phone: str

app = FastAPI(title="病历管理系统")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "病历管理系统运行中"}

@app.post("/patients")
def create_patient(data: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(name=data.name, gender=data.gender, phone=data.phone)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

@app.get("/patients")
def list_patients(db: Session = Depends(get_db)):
    return db.query(Patient).all()