# API 设计文档：智能学习助手 Web 应用

**任务 ID**: task-102-api  
**文档版本**: v1.1  
**创建时间**: 2026-03-07 08:00 UTC  
**更新时间**: 2026-03-07 11:00 UTC  
**负责人**: 张建国 (System Architect - 系统架构师)  
**状态**: 审查修复完成  

---

## 一、API 设计原则

### 1.1 设计规范

| 规范 | 说明 |
|------|------|
| **RESTful 风格** | 资源导向，使用 HTTP 动词 |
| **版本控制** | URL 路径包含版本号 `/api/v1/` |
| **统一响应格式** | JSON 格式，包含 code/message/data |
| **认证方式** | JWT Token (Bearer) |
| **错误处理** | 统一错误码 + 错误信息 |
| **文档生成** | FastAPI 自动生成 OpenAPI/Swagger |

### 1.2 统一响应格式

```json
// 成功响应
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": "2026-03-07T08:00:00Z"
}

// 错误响应
{
  "code": 400,
  "message": "Invalid request parameters",
  "errors": [
    {"field": "email", "message": "Invalid email format"}
  ],
  "timestamp": "2026-03-07T08:00:00Z"
}
```

### 1.3 认证机制

```
请求头：
Authorization: Bearer <jwt_token>

Token 有效期：
- Access Token: 24 小时
- Refresh Token: 7 天
```

---

## 二、API 接口清单

### 2.1 认证模块 (Auth)

| 接口 | 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|------|
| 用户注册 | POST | `/api/v1/auth/register` | ❌ | 创建新用户 |
| 用户登录 | POST | `/api/v1/auth/login` | ❌ | 获取 Token |
| 刷新 Token | POST | `/api/v1/auth/refresh` | ❌ | 刷新 Access Token |
| 用户登出 | POST | `/api/v1/auth/logout` | ✅ | 注销当前会话 |
| 获取当前用户 | GET | `/api/v1/auth/me` | ✅ | 获取当前用户信息 |

### 2.2 知识管理模块 (Knowledge)

| 接口 | 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|------|
| 创建知识 | POST | `/api/v1/knowledge` | ✅ | 创建新知识条目 |
| 获取知识列表 | GET | `/api/v1/knowledge` | ✅ | 分页获取知识列表 |
| 获取知识详情 | GET | `/api/v1/knowledge/{id}` | ✅ | 获取单个知识详情 |
| 更新知识 | PUT | `/api/v1/knowledge/{id}` | ✅ | 更新知识内容 |
| 删除知识 | DELETE | `/api/v1/knowledge/{id}` | ✅ | 删除知识 |
| 语义搜索 | GET | `/api/v1/knowledge/search` | ✅ | 向量语义搜索 |
| 批量导入 | POST | `/api/v1/knowledge/batch` | ✅ | 批量导入知识 |

### 2.3 问答模块 (Chat)

| 接口 | 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|------|
| 发送问题 | POST | `/api/v1/chat` | ✅ | 发送问题获取答案 |
| 流式问答 | POST | `/api/v1/chat/stream` | ✅ | SSE 流式响应 |
| 获取对话历史 | GET | `/api/v1/chat/{session_id}` | ✅ | 获取对话历史 |
| 获取会话列表 | GET | `/api/v1/chat/sessions` | ✅ | 获取所有会话 |
| 删除会话 | DELETE | `/api/v1/chat/{session_id}` | ✅ | 删除会话 |
| 重命名会话 | PUT | `/api/v1/chat/{session_id}/title` | ✅ | 重命名会话 |

### 2.4 用户模块 (User)

| 接口 | 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|------|
| 获取用户信息 | GET | `/api/v1/user/profile` | ✅ | 获取个人资料 |
| 更新用户信息 | PUT | `/api/v1/user/profile` | ✅ | 更新个人资料 |
| 上传头像 | POST | `/api/v1/user/avatar` | ✅ | 上传头像图片 |
| 获取学习统计 | GET | `/api/v1/user/stats` | ✅ | 获取学习统计数据 |
| 获取学习路径 | GET | `/api/v1/user/learning-path` | ✅ | 获取推荐学习路径 |

### 2.5 系统模块 (System)

| 接口 | 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|------|
| 健康检查 | GET | `/api/v1/health` | ❌ | 服务健康状态 |
| 获取配置 | GET | `/api/v1/config` | ❌ | 获取前端配置 |
| 文件上传 | POST | `/api/v1/files/upload` | ✅ | 上传文件到 MinIO |
| 文件下载 | GET | `/api/v1/files/{file_id}` | ✅ | 下载文件 |

---

## 三、详细接口定义

### 3.1 认证模块

#### 3.1.1 用户注册

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "string (3-20 字符)",
  "email": "string (邮箱格式)",
  "password": "string (8-20 字符，含大小写和数字)"
}

// 响应 201 Created
{
  "code": 201,
  "message": "Registration successful",
  "data": {
    "user_id": "uuid",
    "username": "string",
    "email": "string",
    "created_at": "datetime"
  }
}

