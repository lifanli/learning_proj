# 学习智能体系统 (Learning Agent System)

**版本**: 0.1.0  
**状态**: 开发中  
**M1 完成时间**: 2026-03-10  

---

## 项目结构

```
learning-system/
├── src/
│   ├── learning_generator/     # 学习记录生成器
│   │   ├── __init__.py
│   │   ├── generator.py        # 学习记录生成核心逻辑
│   │   └── models.py           # 数据模型
│   ├── knowledge_base/         # 知识库管理
│   │   ├── __init__.py
│   │   ├── storage.py          # 向量数据库操作
│   │   └── retriever.py        # 检索引擎
│   ├── recommendation/         # 智能推荐引擎
│   │   ├── __init__.py
│   │   └── engine.py           # 推荐算法
│   ├── worker_interface/       # Worker 工作台
│   │   ├── __init__.py
│   │   └── bot.py              # Matrix Bot 接口
│   ├── main.py                 # FastAPI 主应用
│   └── config.py               # 配置管理
├── tests/                      # 测试用例
├── requirements.txt            # 依赖
├── pyproject.toml              # 项目配置
└── README.md                   # 本文件
```

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行服务
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest tests/ -v
```

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/learning-records` | POST | 创建学习记录 |
| `/api/learning-records` | GET | 查询学习记录 |
| `/api/search` | POST | 知识库检索 |
| `/api/recommend` | POST | 获取推荐 |
| `/health` | GET | 健康检查 |

---

## 验收标准 (M1)

| 功能 | 指标 | 状态 |
|------|------|------|
| 学习记录生成 | <5 分钟 | ⏳ 开发中 |
| 知识库检索 | <10 秒，≥3 条相关结果 | ⏳ 开发中 |
| 检索相关性 | >80% | ⏳ 开发中 |

---

**开发团队**: DevOps Engineer (刘运维) + 全员  
**GitHub**: https://github.com/lifanli/learning_proj
