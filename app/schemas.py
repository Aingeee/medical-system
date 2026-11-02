from datetime import datetime

from typing import Literal
from pydantic import BaseModel

class UserRegister(BaseModel):
    username: str
    password: str
    real_name: str
    role: Literal["doctor", "nurse"]
    department_id: int | None = None

class PatientCreate(BaseModel):
    name: str
    gender: str
    phone: str

class UserLogin(BaseModel):
    username: str
    password: str

class MedicalRecordCreate(BaseModel):
    patient_id: int
    visit_type: str
    visit_time: datetime
    chief_complaint: str | None = None
    present_illness: str | None = None
    allergy_history: str | None = None

class MedicalRecordResponse(BaseModel):
    id: int
    record_no: str
    patient_id: int
    doctor_id: int
    visit_type: str
    visit_time: datetime
    chief_complaint: str | None
    present_illness: str | None
    allergy_history: str | None
    status: str
    signed_at: datetime | None
    created_at: datetime | None

    class Config:
        from_attributes = True