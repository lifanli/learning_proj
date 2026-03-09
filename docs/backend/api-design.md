# API 设计文档

**版本**: v1.0  
**提交人**: 后端工程师  
**日期**: 2026-03-09

---

## 1. 端点列表

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

### 概念管理
```
GET    /api/v1/concepts         # 获取概念列表
GET    /api/v1/concepts/:id     # 获取概念详情
GET    /api/v1/concepts/:id/related  # 获取相关概念
```

---

## 2. 请求/响应格式

### POST /api/v1/sources
**请求**:
```json
{
  "url": "https://github.com/xxx/yyy",
  "source_type": "github",
  "domain": "深度学习"
}
```

**响应**:
```json
{
  "id": "uuid",
  "url": "https://github.com/xxx/yyy",
  "source_type": "github",
  "domain": "深度学习",
  "status": "active",
  "created_at": "2026-03-09T10:00:00Z"
}
```

### GET /api/v1/knowledge
**请求**:
```
GET /api/v1/knowledge?domain=深度学习&tags=Transformer&page=1&limit=20
```

**响应**:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Transformer 详解",
      "summary": "...",
      "domain": "深度学习",
      "tags": ["Transformer", "Attention"],
      "created_at": "2026-03-09T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 20
}
```

---

## 3. 认证授权

### Token 认证
```
Authorization: Bearer <token>
```

### 速率限制
- 未认证：10 请求/分钟
- 已认证：100 请求/分钟

---

## 4. 错误处理

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "资源不存在",
    "details": {}
  }
}
```

### 错误码
| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |
