# 部署方案文档：智能学习助手 Web 应用

**任务 ID**: task-102-deploy  
**文档版本**: v1.1  
**创建时间**: 2026-03-07 08:30 UTC  
**更新时间**: 2026-03-07 11:00 UTC  
**负责人**: 张建国 (System Architect - 系统架构师)  
**状态**: 审查修复完成  

---

## 一、部署环境

### 1.1 环境规划

| 环境 | 用途 | 访问地址 | 部署方式 |
|------|------|----------|----------|
| **开发环境** | 本地开发调试 | localhost:8080 | Docker Compose |
| **测试环境** | 功能测试、集成测试 | test.hiclaw.io:8080 | Docker Compose |
| **生产环境** | 正式部署 | api.hiclaw.io | Docker + 反向代理 |

### 1.2 硬件要求

#### 最低配置 (开发/测试)
| 资源 | 配置 |
|------|------|
| CPU | 4 核心 |
| 内存 | 8GB |
| 存储 | 50GB SSD |
| 网络 | 100Mbps |

#### 推荐配置 (生产)
| 资源 | 配置 |
|------|------|
| CPU | 8 核心 |
| 内存 | 16GB |
| 存储 | 200GB SSD |
| 网络 | 1Gbps |

### 1.3 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| Docker | 24.0+ | 容器运行时 |
| Docker Compose | 2.20+ | 容器编排 |
| WSL2 | 最新 | Windows 子系统 (仅 Windows) |
| Git | 2.40+ | 版本控制 |

---

## 二、Docker Compose 配置

### 2.1 完整配置文件

```yaml
# docker-compose.yml
version: '3.8'

services:
  # ==================== 前端服务 ====================
  frontend:
    image: nginx:alpine
    container_name: learning-frontend
    ports:
      - "80:80"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
    networks:
      - learning-network
    restart: unless-stopped

  # ==================== 后端服务 ====================
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: learning-backend
    expose:
      - "8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/learning_assistant
      - REDIS_URL=redis://redis:6379/0
      - LIGHTRAG_URL=http://lightrag:8000
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - JWT_SECRET=${JWT_SECRET}
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_BASE_URL=${LLM_BASE_URL}
    volumes:
      - ./backend/logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
      lightrag:
        condition: service_started
      minio:
        condition: service_healthy
    networks:
      - learning-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ==================== PostgreSQL 数据库 ====================
  postgres:
    image: postgres:15-alpine
    container_name: learning-postgres
    environment:
      - POSTGRES_DB=learning_assistant
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d:ro
    ports:
      - "5432:5432"
    networks:
      - learning-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==================== LightRAG 向量数据库 ====================
  lightrag:
    build:
      context: ./lightrag
      dockerfile: Dockerfile
    container_name: learning-lightrag
    expose:
      - "8000"
    volumes:
      - lightrag_data:/app/data
    environment:
      - EMBEDDING_MODEL=text-embedding-3-small
      - EMBEDDING_API_KEY=${LLM_API_KEY}
      - LLM_MODEL=qwen3.5-plus
      - LLM_BASE_URL=${LLM_BASE_URL}
    networks:
      - learning-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ==================== Redis 缓存 ====================
  redis:
    image: redis:7-alpine
    container_name: learning-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - learning-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==================== MinIO 对象存储 ====================
  minio:
    image: minio/minio:latest
    container_name: learning-minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    networks:
      - learning-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ==================== Celery Worker (异步任务) ====================
  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: learning-celery-worker
    command: celery -A app.celery worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/learning_assistant
      - REDIS_URL=redis://redis:6379/0
      - LIGHTRAG_URL=http://lightrag:8000
      - MINIO_ENDPOINT=minio:9000
    volumes:
      - ./backend/logs:/app/logs
    depends_on:
      - postgres
      - redis
      - lightrag
      - minio
    networks:
      - learning-network
    restart: unless-stopped

  # ==================== Celery Beat (定时任务) ====================
  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: learning-celery-beat
    command: celery -A app.celery beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/learning_assistant
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend/logs:/app/logs
    depends_on:
      - redis
    networks:
      - learning-network
    restart: unless-stopped

networks:
  learning-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  lightrag_data:
  minio_data:
```

