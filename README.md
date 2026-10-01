markdown
# 病历管理系统 (Medical Record Management System)

基于 FastAPI + PostgreSQL 的病历管理系统后端，用于学习后端开发和医疗信息化业务。

## 当前进度

项目处于早期开发阶段，目前已实现：

- [x] 数据库连接（PostgreSQL）
- [x] 患者表的创建
- [x] 创建患者接口（POST /patients）
- [x] 查询患者列表接口（GET /patients）
- [ ] 用户登录与权限管理
- [ ] 病历管理模块
- [ ] 处方管理模块
- [ ] 审计日志

## 技术栈

- Python 3.14
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL 18
- psycopg (PostgreSQL 驱动)

## 快速开始

### 1. 环境要求

- Python 3.12+
- PostgreSQL 15+

### 2. 安装依赖

```bash
pip install -r requirements.txt
3. 配置数据库
在 PostgreSQL 中创建数据库：

sql
CREATE DATABASE medical_db;
修改 main.py 中的数据库连接串，换成你自己的密码：

python
DATABASE_URL = "postgresql://postgres:你的密码@localhost:5432/medical_db"
4. 启动服务
bash
uvicorn main:app --reload
5. 访问 API 文档
浏览器打开：

text
http://localhost:8000/docs
项目结构
text
medical_system/
├── main.py              # 主程序
├── requirements.txt     # 依赖清单
├── README.md            # 项目说明
└── .gitignore           # Git 忽略规则
后续计划
用户认证（JWT + bcrypt）

病历 CRUD

权限控制（医生/护士/管理员）

审计日志

说明
本项目为个人学习项目，用于练习后端开发与医疗信息化业务建模。