// 错误响应
// 400 Bad Request - 参数验证失败
// 409 Conflict - 用户名或邮箱已存在
```

#### 3.1.2 用户登录

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}

// 响应 200 OK
{
  "code": 200,
  "message": "Login successful",
  "data": {
    "access_token": "string (JWT)",
    "refresh_token": "string",
    "token_type": "Bearer",
    "expires_in": 86400,
    "user": {
      "user_id": "uuid",
      "username": "string",
      "email": "string",
      "avatar_url": "string"
    }
  }
}

// 错误响应
// 401 Unauthorized - 用户名或密码错误
// 403 Forbidden - 账户已被禁用
```

### 3.2 知识管理模块

#### 3.2.1 创建知识

```http
POST /api/v1/knowledge
Content-Type: application/json
Authorization: Bearer <token>

{
  "title": "string (1-200 字符)",
  "content": "string (Markdown 格式)",
  "tags": ["tag1", "tag2"],
  "category": "string (可选)",
  "is_public": false
}

// 响应 201 Created
{
  "code": 201,
  "message": "Knowledge created",
  "data": {
    "id": "uuid",
    "title": "string",
    "content": "string",
    "user_id": "uuid",
    "tags": ["tag1", "tag2"],
    "embedding_status": "pending",
    "created_at": "datetime"
  }
}
```

#### 3.2.2 语义搜索

```http
GET /api/v1/knowledge/search?q=搜索关键词&limit=10&offset=0
Authorization: Bearer <token>

// 查询参数
// q: 搜索关键词 (必需)
// limit: 返回数量 (默认 10, 最大 50)
// offset: 偏移量 (默认 0)
// tags: 标签过滤 (可选，逗号分隔)
// category: 分类过滤 (可选)

// 响应 200 OK
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "items": [
      {
        "id": "uuid",
        "title": "string",
        "content_preview": "string (前 200 字符)",
        "score": 0.95,
        "tags": ["tag1", "tag2"],
        "user": {
          "username": "string"
        },
        "created_at": "datetime"
      }
    ]
  }
}
```

### 3.3 问答模块

#### 3.3.1 发送问题

```http
POST /api/v1/chat
Content-Type: application/json
Authorization: Bearer <token>

{
  "session_id": "uuid (可选，不传则创建新会话)",
  "message": "string (用户问题)",
  "context": {
    "knowledge_ids": ["uuid1", "uuid2"] (可选，指定参考知识)
  }
}

// 响应 200 OK
{
  "code": 200,
  "message": "success",
  "data": {
    "session_id": "uuid",
    "message_id": "uuid",
    "answer": "string (AI 回答)",
    "sources": [
      {
        "knowledge_id": "uuid",
        "title": "string",
        "relevance_score": 0.9
      }
    ],
    "created_at": "datetime"
  }
}
```

#### 3.3.2 流式问答 (SSE)

```http
POST /api/v1/chat/stream
Content-Type: application/json
Authorization: Bearer <token>
Accept: text/event-stream

// 请求体同上

// 响应 (Server-Sent Events)
event: message
data: {"type": "start", "session_id": "uuid"}

event: message
data: {"type": "token", "content": "部"}

event: message
data: {"type": "token", "content": "分"}

event: message
data: {"type": "token", "content": "答"}

event: message
data: {"type": "end", "sources": [...]}

event: message
data: {"type": "done"}
```

### 3.4 文件上传

```http
POST /api/v1/files/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

// Form Data
// file: 文件 (支持 pdf, docx, txt, md, png, jpg)
// max_size: 10MB

// 响应 200 OK
{
  "code": 200,
  "message": "Upload successful",
  "data": {
    "file_id": "uuid",
    "filename": "string",
    "url": "string (MinIO 下载链接)",
    "size": 102400,
    "mime_type": "application/pdf",
    "uploaded_at": "datetime"
  }
}
```

---

## 四、错误码定义

### 4.1 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证/Token 无效 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 (如重复) |
| 422 | 数据验证失败 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |
| 503 | 服务暂时不可用 |

### 4.2 业务错误码

| 错误码 | 说明 |
|--------|------|
| AUTH_001 | 用户名或密码错误 |
| AUTH_002 | Token 已过期 |
| AUTH_003 | Token 无效 |
| AUTH_004 | 账户已被禁用 |
| KNOW_001 | 知识不存在 |
| KNOW_002 | 无权限访问该知识 |
| KNOW_003 | 知识标题重复 |
| CHAT_001 | 会话不存在 |
| CHAT_002 | AI 服务暂时不可用 |
| CHAT_003 | 问题过长 |
| FILE_001 | 文件类型不支持 |
| FILE_002 | 文件大小超限 |
| SYS_001 | 系统内部错误 |
| SYS_002 | 服务过载 |

---

## 五、限流策略

### 5.1 限流配置

| 接口类型 | 限流规则 | 说明 |
|----------|----------|------|
| 认证接口 | 10 次/分钟/IP | 防止暴力破解 |
| 问答接口 | 60 次/小时/用户 | 控制 AI 调用成本 (已调整) |
| 搜索接口 | 60 次/分钟/用户 | 防止滥用 |
| 文件上传 | 10 次/小时/用户 | 控制存储成本 |
| 其他接口 | 100 次/分钟/用户 | 默认限流 |

