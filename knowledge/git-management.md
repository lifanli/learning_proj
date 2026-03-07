# Git 版本控制管理

## 仓库信息

**仓库地址**: (待 Manager 配置)
**主分支**: `main`
**工作分支**: `develop` + 各功能分支

## 提交规范

### 分支命名
- `main` - 主分支，稳定版本
- `develop` - 开发分支，日常开发
- `feature/{name}` - 功能分支
- `fix/{name}` - 修复分支
- `docs/{name}` - 文档分支

### Commit Message 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**:
- `feat` - 新功能
- `fix` - Bug 修复
- `docs` - 文档更新
- `style` - 代码格式
- `refactor` - 重构
- `test` - 测试
- `chore` - 构建/工具

**示例**:
```
feat(arch): 学习智能体系统架构设计

- 完成 5 层架构设计
- 定义核心模块
- 技术栈选型

Closes #1
```

## 提交流程

```
1. Worker 完成工作
       ↓
2. 本地保存文件
       ↓
3. @manager 发送 git-request
       ↓
4. Manager 执行 git add/commit/push
       ↓
5. 同步到 MinIO 备份
```

## 目录结构

```
hiclaw-learning-agent/
├── docs/                    # 文档
│   ├── architecture.md      # 架构设计
│   ├── roles.md             # 角色定义
│   └── decisions.md         # 技术决策
├── src/                     # 源代码
│   ├── memory/              # 记忆管理模块
│   ├── learning/            # 学习引擎
│   ├── skills/              # 技能管理
│   ├── reflection/          # 反思系统
│   └── collaboration/       # 多智能体协作
├── config/                  # 配置文件
├── tests/                   # 测试
└── README.md
```

## 备份策略

| 类型 | 频率 | 位置 |
|------|------|------|
| Git 提交 | 每次 commit | GitHub/GitLab |
| MinIO 同步 | 实时/每日 | hiclaw-storage |
| 本地备份 | 每日 | 各 Worker 本地 |

---

**本文件由 Project Director 维护**
