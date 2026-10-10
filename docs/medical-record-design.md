# 病历模块表设计（Medical Record）

> 本文档为「病历管理模块」的数据库设计说明，用于指导 `medical_records` 及关联表的落地实现。
> 设计目标：贴合国内医疗机构实际使用的电子病历（EMR）系统，同时保持教学项目可落地。

> **当前状态**：本文档为病历模块的**目标设计**。当前代码实现的是**简化版本**，
> 只包含 `medical_records` 主表的基础字段和创建接口。
> 完整版本将按第 8 节「落地顺序建议」逐步演进。
---

## 1. 设计依据：为什么病历表不能随便建

病历在法律上是**医疗行为的书面证据**，也是医疗纠纷中的核心举证材料。因此真实的 EMR 系统设计受以下规范约束，这些约束直接决定了表结构：

| 规范 / 标准 | 对表结构的直接影响 |
| --- | --- |
| 《医疗机构病历管理规定》（国卫医发〔2013〕31 号） | 门（急）诊病历保存 **≥ 15 年**，住院病历保存 **≥ 30 年** → 不可物理删除，需软删除/作废机制 |
| 《电子病历应用管理规范（试行）》（国卫办医发〔2017〕8 号） | 修改必须**留痕、可追溯**，须使用可靠电子签名 → 需版本表 + 签名时间字段 |
| 《病历书写基本规范》（卫医政发〔2010〕11 号） | 病历内容有固定构成（主诉、现病史、既往史、体格检查、辅助检查、诊断、治疗意见），入院记录 24h 内完成、首次病程记录 8h 内完成 → 决定必填字段与时间字段 |
| WS 445《电子病历基本数据集》 | 字段命名与含义需标准化、结构化，而非整篇大文本 |
| ICD-10 国家临床版 2.0 | 诊断必须编码化 → 诊断不写成文本字段，需独立子表 |
| 电子病历系统应用水平分级评价（0–8 级） | 评级越高，越要求数据**结构化**与**闭环**（如生命体征独立成列而非塞进大文本） |

### 由此推导出的三条硬性设计原则

1. **只增不删**：病历记录不做物理删除，作废用状态字段表达（`status = 'void'` / `deleted_at`）。
2. **修改留痕**：已签名病历不可直接改，修改必须生成新版本并保留历史快照。
3. **能结构化就结构化**：生命体征、诊断、时间这类要用于统计、预警、DRG/DIP 分组的字段，独立成列/子表，不塞进一个大 `Text`。

---

## 2. 表结构总览

```
patients ──< medical_records >── departments
                    │  │
                    │  └──< diagnoses            （诊断，一病历多诊断）
                    │
                    └─────< record_revisions     （修订留痕，一病历多版本）
             users ──┘  └── users（接诊医生 / 上级审签医师）
```

| 表名 | 必要性 | 作用 |
| --- | --- | --- |
| `medical_records` | **必需** | 病历主表，一次就诊一条记录 |
| `diagnoses` | **强烈建议** | 诊断明细，支持主诊断 + 多个次诊断、ICD-10 编码 |
| `record_revisions` | **建议** | 修订留痕，满足"修改可追溯"的合规要求 |

> 真实系统还会拆分护理记录、医嘱、手术记录、病程记录、病案首页等，并按**门诊病历 / 住院病历**建不同表。本项目为学习目的，先做统一主表 + 两张子表，结构已足够表达核心业务。

---

## 3. 主表 `medical_records` 字段清单

### 3.1 标识与归属

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | Integer | PK | 主键 |
| `record_no` | String(32) | NOT NULL, UNIQUE | 病历号，机构内唯一，建议规则 `MR + yyyymmdd + 4位流水` |
| `patient_id` | Integer | FK → `patients.id`, NOT NULL | 所属患者 |
| `visit_type` | String(20) | NOT NULL | 就诊类型：`outpatient` 门诊 / `emergency` 急诊 / `inpatient` 住院 / `physical` 体检 |
| `visit_no` | String(32) | | 就诊流水号（门诊号 / 住院号），同一患者一次就诊唯一 |
| `department_id` | Integer | FK → `departments.id` | 接诊科室 |
| `doctor_id` | Integer | FK → `users.id`, NOT NULL | 接诊 / 主管医师 |
| `supervisor_id` | Integer | FK → `users.id` | 上级审签医师（三级查房、上级医师签名） |

