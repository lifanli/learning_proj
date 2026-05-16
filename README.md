# AI 学习与知识库自动出版系统

默认语言：中文 | [English](README.en.md)

这是一个面向个人学习和技术资料沉淀的 AI 工作台。系统会从课程、网页、GitHub、ArXiv、微信公众号等来源收集资料，整理成本地素材库，再基于素材生成结构化 Markdown 知识库。

当前开发分支：`study-proj-current`

## 核心能力

- 课程表生成：根据学习目标生成领域、主题、搜索关键词和推荐资料源。
- 自动学习：按课程表或手动输入主题/链接，抓取并加工学习资料。
- 素材库管理：用 SQLite 索引和文件系统保存完整正文、图片、代码块、标签、术语和引用。
- 自动出版：从素材库检索资料，规划章节，生成书籍式 Markdown 知识库。
- Web 控制台：通过 FastAPI + Vue 管理学习、出版、素材、日志和设置。
- 后台任务：长任务支持状态查看、进度展示、取消、重试和历史记录。
- OpenAI 兼容模型：默认接入 Xiaomi MiMo，也保留自定义 OpenAI 兼容接口、DashScope/Qwen、Anthropic Claude 预设。

## 项目结构

```text
.
├── config/                 # 系统配置、课程表和预置学习资源注册表
├── frontend/               # Vue 控制台
├── src/
│   ├── core/               # LLM 客户端、任务 DAG、素材库等基础模块
│   ├── student/            # 学生智能体：搜索、抓取、翻译、标注、加工素材
│   ├── publisher_v2/       # 出版社智能体：规划目录、撰写章节、组装知识库
│   ├── researchers/        # ArXiv、微信、文档资料研究器
│   ├── tools/              # 网页、搜索、PDF、GitHub 等工具
│   └── webapi/             # FastAPI 服务和后台任务运行时
├── tests/                  # 单元测试、集成测试和冒烟测试
├── data/                   # 本地运行数据，仅保留 .gitkeep
└── knowledge_base/         # 生成的知识库，仅保留 .gitkeep
```

## 快速开始

### 1. 准备环境

推荐使用项目既有的 Conda 环境名：

```powershell
conda create -n study-proj python=3.11
conda activate study-proj
python -m pip install -r requirements.txt
```

安装前端依赖：

```powershell
cd frontend
npm install
cd ..
```

### 2. 配置 API Key

默认配置使用 Xiaomi MiMo 的 OpenAI 兼容接口：

```text
https://token-plan-cn.xiaomimimo.com/v1
```

把密钥写入本地 `.env`：

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` 中应包含：

```text
XIAOMI_MIMO_API_KEY=your_api_key_here
```

不要把真实密钥写入 `config/settings.yaml`，也不要提交 `.env`。

### 3. 启动系统

一键构建前端并启动集成服务：

```powershell
.\start.bat
```

默认访问地址：

```text
http://localhost:8000
```

也可以只启动 API：

```powershell
python run_api.py
```

## 常用命令

运行后端测试：

```powershell
python -m pytest -q
```

运行真实 LLM 冒烟测试：

```powershell
$env:RUN_LIVE_LLM_TEST="1"
python -m pytest tests/test_llm.py -q
```

运行独立 OpenAI 兼容接口测试脚本：

```powershell
python test-openai.py
```

构建前端：

```powershell
cd frontend
npm run build
```

## 本地数据与 Git 规则

以下内容默认不提交：

- `.env` 和所有本地密钥文件
- `data/` 下的数据库、日志、PDF、任务记录、素材库
- `knowledge_base/` 下生成的书籍、Markdown 文档和压缩包
- `frontend/dist/` 前端构建产物
- 本地过程文档、个人笔记和临时工具状态

仓库只保留程序代码、配置模板、测试和必要的目录占位文件。

## 主要工作流

1. 在“学习流程”中输入学习目标，生成课程表。
2. 审核课程表后启动自动学习，系统会搜索和抓取相关资料。
3. 在“学习资料”中检查素材是否完整、可出版。
4. 在“出版”中输入主题，系统从素材库生成知识库书籍。
5. 在“知识库”中预览生成的 Markdown 文件。

## 注意事项

- 长任务会调用外部模型和数据源，可能产生费用或遇到限流。
- ArXiv、GitHub、网页搜索等外部服务不可用时，系统会尽量降级处理。
- 默认配置面向本地单人使用，设置接口只允许本机访问。
- 生成的知识库是运行产物，不属于代码仓库内容。
