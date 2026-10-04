# 事故记录

## 2026-10-03：数据库密码泄露到 GitHub

### 发生了什么
在项目第二次提交时，把包含真实数据库密码的 `main.py` 推送到了公开的 GitHub 仓库。

### 原因
- 密码硬编码在 `main.py` 里
- 没有使用 `.env` 管理敏感配置
- 提交前没有检查 `git diff`

### 处理
1. 立即修改了 PostgreSQL 的 `postgres` 用户密码（旧密码作废）
2. 引入 `.env` 文件存储密码，用 `python-dotenv` 加载
3. `main.py` 改为从环境变量读取密码，代码里只留占位符
4. `.gitignore` 增加 `.env`，防止再次泄露
5. 用 `git rebase -i` 重写历史，把泄露密码的那次提交合并掉
6. `git push --force` 覆盖远程历史