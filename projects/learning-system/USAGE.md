# 📋 使用说明

**版本**: v1.0  
**更新时间**: 2026-03-09  
**状态**: Docker 部署完成

---

## 🚀 快速启动

### 1. 启动服务

```bash
cd D:\hiclaw\learning_proj\learning_proj\docker
docker-compose up -d
```

### 2. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| **API** | http://localhost:8000 | FastAPI 后端 |
| **健康检查** | http://localhost:8000/health | 检查状态 |
| **API 文档** | http://localhost:8000/docs | Swagger UI |

### 3. 测试 API

```bash
# 浏览器访问
http://localhost:8000/docs

# 或命令行测试
curl http://localhost:8000/health
curl http://localhost:8000/
```

---

## 📁 项目结构

```
learning_proj/
├── docker/              # Docker 配置
│   ├── Dockerfile
│   └── docker-compose.yml
├── backend/             # 后端代码
│   ├── app/
│   │   └── main.py
│   └── requirements.txt
└── projects/learning-system/  # 学习系统
    ├── src/
    ├── main.py
    └── run_tests.py
```

---

## 🧪 测试命令

```bash
# Docker 测试
docker-compose ps
docker-compose logs -f api

# 本地测试
cd projects/learning-system
python3 main.py
python3 run_tests.py
```

---

## 📊 服务状态

| 服务 | 端口 | 状态 |
|------|------|------|
| API | 8000 | ✅ 运行中 |
| Database | 5432 | ✅ 运行中 |
| Redis | 6379 | ✅ 运行中 |
| Worker | - | ✅ 运行中 |

---

## 🆘 常见问题

### Q: Docker 启动失败
```bash
docker-compose down
docker-compose up -d --build
```

### Q: API 无法访问
```bash
# 检查容器状态
docker-compose ps

# 查看日志
docker-compose logs -f api
```

---

**文档由运维 Worker 和测试 Worker 共同维护**
