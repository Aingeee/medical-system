import json
import uuid

import bcrypt
from datetime import datetime
from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Patient, MedicalRecord, Department, RecordRevision
from app.schemas import UserLogin, UserRegister, PatientCreate, MedicalRecordCreate, MedicalRecordResponse, \
    DepartmentCreate, MedicalRecordUpdate, MedicalRecordAmend
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
    if data.department_id is not None:
        dept = db.query(Department).filter(Department.id == data.department_id).first()
        if not dept:
            raise HTTPException(status_code=400, detail="所选科室不存在")
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
        skip: int = 0,
        limit: int = 10,
        patient_id: int | None = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    query = db.query(MedicalRecord)
    if current_user.role != "admin":
        query = query.filter(MedicalRecord.doctor_id == current_user.id)

    if patient_id is not None:
        query = query.filter(MedicalRecord.patient_id == patient_id)

    records = query.order_by(MedicalRecord.created_at.desc()).offset(skip).limit(limit).all()
    return records

@router.get("/records/{record_id}",response_model=MedicalRecordResponse)
def get_record(record_id: int, current_user: User = Depends(get_current_user) , db: Session = Depends(get_db)):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="病历不存在")

    if current_user.role != "admin" and record.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="你没有权限查看他人的病历")

    return record

@router.post("/records/{record_id}/sign")
def sign_record(
        record_id: int,
        current_user: User = Depends(require_role("doctor")),
        db: Session = Depends(get_db),
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404,detail="病历不存在")

    if record.doctor_id != current_user.id:
        raise HTTPException(status_code=403,detail="你没有权限签名他人的病历")

    if record.status == "signed":
        raise HTTPException(status_code=400,detail="该病历已被签名锁定，请勿重复操作")

    record.status = "signed"
    record.signed_at = datetime.now()

    db.commit()
    db.refresh(record)

    return {"message": "签名成功，病历已锁定","record": record}

@router.post("/departments")
def create_department(
        data: DepartmentCreate,
        current_user: User = Depends(require_role("admin")),
        db: Session = Depends(get_db),
):
    existing = db.query(Department).filter(Department.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="科室已存在")

    dept = Department(name=data.name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

@router.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@router.put("/records/{record_id}",response_model=MedicalRecordResponse)
def update_draft_record(
        record_id: int,
        data: MedicalRecordUpdate,
        current_user: User = Depends(require_role("doctor")),
        db: Session = Depends(get_db),
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404,detail="病历不存在")
    if record.doctor_id != current_user.id:
        raise HTTPException(status_code=403,detail="只能修改自己的病历")
    if record.status != "draft":
        raise HTTPException(status_code=400,detail="该病历已签名锁定，请使用修订接口(amend)")

    if data.chief_complaint is not None:
        record.chief_complaint = data.chief_complaint
    if data.present_illness is not None:
        record.present_illness = data.present_illness
    if data.allergy_history is not None:
        record.allergy_history = data.allergy_history

    db.commit()
    db.refresh(record)
    return record

@router.post("/records/{record_id}/amend",response_model=MedicalRecordResponse)
def amend_record(
        record_id: int,
        data: MedicalRecordAmend,
        current_user: User = Depends(require_role("doctor")),
        db: Session = Depends(get_db)
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404,detail="病历不存在")
    if record.doctor_id != current_user.id:
        raise HTTPException(status_code=403,detail="只能修订自己的病历")
    if record.status == "draft":
        raise HTTPException(status_code=400,detail="草稿病历请使用 PUT /records/{id} 直接修改，修订只用于已签名病历")
    if record.status == "void":
        raise HTTPException(status_code=400,detail="作废病历不可修订")
    if data.chief_complaint is None and data.present_illness is None and data.allergy_history is None:
        raise HTTPException(status_code=400,detail="修订内容不能为空，至少要改一个字段")

    # 关键：快照必须在覆盖字段之前取。先改后取存进去的就是新值，留痕等于没做。
    old_snapshot = {
        "version": record.version,
        "chief_complaint": record.chief_complaint,
        "present_illness": record.present_illness,
        "allergy_history": record.allergy_history,
    }

    revision = RecordRevision(
        record_id=record.id,
        version=record.version,  # 记录的是「被替换掉的那一版」，与 snapshot 内容一致
        snapshot=json.dumps(old_snapshot, ensure_ascii=False),
        change_reason=data.change_reason,
        changed_by=current_user.id,
    )
    db.add(revision)

    if data.chief_complaint is not None:
        record.chief_complaint = data.chief_complaint
    if data.present_illness is not None:
        record.present_illness = data.present_illness
    if data.allergy_history is not None:
        record.allergy_history = data.allergy_history

    record.version +=1
    record.status = "amended"

    db.commit()
    db.refresh(record)
    return record


@router.get("/records/{record_id}/history")
def get_record_history(
        record_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404,detail="病历不存在")
    if current_user.role != "admin" and record.doctor_id != current_user.id:
        raise HTTPException(status_code=403,detail="你没有权限查看他人病历的修订历史")

    # 查该病历的所有修订记录
    revisions = db.query(RecordRevision).filter(RecordRevision.record_id == record_id).order_by(
        RecordRevision.changed_at.desc()).all()

    return [
        {
            "version": rev.version,
            "changed_at": rev.changed_at,
            "changed_by": rev.changed_by,
            "change_reason": rev.change_reason,
            "old_snapshot": json.loads(rev.snapshot)  # 把存的 JSON 字符串转回对象
        }
        for rev in revisions
    ]