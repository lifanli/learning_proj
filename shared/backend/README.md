# 学习智能体系统 - 后端服务

## 技术栈

- **语言**: Python 3.11+
- **框架**: FastAPI 0.104+
- **数据库**: PostgreSQL 15+ with pgvector
- **ORM**: SQLAlchemy 2.0+
- **认证**: JWT + OAuth2
- **AI 框架**: LangChain

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等
```

### 3. 启动开发服务器

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问 API 文档

打开浏览器访问：http://localhost:8000/docs

## 项目结构

```
backend/
├── app/
│   ├── api/v1/        # API 路由
│   ├── core/          # 核心配置
│   ├── models/        # 数据库模型
│   ├── schemas/       # Pydantic 模型
│   ├── services/      # 业务逻辑
│   └── main.py        # 应用入口
├── tests/             # 测试
├── requirements.txt
├── Dockerfile
└── README.md
```

## API 端点

### 认证
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册

### 用户
- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新用户信息

### 课程
- `GET /api/v1/courses` - 获取课程列表
- `GET /api/v1/courses/{id}` - 获取课程详情

### 智能体
- `POST /api/v1/agents/chat` - 与智能体对话
- `GET /api/v1/agents/sessions` - 获取对话历史

## 开发规范

### 代码风格
- 遵循 PEP 8
- 使用 Black 格式化
- 使用 Flake8 检查

### 测试
```bash
pytest tests/ -v --cov=app
```

## Docker 部署

```bash
docker build -t learning-agent-backend .
docker run -p 8000:8000 --env-file .env learning-agent-backend
```

## 负责人

**赵子轩 | 后端工程师**（由现有团队兼任）