### 2.2 环境变量配置

```bash
# .env 文件 (不要提交到 Git)

# ==================== 数据库配置 ====================
POSTGRES_PASSWORD=your_secure_postgres_password

# ==================== JWT 配置 ====================
JWT_SECRET=your_super_secure_jwt_secret_key_min_32_chars

# ==================== LLM 配置 ====================
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://api.higress.io/v1

# ==================== MinIO 配置 ====================
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your_secure_minio_password

# ==================== 应用配置 ====================
APP_ENV=production
APP_DEBUG=false
APP_URL=https://api.hiclaw.io
```

### 2.3 Nginx 配置

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss 
               application/json application/javascript;

    # 前端服务
    server {
        listen 80;
        server_name _;

        root /usr/share/nginx/html;
        index index.html;

        # 静态文件缓存
        location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # SPA 路由 fallback
        location / {
            try_files $uri $uri/ /index.html;
        }

        # API 代理
        location /api/ {
            proxy_pass http://backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # SSE 流式响应支持
        location /api/v1/chat/stream {
            proxy_pass http://backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_buffering off;
            proxy_cache off;
            chunked_transfer_encoding off;
            
            # SSE 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }
    }
}
```

### 2.4 LightRAG Dockerfile (本地构建)

由于 LightRAG 官方可能无正式 Docker 镜像，提供本地构建方案：

```dockerfile
# lightrag/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 LightRAG 源码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "-m", "lightrag.server", "--host", "0.0.0.0", "--port", "8000"]
```

```txt
# lightrag/requirements.txt
lightrag>=0.1.0
fastapi>=0.109.0
uvicorn>=0.27.0
openai>=1.12.0
numpy>=1.26.0
faiss-cpu>=1.7.4
networkx>=3.2.0
```

**构建命令**:
```bash
cd lightrag
docker build -t lightrag:latest .
```

---

## 三、部署步骤

### 3.1 开发环境部署

```bash
# 1. 克隆项目
cd ~/hiclaw-fs/shared/projects
git clone https://github.com/lifanli/learning_proj.git
cd learning_proj

# 2. 创建环境变量文件
cp .env.example .env
# 编辑 .env 文件，填写配置

# 3. 启动所有服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f backend

# 6. 访问应用
# 前端：http://localhost
# 后端 API: http://localhost/api/v1/health
# MinIO Console: http://localhost:9001
```

### 3.2 测试环境部署

```bash
# 1. 上传代码到服务器
scp -r ./learning_proj user@test.hiclaw.io:/opt/

# 2. SSH 登录服务器
ssh user@test.hiclaw.io

# 3. 进入项目目录
cd /opt/learning_proj

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 5. 启动服务
docker-compose up -d

# 6. 初始化数据库
docker-compose exec backend python -m app.db.init

# 7. 验证部署
curl http://test.hiclaw.io:8080/api/v1/health
```

### 3.3 生产环境部署

```bash
# 1. 准备服务器 (参考硬件要求)

# 2. 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 3. 配置防火墙
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 4. 安装 SSL 证书 (使用 Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.hiclaw.io

# 5. 部署应用
# (同测试环境步骤)

# 6. 配置监控和告警
# (见第六节)
```

---

## 四、服务启动顺序

```
1. PostgreSQL      (数据库)
       ↓
2. Redis           (缓存)
       ↓
3. MinIO           (对象存储)
       ↓
4. LightRAG        (向量数据库)
       ↓
5. Backend         (后端服务)
       ↓
6. Celery Worker   (异步任务)
       ↓
7. Celery Beat     (定时任务)
       ↓
8. Frontend        (前端服务)
```

### 4.1 健康检查脚本

```bash
#!/bin/bash
# health-check.sh

echo "=== 健康检查开始 ==="

# 检查 PostgreSQL
echo -n "PostgreSQL: "
docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1 && echo "✅ OK" || echo "❌ FAILED"

# 检查 Redis
echo -n "Redis: "
docker-compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo "✅ OK" || echo "❌ FAILED"

# 检查 MinIO
echo -n "MinIO: "
curl -s http://localhost:9000/minio/health/live > /dev/null && echo "✅ OK" || echo "❌ FAILED"

# 检查 LightRAG
echo -n "LightRAG: "
curl -s http://localhost:8000/health > /dev/null && echo "✅ OK" || echo "❌ FAILED"

# 检查 Backend
echo -n "Backend: "
curl -s http://localhost:8000/api/v1/health > /dev/null && echo "✅ OK" || echo "❌ FAILED"

# 检查 Frontend
echo -n "Frontend: "
curl -s http://localhost/ > /dev/null && echo "✅ OK" || echo "❌ FAILED"

echo "=== 健康检查结束 ==="
```

---

## 五、数据迁移

### 5.1 数据库迁移

```bash
# 使用 Alembic 进行数据库迁移
# 后端服务内执行

# 生成新迁移
docker-compose exec backend alembic revision --autogenerate -m "Description"

# 应用迁移
docker-compose exec backend alembic upgrade head

# 回滚迁移
docker-compose exec backend alembic downgrade -1
```

### 5.2 向量数据迁移

```python
# 向量数据同步脚本
# scripts/sync_vectors.py

from lightrag import LightRAG
import json

def sync_knowledge_to_lightrag(knowledge_entries):
    """同步知识到 LightRAG"""
    rag = LightRAG(working_dir="./data")
    
    for entry in knowledge_entries:
        rag.insert({
            "id": entry["id"],
            "title": entry["title"],
            "content": entry["content"],
            "metadata": {
                "tags": entry["tags"],
                "category": entry["category"]
            }
        })
    
    print(f"同步完成：{len(knowledge_entries)} 条知识")
```

---

## 六、监控与日志

### 6.1 日志配置

```python
# backend/logging_config.py
import logging

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
            'level': 'DEBUG'
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO'
    }
}
```

### 6.2 监控指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| CPU 使用率 | 后端服务 CPU | > 80% 持续 5 分钟 |
| 内存使用率 | 后端服务内存 | > 90% 持续 5 分钟 |
| 请求延迟 | API P95 延迟 | > 2 秒 |
| 错误率 | 5xx 错误比例 | > 1% |
| 数据库连接 | 活跃连接数 | > 80% 最大连接 |
| 磁盘使用率 | 存储使用 | > 85% |

### 6.3 Prometheus 配置 (可选)

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

---

## 七、备份与恢复

### 7.1 备份脚本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/learning-$(date +%Y%m%d-%H%M%S)"
mkdir -p $BACKUP_DIR

echo "开始备份..."

# 备份 PostgreSQL
docker-compose exec -T postgres pg_dump -U postgres learning_assistant > $BACKUP_DIR/postgres.sql
echo "✅ PostgreSQL 备份完成"

# 备份 LightRAG 数据
tar -czf $BACKUP_DIR/lightrag.tar.gz ./lightrag_data/
echo "✅ LightRAG 备份完成"

# 备份 MinIO 数据
mc cp -r minio/learning-uploads $BACKUP_DIR/minio/
echo "✅ MinIO 备份完成"

# 备份环境变量
cp .env $BACKUP_DIR/
echo "✅ 配置备份完成"

# 压缩备份
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# 清理旧备份 (保留 7 天)
find /backups -name "*.tar.gz" -mtime +7 -delete

echo "备份完成：$BACKUP_DIR.tar.gz"
```

