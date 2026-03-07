# 学习智能体系统 - 前端

## 技术栈

- **框架**: Vue 3.4+ + TypeScript
- **构建工具**: Vite 5.0+
- **UI 框架**: Element Plus 2.4+
- **状态管理**: Pinia 2.1+
- **路由**: Vue Router 4.2+
- **HTTP**: Axios 1.6+

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问：http://localhost:5173

### 3. 构建生产版本

```bash
npm run build
```

## 项目结构

```
frontend/
├── src/
│   ├── components/    # 可复用组件
│   ├── views/         # 页面视图
│   ├── router/        # 路由配置
│   ├── store/         # 状态管理
│   ├── assets/        # 静态资源
│   ├── App.vue        # 根组件
│   └── main.ts        # 应用入口
├── public/
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## 页面

- **登录页** (`/login`) - 用户登录
- **仪表盘** (`/dashboard`) - 学习进度概览
- **课程页** (`/course/:id`) - 课程详情
- **对话页** (`/chat`) - 与智能体对话

## 开发规范

### 代码风格
- 使用 TypeScript
- 组件使用 `<script setup>` 语法
- 遵循 Vue 3 最佳实践

### 提交规范
```
feat: 新功能
fix: Bug 修复
docs: 文档更新
style: 代码格式
refactor: 重构
```

## 负责人

**陈明轩 | 前端工程师**
