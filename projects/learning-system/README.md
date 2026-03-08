# 学习智能体系统

一个能够自主学习、持续进化的智能体系统。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行核心系统
python main.py

# 运行 API 服务
python -m src.api

# 运行 Web 界面
python -m src.web

# 运行测试 (测试 Worker)
python run_tests.py
```

## 项目结构

```
learning-system/
├── src/
│   ├── core/           # 核心框架
│   │   ├── agent.py    # 智能体基类
│   │   ├── memory.py   # 记忆管理
│   │   └── vector_db.py # 向量数据库
│   ├── skills/         # 技能模块
│   │   ├── skill_manager.py
│   │   └── builtin/    # 内置技能
│   ├── learning/       # 学习引擎
│   │   ├── reflection.py
│   │   └── optimizer.py
│   ├── workers.py      # Worker 实现
│   ├── api.py          # REST API
│   └── web.py          # Web 界面
├── tests/              # 测试
├── main.py             # 主入口
├── requirements.txt    # 依赖
└── README.md           # 说明
```

## 核心功能

- **记忆管理**: 短期/长期记忆、记忆巩固、遗忘机制
- **技能管理**: 技能注册、发现、调用、组合
- **学习引擎**: 任务反思、经验提取、策略优化
- **Worker 系统**: 多角色智能体协作
- **REST API**: 完整的 API 接口
- **Web 界面**: 简单的 Web 操作界面

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/worker/create` | POST | 创建 Worker |
| `/api/v1/worker/<name>/execute` | POST | 执行任务 |
| `/api/v1/memory/add` | POST | 添加记忆 |
| `/api/v1/memory/search` | GET | 搜索记忆 |
| `/api/v1/skill/list` | GET | 列出技能 |
| `/api/v1/skill/execute` | POST | 执行技能 |
| `/api/v1/vector/insert` | POST | 插入向量 |
| `/api/v1/vector/search` | POST | 搜索向量 |
| `/api/v1/status` | GET | 系统状态 |

## 开发状态

- [x] 项目骨架
- [x] 核心框架
- [x] 技能管理
- [x] 学习引擎
- [x] Worker 实现
- [x] API 接口
- [x] Web 界面
- [x] 单元测试
- [ ] 向量数据库集成 (Weaviate/Chroma)
- [ ] 前端界面完善
- [ ] 部署配置

## License

MIT
