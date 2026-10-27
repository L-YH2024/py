# 在线投票与问卷系统

## 运行环境

Python 3.10+、MySQL 8.0+。

```sql
CREATE DATABASE vote_system DEFAULT CHARACTER SET utf8mb4;
```

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# 修改 .env 中的 MySQL 用户名和密码
python app.py
```

首次启动会自动创建表。也可以执行 `flask --app app init-db` 初始化数据库。

## 测试账号与测试数据

启动后访问 `/register` 注册账号。运行 `python seed.py` 可创建测试账号 `demo / demo123456`、一份示例问卷和 12 条回答。

## 演示路径

登录 → 创建问卷 → 添加单选题/多选题/填空题 → 复制填写链接 → 匿名填写 → 查看统计 → 导出 CSV。

统计页使用数据库查询实时汇总，单选题和多选题均使用选项计数展示 ECharts 柱状图；CSV 文件带 UTF-8 BOM，可直接用 Excel 打开。

## 功能演示截图

完整演示截图已放在 `screenshots/` 目录，覆盖注册、登录、创建问卷、匿名填写、必填校验、重复提交限制、统计图表和 CSV 导出。建议按文件名前的序号查看。