### 3.2 时间

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `visit_time` | DateTime | NOT NULL | 就诊时间（门诊挂号 / 入院时间） |
| `admission_time` | DateTime | | 入院时间（住院病历使用） |
| `discharge_time` | DateTime | | 出院时间，与 `admission_time` 共同决定住院天数 |
| `signed_at` | DateTime | | 医师签名时间，签名后病历生效并锁定 |
| `supervised_at` | DateTime | | 上级医师审签时间 |
| `created_at` | DateTime | server_default=now() | 记录创建时间 |
| `updated_at` | DateTime | onupdate=now() | 最后更新时间 |
| `deleted_at` | DateTime | | 作废时间（软删除，**不做物理删除**） |

### 3.3 病史采集（病历书写基本规范要求的固定构成）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `chief_complaint` | String(500) | **NOT NULL** | 主诉：症状 + 持续时间，规范要求精炼（一般 ≤ 20 字） |
| `present_illness` | Text | | 现病史：起病、演变、诊疗经过 |
| `past_history` | Text | | 既往史：既往疾病、手术、传染病史 |
| `personal_history` | Text | | 个人史 / 婚育史 / 职业接触史 |
| `family_history` | Text | | 家族史 |
| `allergy_history` | Text | | **过敏史**（抢救场景关键字段，必须可快速读取） |

### 3.4 体格检查

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `physical_exam` | Text | 体格检查描述（系统查体） |
| `temperature` | Numeric(4,1) | 体温 ℃ |
| `pulse` | Integer | 脉搏 次/分 |
| `respiration` | Integer | 呼吸 次/分 |
| `systolic_bp` | Integer | 收缩压 mmHg |
| `diastolic_bp` | Integer | 舒张压 mmHg |

> 生命体征为什么独立成列而不是写进 `physical_exam` 文本？因为分级评价要求数据可用于**预警、趋势分析、质控统计**。真机上护士站的体温单、危急值提醒都依赖这些列。

### 3.5 辅助检查与处理

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `auxiliary_exam` | Text | 辅助检查：检验、影像、心电等结果 |
| `preliminary_diagnosis` | String(500) | 初步诊断文本（结构化的诊断明细见 `diagnoses` 表） |
| `treatment_plan` | Text | 处理意见 / 治疗方案 |
| `medical_advice` | Text | 医嘱 |

### 3.6 状态控制与质控

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `status` | String(20) | NOT NULL, DEFAULT `draft` | `draft` 草稿 → `signed` 已签名 → `amended` 已修订 → `void` 作废 |
| `version` | Integer | NOT NULL, DEFAULT 1 | 版本号，每次修订 +1 |
| `quality_level` | String(2) | | 病案质控等级：甲 / 乙 / 丙（丙级为不合格病历） |

---

## 4. 关联子表设计

### 4.1 `diagnoses` 诊断表

一次就诊通常有 1 个主诊断 + N 个次诊断，且必须编码化（ICD-10），所以必须独立成表。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | Integer | PK |
| `record_id` | Integer | FK → `medical_records.id`, NOT NULL |
| `icd_code` | String(20) | ICD-10 国家临床版编码，如 `J06.900` |
| `diagnosis_name` | String(200) | 诊断名称，NOT NULL |
| `diagnosis_type` | String(20) | `primary` 主诊断 / `secondary` 次诊断 / `admission` 入院诊断 / `discharge` 出院诊断 / `suspected` 疑诊 |
| `certainty` | String(10) | 确定性：`confirmed` 确诊 / `suspected` 疑似 |
| `diagnosed_at` | DateTime | 诊断时间 |
| `doctor_id` | Integer | FK → `users.id`，诊断医师 |
| `sort_order` | Integer | 展示顺序 |

> **业务约束**：同一份病历中 `diagnosis_type = 'primary'` 的记录**有且仅有一条**。住院场景下主诊断直接决定 DRG/DIP 分组与医保结算，因此这条约束必须在应用层校验（PostgreSQL 可用部分唯一索引实现）。

### 4.2 `record_revisions` 修订留痕表

《电子病历应用管理规范》要求修改留痕，因此每次对已签名病历的修改都要落一条快照。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | Integer | PK |
| `record_id` | Integer | FK → `medical_records.id`, NOT NULL |
| `version` | Integer | 修订后的版本号 |
| `snapshot` | Text | 修订前内容的 JSON 快照（可追溯"改了什么"） |
| `change_reason` | String(500) | 修订原因（合规要求必须填写） |
| `changed_by` | Integer | FK → `users.id`，操作人 |
| `changed_at` | DateTime | 修订时间 |

---

## 5. 建表 DDL（PostgreSQL）

