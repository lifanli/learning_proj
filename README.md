# Learning Code Project

Learning Code Project 是一个本地优先的 AI 学习与知识生产工作台。它把“课程规划、素材学习、知识库整理、长文出版、任务进度跟踪”串成一个可运行的端到端流程，适合用来围绕一个学习目标持续构建个人知识库。

## 核心能力

- 课程表生成：根据学习目标生成结构化 curriculum，并支持审批后执行。
- 自动学习：按课程表抓取和分析网页、GitHub、ArXiv、课程页面等素材。
- 知识库管理：读取本地 Markdown 知识库，前端可浏览目录和文件内容。
- 出版流程：基于已收集素材生成章节、小节和汇总报告。
- 后台任务：课程生成、自动学习、出版任务支持进度、重试、取消和详情查看。
- Web 控制台：FastAPI 后端 + Vue/Vite 前端，支持一键集成启动。

## 技术栈

- 后端：Python, FastAPI, Pydantic, PyYAML
- 前端：Vue 3, Vite
- LLM：OpenAI-compatible API，可配置 DashScope/Qwen 等兼容服务
- 数据：本地文件、Markdown、SQLite/JSON 运行缓存

## 快速启动

项目默认使用 conda 环境 `study-proj`。

```powershell
copy .env.example .env
# 编辑 .env，设置 DASHSCOPE_API_KEY

.\start.bat
```

等价的 PowerShell 启动方式：

```powershell
.\scripts\start.ps1 -CondaEnv study-proj
```

启动后访问：

```text
http://localhost:8000
```

默认只监听 `127.0.0.1`。如果确实需要局域网访问，可以显式传入 `-HostAddress 0.0.0.0`。

## 配置说明

主要配置位于 `config/settings.yaml`。

- `llm.api_key_env` 指定读取哪个环境变量作为 API Key。
- API Key 不写入 `settings.yaml`，请放在本地 `.env` 中。
- `.env`、运行数据、日志、素材库、知识库生成结果和前端构建产物默认不会提交到 Git。

## 常用命令

后端测试：

```powershell
conda run -n study-proj python -m pytest -q
```

前端构建：

```powershell
cd frontend
npm install
npm run build
```

手动 LLM smoke test：

```powershell
$env:RUN_LIVE_LLM_TEST="1"
conda run -n study-proj python -m pytest tests/test_llm.py -q
```

## 分支策略

- `main`：面向展示和稳定版本，README 保持清晰准确。
- `study-proj-current`：日常开发与代码记录分支，不跟踪过程文档和个人笔记。

## 安全边界

- `/api/settings` 仅允许本机访问，并且不会返回或保存明文密钥。
- `/api/system/state` 返回脱敏后的诊断信息。
- 日志和知识库文件读取使用路径归一化与目录包含校验，避免路径穿越。
- 任务列表只返回错误摘要，完整 traceback 仅在任务详情中查看。
