# API 与数据库设计（草案）

**提交人**：后端工程师（待提交）
**版本**：v0.1（草案）
**最后更新**：2026-03-07

---

## 1. 数据库表结构

### sources 表（内容源）
```sql
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50) NOT NULL,  -- github/arxiv/wechat
    domain VARCHAR(100),               -- 领域
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### knowledge_entries 表（知识条目）
```sql
CREATE TABLE knowledge_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    summary TEXT,                      -- 摘要
    source_url TEXT,
    source_id UUID REFERENCES sources(id),
    domain VARCHAR(100),
    tags TEXT[],
    difficulty_level INTEGER DEFAULT 1,
    markdown_path TEXT,                -- 文件路径
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### concepts 表（概念）
```sql
CREATE TABLE concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    domain VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### concept_relations 表（概念关系）
```sql
CREATE TABLE concept_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_concept_id UUID REFERENCES concepts(id),
    target_concept_id UUID REFERENCES concepts(id),
    relation_type VARCHAR(50),         -- prerequisite/related_to
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 索引
```sql
CREATE INDEX idx_knowledge_domain ON knowledge_entries(domain);
CREATE INDEX idx_knowledge_tags ON knowledge_entries USING GIN(tags);
CREATE INDEX idx_knowledge_status ON knowledge_entries(status);
```

---

## 2. API 设计

### 内容源管理
```
POST   /api/v1/sources          # 添加内容源
GET    /api/v1/sources          # 获取源列表
DELETE /api/v1/sources/:id      # 删除源
POST   /api/v1/sources/:id/crawl # 触发抓取
```

### 知识库浏览
```
GET    /api/v1/knowledge        # 获取知识列表
GET    /api/v1/knowledge/:id    # 获取知识详情
```

### 搜索
```
GET    /api/v1/search?q=        # 关键词搜索
POST   /api/v1/search/vector    # 向量搜索
```

---

## 3. 定时任务设计

### Celery 配置
```python
from celery import Celery

app = Celery('knowledge', broker='redis://localhost:6379/0')

app.conf.beat_schedule = {
    'daily-crawl': {
        'task': 'tasks.crawl_sources',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

### 任务状态机
```
pending → running → success/failed
                ↓
              retry (max 3 times)
                ↓
              dead_letter
```

---

## 4. 安全验证方案

### SSRF 防护
- URL 白名单验证
- 禁止内网 IP（10.x/172.16.x/192.168.x）
- 禁用重定向

### 文件上传验证
- 文件类型检查
- 文件大小限制
- 病毒扫描（可选）

### API 认证
- Token 认证
- 速率限制

---

**待完成**：后端工程师需补充完整 API 和数据库设计
