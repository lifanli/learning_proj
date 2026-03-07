# 数据库设计文档：智能学习助手 Web 应用

**任务 ID**: task-102-db  
**文档版本**: v1.1  
**创建时间**: 2026-03-07 08:15 UTC  
**更新时间**: 2026-03-07 11:00 UTC  
**负责人**: 张建国 (System Architect - 系统架构师)  
**状态**: 审查修复完成  

---

## 一、数据库选型

### 1.1 数据库总览

| 数据库类型 | 选型 | 用途 | 部署方式 |
|------------|------|------|----------|
| **关系数据库** | PostgreSQL 15 | 用户数据、会话记录、系统配置 | Docker 容器 |
| **向量数据库** | LightRAG (最新) | 知识向量存储、语义检索、知识图谱 | Docker 容器/本地 |
| **缓存数据库** | Redis 7 | 会话缓存、限流计数、任务队列 | Docker 容器 |
| **对象存储** | MinIO | 文件附件、头像、导出文件 | Docker 容器 |

### 1.2 选型理由

#### PostgreSQL
- 成熟稳定，ACID 事务支持
- 丰富的数据类型和索引
- 良好的 JSON 支持
- 社区活跃，文档完善

#### LightRAG
- **图 + 向量混合检索**是核心优势
- 适合知识关联推荐场景
- 自托管友好，Python 原生
- 支持增量更新

#### Redis
- 高性能内存存储
- 支持多种数据结构
- 发布订阅功能
- 持久化选项

#### MinIO
- S3 兼容 API
- 自托管对象存储
- 支持版本控制和生命周期
- 性能优秀

---

## 二、PostgreSQL 表结构设计

### 2.1 ER 图

```
┌─────────────────┐       ┌─────────────────┐
│     users       │       │   conversations │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │◄──────│ user_id (FK)    │
│ username        │       │ id (PK)         │
│ email           │       │ title           │
│ password_hash   │       │ created_at      │
│ avatar_url      │       │ updated_at      │
│ created_at      │       └────────┬────────┘
│ updated_at      │                │
└────────┬────────┘                │
         │                         │
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│   knowledge     │       │    messages     │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ user_id (FK)    │       │ conversation_id │
│ title           │       │ role            │
│ content         │       │ content         │
│ embedding_id    │       │ created_at      │
│ created_at      │       └─────────────────┘
│ updated_at      │
└─────────────────┘
```

### 2.2 用户表 (users)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    -- 索引
    CONSTRAINT chk_username_length CHECK (LENGTH(username) BETWEEN 3 AND 50),
    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### 2.3 知识表 (knowledge)

```sql
CREATE TABLE knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    content_preview VARCHAR(500),  -- 用于列表展示
    category VARCHAR(50),
    tags TEXT[],  -- 标签数组
    is_public BOOLEAN DEFAULT false,
    embedding_id VARCHAR(100),  -- LightRAG 中的向量 ID
    view_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    CONSTRAINT chk_title_length CHECK (LENGTH(title) BETWEEN 1 AND 200)
);

CREATE INDEX idx_knowledge_user_id ON knowledge(user_id);
CREATE INDEX idx_knowledge_title ON knowledge(title);
CREATE INDEX idx_knowledge_category ON knowledge(category);
CREATE INDEX idx_knowledge_tags ON knowledge USING GIN(tags);
CREATE INDEX idx_knowledge_is_public ON knowledge(is_public);
CREATE INDEX idx_knowledge_created_at ON knowledge(created_at);
-- 全文搜索索引
CREATE INDEX idx_knowledge_content_fts ON knowledge USING GIN(to_tsvector('simple', content));
```

### 2.4 会话表 (conversations)

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) DEFAULT '新对话',
    model VARCHAR(50) DEFAULT 'qwen3.5-plus',
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);
CREATE INDEX idx_conversations_last_message ON conversations(last_message_at DESC);
```

### 2.5 消息表 (messages)

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    token_count INTEGER,
    sources JSONB,  -- 引用的知识来源 [{knowledge_id, title, score}]
    metadata JSONB,  -- 额外元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
-- 复合索引用于分页查询
CREATE INDEX idx_messages_conv_created ON messages(conversation_id, created_at);
```

### 2.6 文件表 (files)

