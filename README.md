# 病历管理系统（Medical Record Management System）

> 一个基于 **FastAPI + PostgreSQL** 的病历管理系统后端，用于个人练习后端开发与医疗信息化业务建模。

**当前版本：`v0.10.0`**
（版本号唯一来源为 `main.py` 中的 `__version__`，启动后访问 `/docs` 可见）

---

## 目录

- [项目简介](#项目简介)
- [开发进度](#开发进度)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 接口一览](#api-接口一览)
- [数据模型](#数据模型)
- [鉴权说明](#鉴权说明)
- [版本管理](#版本管理)
- [最新更新内容](#最新更新内容v0100)
- [版本历史](#版本历史)
- [事故记录](#事故记录)
- [后续计划](#后续计划)
- [设计文档](#设计文档)
- [说明](#说明)

---

## 项目简介

本项目是一个学习性质的病历管理后端。目标是在真实业务场景（患者、科室、医生、病历、处方）中练习：

- RESTful API 设计
- 关系型数据库建模（SQLAlchemy ORM）
- 用户认证与授权（JWT + 基于角色的权限控制）
- 敏感配置管理（环境变量、密钥隔离）
- 语义化版本与发布流程

## 开发进度

- [x] 数据库连接（PostgreSQL）
- [x] 患者表创建
- [x] 创建患者接口（`POST /patients`）
- [x] 查询患者列表接口（`GET /patients`）
- [x] 科室表、用户表创建
- [x] 用户注册接口（`POST /register`）
- [x] 用户登录接口（`POST /login`）
- [x] JWT 鉴权与受保护接口（`GET /me`）
- [x] 基于角色的权限控制（`require_role`）
- [x] 病历主表（`medical_records`）与创建接口（`POST /records`）
- [x] 病历模块表设计文档（[`docs/medical-record-design.md`](./docs/medical-record-design.md)）
- [x] 应用模块化拆分（`app/` 包：config / database / models / schemas / auth / routers）
- [x] 配置中心化（`pydantic-settings` 统一读取 `.env`）
- [x] 病历列表与详情接口（`GET /records`、`GET /records/{record_id}`）
- [x] 跨域支持（CORS 白名单，供前端联调）
- [x] 病历签名锁定（`POST /records/{record_id}/sign`：仅接诊医生可签、重复签名拦截、写入 `signed_at`）
- [x] 病历数据隔离：列表与详情均按 `doctor_id` 过滤，非 `admin` 医生看不到他人病历
- [x] 角色字段校验（`role` 只允许 `doctor` / `nurse`，由 `Literal` 在入口拦截）
- [x] JWT 异常处理细分（`JWTError` → 401、`ValueError` → 载荷格式错误）
- [x] 科室管理接口（`POST /departments` 仅 `admin`、`GET /departments` 公开供注册页选择）
- [x] 病历反向查询（`GET /records?patient_id=`，按患者查历史病历）
- [ ] 注册时校验科室外键（校验代码已写，但 `filter(department_id=...)` 用法有误会抛 `TypeError`，见下方「已知问题」）
- [ ] 病历修改接口（仅 `draft` 可改，`signed` 状态拒绝修改）
- [ ] 诊断子表（`diagnoses`）与修订留痕表（`record_revisions`）
- [ ] 处方管理模块
- [ ] 审计日志

## 技术栈

| 类别 | 选型 | 版本 |
| --- | --- | --- |
| 语言 | Python | 3.14 |
| Web 框架 | FastAPI | 0.142.2 |
| ASGI 服务器 | Uvicorn | 0.54.0 |
| ORM | SQLAlchemy | 2.1.1 |
| 数据库 | PostgreSQL | 18 |
| 数据库驱动 | psycopg（+ psycopg2-binary） | 3.3.6 / 2.9.13 |
| 密码哈希 | bcrypt | 5.0.0 |
| JWT | python-jose | 3.5.0 |
| 环境变量 | python-dotenv | 1.2.4 |
| 配置管理 | pydantic-settings | 2.15.0 |
| 数据校验 | Pydantic | 2.13.5 |

> 完整依赖清单见 [`requirements.txt`](./requirements.txt)。

## 项目结构

```text
medical_system/
├── app/                       # 应用包：按职责拆分为六个模块
│   ├── __init__.py
│   ├── config.py              # 配置中心：pydantic-settings 读取 .env
│   ├── database.py            # 数据库：engine / SessionLocal / Base / get_db
│   ├── models.py              # 数据模型：Patient / Department / User / MedicalRecord
│   ├── schemas.py             # 请求体校验模型（Pydantic）
│   ├── auth.py                # 密码哈希、JWT 签发与校验、角色权限依赖
│   └── routers.py             # 全部业务路由（APIRouter）
├── docs/
│   ├── incident-log.md        # 事故记录（数据库密码泄露事件复盘）
│   └── medical-record-design.md  # 病历模块表设计（字段、DDL、业务规则）
├── main.py                    # 应用入口：创建 FastAPI 实例、注册异常处理与路由
├── requirements.txt           # 依赖清单
├── README.md                  # 项目说明（本文件）
├── .env                       # 环境变量：数据库连接串、密钥（已被 .gitignore 排除）
└── .gitignore                 # Git 忽略规则
```

> **分层原则**：`main.py` 只负责装配，业务代码全部下沉到 `app/`。依赖方向单向——`routers` → `auth`/`schemas`/`models` → `database` → `config`，反向 import 会造成循环导入。

## 快速开始

### 1. 环境要求

| 项目 | 最低要求 | 本项目开发环境 |
| --- | --- | --- |
| Python | 3.12+ | 3.14 |
| PostgreSQL | 15+ | 18 |

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
DATABASE_URL=postgresql://postgres:你的密码@localhost:5432/medical_db
SECRET_KEY=你的随机密钥
```

`SECRET_KEY` 可用以下命令生成：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> **注意**：`.env` 已在 `.gitignore` 中排除，不会上传到 GitHub。

### 4. 启动服务

```bash
uvicorn main:app --reload
```

### 5. 访问 API 文档

浏览器打开 <http://localhost:8000/docs>（Swagger UI），或 <http://localhost:8000/redoc>。

### 6. 与前端联调（可选）

本仓库只提供 API，界面在 [`../medical-frontend`](../medical-frontend)。联调时两个都要启动：

```bash
# 终端 1：后端
uvicorn main:app --reload

# 终端 2：前端（Vue 3 + Vite）
cd ../medical-frontend
npm install
npm run dev
```

前端默认跑在 `http://localhost:5173`，后端的 CORS 白名单已按这个端口配置。若前端换了端口，需同步修改 `main.py` 中的 `allow_origins` 并重启后端，否则浏览器会拦截请求。

## API 接口一览

| 方法 | 路径 | 说明 | 是否需要鉴权 |
| --- | --- | --- | --- |
| `GET` | `/` | 服务运行状态 | 否 |
| `POST` | `/patients` | 创建患者 | 否 |
| `GET` | `/patients` | 查询患者列表 | 否 |
| `GET` | `/departments` | 查询科室列表（注册页的科室下拉数据源，未登录也可调用） | 否 |
| `POST` | `/departments` | 新增科室，`name` 重复返回 `400` | 是（`admin`） |
| `POST` | `/register` | 用户注册（`role` 仅允许 `doctor` / `nurse`，其他值返回 `422`） | 否 |
| `POST` | `/login` | 用户登录，返回访问令牌 | 否 |
| `GET` | `/me` | 查询当前登录用户信息 | 是（任意角色） |
| `POST` | `/records` | 创建病历（`record_no` 自动生成，初始状态 `draft`） | 是（`doctor`） |
| `GET` | `/records` | 病历列表（`skip` / `limit` 分页，`patient_id` 过滤，按创建时间倒序；非 `admin` 只返回自己接诊的病历） | 是（任意角色） |
| `GET` | `/records/{record_id}` | 病历详情（仅 `admin` 或该病历的接诊医生） | 是（`admin` 或本人） |
| `POST` | `/records/{record_id}/sign` | 病历签名锁定（仅该病历的接诊医生，且病历须为 `draft`；重复签名返回 `400`） | 是（`doctor` 本人） |
| `GET` | `/doctor-only` | 医生专属示例接口 | 是（`doctor`） |
| `GET` | `/admin-only` | 管理员专属示例接口 | 是（`admin`） |

> `POST /records/{record_id}/sign` 的三种失败情况：病历不存在 → `404`；不是自己的病历 → `403`；已经签过名 → `400`。
>
> ⚠️ **`role` 收紧后如何创建管理员**：`POST /register` 现在只接受 `doctor` 与 `nurse`，`admin` 账号无法自助注册。新建管理员需要直接操作数据库：先按普通医生注册，再执行 `UPDATE users SET role = 'admin' WHERE username = '你的用户名';`。这样设计是有意的——管理员属于系统级权限，不应由公开接口发放。
>
> **`GET /records?patient_id=` 的过滤语义**：`patient_id` 是追加在数据隔离条件之后的 `AND`，不是覆盖。所以管理员能查到该患者的全部病历；医生只能查到「该患者 + 自己接诊」这部分；医生查一个自己没接诊过的患者会得到**空列表**（而不是 `403`）。前端据此把空态文案写成「该患者暂无你接诊的记录」，避免被误读成数据丢失。
>
> ⚠️ **已知问题（待修复）**：`register_user` 中的科室校验写成了 `db.query(Department).filter(department_id=data.department_id)`，SQLAlchemy 的 `filter()` 只接受位置参数，这样写会抛 `TypeError: Query.filter() got an unexpected keyword argument 'department_id'`。只要注册时选了科室就返回 `500`。正确写法是 `db.query(Department).filter(Department.id == data.department_id).first()`（或 `filter_by(id=...)`）。

## 数据模型

| 表 | 字段 | 说明 |
| --- | --- | --- |
| `patients` | `id`、`name`、`gender`、`phone` | 患者基本信息 |
| `departments` | `id`、`name` | 科室，`name` 唯一 |
| `users` | `id`、`username`、`password_hash`、`real_name`、`role`、`department_id`、`created_at` | 系统用户，`username` 唯一，`department_id` 外键关联 `departments` |
| `medical_records` | `id`、`record_no`、`patient_id`、`doctor_id`、`visit_type`、`visit_time`、`chief_complaint`、`present_illness`、`allergy_history`、`status`、`signed_at`、`created_at`、`updated_at` | 病历主表，一次就诊一条；`record_no` 唯一，`patient_id` → `patients`、`doctor_id` → `users`；`status` 取值 `draft` / `signed` / `amended` / `void` |

> `medical_records` 目前只实现了主表的最小字段集。完整的字段分组、`diagnoses`（诊断）与 `record_revisions`（修订留痕）两张子表、DDL 与业务规则见[设计文档](./docs/medical-record-design.md)。

## 鉴权说明

登录成功后返回的 `access_token` 为 Bearer 令牌，访问受保护接口时放在请求头中：

```bash
# 1. 登录，获取 token
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "doctor01", "password": "your_password"}'

# 2. 携带 token 访问受保护接口
curl http://localhost:8000/me \
  -H "Authorization: Bearer <你的 access_token>"
```

- 令牌算法：`HS256`
- 有效期：60 分钟
- 权限不足时返回 `403`，令牌无效或过期时返回 `401`

## 版本管理

> 项目自 `v0.4.0` 起引入版本管理：在此之前提交到 GitHub 时从未打过版本号，历史提交只能靠 commit message 区分。自 `v0.4.0` 起统一采用语义化版本与 Git Tag 规范。

### 为什么需要版本号

- 提交历史（commit）是「做了什么」，版本号（tag）是「发布了什么」——一个版本可以包含多次提交。
- 有了 tag，才能随时回到某个稳定状态：`git checkout v0.2.0`。
- GitHub 的 Releases 页面基于 tag 生成，便于归档与回溯。

### 语义化版本规范（SemVer）

版本号格式为 `MAJOR.MINOR.PATCH`：

| 位 | 何时递增 | 示例 |
| --- | --- | --- |
| `MAJOR` | 不兼容的重大变更 | `1.0.0` |
| `MINOR` | 向下兼容地新增功能 | `0.4.0` → `0.5.0` |
| `PATCH` | 向下兼容地修复缺陷 | `0.4.0` → `0.4.1` |

本项目当前处于 `0.x` 阶段：此时 API 尚未定型，**新增功能递增 MINOR，修复问题递增 PATCH**，`1.0.0` 留给首个功能完整的正式版。

### 版本号唯一来源

`main.py` 顶部维护唯一版本号，并传给 FastAPI：

```python
__version__ = "0.10.0"
app = FastAPI(title="病历管理系统", version=__version__)
```

发版时只需改这一处，`/docs` 页面上显示的版本会自动同步。

### Git Tag 常用命令

```bash
# 打一个带说明的附注标签（推荐，附注标签会记录打标人和时间）
git tag -a v0.6.0 -m "v0.6.0: 工程化重构，main.py 拆分为六个模块"

# 查看已有标签
git tag -l

# 查看某个标签指向的提交及其说明
git show v0.6.0

# 推送单个标签到 GitHub
git push origin v0.6.0

# 一次推送所有本地标签
git push origin --tags

# 删除本地标签（打错了时使用）
git tag -d v0.6.0
```

### 标准发版流程

1. 完成功能开发，本地启动确认 `/docs` 中接口数量与版本号正确
2. 更新 `main.py` 中的 `__version__`（代码中的唯一来源）
3. 更新 README 中全部版本号位置（见下表）
4. 提交代码：`git commit -m "..."`，再 `git push`
5. 打标签并推送：`git tag -a vX.Y.Z -m "..."` → `git push origin vX.Y.Z`
6. 校验：`grep -n "当前版本" README.md` 显示的是新版本号

**README 中版本号共有 5 处，发版时必须一起改**——`v0.5.0` 那次就漏掉了前两处，导致标签指向的 README 仍写着 `v0.4.0`：

| # | 位置 |
| --- | --- |
| 1 | 文件开头「当前版本」一行 |
| 2 | 「版本管理 → 版本号唯一来源」中的示例代码 |
| 3 | 「版本与提交对照」表格（新增一行） |
| 4 | 「最新更新内容」标题及正文 |
| 5 | 「版本历史」表格（新增一行） |

> **关于已发布版本的历史状态**：标签指向的提交快照是不可变的，本项目历史上两次出现「代码已更新、README 未同步」：
>
> - `v0.5.0`（`c38d3dc`）的 README 仍显示 `v0.4.0`；
> - 第 8 次代码提交 `f6bde48` 的 README 仍显示 `v0.7.0`，已由紧随其后的文档提交修正，`v0.8.0` 标签打在修正后的提交上。
>
> 这类**已经推送的历史不应通过改写历史（`git commit --amend`、`git push --force`）修复**，正确做法是在下一个提交中修正、在文档中记录，并把标签打在修正后的提交上，就像现在这样。

### 版本与提交对照

> 已发布的版本均已打附注标签并推送到 GitHub，可用 `git ls-remote --tags origin` 核对。标为「本次提交」的版本，在提交后再执行打标签命令。

| 版本 | 对应提交 | 提交日期 | 标签说明 |
| --- | --- | --- | --- |
| `v0.10.0` | 本次提交 | 2026-11-11 | 科室管理接口、病历反向查询，业务闭环打通 |
| `v0.9.0` | `04987a9` | 2026-11-02 | 病历数据隔离、角色校验、JWT 异常细分 |
| `v0.8.0` | `ff8227e` | 2026-10-29 | 病历签名锁定接口；病历详情与签名的前后端闭环 |
| `v0.7.0` | `91f8358` | 2026-10-24 | 病历列表/详情接口与 CORS 支持，为前端联调做准备 |
| `v0.6.0` | `b1c151c` | 2026-10-17 | 工程化重构：`main.py` 拆分为 `app/` 六个模块 |
| `v0.5.0` | `c38d3dc` | 2026-10-11 | 病历模块最小版本（主表 + 创建接口）与表设计文档 |
| `v0.4.0` | `d175c43` | 2026-10-08 | 引入语义化版本与发版流程，README 重写 |
| `v0.3.0` | `f8ce034` | 2026-10-04 | 注册登录、JWT 鉴权与角色权限 |
| `v0.2.0` | `c816643` | 2026-10-04 | 科室表、用户表，密码改用环境变量 |
| `v0.1.0` | `c6257c7` | 2026-10-02 | 项目初始化，患者基础接口 |

核对本地标签及其指向的提交：

```bash
# 列出所有标签及一行说明
git tag -l -n1

# 查看最近 6 条提交，以及各自挂着的标签
git log --oneline --decorate -6
```

## 最新更新内容（`v0.10.0`）

本次更新是项目自创建以来的**第 10 次版本提交**，主题是**业务闭环**——科室从「只能手改数据库」变成「管理员可维护」，病历从「只能顺着看」变成「可以按患者倒着查」。

- 🏢 **科室管理接口（新增 2 个）**：`POST /departments` 仅 `admin` 可调用，`name` 重复返回 `400`；`GET /departments` **不要求登录**，因为注册页要在拿到 token 之前就把科室下拉框填上。这个「公开读、管理员写」的组合是刻意的
- 🔁 **病历反向查询**：`GET /records` 增加 `patient_id` 查询参数，与已有的「非 `admin` 只看自己接诊」形成 `AND` 叠加，前端因此能做「点患者 → 看他的全部就诊记录」
- 🧩 **业务链闭环**：注册 → 建患者 → 建病历 → 签名 → 按患者回查，五个动作现在都能在界面上走完，不再需要 Swagger 或手写 SQL 补位
- 🖥️ **前端配套**：新增注册页（`/register`）与科室下拉；管理员登录后多出「科室管理」标签页；患者列表每行加「查看档案」，抽屉里按 `patient_id` 拉历史病历
- 📝 **文档同步**：接口一览补到 14 个，开发进度勾选三项

> **这一版还留了一个 bug**：注册时选择科室会返回 `500`（`filter(department_id=...)` 用法错误），修复方式见「API 接口一览」下方的「已知问题」。**提交前建议先修掉**——否则注册页只要不选科室能用、选了就崩，演示时很容易踩到。

**如何验收**：`/docs` 中接口数量 **14 个**，版本号显示 `0.10.0`。用管理员登录前端，能在「科室管理」里新增科室；用医生登录，点患者行的「查看档案」能看到该患者的病历列表（只含自己接诊的部分）。

## 版本历史

| 版本 | 日期 | 主要内容 |
| --- | --- | --- |
| `v0.10.0` | 2026-11-11 | 新增科室管理接口（`POST /departments` 仅 `admin`、`GET /departments` 公开）；`GET /records` 支持 `patient_id` 反向查询；前端新增注册页、科室管理标签页与患者历史档案抽屉 |
| `v0.9.0` | 2026-11-02 | 修复 `GET /records` 列表越权（非 `admin` 追加 `doctor_id` 过滤）；`role` 改为 `Literal["doctor","nurse"]` 阻止任意角色注册；JWT 异常细分为 `JWTError` / `ValueError`；前端新增 axios 统一封装 |
| `v0.8.0` | 2026-10-29 | 新增病历签名锁定接口（`POST /records/{record_id}/sign`）：仅接诊医生可签、重复签名返回 `400`、写入 `signed_at`；前端补齐病历列表、详情抽屉与签名交互 |
| `v0.7.0` | 2026-10-24 | 新增病历列表（`GET /records`）与详情（`GET /records/{record_id}`）接口、`MedicalRecordResponse` 响应模型；增加 CORS 中间件供前端联调 |
| `v0.6.0` | 2026-10-17 | 工程化重构：`main.py` 拆分为 `app/` 六个模块；引入 `pydantic-settings` 配置中心；修复重复定义、缺失默认值与冗余导入；同步 README |
| `v0.5.0` | 2026-10-11 | 新增病历主表（`medical_records`）与创建接口（`POST /records`，仅医生）；新增病历模块表设计文档 |
| `v0.4.0` | 2026-10-08 | 引入语义化版本与 Git Tag 规范；README 工程化重写（接口一览、数据模型、鉴权示例、版本管理） |
| `v0.3.0` | 2026-10-04 | 新增用户注册（`POST /register`）、登录（`POST /login`）；JWT 鉴权与受保护接口（`GET /me`）；基于角色的权限控制（`require_role`、`/doctor-only`、`/admin-only`）；补充事故记录文档 |
| `v0.2.0` | 2026-10-04 | 新增科室表（`departments`）和用户表（`users`）；数据库密码改用环境变量管理（修复密码泄露事故） |
| `v0.1.0` | 2026-10-02 | 项目初始化，FastAPI + PostgreSQL 最小可运行版本，患者基础接口（`POST /patients`、`GET /patients`） |

## 事故记录

详见 [`docs/incident-log.md`](./docs/incident-log.md)（2026-10-03 数据库密码泄露到 GitHub 的完整复盘）。

## 后续计划

- [ ] 病历修改接口（`PATCH /records/{id}`：仅 `draft` 可改，`signed` 状态拒绝修改）
- [ ] 修订留痕（`record_revisions`：记录每次修改的前后快照与修改人）
- [ ] 诊断子表（`diagnoses`）与 ICD-10 编码
- [ ] 审计日志（记录所有敏感操作）
- [ ] 细粒度权限（医生只能查看自己科室的患者）
- [ ] 路由版本化（统一前缀 `/api/v1`）
- [ ] 补充 pytest 自动化测试，为 `1.0.0` 做准备
- [ ] 技术债清理（计划在 `1.0.0` 前处理）：`requirements.txt` 转 UTF-8、病史字段由 `String(255)` 改为 `Text`、删除 `app/auth.py` 末尾残留的 `except Exception` 兜底（`JWTError` / `ValueError` 已细化，但宽泛捕获仍在，等于没完全收窄）

## 设计文档

- [病历模块表设计](docs/medical-record-design.md)
- [事故记录](docs/incident-log.md)

## 说明

本项目为个人学习项目，仅用于练习后端开发与医疗信息化业务建模，**不可用于生产环境**。

前端代码位于 [`../medical-frontend`](../medical-frontend)，启动与接口对接说明见该目录的 README。
