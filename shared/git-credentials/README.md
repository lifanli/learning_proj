# Git 版本管理配置记录

**配置时间**: 2026-03-07 05:25 UTC  
**配置人**: 林小雅（项目总监）  
**仓库地址**: https://github.com/lifanli/learning_proj.git

---

## Git 配置

### 凭证存储
- **位置**: `/root/hiclaw-fs/shared/git-credentials/`
- **权限**: 600 (仅所有者可读写)
- **配置方式**: Git credential store

### Git 用户信息
- **用户名**: 林小雅 | 项目总监
- **邮箱**: project-director@hiclaw.local

### 远程仓库
- **名称**: origin
- **URL**: https://github.com/lifanli/learning_proj.git

---

## 版本管理策略

### 分支策略

```
main (主分支，保护)
  ├── develop (开发分支)
  │     ├── feature/frontend (前端功能)
  │     ├── feature/backend (后端功能)
  │     └── feature/research (调研报告)
  └── release/v1.0 (发布分支)
```

### 提交规范

```
<类型>(<范围>): <描述>

[可选的正文]

[可选的脚注]
```

**类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例**:
```
feat(frontend): 添加登录页面组件

- 实现用户名/密码输入框
- 添加表单验证
- 集成后端 API

Closes #12
```

### 上传内容

**需要上传**:
- ✅ 项目文档 (`shared/projects/`)
- ✅ 技术调研报告 (`shared/knowledge/search-results/`)
- ✅ 团队配置 (`agents/*/`)
- ✅ 最终方案 (`final-plan.md`)

**不上传**:
- ❌ 凭证文件 (`.git-credentials`)
- ❌ 本地缓存 (`.cache/`)
- ❌ 大型二进制文件

---

## 工作流程

### 日常提交

1. **Worker 完成工作** → 提交到共享目录
2. **项目总监审查** → 合并到 `develop` 分支
3. **里程碑完成** → 合并到 `main` 分支，打 tag

### 推送频率

- **小改动**: 每日推送
- **大功能**: 完成后立即推送
- **里程碑**: 必须推送

---

## 安全注意事项

1. **Token 保护**:
   - 凭证文件权限 600
   - 不提交到 Git
   - 不在聊天中显示完整 token

2. **敏感信息**:
   - 检查提交内容，不包含密码/密钥
   - 使用 `.gitignore` 排除敏感文件

3. **访问控制**:
   - 仅项目成员有仓库访问权限
   - 定期审查访问列表

---

## 下一步

1. 创建 `.gitignore` 文件
2. 初次提交现有文件
3. 推送到 GitHub
4. 建立定期同步机制

---

**配置人**: 林小雅  
**状态**: 配置完成，等待初次提交