```sql
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    storage_path VARCHAR(500) NOT NULL,  -- MinIO 路径
    checksum VARCHAR(64),  -- SHA256 校验和
    is_public BOOLEAN DEFAULT false,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE  -- 可选的过期时间
);

CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_files_storage_path ON files(storage_path);
CREATE INDEX idx_files_checksum ON files(checksum);
```

### 2.7 系统配置表 (system_config)

```sql
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_config_key ON system_config(config_key);

-- 初始化配置
INSERT INTO system_config (config_key, config_value, description, is_public) VALUES
('app.name', '{"value": "智能学习助手"}', '应用名称', true),
('app.version', '{"value": "1.0.0"}', '应用版本', true),
('llm.model', '{"value": "qwen3.5-plus"}', '默认 LLM 模型', false),
('llm.max_tokens', '{"value": 4096}', '最大 Token 数', false),
('upload.max_size', '{"value": 10485760}', '最大上传大小 (字节)', true),
('upload.allowed_types', '{"value": ["pdf", "docx", "txt", "md", "png", "jpg"]}', '允许的文件类型', true);
```

### 2.8 审计日志表 (audit_logs)

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    request_ip INET,
    request_user_agent TEXT,
    status_code INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
```

### 2.9 外键约束与级联规则

**ER 关系图**:
```
users (1) ─────< (N) knowledge
users (1) ─────< (N) conversations
users (1) ─────< (N) files
users (1) ─────< (N) audit_logs

conversations (1) ─────< (N) messages
```

**外键约束与级联策略**:

| 表 | 外键字段 | 引用表 | 删除规则 | 更新规则 | 理由 |
|----|----------|--------|----------|----------|------|
| knowledge | user_id | users(id) | CASCADE | CASCADE | 用户删除时，其知识同步删除 |
| conversations | user_id | users(id) | CASCADE | CASCADE | 用户删除时，会话同步删除 |
| messages | conversation_id | conversations(id) | CASCADE | CASCADE | 会话删除时，消息同步删除 |
| files | user_id | users(id) | CASCADE | CASCADE | 用户删除时，文件同步删除 |
| audit_logs | user_id | users(id) | SET NULL | CASCADE | 用户删除时，审计日志保留但匿名化 |

**级联删除顺序**:
```
删除用户
    ↓
1. knowledge (CASCADE)
2. conversations → messages (CASCADE)
3. files (CASCADE)
4. audit_logs (SET NULL - 保留审计追踪)
```

**SQL 实现示例**:
```sql
-- knowledge 表外键
ALTER TABLE knowledge 
    ADD CONSTRAINT fk_knowledge_user 
    FOREIGN KEY (user_id) 
    REFERENCES users(id) 
    ON DELETE CASCADE 
    ON UPDATE CASCADE;

-- conversations 表外键
ALTER TABLE conversations 
    ADD CONSTRAINT fk_conversations_user 
    FOREIGN KEY (user_id) 
    REFERENCES users(id) 
    ON DELETE CASCADE 
    ON UPDATE CASCADE;

-- messages 表外键
ALTER TABLE messages 
    ADD CONSTRAINT fk_messages_conversation 
    FOREIGN KEY (conversation_id) 
    REFERENCES conversations(id) 
    ON DELETE CASCADE 
    ON UPDATE CASCADE;

-- files 表外键
ALTER TABLE files 
    ADD CONSTRAINT fk_files_user 
    FOREIGN KEY (user_id) 
    REFERENCES users(id) 
    ON DELETE CASCADE 
    ON UPDATE CASCADE;

-- audit_logs 表外键 (SET NULL)
ALTER TABLE audit_logs 
    ADD CONSTRAINT fk_audit_logs_user 
    FOREIGN KEY (user_id) 
    REFERENCES users(id) 
    ON DELETE SET NULL 
    ON UPDATE CASCADE;
