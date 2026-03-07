# 后端技术方案设计

**文档 ID**: backend-technical-design  
**项目名称**: 智能学习助手 (Learning Agent System)  
**负责人**: 王志强 (Backend Engineer)  
**创建时间**: 2026-03-06 20:38 UTC  
**状态**: 初稿  

---

## 一、技术栈选型

### 1.1 核心技术栈

| 层级 | 技术选型 | 版本 | 理由 |
|------|----------|------|------|
| **Web 框架** | FastAPI | 0.109+ | 异步支持、自动文档、类型安全 |
| **AI 框架** | LangChain | 0.1+ | 智能体编排、工具链、记忆管理 |
| **向量数据库** | LightRAG | latest | 图 + 向量混合检索，适合任务关联推荐 |
| **嵌入模型** | text-embedding-3-small | - | OpenAI API，成本低、效果好 |
| **LLM** | Qwen3.5-Plus | - | 通过 Higress Gateway 调用 |
| **文件存储** | MinIO | latest | S3 兼容，本地部署 |
| **数据库** | SQLite / PostgreSQL | - | SQLite(开发) / PostgreSQL(生产) |
| **任务队列** | Celery + Redis | - | 异步任务处理 |

### 1.2 开发环境

```yaml
Python: 3.11+
Package Manager: uv / pip
Code Style: ruff + black
Type Check: mypy
Testing: pytest + pytest-asyncio
```

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         智能学习助手 - 后端架构                          │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────────────────────────────────────────┐
│   前端       │────▶│              FastAPI Gateway                         │
│  (Vue3)      │     │  - 认证中间件                                        │
│              │     │  - 请求路由                                          │
│              │     │  - 限流/日志                                         │
└──────────────┘     └──────────────────────────────────────────────────────┘
                                              │
         ┌────────────────────────────────────┼────────────────────────────┐
         │                                    │                            │
         ▼                                    ▼                            ▼
┌─────────────────┐              ┌─────────────────┐           ┌─────────────────┐
│  用户服务       │              │  知识服务       │           │  智能体服务     │
│  - 用户管理     │              │  - 知识检索     │           │  - LangChain    │
│  - 认证授权     │              │  - 向量搜索     │           │  - 工具调用     │
│  - 会话管理     │              │  - 文档解析     │           │  - 记忆管理     │
└────────┬────────┘              └────────┬────────┘           └────────┬────────┘
         │                                │                             │
         └────────────────────────────────┼─────────────────────────────┘
                                          │
         ┌────────────────────────────────┼─────────────────────────────┐
         │                                │                             │
         ▼                                ▼                             ▼
┌─────────────────┐              ┌─────────────────┐           ┌─────────────────┐
│   PostgreSQL    │              │    LightRAG     │           │     MinIO       │
│   (用户/任务)   │              │  (向量/图检索)  │           │   (文件存储)    │
└─────────────────┘              └─────────────────┘           └─────────────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │    Redis        │
                                 │  (缓存/队列)    │
                                 └─────────────────┘
```

### 2.2 服务分层

| 层级 | 职责 | 模块 |
|------|------|------|
| **API Layer** | HTTP 接口、请求验证、响应格式化 | `api/` |
| **Service Layer** | 业务逻辑、事务管理 | `services/` |
| **Model Layer** | 数据模型、ORM 映射 | `models/` |
| **AI Layer** | LLM 调用、向量嵌入、智能体编排 | `ai/` |
| **Storage Layer** | 数据库、向量库、文件存储 | `storage/` |

---

## 三、数据库设计

### 3.1 ER 图

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│      users       │       │      tasks       │       │   learning_      │
│──────────────────│       │──────────────────│       │   records        │
│ id (PK)          │       │ id (PK)          │       │──────────────────│
│ username         │◀─────▶│ user_id (FK)     │       │ id (PK)          │
│ email            │  1:N  │ title            │  1:1  │ task_id (FK)     │
│ password_hash    │       │ description      │       │ content (JSON)   │
│ created_at       │       │ status           │       │ embedding_ref    │
│ updated_at       │       │ created_at       │       │ created_at       │
└──────────────────┘       │ updated_at       │       └──────────────────┘
                           └──────────────────┘
                                    │
                                    │ 1:N
                                    ▼
                           ┌──────────────────┐
                           │   search_        │
                           │   requests       │
                           │──────────────────│
                           │ id (PK)          │
                           │ task_id (FK)     │
                           │ query            │
                           │ result_ref       │
                           │ status           │
                           │ created_at       │
                           └──────────────────┘
```

