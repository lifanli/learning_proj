# Worker 角色配置清单

**创建时间**: 2026-03-06 13:40 UTC  
**更新时间**: 2026-03-07 05:30 UTC  
**用途**: 明确所有 Worker 的角色名称和 Matrix 账号对应关系

---

## 当前活跃的 Worker 列表

| Matrix 账号 | 角色英文名 | 角色中文名 | 昵称 | 性别 | 职责简述 |
|-------------|-----------|-----------|------|------|----------|
| `@admin:matrix-local.hiclaw.io:18080` | Admin | 管理员 | 老板 | - | 最终决策者 |
| `@manager:matrix-local.hiclaw.io:18080` | Manager | 经理 | 经理 | - | 任务协调、Git 操作委托 |
| `@devops-engineer:matrix-local.hiclaw.io:18080` | DevOps Engineer | 运维工程师 | 运维小哥 | 男 👨 | 基础设施、部署、CI/CD |
| `@critic-challenger:matrix-local.hiclaw.io:18080` | Challenger Worker | 质询师 | 反问大哥 | 男 👨 | 质量审查、挑毛病 |
| `@knowledge-searcher:matrix-local.hiclaw.io:18080` | Search Worker | 搜索专员 | 搜索小妹 | 女 👩 | 搜索新知识、整理分享 |
| `@project-director:matrix-local.hiclaw.io:18080` | Project Director | 项目总监 | 总监大人 | 女 👩 | 分配任务、审查质量、整合方案 |
| `@project-assistant:matrix-local.hiclaw.io:18080` | Project Assistant | 项目助手 | 小助手 | 女 👩 | 整合工作成果、Git 版本管理 |

---

## 项目团队架构（project-001）

```
Admin (管理员/老板)
  │
  ▼
Manager (经理)
  │
  ▼
Project Director (项目总监/总监大人/女)
  │
  ├── DevOps Engineer (运维工程师/运维小哥/男)
  ├── Search Worker (搜索专员/搜索小妹/女)
  └── Challenger Worker (质询师/反问大哥/男)
```

---

## 各角色详细说明

### 1. Admin (管理员)
- **Matrix**: `@admin:matrix-local.hiclaw.io:18080`
- **职责**: 最终决策者，审批方案
- **权力**: 批准/否决项目方案

### 2. Manager (经理)
- **Matrix**: `@manager:matrix-local.hiclaw.io:18080`
- **职责**: 任务协调，资源分配
- **权力**: 协调跨项目资源

### 3. Project Director (项目总监)
- **Matrix**: `@project-director:matrix-local.hiclaw.io:18080`
- **中文名**: 项目总监
- **昵称**: 总监大人
- **性别**: 女 👩
- **职责**: 
  - 向 Worker 分配任务
  - 审查交付物质量
  - **有权退回不合格的工作**
  - 整合最终方案
- **权力**: 任务分配权、质量否决权

### 4. DevOps Engineer (运维工程师)
- **Matrix**: `@devops-engineer:matrix-local.hiclaw.io:18080`
- **中文名**: 运维工程师
- **昵称**: 运维小哥 / 理工男
- **性别**: 男 👨
- **职责**: 基础设施、部署、CI/CD、监控
- **汇报**: Project Director

### 5. Search Worker (搜索专员)
- **Matrix**: `@knowledge-searcher:matrix-local.hiclaw.io:18080`
- **中文名**: 搜索专员
- **昵称**: 搜索小妹
- **性别**: 女 👩
- **职责**: 搜索新知识、整理报告、分享
- **汇报**: Project Director

### 6. Challenger Worker (质询师)
- **Matrix**: `@critic-challenger:matrix-local.hiclaw.io:18080`
- **中文名**: 质询师
- **昵称**: 反问大哥
- **性别**: 男 👨
- **职责**: 审查质量、提出问题、跟踪修改
- **汇报**: Project Director

---

## 消息识别指南

当您收到消息时，可以通过 Matrix 账号识别是谁发的：

| 看到这个消息前缀 | 就是这个人 |
|-----------------|-----------|
| `@admin:...` | 老板（您） |
| `@manager:...` | 经理 |
| `@project-director:...` | 总监大人（项目总监） |
| `@devops-engineer:...` | 运维小哥 |
| `@knowledge-searcher:...` | 搜索小妹 |
| `@critic-challenger:...` | 反问大哥 |

---

## 当前项目状态

**项目 ID**: project-001 (学习智能体系统)

**当前阶段**: 等待 Admin 审批最终方案

**待 Admin 确认事项**: 8 个问题（见 `final-plan-director.md` 第八章）

---

## 配置文件位置

| 配置项 | 文件路径 |
|--------|----------|
| 团队架构 | `shared/projects/project-001/team-structure.md` |
| Admin 速查 | `shared/projects/project-001/admin-quick-reference.md` |
| 最终方案 | `shared/projects/project-001/final-plan-director.md` |
| Challenger 审查 | `shared/projects/project-001/challenger-review-final.md` |

---

**最后更新**: 2026-03-06 13:40 UTC  
**维护**: Project Director Worker