```

**数据完整性检查**:
```sql
-- 检查孤儿记录 (应返回 0)
SELECT COUNT(*) FROM knowledge WHERE user_id NOT IN (SELECT id FROM users);
SELECT COUNT(*) FROM conversations WHERE user_id NOT IN (SELECT id FROM users);
SELECT COUNT(*) FROM messages WHERE conversation_id NOT IN (SELECT id FROM conversations);
SELECT COUNT(*) FROM files WHERE user_id NOT IN (SELECT id FROM users);
```

---

## 三、LightRAG 向量数据库设计

### 3.1 LightRAG 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      LightRAG                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │   向量索引      │         │    图索引       │           │
│  │  (Vector Index) │         │  (Graph Index)  │           │
│  │                 │         │                 │           │
│  │  - 知识向量     │◄───────►│  - 概念节点     │           │
│  │  - 语义嵌入     │  关联   │  - 关系边       │           │
│  └─────────────────┘         └─────────────────┘           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              混合检索引擎                            │   │
│  │  - 向量相似度检索                                    │   │
│  │  - 图遍历检索                                        │   │
│  │  - 结果融合排序                                      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 知识向量存储

LightRAG 使用本地文件系统存储向量数据：

```
lightrag_data/
├── vectors/
│   ├── knowledge_vectors.npy      # 知识向量矩阵
│   ├── vector_ids.json            # 向量 ID 映射
│   └── metadata.json              # 向量元数据
├── graph/
│   ├── nodes.json                 # 图节点
│   ├── edges.json                 # 图边
│   └── relations.json             # 关系定义
├── index/
│   ├── faiss_index.bin            # FAISS 索引
│   └── index_config.json          # 索引配置
└── cache/
    └── query_cache.json           # 查询缓存
```

### 3.3 向量元数据结构

```json
{
  "vector_id": "vec_knowledge_001",
  "knowledge_id": "uuid",
  "title": "知识标题",
  "content_hash": "sha256...",
  "embedding_model": "text-embedding-3-small",
  "embedding_dim": 1536,
  "created_at": "2026-03-07T08:00:00Z",
  "updated_at": "2026-03-07T08:00:00Z",
  "tags": ["tag1", "tag2"],
  "category": "category_name"
}
```

### 3.4 知识图谱结构

```json
{
  "nodes": [
    {
      "id": "node_001",
      "type": "concept",
      "name": "向量数据库",
      "description": "存储向量数据的数据库",
      "knowledge_ids": ["uuid1", "uuid2"]
    },
    {
      "id": "node_002",
      "type": "concept",
      "name": "语义检索",
      "description": "基于语义的检索方式",
      "knowledge_ids": ["uuid2", "uuid3"]
    }
  ],
  "edges": [
    {
      "source": "node_001",
      "target": "node_002",
      "relation": "supports",
      "weight": 0.9
    }
  ]
}
```

### 3.5 检索策略

#### 向量检索
```python
# 伪代码
def vector_search(query_embedding, top_k=10):
    # 使用 FAISS 进行近似最近邻搜索
    distances, indices = faiss_index.search(query_embedding, top_k)
    return [(id, score) for id, score in zip(indices, distances)]
```

#### 图检索
```python
# 伪代码
def graph_search(start_nodes, max_depth=2):
    # 从起始节点开始 BFS 遍历
    visited = set()
    queue = [(node, 0) for node in start_nodes]
    results = []
    
    while queue:
        node, depth = queue.pop(0)
        if node in visited or depth > max_depth:
            continue
        visited.add(node)
        results.append(node)
        
        for neighbor in graph.get_neighbors(node):
            queue.append((neighbor, depth + 1))
    
    return results
```

#### 混合检索融合
```python
# 伪代码
def hybrid_search(query, top_k=10):
    # 1. 向量检索
    vector_results = vector_search(embed(query), top_k * 2)
    
    # 2. 图检索 (从向量结果中的概念节点开始)
    concept_nodes = extract_concepts(vector_results)
    graph_results = graph_search(concept_nodes)
    
    # 3. 结果融合 (加权排序)
    fused = fuse_results(vector_results, graph_results, 
                         vector_weight=0.7, graph_weight=0.3)
    
    return fused[:top_k]
```

---

## 四、Redis 缓存设计

### 4.1 缓存键命名规范

```
格式：app:module:key:identifier

示例:
- app:auth:token:{user_id}        # 用户 Token
- app:session:{session_id}        # 会话缓存
- app:ratelimit:{user_id}:{api}   # 限流计数
- app:cache:knowledge:{id}        # 知识缓存
- app:queue:tasks                 # 任务队列
```

### 4.2 缓存数据结构

#### Token 存储
```redis
# Key: app:auth:token:{user_id}
# Type: String
# TTL: 24 小时
SET app:auth:token:user_123 "eyJhbGciOiJIUzI1NiIs..." EX 86400
```

#### 会话缓存
```redis
# Key: app:session:{session_id}
# Type: Hash
# TTL: 1 小时 (滑动过期)
HSET app:session:conv_456 user_id "user_123" 
                          last_active "2026-03-07T08:00:00Z"
                          message_count "10"