### 7.2 恢复脚本

```bash
#!/bin/bash
# restore.sh <backup_file>

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "用法：./restore.sh <backup_file.tar.gz>"
    exit 1
fi

echo "开始恢复..."

# 解压备份
tar -xzf $BACKUP_FILE

# 恢复 PostgreSQL
docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS learning_assistant;"
docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE learning_assistant;"
docker-compose exec -T postgres psql -U postgres learning_assistant < postgres.sql
echo "✅ PostgreSQL 恢复完成"

# 恢复 LightRAG
tar -xzf lightrag.tar.gz -C ./
echo "✅ LightRAG 恢复完成"

# 恢复 MinIO
mc cp -r minio/learning-uploads minio/
echo "✅ MinIO 恢复完成"

echo "恢复完成！请重启服务。"
```

### 7.3 版本回滚策略

**回滚触发条件**:
- 新版本部署后健康检查失败
- 关键功能出现严重 Bug (P0 级)
- 性能指标严重下降 (延迟>5 秒，错误率>5%)
- Admin 或 Project Director 要求回滚

**回滚步骤**:

```bash
#!/bin/bash
# rollback.sh <target_version>

TARGET_VERSION=$1

if [ -z "$TARGET_VERSION" ]; then
    echo "用法：./rollback.sh <target_version>"
    echo "示例：./rollback.sh v1.0"
    exit 1
fi

echo "=== 开始回滚到版本 $TARGET_VERSION ==="

# 1. 备份当前状态 (防止回滚失败)
echo "步骤 1: 备份当前状态..."
./backup.sh

# 2. 停止当前服务
echo "步骤 2: 停止当前服务..."
docker-compose down

# 3. 切换到目标版本
echo "步骤 3: 切换到版本 $TARGET_VERSION..."
git fetch --tags
git checkout $TARGET_VERSION

# 4. 恢复数据库 (从回滚点备份)
echo "步骤 4: 恢复数据库..."
# 假设备份文件名为 backup_<version>.tar.gz
./restore.sh /backups/backup_${TARGET_VERSION}.tar.gz

# 5. 重新启动服务
echo "步骤 5: 启动服务..."
docker-compose up -d

# 6. 验证回滚
echo "步骤 6: 验证回滚..."
sleep 30
./health-check.sh

# 7. 通知相关人员
echo "步骤 7: 发送回滚完成通知..."
# 可集成钉钉/企业微信/邮件通知

echo "=== 回滚完成 ==="
echo "当前版本：$(git describe --tags)"
```

