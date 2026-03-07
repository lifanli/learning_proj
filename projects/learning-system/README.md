# 学习智能体系统

一个能够自主学习、持续进化的智能体系统。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

## 项目结构

```
learning-system/
├── src/
│   ├── core/           # 核心框架
│   │   ├── agent.py    # 智能体基类
│   │   └── memory.py   # 记忆管理
│   ├── skills/         # 技能模块
│   │   ├── skill_manager.py
│   │   └── builtin/    # 内置技能
│   └── learning/       # 学习引擎
│       ├── reflection.py
│       └── optimizer.py
├── tests/              # 测试
├── docs/               # 文档
└── main.py            # 主入口
```

## 核心功能

- **记忆管理**: 短期/长期记忆、记忆巩固、遗忘机制
- **技能管理**: 技能注册、发现、调用、组合
- **学习引擎**: 任务反思、经验提取、策略优化

## 开发状态

- [x] 项目骨架
- [x] 核心框架
- [x] 技能管理
- [x] 学习引擎
- [ ] 向量数据库集成
- [ ] 前端界面
- [ ] API 接口

## License

MIT