```sql
CREATE TABLE medical_records (
    id                 SERIAL PRIMARY KEY,
    record_no          VARCHAR(32)  NOT NULL UNIQUE,
    patient_id         INTEGER      NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    visit_type         VARCHAR(20)  NOT NULL DEFAULT 'outpatient',
    visit_no           VARCHAR(32),
    department_id      INTEGER      REFERENCES departments(id),
    doctor_id          INTEGER      NOT NULL REFERENCES users(id),
    supervisor_id      INTEGER      REFERENCES users(id),

    visit_time         TIMESTAMP    NOT NULL DEFAULT NOW(),
    admission_time     TIMESTAMP,
    discharge_time     TIMESTAMP,
    signed_at          TIMESTAMP,
    supervised_at      TIMESTAMP,
    created_at         TIMESTAMP    DEFAULT NOW(),
    updated_at         TIMESTAMP    DEFAULT NOW(),
    deleted_at         TIMESTAMP,

    chief_complaint    VARCHAR(500) NOT NULL,
    present_illness    TEXT,
    past_history       TEXT,
    personal_history   TEXT,
    family_history     TEXT,
    allergy_history    TEXT,

    physical_exam      TEXT,
    temperature        NUMERIC(4,1),
    pulse              INTEGER,
    respiration        INTEGER,
    systolic_bp        INTEGER,
    diastolic_bp       INTEGER,

    auxiliary_exam     TEXT,
    preliminary_diagnosis VARCHAR(500),
    treatment_plan     TEXT,
    medical_advice     TEXT,

    status             VARCHAR(20)  NOT NULL DEFAULT 'draft',
    version            INTEGER      NOT NULL DEFAULT 1,
    quality_level      VARCHAR(2),

    CONSTRAINT ck_records_visit_type CHECK (visit_type IN ('outpatient','emergency','inpatient','physical')),
    CONSTRAINT ck_records_status     CHECK (status IN ('draft','signed','amended','void')),
    CONSTRAINT ck_records_quality    CHECK (quality_level IS NULL OR quality_level IN ('甲','乙','丙')),
    CONSTRAINT ck_records_vitals     CHECK (
        (temperature IS NULL OR temperature BETWEEN 25 AND 45) AND
        (pulse       IS NULL OR pulse       BETWEEN 0  AND 300) AND
        (systolic_bp IS NULL OR systolic_bp BETWEEN 0  AND 400)
    )
);

CREATE INDEX idx_records_patient    ON medical_records(patient_id);
CREATE INDEX idx_records_doctor     ON medical_records(doctor_id);
CREATE INDEX idx_records_department ON medical_records(department_id);
CREATE INDEX idx_records_visit_time ON medical_records(visit_time DESC);
CREATE INDEX idx_records_status     ON medical_records(status);
CREATE UNIQUE INDEX uk_records_visit ON medical_records(patient_id, visit_no)
    WHERE visit_no IS NOT NULL;
```

---

## 6. SQLAlchemy 模型代码（可直接并入 `main.py`）

### 需要补充的导入

```python
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Numeric,
    ForeignKey, DateTime, CheckConstraint, Index, func
)
```

### 模型定义

```python
class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    record_no = Column(String(32), nullable=False, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    visit_type = Column(String(20), nullable=False, default="outpatient")
    visit_no = Column(String(32))
    department_id = Column(Integer, ForeignKey("departments.id"), index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    supervisor_id = Column(Integer, ForeignKey("users.id"))

    visit_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    admission_time = Column(DateTime)
    discharge_time = Column(DateTime)
    signed_at = Column(DateTime)
    supervised_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime)

    # 病史
    chief_complaint = Column(String(500), nullable=False)
    present_illness = Column(Text)
    past_history = Column(Text)
    personal_history = Column(Text)
    family_history = Column(Text)
    allergy_history = Column(Text)

    # 体格检查与生命体征
    physical_exam = Column(Text)
    temperature = Column(Numeric(4, 1))
    pulse = Column(Integer)
    respiration = Column(Integer)
    systolic_bp = Column(Integer)
    diastolic_bp = Column(Integer)

    # 辅检与处理
    auxiliary_exam = Column(Text)
    preliminary_diagnosis = Column(String(500))
    treatment_plan = Column(Text)
    medical_advice = Column(Text)

    # 状态与质控
    status = Column(String(20), nullable=False, default="draft", index=True)
    version = Column(Integer, nullable=False, default=1)
    quality_level = Column(String(2))

    __table_args__ = (
        CheckConstraint(
            "visit_type IN ('outpatient','emergency','inpatient','physical')",
            name="ck_records_visit_type",
        ),
        CheckConstraint(
            "status IN ('draft','signed','amended','void')",
            name="ck_records_status",
        ),
        Index("idx_records_visit_time", "visit_time"),
    )


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False, index=True)
    icd_code = Column(String(20))
    diagnosis_name = Column(String(200), nullable=False)
    diagnosis_type = Column(String(20), nullable=False, default="primary")
    certainty = Column(String(10), default="confirmed")
    diagnosed_at = Column(DateTime, default=datetime.utcnow)
    doctor_id = Column(Integer, ForeignKey("users.id"))
    sort_order = Column(Integer, default=0)

    __table_args__ = (
        CheckConstraint(
            "diagnosis_type IN ('primary','secondary','admission','discharge','suspected')",
            name="ck_diagnosis_type",
        ),
    )


class RecordRevision(Base):
    __tablename__ = "record_revisions"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    snapshot = Column(Text)
    change_reason = Column(String(500))
    changed_by = Column(Integer, ForeignKey("users.id"))
    changed_at = Column(DateTime, server_default=func.now())
```

