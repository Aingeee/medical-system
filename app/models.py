from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func

from app.database import Base


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

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    id = Column(Integer, primary_key=True, index=True)
    record_no = Column(String(30),unique=True,nullable=False,index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"),nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"),nullable=False)
    visit_type = Column(String(20), nullable=False)
    visit_time = Column(DateTime, nullable=False)
    chief_complaint = Column(String(255))
    present_illness = Column(String(255))
    allergy_history = Column(String(255))
    status = Column(String(20), nullable=False,default="draft")
    signed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(),onupdate=func.now())