**配额申请机制**:

对于高频率使用场景 (如批量测试、企业用户)，可申请提升配额：

```
申请流程:
1. 用户提交配额提升申请 (邮件/工单)
2. 说明使用场景和预期 QPS
3. 技术总监审批 (1 个工作日内)
4. 运维工程师配置限流规则
5. 通知用户配额已提升
```

**配额等级**:
| 等级 | 问答接口限流 | 适用场景 |
|------|-------------|----------|
| 普通用户 | 60 次/小时 | 日常学习使用 |
| 高级用户 | 200 次/小时 | 高频学习/研究 |
| 企业用户 | 1000 次/小时 | 企业批量使用 |
| 内部测试 | 无限制 | 内部开发和测试 |

### 5.2 限流响应

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1678176000

{
  "code": 429,
  "message": "Rate limit exceeded. Please try again later.",
  "retry_after": 60
}
```

---

## 六、API 版本管理

### 6.1 版本策略

- **URL 路径版本**: `/api/v1/`, `/api/v2/`
- **向后兼容**: 新版本不破坏旧版本功能
- **废弃策略**: 旧版本提前 30 天通知废弃

### 6.2 版本生命周期

```
v1.0 (当前)
├── v1.1 (小版本，向后兼容)
├── v1.2 (小版本，向后兼容)
└── v2.0 (大版本，可能不兼容)
    └── v1.x 废弃通知 (30 天)
        └── v1.x 停止支持
```

---

## 六、安全设计 (补充)

### 6.1 认证与授权

| 机制 | 说明 |
|------|------|
| **JWT Token** | 用户认证，有效期 24 小时 |
| **Refresh Token** | Token 刷新，有效期 7 天 |
| **OAuth2** | 支持第三方登录 (可选) |
| **RBAC** | 基于角色的访问控制 |

### 6.2 数据加密存储

**敏感数据加密方案**:

| 数据类型 | 加密方式 | 存储位置 | 密钥管理 |
|----------|----------|----------|----------|
| JWT Secret | HMAC-SHA256 | 环境变量 | Docker secrets |
| 数据库密码 | AES-256 | 环境变量 | Docker secrets |
| MinIO 密钥 | AES-256 | 环境变量 | Docker secrets |
| LLM API Key | AES-256 | 环境变量 | Docker secrets |
| 用户密码 | bcrypt | PostgreSQL | - |
| Token (Redis) | 明文 (内存) | Redis | 过期自动清除 |

**环境变量加密存储**:

```bash
# .env 文件 (生产环境使用加密)
# 使用 age 或 sops 加密敏感配置

# 加密示例 (使用 age)
age -o .env.enc -R recipients.txt .env
rm .env

# 解密示例
age -d -i key.txt .env.enc > .env
```

**Docker Secrets 集成**:

```yaml
# docker-compose.yml (生产环境)
services:
  backend:
    secrets:
      - jwt_secret
      - database_password
      - llm_api_key

secrets:
  jwt_secret:
    external: true
  database_password:
    external: true
  llm_api_key:
    external: true
```

**Token 安全存储**:

```python
# Redis 中 Token 存储 (自动过期)
import redis
from datetime import timedelta

redis_client = redis.Redis(host='redis', port=6379, db=0)

# 存储 Token (带过期时间)
def store_token(user_id: str, token: str, expires_in: int = 86400):
    key = f"app:auth:token:{user_id}"
    redis_client.setex(key, timedelta(seconds=expires_in), token)

# Token 自动过期，无需手动清除
```

### 6.3 传输安全

| 措施 | 说明 |
|------|------|
| **HTTPS** | 全站加密传输 (生产环境强制) |
| **TLS 1.3** | 使用最新 TLS 版本 |
| **HSTS** | 强制 HTTPS 跳转 |
| **CORS** | 限制跨域请求来源 |

### 6.4 输入验证

| 验证类型 | 说明 |
|----------|------|
| **SQL 注入防护** | 使用参数化查询 |
| **XSS 防护** | 输入过滤 + 输出编码 |
| **CSRF 防护** | CSRF Token 验证 |
| **文件上传验证** | 类型检查 + 大小限制 + 病毒扫描 |

---

## 七、参考链接

1. [FastAPI 官方文档](https://fastapi.tiangolo.com/)
2. [OpenAPI 规范](https://swagger.io/specification/)
3. [RESTful API 最佳实践](https://restfulapi.net/)
4. [JWT 规范](https://jwt.io/)
5. [OWASP 安全指南](https://owasp.org/)

---

## 八、版本历史

| 版本 | 时间 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-07 08:00 UTC | 初始版本 | 张建国 |
| v1.1 | 2026-03-07 11:00 UTC | 修复 P0-6(限流调整)、P1-4(加密存储) | 张建国 |

---

**文档状态**: v1.1 - 审查修复完成  
**最后更新**: 2026-03-07 11:00 UTC  
**下一步**: 
1. 提交技术总监复审
2. Admin 审批