> 项目使用 `Base.metadata.create_all(bind=engine)`，因此新模型一加入，启动时就会自动建表，无需手写迁移。

---

## 7. 业务规则（决定接口怎么写）

| 规则 | 说明 |
| --- | --- |
| 谁能创建 | `doctor`、`admin`；患者与普通用户不可 |
| 谁能查看 | 接诊医师本人、本科室医师、`admin`；其他医师默认不可见（细粒度权限，后续迭代） |
| 草稿态 | `status = draft` 时可自由修改，仅创建者与 `admin` 可改 |
| 签名即锁定 | `POST /records/{id}/sign` 将状态置为 `signed` 并写入 `signed_at`，此后**禁止直接 UPDATE** |
| 修订走留痕 | 已签名病历需修改时，走 `amend`：先把旧内容写入 `record_revisions`，`version + 1`，状态置为 `amended` |
| 作废不删除 | 错误病历置 `status = void` + `deleted_at`，数据保留（满足 15/30 年保存要求） |
| 主诊断唯一 | 同一病历 `diagnosis_type = 'primary'` 只能有一条 |

### 接口草图

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| `POST` | `/records` | `doctor` / `admin` | 创建病历（草稿），自动生成 `record_no` |
| `GET` | `/records` | 登录用户 | 列表，支持 `patient_id`、`department_id`、`status` 过滤 |
| `GET` | `/records/{id}` | 登录用户 | 详情，含诊断明细 |
| `PUT` | `/records/{id}` | 创建者 / `admin` | 仅 `draft` 可改 |
| `POST` | `/records/{id}/sign` | 创建者 | 签名并锁定 |
| `POST` | `/records/{id}/amend` | 创建者 | 修订，生成版本快照 |
| `POST` | `/records/{id}/diagnoses` | 创建者 | 追加诊断 |

---

## 8. 落地顺序建议

1. 建三张表，跑通 `Base.metadata.create_all`，用 `/docs` 确认表结构
2. 实现 `POST /records` + `GET /records` + `GET /records/{id}`（最小闭环）
3. 加入状态机校验（`draft` 才可改、`signed` 后拒改）
4. 加入签名与修订留痕
5. 接入细粒度权限（医生只看自己科室的患者）

---

## 9. 与真实系统的差异说明

本项目为教学目的做了简化，真实 EMR 的差异主要有：

- 门诊病历与住院病历分表；住院另有病案首页、病程记录、医嘱单、护理记录单、手术记录
- 诊断表对接 ICD-10 / ICD-9-CM-3 手术编码字典表，而非直接存字符串
- 电子签名使用 CA 证书 + 时间戳服务，而非普通字段
- 有独立的质控模块（三级质控：科室自查 → 病案室抽查 → 医务科终审）
- 数据长期归档于独立归档库，热库只保留近期数据

## 10. 当前实现进度（对应本文档）

- [x] `medical_records` 基础表（简化版：12 字段）
- [x] `POST /records` 创建病历接口
- [ ] 扩展字段：`department_id`、`visit_no`、`supervisor_id`
- [ ] `diagnoses` 诊断子表（ICD-10 编码）
- [ ] `record_revisions` 修订留痕表
- [ ] 状态机校验：`draft` 才可改，`signed` 后拒改
- [ ] 软删除：`deleted_at` 字段
- [ ] 签名接口：`POST /records/{id}/sign`
- [ ] 修订接口：`POST /records/{id}/amend`
- [ ] 细粒度权限：医生只能看自己科室的患者

> 每完成一项，在此处更新状态，并在 README 的「版本历史」里记录。