**回滚决策流程**:
```
问题发现
    ↓
技术总监评估 (5 分钟内)
    ↓
┌─────────────────┬─────────────────┐
│   可快速修复    │   需要回滚      │
│   (修复部署)    │   (执行回滚)    │
└─────────────────┴─────────────────┘
```

**回滚后行动**:
1. 记录回滚原因和时间
2. 分析问题根因
3. 修复后重新走部署流程
4. 更新部署检查清单

---

## 八、故障排查

### 8.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 服务无法启动 | 端口被占用 | `docker-compose down` 后重启 |
| 数据库连接失败 | 密码错误或网络问题 | 检查 .env 和网络配置 |
| 后端健康检查失败 | 依赖服务未就绪 | 检查依赖服务状态 |
| 前端 404 | 静态文件未生成 | 重新构建前端 |
| 向量检索慢 | 索引未建立 | 检查 LightRAG 初始化 |

### 8.2 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs postgres

# 实时跟踪日志
docker-compose logs -f backend

# 查看最近 100 行
docker-compose logs --tail=100 backend
```

---

## 九、参考链接

1. [Docker 官方文档](https://docs.docker.com/)
2. [Docker Compose 文档](https://docs.docker.com/compose/)
3. [Nginx 配置最佳实践](https://www.nginx.com/resources/wiki/start/)
4. [Let's Encrypt 证书](https://letsencrypt.org/)

---

## 十、版本历史

| 版本 | 时间 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-07 08:30 UTC | 初始版本 | 张建国 |

---

**文档状态**: v1.0 - 初稿完成  
**最后更新**: 2026-03-07 08:30 UTC  
**下一步**: 
1. 同步文档到中心化存储
2. 提交 Challenger 审查
3. Admin 审批
