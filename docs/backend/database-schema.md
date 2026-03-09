# 数据库设计文档

**版本**: v1.0  
**提交人**: 后端工程师  
**日期**: 2026-03-09

---

## 1. 表结构

### sources 表（内容源）
```sql
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50) NOT NULL,  -- github/arxiv/wechat
    domain VARCHAR(100),               -- 领域
    status VARCHAR(20) DEFAULT 'active',
    last_crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
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
    word_count INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### concepts 表（概念）
```sql
CREATE TABLE concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    domain VARCHAR(100),
    difficulty_level INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### concept_relations 表（概念关系）
```sql
CREATE TABLE concept_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_concept_id UUID REFERENCES concepts(id),
    target_concept_id UUID REFERENCES concepts(id),
    relation_type VARCHAR(50),         -- prerequisite/related_to/extends
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_concept_id, target_concept_id, relation_type)
);
```

### entry_concepts 表（知识 - 概念关联）
```sql
CREATE TABLE entry_concepts (
    entry_id UUID REFERENCES knowledge_entries(id),
    concept_id UUID REFERENCES concepts(id),
    relevance_score FLOAT,
    PRIMARY KEY (entry_id, concept_id)
);
```

---

## 2. 索引设计

```sql
-- 知识条目索引
CREATE INDEX idx_knowledge_domain ON knowledge_entries(domain);
CREATE INDEX idx_knowledge_tags ON knowledge_entries USING GIN(tags);
CREATE INDEX idx_knowledge_status ON knowledge_entries(status);
CREATE INDEX idx_knowledge_source ON knowledge_entries(source_id);

-- 概念索引
CREATE INDEX idx_concepts_domain ON concepts(domain);
CREATE INDEX idx_concepts_name ON concepts(name);

-- 任务调度索引
CREATE INDEX idx_jobs_next_run ON scheduled_jobs(next_run_at);
```

---

## 3. ER 图

```
sources ──< knowledge_entries >── entry_concepts ──> concepts
                                               │
                                               └──< concept_relations
```

---

## 4. 数据迁移

使用 Alembic 管理数据库迁移：

```bash
# 初始化
alembic init alembic

# 创建新迁移
alembic revision --autogenerate -m "Initial schema"

# 应用迁移
alembic upgrade head
```
