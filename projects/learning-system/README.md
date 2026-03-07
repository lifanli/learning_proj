# 学习智能体系统

**版本**: 0.1.0  
**状态**: 开发中  
**M1 目标**: 2026-03-10 完成

---

## 项目结构

```
learning-system/
├── src/
│   ├── learning-generator/     # 学习记录生成器
│   ├── knowledge-base/         # 知识库管理
│   ├── recommendation/         # 智能推荐引擎
│   └── worker-interface/       # Worker 工作台
├── tests/                      # 测试用例
├── pyproject.toml              # 项目配置
└── README.md                   # 本文件
```

---

## 核心功能

### M1 (2026-03-10)
- [x] 学习记录生成器
- [ ] 知识库基础功能
- [ ] 向量数据库集成

### M2 (2026-03-21)
- [ ] 智能推荐引擎
- [ ] Search Worker 集成

### M3 (2026-04-04)
- [ ] Worker 工作台
- [ ] Challenger 集成

---

## 快速开始

```bash
# 安装依赖
pip install -e .

# 运行服务
uvicorn src.main:app --reload

# 运行测试
pytest tests/
```

---

## 验收标准

| 功能 | 指标 |
|------|------|
| 学习记录生成 | <5 分钟 |
| 知识库检索 | <10 秒，≥3 条相关结果 |
| 检索相关性 | >80% |
| 推荐准确率 | >70% |

---

**开发团队**: Learning Agent System Team  
**GitHub**: https://github.com/lifanli/learning_proj.git
