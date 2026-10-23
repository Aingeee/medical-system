import uuid

import bcrypt
from datetime import datetime
from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User,Patient,MedicalRecord
from app.schemas import UserLogin, UserRegister, PatientCreate, MedicalRecordCreate, MedicalRecordResponse
from app.auth import create_access_token,get_current_user,require_role

router = APIRouter()

@router.get("/")
def root():
    return {"message": "病历管理系统运行中"}

@router.post("/patients")
def create_patient(data: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(name=data.name, gender=data.gender, phone=data.phone)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

@router.get("/patients")
def list_patients(db: Session = Depends(get_db)):
    return db.query(Patient).all()

@router.post("/register")
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    hashed = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user=User(
        username=data.username,
        password_hash=hashed,
        real_name=data.real_name,
        role=data.role,
        department_id=data.department_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
    }

@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user:
        raise HTTPException(status_code=401,detail="用户名或密码错误")

    if not bcrypt.checkpw(data.password.encode("utf-8"), user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401,detail="用户名或密码错误")

    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "real_name": current_user.real_name,
        "role": current_user.role,
    }

@router.post("/records")
def create_record(
        data: MedicalRecordCreate,
        current_user: User = Depends(require_role("doctor")),
        db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")

    record_no = f"MR{datetime.now().strftime('%Y%m%d%H%M')}{uuid.uuid4().hex[:6].upper()}"

    record = MedicalRecord(
        record_no=record_no,
        patient_id=data.patient_id,
        doctor_id=current_user.id,
        visit_type=data.visit_type,
        visit_time=data.visit_time,
        chief_complaint=data.chief_complaint,
        present_illness=data.present_illness,
        allergy_history=data.allergy_history,
        status="draft",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.get("/doctor-only")
def doctor_only(current_user: User = Depends(require_role("doctor"))):
    return {"message":f"你好，医生{current_user.real_name}"}

@router.get("/admin-only")
def admin_only(current_user: User = Depends(require_role("admin"))):
    return {"message":f"你好，管理员{current_user.real_name}"}

@router.get("/records",response_model=list[MedicalRecordResponse])
def list_records(
    skip: int = 0, limit: int = 10, current_user: User = Depends(get_current_user),db: Session = Depends(get_db)
):
    records = db.query(MedicalRecord).order_by(MedicalRecord.created_at.desc()).offset(skip).limit(limit).all()
    return records

@router.get("/records/{record_id}",response_model=MedicalRecordResponse)
def get_record(record_id: int, current_user: User = Depends(get_current_user) , db: Session = Depends(get_db)):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="/病历不存在")

    if current_user.role != "admin" and record.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="你没有权限查看他人的病历")

    return record