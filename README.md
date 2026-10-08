# 病历管理系统（Medical Record Management System）

> 一个基于 **FastAPI + PostgreSQL** 的病历管理系统后端，用于个人练习后端开发与医疗信息化业务建模。

**当前版本：`v0.4.0`**
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
- [本次更新内容](#本次更新内容v040)
- [版本历史](#版本历史)
- [事故记录](#事故记录)
- [后续计划](#后续计划)
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
- [ ] 病历管理模块
- [ ] 处方管理模块
- [ ] 审计日志
- [ ] 角色字段校验（`role` 只允许预定义值）

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
| 数据校验 | Pydantic | 2.13.5 |

> 完整依赖清单见 [`requirements.txt`](./requirements.txt)。

## 项目结构

```text
medical_system/
├── docs/
│   └── incident-log.md    # 事故记录（数据库密码泄露事件复盘）
├── main.py                # 主程序：数据模型、鉴权逻辑、全部接口
├── requirements.txt       # 依赖清单
├── README.md              # 项目说明（本文件）
├── .env                   # 环境变量：数据库连接串、密钥（已被 .gitignore 排除）
└── .gitignore             # Git 忽略规则
```

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

## API 接口一览

| 方法 | 路径 | 说明 | 是否需要鉴权 |
| --- | --- | --- | --- |
| `GET` | `/` | 服务运行状态 | 否 |
| `POST` | `/patients` | 创建患者 | 否 |
| `GET` | `/patients` | 查询患者列表 | 否 |
| `POST` | `/register` | 用户注册 | 否 |
| `POST` | `/login` | 用户登录，返回访问令牌 | 否 |
| `GET` | `/me` | 查询当前登录用户信息 | 是（任意角色） |
| `GET` | `/doctor-only` | 医生专属示例接口 | 是（`doctor`） |
| `GET` | `/admin-only` | 管理员专属示例接口 | 是（`admin`） |

## 数据模型

| 表 | 字段 | 说明 |
| --- | --- | --- |
| `patients` | `id`、`name`、`gender`、`phone` | 患者基本信息 |
| `departments` | `id`、`name` | 科室，`name` 唯一 |
| `users` | `id`、`username`、`password_hash`、`real_name`、`role`、`department_id`、`created_at` | 系统用户，`username` 唯一，`department_id` 外键关联 `departments` |

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

> 本节为本次新增内容：在此之前，项目提交到 GitHub 时**从未打过版本号**，历史提交只能靠 commit message 区分。从现在起引入语义化版本与 Git Tag 规范。

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
__version__ = "0.4.0"
app = FastAPI(title="病历管理系统", version=__version__)
```

发版时只需改这一处，`/docs` 页面上显示的版本会自动同步。

### Git Tag 常用命令

```bash
# 打一个带说明的附注标签（推荐，附注标签会记录打标人和时间）
git tag -a v0.4.0 -m "v0.4.0: 引入版本管理，README 工程化重写"

# 查看已有标签
git tag -l

# 查看某个标签指向的提交及其说明
git show v0.4.0

# 推送单个标签到 GitHub
git push origin v0.4.0

# 一次推送所有本地标签
git push origin --tags

# 删除本地标签（打错了时使用）
git tag -d v0.4.0
```

### 标准发版流程

1. 完成功能开发，确认本地测试通过
2. 更新 `main.py` 中的 `__version__`
3. 更新 README 的「版本历史」章节
4. 提交代码：`git commit -m "..."` 并 `git push`
5. 打标签并推送：`git tag -a vX.Y.Z -m "..."` → `git push origin vX.Y.Z`

### 版本与提交对照

> 项目自创建以来的提交与版本号对照如下。前 3 次提交均**尚未打标签**，可按下表补齐；`v0.4.0` 对应本次更新，需先提交再打标签。

| 版本 | 对应提交 | 提交日期 | 打标命令 |
| --- | --- | --- | --- |
| `v0.1.0` | `c6257c7` | 2026-10-02 | `git tag -a v0.1.0 c6257c7 -m "v0.1.0: 项目初始化，患者基础接口"` |
| `v0.2.0` | `c816643` | 2026-10-04 | `git tag -a v0.2.0 c816643 -m "v0.2.0: 科室表、用户表，密码改用环境变量"` |
| `v0.3.0` | `f8ce034` | 2026-10-04 | `git tag -a v0.3.0 f8ce034 -m "v0.3.0: 注册登录、JWT 鉴权与角色权限"` |
| `v0.4.0` | 本次更新 | 2026-10-08 | 提交后执行 `git tag -a v0.4.0 -m "v0.4.0: 引入版本管理，README 重写"` |

补齐历史标签（一次性推送全部本地标签）：

```bash
git tag -a v0.1.0 c6257c7 -m "v0.1.0: 项目初始化，患者基础接口"
git tag -a v0.2.0 c816643 -m "v0.2.0: 科室表、用户表，密码改用环境变量"
git tag -a v0.3.0 f8ce034 -m "v0.3.0: 注册登录、JWT 鉴权与角色权限"
git push origin --tags
```

## 本次更新内容（`v0.4.0`）

本次更新是项目自创建以来的**第 4 次版本提交**，版本号定为 `v0.4.0`。此前 3 次提交均未打版本号，从本次起正式建立版本规范。

- 🏷️ **引入版本管理**：首次确立语义化版本（SemVer）规范与 Git Tag 发版流程，并为历史 3 次提交补齐版本号
- 🔢 **统一版本号来源**：版本号统一由 `main.py` 的 `__version__` 维护，并同步到 FastAPI 应用的 `/docs` 页面
- 📝 **README 工程化重写**：修复原先代码块未闭合、章节层级丢失等格式问题，补充接口一览、数据模型、目录结构、鉴权示例等说明
- 📅 **核对版本历史**：原「版本历史」的日期与真实提交记录不一致，已按 `git log` 重新核对

## 版本历史

| 版本 | 日期 | 主要内容 |
| --- | --- | --- |
| `v0.4.0` | 2026-10-08 | 引入语义化版本与 Git Tag 规范；README 工程化重写（接口一览、数据模型、鉴权示例、版本管理） |
| `v0.3.0` | 2026-10-04 | 新增用户注册（`POST /register`）、登录（`POST /login`）；JWT 鉴权与受保护接口（`GET /me`）；基于角色的权限控制（`require_role`、`/doctor-only`、`/admin-only`）；补充事故记录文档 |
| `v0.2.0` | 2026-10-04 | 新增科室表（`departments`）和用户表（`users`）；数据库密码改用环境变量管理（修复密码泄露事故） |
| `v0.1.0` | 2026-10-02 | 项目初始化，FastAPI + PostgreSQL 最小可运行版本，患者基础接口（`POST /patients`、`GET /patients`） |

## 事故记录

详见 [`docs/incident-log.md`](./docs/incident-log.md)（2026-10-03 数据库密码泄露到 GitHub 的完整复盘）。

## 后续计划

- [ ] 病历管理模块（创建、查询、修改）
- [ ] 处方管理模块
- [ ] 审计日志（记录所有敏感操作）
- [ ] 角色字段校验（限制 `role` 为预定义值）
- [ ] 细粒度权限（医生只能查看自己科室的患者）
- [ ] 补充自动化测试，为 `1.0.0` 做准备

## 说明

本项目为个人学习项目，仅用于练习后端开发与医疗信息化业务建模，**不可用于生产环境**。
