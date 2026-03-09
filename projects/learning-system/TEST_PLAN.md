# 🧪 测试 Worker - 测试计划

**负责人**: 测试 Worker  
**时间**: 2026-03-09 16:20  
**状态**: 📋 准备测试

---

## 测试流程

### 阶段 1: 环境验证

```bash
# 1. 检查 Docker 容器
docker-compose ps

# 预期结果:
# NAME              STATUS
# docker-api-1      Up
# docker-db-1       Up
# docker-redis-1    Up
# docker-worker-1   Up
```

### 阶段 2: API 功能测试

```bash
# 2.1 健康检查
curl http://localhost:8000/health
# 预期：{"status": "healthy"}

# 2.2 根路径
curl http://localhost:8000/
# 预期：{"message": "智能出版学习系统 API", "status": "running"}

# 2.3 API 状态
curl http://localhost:8000/api/v1/status
# 预期：{"api": "ok", "database": "ok", "vector_store": "ok"}

# 2.4 API 文档
# 浏览器访问 http://localhost:8000/docs
```

### 阶段 3: 学习系统测试

```bash
# 3.1 运行主程序
cd projects/learning-system
python3 main.py

# 3.2 运行 API 服务
python3 -m src.api

# 3.3 运行测试
python3 run_tests.py
```

---

## 测试报告模板

| 测试项 | 预期结果 | 实际结果 | 状态 |
|--------|----------|----------|------|
| Docker 容器启动 | 全部 Up | - | ⏳ |
| 健康检查 | healthy | - | ⏳ |
| API 根路径 | 200 OK | - | ⏳ |
| API 状态 | api: ok | - | ⏳ |
| API 文档 | 可访问 | - | ⏳ |

---

## 阻塞问题

| 问题 | 依赖 | 状态 |
|------|------|------|
| Docker 重启 | 运维完成修复 | ⏳ 等待 |
| 环境访问 | Admin 执行命令 | ⏳ 等待 |

---

**测试 Worker 准备就绪，等待运维修复完成后开始测试！**