EXPIRE app:session:conv_456 3600
```

#### 限流计数
```redis
# Key: app:ratelimit:{user_id}:{api}
# Type: String (计数器)
# TTL: 1 分钟
INCR app:ratelimit:user_123:chat
EXPIRE app:ratelimit:user_123:chat 60
```

---

## 五、MinIO 对象存储设计

### 5.1 Bucket 规划

| Bucket 名称 | 用途 | 访问策略 | 生命周期 |
|------------|------|----------|----------|
| `avatars` | 用户头像 | 公开读 | 永久 |
| `uploads` | 用户上传文件 | 私有 | 永久 |
| `exports` | 导出文件 | 私有 | 30 天 |
| `temp` | 临时文件 | 私有 | 24 小时 |

### 5.2 对象键命名

```
格式：{user_id}/{YYYY}/{MM}/{UUID}.{ext}

示例:
- avatars/user_123/avatar.png
- uploads/user_123/2026/03/abc123.pdf
- exports/user_123/2026/03/def456.zip
```

---

## 六、数据库初始化脚本

### 6.1 PostgreSQL 初始化

```sql
-- 创建数据库
CREATE DATABASE learning_assistant 
    WITH ENCODING 'UTF8' 
    LC_COLLATE='zh_CN.UTF-8' 
    LC_CTYPE='zh_CN.UTF-8';

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 模糊搜索

-- 运行表结构脚本
\i schema.sql

-- 创建只读用户 (用于报表查询)
CREATE USER readonly WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;
```

### 6.2 LightRAG 初始化

```python
# Python 初始化脚本
from lightrag import LightRAG

# 初始化 LightRAG 实例
rag = LightRAG(
    working_dir="./lightrag_data",
    embedding_model="text-embedding-3-small",
    llm_model="qwen3.5-plus",
    vector_dim=1536,
    graph_enabled=True
)

# 创建索引
rag.create_index()

print("LightRAG 初始化完成")
```

---

## 七、性能优化

### 7.1 PostgreSQL 优化

| 优化项 | 配置 | 说明 |
|--------|------|------|
| 连接池 | PgBouncer | 最大连接数 100 |
| 共享缓冲区 | 256MB | 根据内存调整 |
| 工作内存 | 64MB | 排序和哈希操作 |
| 有效缓存 | 1GB | 查询规划器参考 |
| WAL 级别 | minimal | 减少日志写入 |

### 7.2 查询优化

```sql
-- 使用 EXPLAIN ANALYZE 分析慢查询
EXPLAIN ANALYZE 
SELECT * FROM knowledge 
WHERE user_id = 'uuid' 
  AND is_public = true 
ORDER BY created_at DESC 
LIMIT 10;

-- 添加覆盖索引减少回表
CREATE INDEX idx_knowledge_user_public_created 
ON knowledge(user_id, is_public, created_at DESC);
```

### 7.3 向量检索优化

| 优化项 | 配置 | 说明 |
|--------|------|------|
| 索引类型 | HNSW | 平衡精度和速度 |
| M 参数 | 16 | 邻居数量 |
| efConstruction | 200 | 构建时搜索范围 |
| efSearch | 50 | 查询时搜索范围 |

---

## 八、备份策略

### 8.1 PostgreSQL 备份

```bash
# 每日全量备份
pg_dump -h localhost -U postgres learning_assistant > backup_$(date +%Y%m%d).sql

# 保留 7 天
find /backups -name "*.sql" -mtime +7 -delete
```

### 8.2 LightRAG 备份

```bash
# 备份向量数据
tar -czf lightrag_backup_$(date +%Y%m%d).tar.gz ./lightrag_data/

# 同步到远程存储
mc cp lightrag_backup_*.tar.gz minio/backups/
```

---

## 九、参考链接

1. [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
2. [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
3. [Redis 官方文档](https://redis.io/docs/)
4. [MinIO 官方文档](https://min.io/docs/)

---

## 十、版本历史

| 版本 | 时间 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-07 08:15 UTC | 初始版本 | 张建国 |

---

**文档状态**: v1.0 - 初稿完成  
**最后更新**: 2026-03-07 08:15 UTC  
**下一步**: 
1. 补充部署方案文档
2. 提交 Challenger 审查
3. Admin 审批