### 3.2 表结构定义

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'worker',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 任务表
CREATE TABLE tasks (
    id VARCHAR(50) PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 学习记录表
CREATE TABLE learning_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(50) REFERENCES tasks(id),
    content JSONB NOT NULL,
    embedding_ref VARCHAR(255),
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 搜索请求表
CREATE TABLE search_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(50) REFERENCES tasks(id),
    query TEXT NOT NULL,
    result_ref VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(10) DEFAULT 'P1',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 索引
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_learning_records_task_id ON learning_records(task_id);
CREATE INDEX idx_search_requests_task_id ON search_requests(task_id);
CREATE INDEX idx_search_requests_status ON search_requests(status);
```

---

## 四、API 设计

### 4.1 API 概览

| 模块 | 端点 | 方法 | 描述 |
|------|------|------|------|
| **认证** | `/api/v1/auth/login` | POST | 用户登录 |
| | `/api/v1/auth/logout` | POST | 用户登出 |
| | `/api/v1/auth/refresh` | POST | 刷新 Token |
| **用户** | `/api/v1/users/me` | GET | 获取当前用户信息 |
| | `/api/v1/users/me` | PUT | 更新用户信息 |
| **任务** | `/api/v1/tasks` | GET | 获取任务列表 |
| | `/api/v1/tasks` | POST | 创建任务 |
| | `/api/v1/tasks/{id}` | GET | 获取任务详情 |
| | `/api/v1/tasks/{id}` | PUT | 更新任务 |
| | `/api/v1/tasks/{id}/complete` | POST | 完成任务 |
| **知识** | `/api/v1/knowledge/search` | POST | 知识检索 |
| | `/api/v1/knowledge/records` | GET | 获取学习记录 |
| | `/api/v1/knowledge/records/{id}` | GET | 获取学习记录详情 |
| **搜索** | `/api/v1/search/request` | POST | 提交搜索请求 |
| | `/api/v1/search/status/{id}` | GET | 查询搜索状态 |
| **智能体** | `/api/v1/agent/chat` | POST | 智能体对话 |
| | `/api/v1/agent/recommend` | POST | 获取任务推荐 |

### 4.2 核心 API 详细设计

#### 4.2.1 任务管理

```python
# POST /api/v1/tasks
# 创建任务
Request:
{
    "title": "实现用户认证模块",
    "description": "使用 JWT 实现用户登录认证",
    "type": "backend",
    "priority": "P1"
}

Response:
{
    "id": "task-20260306-001",
    "title": "实现用户认证模块",
    "status": "pending",
    "created_at": "2026-03-06T20:38:00Z",
    "recommended_cases": [
        {
            "task_id": "task-20260201-003",
            "title": "实现 OAuth2 登录",
            "similarity": 0.85
        }
    ]
}

# POST /api/v1/tasks/{id}/complete
# 完成任务（触发学习记录生成）
Request:
{
    "status": "completed",
    "self_rating": 4,
    "notes": "功能完成，待审查"
}

Response:
{
    "id": "task-20260306-001",
    "status": "completed",
    "learning_record_id": "lr-xxx-xxx",
    "next_steps": ["等待 Challenger 审查"]
}
```

#### 4.2.2 知识检索

```python
# POST /api/v1/knowledge/search
# 知识检索
Request:
{
    "query": "如何实现 JWT 认证？",
    "filters": {
        "task_type": "backend",
        "tags": ["认证", "安全"]
    },
    "top_k": 5
}

Response:
{
    "results": [
        {
            "type": "learning_record",
            "task_id": "task-20260201-003",
            "title": "实现 OAuth2 登录",
            "snippet": "使用 PyJWT 库生成和验证 token...",
            "similarity": 0.92,
            "url": "/api/v1/knowledge/records/lr-xxx"
        },
        {
            "type": "search_report",
            "search_id": "sr-xxx",
            "title": "JWT 认证最佳实践",
            "snippet": "JWT 应该设置合理的过期时间...",
            "similarity": 0.88
        }
    ]
}
```

#### 4.2.3 搜索请求

```python
# POST /api/v1/search/request
# 提交搜索请求
Request:
{
    "query": "LightRAG 向量数据库如何使用？",
    "priority": "P1",
    "context": "需要部署向量数据库用于知识检索"
}

Response:
{
    "id": "sr-20260306-001",
    "status": "pending",
    "estimated_completion": "2026-03-06T24:38:00Z",
    "sla_deadline": "2026-03-07T00:38:00Z"
}

# GET /api/v1/search/status/{id}
# 查询搜索状态
Response:
{
    "id": "sr-20260306-001",
    "status": "completed",
    "result_url": "/api/v1/search/results/sr-20260306-001",
    "completed_at": "2026-03-06T22:15:00Z"
}
```

#### 4.2.4 智能体对话

```python
# POST /api/v1/agent/chat
# 智能体对话
Request:
{
    "message": "这个任务我应该怎么做？",
    "context": {
        "task_id": "task-20260306-001",
        "task_type": "backend"
    },
    "history": [...]  # 对话历史
}

Response:
{
    "message": "根据历史相似任务，建议按以下步骤进行：1. 设计 API 接口 2. 实现认证逻辑...",
    "references": [
        {"task_id": "task-20260201-003", "title": "实现 OAuth2 登录"}
    ],
    "suggested_tools": ["code_editor", "search"]
}
```

---

## 五、LangChain 智能体设计

### 5.1 智能体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    LangChain 智能体架构                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│   Agent Executor│
│   (智能体执行器) │
└────────┬────────┘
         │
         ├──────────────────────────────────────────────────────┐
         │                                                      │
         ▼                                                      ▼
┌─────────────────┐                                    ┌─────────────────┐
│   Memory        │                                    │   Tools         │
│   (记忆管理)    │                                    │   (工具集)      │
│                 │                                    │                 │
│ - Conversation  │                                    │ - search_tool   │
│   Memory        │                                    │ - knowledge_    │
│ - Vector Store  │                                    │   search_tool   │
│   Memory        │                                    │ - code_tool     │
│ - Task History  │                                    │ - file_tool     │
└─────────────────┘                                    └─────────────────┘
```

### 5.2 工具定义

```python
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_openai_functions_agent

# 知识检索工具
@tool
def search_knowledge(query: str, top_k: int = 5) -> str:
    """从知识库中检索相关信息"""
    results = vector_store.similarity_search(query, k=top_k)
    return format_results(results)

# 搜索请求工具
@tool
def request_search(query: str, priority: str = "P1") -> str:
    """提交新的搜索请求给 Search Worker"""
    search_id = create_search_request(query, priority)
    return f"搜索请求已提交，ID: {search_id}，预计 {get_sla(priority)} 内完成"

# 任务查询工具
@tool
def get_similar_tasks(task_description: str) -> str:
    """查询相似的历史任务"""
    similar = find_similar_tasks(task_description)
    return format_task_list(similar)

# 学习记录工具
@tool
def generate_learning_record(task_id: str, notes: str) -> str:
    """生成学习记录"""
    record = create_learning_record(task_id, notes)
    return f"学习记录已生成：{record.id}"
```

### 5.3 智能体提示词

```python
SYSTEM_PROMPT = """
你是一个智能学习助手，帮助 Worker 高效完成任务。

你的能力：
1. 检索历史学习记录，提供相似任务参考
2. 提交搜索请求给 Search Worker 获取新知识
3. 生成学习记录，帮助经验沉淀
4. 回答技术问题，提供解决方案建议

你的工作原则：
- 优先检索知识库，避免重复搜索
- 对于新概念，主动建议提交搜索请求
- 任务完成后，提醒生成学习记录
- 保持回答简洁、实用

当前用户信息：
- 角色：{user_role}
- 进行中任务：{current_tasks}
"""
```

---

## 六、安全设计

### 6.1 认证方案

| 机制 | 实现 | 说明 |
|------|------|------|
| **登录认证** | JWT (Access + Refresh) | Access Token 15 分钟，Refresh Token 7 天 |
| **密码存储** | bcrypt + salt | 成本因子 12 |
| **会话管理** | Redis 存储黑名单 | 支持登出失效 |
| **API 密钥** | 前缀 + 哈希存储 | 用于服务间调用 |

### 6.2 授权模型

```python
# 角色权限矩阵
ROLE_PERMISSIONS = {
    "admin": ["*"],
    "manager": ["tasks:*", "users:read", "search:*"],
    "worker": ["tasks:*", "knowledge:read", "search:create"],
    "service": ["internal:*"]  # 服务间调用
}
```

### 6.3 安全防护

| 风险 | 防护措施 |
|------|----------|
| **SSRF** | URL 白名单、禁止内网访问、请求代理 |
| **文件上传** | 类型检查、大小限制、病毒扫描、隔离存储 |
| **SQL 注入** | 参数化查询、ORM 使用 |
| **XSS** | 输入过滤、输出转义 |
| **速率限制** | Redis 计数器、IP/用户维度限流 |
| **敏感数据** | 加密存储、日志脱敏 |

### 6.4 安全中间件

```python
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # CORS 检查
    if not is_allowed_origin(request.headers.get("origin")):
        return JSONResponse({"error": "CORS not allowed"}, status_code=403)
    
    # 速率限制
    client_ip = request.client.host
    if await is_rate_limited(client_ip):
        return JSONResponse({"error": "Rate limited"}, status_code=429)
    
    # 请求日志（脱敏）
    log_request(sanitize(request))
    
    response = await call_next(request)
    return response
```

---

## 七、任务队列设计

### 7.1 Celery 任务定义

```python
from celery import Celery

app = Celery('learning_agent', broker='redis://localhost:6379/0')

# 学习记录生成任务
@app.task(bind=True, max_retries=3)
def generate_learning_record_task(self, task_id: str):
    try:
        task = get_task(task_id)
        record = llm_generate_learning_record(task)
        save_learning_record(record)
        index_to_vector_store(record)
        return {"status": "success", "record_id": record.id}
    except Exception as e:
        raise self.retry(exc=e, countdown=60)

# 搜索请求处理任务
@app.task(bind=True)
def process_search_request_task(self, search_id: str):
    search_req = get_search_request(search_id)
    results = search_web(search_req.query)
    report = llm_summarize_search(results)
    save_search_report(search_id, report)
    index_to_vector_store(report)
    notify_requester(search_id)
    return {"status": "success"}

# 推荐引擎任务
@app.task
def generate_recommendations_task(user_id: str, task_description: str):
    similar = find_similar_tasks(task_description)
    recommendations = rank_recommendations(similar)
    cache_recommendations(user_id, recommendations)
    return recommendations
```

### 7.2 任务状态机

```
┌─────────────┐
│   pending   │ ──▶ 任务创建
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ in_progress │ ──▶ 任务开始执行
└──────┬──────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌─────────────┐ ┌─────────────┐
│  completed  │ │   failed    │
└──────┬──────┘ └──────┬──────┘
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│  reviewing  │ │   retry     │
└──────┬──────┘ └─────────────┘
       │
       ▼
┌─────────────┐
│   archived  │
└─────────────┘
```

---

## 八、项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   │
│   ├── api/                    # API 层
│   │   ├── __init__.py
│   │   ├── deps.py             # 依赖注入
│   │   ├── auth.py             # 认证端点
│   │   ├── users.py            # 用户端点
│   │   ├── tasks.py            # 任务端点
│   │   ├── knowledge.py        # 知识端点
│   │   ├── search.py           # 搜索端点
│   │   └── agent.py            # 智能体端点
│   │
│   ├── services/               # 服务层
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── task_service.py
│   │   ├── knowledge_service.py
│   │   ├── search_service.py
│   │   └── agent_service.py
│   │
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── learning_record.py
│   │   └── search_request.py
│   │
│   ├── ai/                     # AI 层
│   │   ├── __init__.py
│   │   ├── llm.py              # LLM 客户端
│   │   ├── embeddings.py       # 嵌入模型
│   │   ├── vector_store.py     # 向量存储
│   │   └── agent.py            # LangChain 智能体
│   │
│   ├── storage/                # 存储层
│   │   ├── __init__.py
│   │   ├── database.py         # PostgreSQL 连接
│   │   ├── minio_client.py     # MinIO 客户端
│   │   └── redis_client.py     # Redis 连接
│   │
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── security.py         # 安全工具
│       └── helpers.py          # 辅助函数
│
├── celery_app.py               # Celery 应用
├── celery_config.py            # Celery 配置
├── alembic/                    # 数据库迁移
├── tests/                      # 测试
├── requirements.txt            # 依赖
├── Dockerfile                  # Docker 镜像
└── docker-compose.yml          # Docker 编排
```

---

## 九、部署方案

### 9.1 Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/learning_agent
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on:
      - db
      - redis
      - minio

  celery_worker:
    build: ./backend
    command: celery -A celery_app worker -l info
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/learning_agent
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=learning_agent

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### 9.2 环境变量

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/learning_agent

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# LLM
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://gateway.hiclaw.io/v1

# 安全
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# 应用
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
```

---

## 十、开发计划

### 10.1 里程碑

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| **M1** | 第 1 周 | 项目骨架、数据库设计、基础 API |
| **M2** | 第 2 周 | 认证系统、任务管理 API |
| **M3** | 第 3 周 | 知识检索、LightRAG 集成 |
| **M4** | 第 4 周 | LangChain 智能体、搜索请求 |
| **M5** | 第 5 周 | 学习记录生成、完整联调 |

### 10.2 任务分解

| 任务 | 优先级 | 预计工时 |
|------|--------|----------|
| 项目初始化 | P0 | 4h |
| 数据库设计实现 | P0 | 8h |
| 认证系统 | P0 | 12h |
| 任务管理 API | P0 | 16h |
| LightRAG 集成 | P0 | 16h |
| 知识检索 API | P1 | 12h |
| LangChain 智能体 | P1 | 20h |
| 搜索请求系统 | P1 | 12h |
| 学习记录生成 | P0 | 16h |
| 安全加固 | P0 | 8h |
| 测试编写 | P1 | 16h |
| 文档编写 | P1 | 8h |

---

## 十一、风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| LightRAG 学习曲线陡 | 中 | 中 | 预留调研时间，参考官方示例 |
| LLM 响应不稳定 | 中 | 中 | 重试机制、降级方案 |
| 向量检索性能不足 | 低 | 中 | 定期性能测试，优化索引 |
| 安全风险 | 中 | 高 | 代码审查、安全测试、依赖扫描 |

---

## 十二、待确认事项

| 事项 | 说明 | 负责人 |
|------|------|--------|
| PostgreSQL 或 SQLite | 开发环境用 SQLite，生产用 PostgreSQL | 运维工程师 |
| LLM API 接入方式 | Higress Gateway 配置确认 | 架构师 |
| 部署环境细节 | WSL2 / Docker Desktop | 运维工程师 |

---

**文档状态**: 初稿完成，待审查  
**下一步**: @critic-reviewer 进行方案审查
